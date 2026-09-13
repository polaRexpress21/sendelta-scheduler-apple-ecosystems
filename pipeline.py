"""编排流水线：登录 -> 抓课表 -> 解析 -> 存 JSON -> 推送到日历(Apple Watch)。

未配置精确选择器时，进入“探测”流程：保存页面 HTML/表格原文，返回 needs_selector，
由用户把探针产物发回，我们再锁定 config.json 里的 selectors。
"""
import json
import re
from datetime import date, datetime, timedelta, time

from config import load_config, DATA_DIR
from auth import get_credentials, has_credentials
from scraper import (
    run_browser, login, open_schedule, extract_schedule,
    save_probe, save_schedule_json,
)
from calendar_sync import push_to_calendar

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

LAST_SYNC_PATH = DATA_DIR / "last_sync.json"


def save_last_sync(pushed, note=""):
    """记录上次成功同步到日历的时间与节数（供网页展示“上次更新时间”）。"""
    info = {"pushed": int(pushed or 0),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "note": note or ""}
    try:
        LAST_SYNC_PATH.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def load_last_sync():
    if LAST_SYNC_PATH.exists():
        try:
            return json.loads(LAST_SYNC_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _next_monday(today: date) -> date:
    days_ahead = (0 - today.weekday()) % 7  # 0=Monday
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _resolve_week_start(cfg):
    mode = cfg.get("week_start_mode", "next_monday")
    today = date.today()
    if mode == "explicit" and cfg.get("week_start_date"):
        try:
            return datetime.strptime(cfg["week_start_date"], "%Y-%m-%d").date()
        except Exception:
            pass
    return _next_monday(today)


def _parse_time(t):
    if not t:
        return None
    m = re.search(r'(\d{1,2})[:：](\d{2})\s*[-~～到至]\s*(\d{1,2})[:：](\d{2})', t)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    m2 = re.search(r'(\d{1,2})[:：](\d{2})', t)
    if m2:
        sh, sm = int(m2.group(1)), int(m2.group(2))
        return sh, sm, sh, min(sm + 45, 59)
    return None


def _parse_date(raw, week_start):
    if not raw:
        return None
    raw = raw.strip()
    # 2026-09-14 / 09-14 / 9.14
    m = re.search(r'(20\d{2})[-/年.](\d{1,2})[-/月.](\d{1,2})', raw)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(\d{1,2})[-/月.](\d{1,2})', raw)
    if m:
        return date(week_start.year, int(m.group(1)), int(m.group(2)))
    # 周一..周日
    for i, w in enumerate(WEEKDAY_CN):
        if w in raw:
            return week_start + timedelta(days=i)
    return None


def _resolve_date(session, cfg, week_start):
    iso = session.get("date")
    if iso:
        try:
            return datetime.strptime(iso, "%Y-%m-%d").date()
        except Exception:
            pass
    d = _parse_date(session.get("date_raw"), week_start)
    if d:
        return d
    di = session.get("day_index")
    if isinstance(di, int):
        return week_start + timedelta(days=di)
    return None


def _build_events(sessions, cfg, week_start):
    events = []
    skipped = []
    now = datetime.now()
    for s in sessions:
        d = _resolve_date(s, cfg, week_start)
        t = _parse_time(s.get("time", ""))
        if not d or not t:
            skipped.append(s)
            continue
        sh, sm, eh, em = t
        # 丢弃已过去的课（防止手动在周中运行时把过去的也写进日历）
        if datetime.combine(d, time(sh, sm)) < now:
            skipped.append(s)
            continue
        # 跨午夜处理（极少）：结束小于开始则 +1 天
        end_date = d
        if (eh, em) < (sh, sm):
            end_date = d + timedelta(days=1)
        events.append({
            "year": d.year, "month": d.month, "day": d.day,
            "start_h": sh, "start_m": sm,
            "end_h": eh, "end_m": em,
            "subject": s.get("subject", "（未命名）"),
            "location": s.get("location", ""),
        })
    return events, skipped


def run_pipeline(probe: bool = False):
    if not has_credentials():
        return {"status": "no_credentials", "msg": "尚未配置账号，请先在网页首页登录。"}
    cfg = load_config()
    user, pw = get_credentials()

    def task(page, cfg):
        login(page, user, pw, cfg)
        open_schedule(page, cfg)
        if probe:
            probe_out = save_probe(page)
            # 解析并保存结构化课表，便于直接核对（无需再发原始 HTML）
            sessions, _, debug = extract_schedule(page, cfg)
            if sessions:
                ws = min(s["date"] for s in sessions)
                save_schedule_json(sessions, date.fromisoformat(ws))
            return {"probe": probe_out, "sessions": len(sessions),
                    "tables_file": debug.get("tables_file"),
                    "schedule_json": str(DATA_DIR / "schedule.json")}
        sessions, needs_selector, debug = extract_schedule(page, cfg)
        return {"sessions": sessions, "needs_selector": needs_selector, "debug": debug}

    try:
        out = run_browser(task, cfg)
    except Exception as e:
        return {"status": "error", "msg": f"浏览器任务失败：{e}"}

    if probe:
        p = out.get("probe", {})
        return {"status": "probe_saved", "html": p.get("html"), "png": p.get("png"),
                "sessions": out.get("sessions"),
                "schedule_json": out.get("schedule_json"),
                "msg": f"已保存页面 HTML 与截图，并解析出 {out.get('sessions', 0)} 节课。请核对 data/schedule.json。"}

    if out.get("needs_selector"):
        return {"status": "needs_selector",
                "msg": "尚未配置课表解析选择器。请运行探测模式并把 data/schedule_probe.html 与 data/schedule_tables.json 发回。",
                "tables_file": out["debug"].get("tables_file")}

    week_start = _resolve_week_start(cfg)
    events, skipped = _build_events(out["sessions"], cfg, week_start)
    save_schedule_json(events, week_start)
    result = push_to_calendar(events, cfg["calendar_name"], cfg["reminder_lead_minutes"])
    if result.get("pushed"):
        save_last_sync(result["pushed"], result.get("note", ""))
    return {"status": "ok", "week_start": week_start.isoformat(),
            "pushed": result.get("pushed"), "skipped": len(skipped),
            "schedule_json": str(DATA_DIR / "schedule.json"),
            "msg": result.get("error") or result.get("note", ""),
            "error": result.get("error")}


def push_existing_schedule():
    """直接把已抓取的 data/schedule.json 推送到日历（不重新登录/抓取）。
    用于：调试日历同步、或网站暂无更新时手动补推。"""
    cfg = load_config()
    p = DATA_DIR / "schedule.json"
    if not p.exists():
        return {"status": "no_schedule",
                "msg": "尚未抓取课表，请先运行 --run 或在网页点“运行同步”。"}
    data = json.loads(p.read_text(encoding="utf-8"))
    events = data.get("classes") or data.get("events") or []
    if not events:
        return {"status": "empty", "msg": "schedule.json 中没有课表事件。"}
    result = push_to_calendar(events, cfg["calendar_name"], cfg["reminder_lead_minutes"])
    if result.get("pushed"):
        save_last_sync(result["pushed"], result.get("note", ""))
    return {"status": "ok" if result.get("pushed") else "error",
            "pushed": result.get("pushed", 0),
            "msg": result.get("error") or result.get("note", ""),
            "error": result.get("error")}
