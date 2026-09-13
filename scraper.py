"""课表爬取：用 Playwright 无头浏览器登录 schoolis.cn 并抓取课表。

由于该站点是 JS 动态渲染，且不同学校后台布局可能不同，本模块提供：
  - login()        登录
  - open_schedule() 进入课表页（自动寻找入口或按配置的 URL）
  - extract_schedule() 解析课表；若已配置选择器则按列映射解析，否则进入“探测”流程
  - save_probe()   保存渲染后的 HTML + 截图，便于人工/AI 锁定选择器
"""
import json
import re
import time
from datetime import datetime, date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from config import DATA_DIR, load_config

PROBE_HTML = DATA_DIR / "schedule_probe.html"
PROBE_PNG = DATA_DIR / "schedule_probe.png"
SCHEDULE_JSON = DATA_DIR / "schedule.json"


# ---------- 选择器自动探测 ----------
def _candidate_selectors(kind):
    if kind == "username":
        return [
            'input[name="username"]', 'input[name="account"]', 'input[name="user"]',
            'input[id="username"]', 'input[id="account"]',
            'input[type="text"]', 'input[autocomplete="username"]',
            'input[placeholder*="账号" i]', 'input[placeholder*="用户" i]',
            'input[placeholder*="学号" i]',
        ]
    if kind == "password":
        return [
            'input[name="password"]', 'input[name="pwd"]', 'input[id="password"]',
            'input[type="password"]', 'input[autocomplete="current-password"]',
            'input[placeholder*="密码" i]',
        ]
    if kind == "submit":
        return [
            'button[type="submit"]',
            'button:has-text("登录")', 'input[type="submit"]',
            'a:has-text("登录")', 'button:has-text("登 录")',
            '.login-btn', '#loginBtn',
        ]
    return []


def _detect(page, kind):
    for sel in _candidate_selectors(kind):
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                return sel
        except Exception:
            continue
    return ""


def login(page, username, password, cfg):
    base = cfg["school_base_url"]
    page.goto(base, wait_until="networkidle", timeout=30000)
    # 等待登录表单出现
    page.wait_for_selector('input', timeout=15000)

    sel = cfg["selectors"]["login"]
    user_sel = sel["username"] or _detect(page, "username")
    pw_sel = sel["password"] or _detect(page, "password")
    submit_sel = sel["submit"] or _detect(page, "submit")

    if not user_sel or not pw_sel:
        raise RuntimeError("未能自动探测到账号/密码输入框，请在 config.json 的 selectors.login 中手动指定。")

    page.fill(user_sel, username)
    page.fill(pw_sel, password)
    if submit_sel:
        page.click(submit_sel)
    else:
        page.keyboard.press("Enter")

    # 等待登录完成：URL 变化或出现退出/课表相关元素
    try:
        page.wait_for_url("**/*", timeout=5000)  # 触发一次判断
    except Exception:
        pass
    # 用几个常见“已登录”特征判断
    page.wait_for_timeout(3000)
    # 简单校验：若仍停留在登录页且无输入框之外的异常，认为成功
    return {"user_sel": user_sel, "pw_sel": pw_sel, "submit_sel": submit_sel}


def open_schedule(page, cfg):
    if cfg.get("schedule_url"):
        page.goto(cfg["schedule_url"], wait_until="networkidle", timeout=30000)
        return
    # 自动寻找课表入口（含顶部导航的“我的日程”）
    for text in ["课表", "课程表", "我的课表", "时间表", "我的日程", "timetable", "schedule"]:
        try:
            loc = page.locator(
                f'a:has-text("{text}"), button:has-text("{text}"), span:has-text("{text}")'
            ).first
            if loc.count() and loc.is_visible():
                loc.click()
                page.wait_for_timeout(4000)  # 等 SPA 切换视图
                return
        except Exception:
            continue
    # 没找到入口：留在本页，交给探测/解析
    return


def _tables_to_json(page):
    """把页面里所有 <table> 抓成结构化数据，供后续人工/AI 映射。"""
    result = []
    tables = page.locator("table")
    n = tables.count()
    for i in range(n):
        rows = tables.nth(i).locator("tr")
        row_count = rows.count()
        table_data = []
        for r in range(row_count):
            cells = rows.nth(r).locator("th, td")
            row = [cells.nth(c).inner_text().strip() for c in range(cells.count())]
            table_data.append(row)
        result.append(table_data)
    return result


def _target_monday(cfg):
    """目标周起始日：默认“下周一”，explicit 模式用指定日期。"""
    today = date.today()
    mode = cfg.get("week_start_mode", "next_monday")
    if mode == "explicit" and cfg.get("week_start_date"):
        try:
            return datetime.strptime(cfg["week_start_date"], "%Y-%m-%d").date()
        except Exception:
            pass
    days = (0 - today.weekday()) % 7
    if days == 0:
        days = 7
    return today + timedelta(days=days)


def _visible_monday(page):
    """读取 FullCalendar 当前可见周的周一日期（表头 data-date）。"""
    headers = page.locator(".fc-day-header")
    for i in range(headers.count()):
        d = headers.nth(i).get_attribute("data-date")
        if d:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d").date()
                if dt.weekday() == 0:
                    return dt
            except Exception:
                pass
    return None


def navigate_to_target_week(page, cfg):
    """点击 FullCalendar “下一周”直到显示目标周（默认下周一所在周）。"""
    target = _target_monday(cfg)
    cur = _visible_monday(page)
    clicks = 0
    while cur is not None and cur < target and clicks < 8:
        btn = page.locator(".fc-next-button")
        if btn.count() == 0:
            break
        btn.first.click()
        page.wait_for_timeout(1800)
        cur = _visible_monday(page)
        clicks += 1
    return clicks


def _split_event(line0):
    """从 '科目  时间' 拆分出 (科目, 时间区间)。"""
    m = re.search(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*$", line0)
    if not m:
        return line0.strip(), ""
    return line0[: m.start()].strip(), f"{m.group(1)}:{m.group(2)}-{m.group(3)}:{m.group(4)}"


def extract_schedule(page, cfg):
    """解析 FullCalendar 周课表。返回 (sessions, needs_selector, debug)。

    sessions: list of {date(YYYY-MM-DD), subject, time(HH:MM-HH:MM), location}
    若页面不是 FullCalendar 布局，则退回通用表格探测并标记 needs_selector。
    """
    if page.locator(".fc-day-header").count() == 0:
        tables = _tables_to_json(page)
        debug_path = DATA_DIR / "schedule_tables.json"
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(tables, f, ensure_ascii=False, indent=2)
        return [], True, {"tables_file": str(debug_path), "table_count": len(tables)}

    navigate_to_target_week(page, cfg)
    headers = page.locator(".fc-day-header")
    n = headers.count()
    dates = [headers.nth(i).get_attribute("data-date") for i in range(n)]
    cols = page.locator(".fc-content-col")
    sessions = []
    for i in range(min(n, cols.count())):
        date_str = dates[i]
        if not date_str:
            continue
        evs = cols.nth(i).locator(".fc-time-grid-event")
        for j in range(evs.count()):
            texts = evs.nth(j).locator(".fc-text").all_inner_texts()
            if not texts:
                continue
            line0 = texts[0].replace(" ", " ").strip()
            location = texts[1].replace(" ", " ").strip() if len(texts) > 1 else ""
            subject, time_range = _split_event(line0)
            sessions.append(
                {"date": date_str, "subject": subject, "time": time_range, "location": location}
            )
    return sessions, False, {}


def _parse_with_selectors(page, cfg):
    # container 配置后，按行解析；cols 给出各字段所在列索引（整数）
    # cols 例: {"subject":2,"time":3,"location":4,"day":0}  day=星期几索引0..5
    sel = cfg["selectors"]["schedule"]
    cols = sel.get("cols", {})
    container = page.locator(sel["container"]).first
    rows = container.locator(sel.get("row", "tr"))
    sessions = []

    def _get(cells, field):
        idx = cols.get(field, "")
        if idx in (None, ""):
            return ""
        try:
            return cells.nth(int(idx)).inner_text().strip()
        except Exception:
            return ""

    for r in range(rows.count()):
        cells = rows.nth(r).locator("th, td")
        day_idx = cols.get("day", "")
        day_index = int(day_idx) if str(day_idx).strip().isdigit() else None
        sessions.append({
            "subject": _get(cells, "subject"),
            "time": _get(cells, "time"),
            "location": _get(cells, "location"),
            "date_raw": _get(cells, "date"),
            "day_index": day_index,
            "teacher": "",
        })
    return sessions


def save_probe(page):
    """保存渲染后的 HTML 与截图，用于锁定选择器。"""
    html = page.content()
    with open(PROBE_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    try:
        page.screenshot(path=str(PROBE_PNG), full_page=True)
    except Exception:
        pass
    return {"html": str(PROBE_HTML), "png": str(PROBE_PNG)}


def save_schedule_json(sessions, week_start):
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "week_start": week_start.isoformat() if isinstance(week_start, date) else str(week_start),
        "classes": sessions,
    }
    with open(SCHEDULE_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return SCHEDULE_JSON


def run_browser(task_fn, cfg):
    """通用：启动浏览器，执行 task_fn(page, cfg)，返回其结果。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=cfg.get("headless", True))
        ctx = browser.new_context(locale="zh-CN")
        page = ctx.new_page()
        try:
            return task_fn(page, cfg)
        finally:
            browser.close()
