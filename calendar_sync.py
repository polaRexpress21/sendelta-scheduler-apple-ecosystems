"""把课表同步到 macOS「日历」（Calendar），从而经由 iCloud 推送到 iPhone / Apple Watch。

关键事实（踩坑结论）：
  - macOS 新版「日历」的 AppleScript 字典里 **根本没有 account 类**，无法通过
    AppleScript 指定“建在 iCloud 账户下”。`make new calendar` 只会落在
    「系统设置 → 日历 → 默认日历账户」所指向的账户。
  - 因此要让手表/手机收到，必须保证该日历落在 iCloud 上，二选一：
      方案 A（推荐）：系统设置 → 日历 → 默认日历账户 设为「iCloud」，再运行本程序，
                      “课表”日历会自动建在 iCloud 下并同步。
      方案 B：手动在「日历」App 里、iCloud 分组下新建一个名为“课表”的日历，
              本程序检测到已存在就直接往里写事件（同样会同步）。
  - 首次运行会弹“终端/Python 访问日历”的授权框，必须点「允许」。
    若错过：系统设置 → 隐私与安全性 → 自动化 → 勾选「终端/Python」访问「日历」。
  - 日期用『分量赋值』构造，避免中文本地化导致 AppleScript date 解析失败。
  - 每次运行会先清空“课表”日历里的旧事件，再写入本周，避免每周堆积重复。
"""
import subprocess
import tempfile
from pathlib import Path


def _esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def build_applescript(events, calendar_name, lead_minutes):
    """events: list of dict{year,month,day,start_h,start_m,end_h,end_m,subject,location}"""
    L = []
    L.append('tell application "Calendar"')
    L.append(f'  set calName to "{_esc(calendar_name)}"')
    # 防重复护栏：若存在多个同名日历（本地+iCloud 各一），写错账户会导致手机收不到
    L.append('  set dupCount to count of (every calendar whose name is calName)')
    L.append('  if dupCount > 1 then')
    L.append('    error "发现多个名为「%s」的日历（本地与 iCloud 可能各一个）。请先在 Mac「日历」里把名为「%s」的日历全部删除，确保只剩一个，再重跑 --push。"'
             % (_esc(calendar_name), _esc(calendar_name)))
    L.append('  end if')
    L.append('  set targetCal to missing value')
    L.append('  if exists calendar calName then')
    L.append('    set targetCal to calendar calName')
    L.append('  else')
    # 落点由“默认日历账户”决定；若默认是 iCloud，则自动在 iCloud 下创建
    L.append('    set targetCal to (make new calendar with properties {name:calName})')
    L.append('  end if')
    # 清空旧事件，避免每周重复堆积
    L.append('  delete (every event of targetCal)')
    for ev in events:
        L.append('  tell targetCal')
        L.append('    set startDate to current date')
        L.append(f'    set year of startDate to {ev["year"]}')
        L.append(f'    set month of startDate to {ev["month"]}')
        L.append(f'    set day of startDate to {ev["day"]}')
        L.append(f'    set hours of startDate to {ev["start_h"]}')
        L.append(f'    set minutes of startDate to {ev["start_m"]}')
        L.append('    set seconds of startDate to 0')
        L.append('    set endDate to current date')
        L.append(f'    set year of endDate to {ev["year"]}')
        L.append(f'    set month of endDate to {ev["month"]}')
        L.append(f'    set day of endDate to {ev["day"]}')
        L.append(f'    set hours of endDate to {ev["end_h"]}')
        L.append(f'    set minutes of endDate to {ev["end_m"]}')
        L.append('    set seconds of endDate to 0')
        L.append('    set newEv to make new event with properties {summary:"%s", start date:startDate, end date:endDate%s}'
                 % (_esc(ev.get("title") or ev.get("subject") or "（未命名）"),
                    (', description:"%s"' % _esc(ev["note"])) if ev.get("note") else ""))
        L.append('    tell newEv')
        L.append(f'      make new display alarm at end with properties {{trigger interval:-{int(lead_minutes)}}}')
        L.append('    end tell')
        L.append('  end tell')
    L.append('  return (count of events of targetCal)')
    L.append('end tell')
    return "\n".join(L)


def _run_osascript(src: str) -> str:
    """写临时文件并执行 osascript，返回 stdout。权限/执行错误抛 RuntimeError。"""
    with tempfile.NamedTemporaryFile("w", suffix=".applescript", delete=False, encoding="utf-8") as f:
        f.write(src)
        path = f.name
    try:
        res = subprocess.run(["osascript", path], capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        Path(path).unlink(missing_ok=True)
        raise RuntimeError(
            "等待“日历”授权超时（约 3 分钟未响应）。\n"
            "请确认 macOS 弹出的“终端/Python 访问日历”对话框已点「允许」，然后重新运行。"
        )
    finally:
        Path(path).unlink(missing_ok=True)
    if res.returncode != 0:
        err = (res.stderr or res.stdout).strip()
        if "-10004" in err or "权限" in err or "not authorized" in err.lower() or "automation" in err.lower():
            raise RuntimeError(
                "macOS 拒绝了“日历”访问权限。请这样授权：\n"
                "  1) 首次运行弹窗要点「允许」；若已错过：\n"
                "  2) 系统设置 → 隐私与安全性 → 自动化 → 勾选「终端 / Python」访问「日历」。\n"
                "授权后重新运行本程序即可。"
            )
        raise RuntimeError(f"AppleScript 执行失败: {err}")
    return res.stdout.strip()


def push_to_calendar(events, calendar_name, lead_minutes):
    if not events:
        return {"pushed": 0, "note": "没有可同步的课表事件（本周课表为空或已全部过期）"}
    script = build_applescript(events, calendar_name, lead_minutes)
    try:
        out = _run_osascript(script)
    except RuntimeError as e:
        return {"pushed": 0, "error": str(e)}
    try:
        count = int(out)
    except ValueError:
        count = len(events)
    note = (
        "已写入“%s”日历（事件数 %d）。\n"
        "⚠️ 请确认该日历在「日历」App 左侧栏的「iCloud」分组下；"
        "若它在「我的 Mac / On My Mac」分组，则不会同步到手机/手表。\n"
        "  修复：系统设置 → 日历 → 默认日历账户 改为「iCloud」，删掉旧“课表”后重跑；"
        "或在 iCloud 分组下手动新建“课表”后重跑。"
    ) % (calendar_name, count)
    return {"pushed": count, "note": note}


def clear_calendar(calendar_name):
    """仅清空专用日历（调试/重置用）。"""
    script = (
        'tell application "Calendar"\n'
        f'  if exists calendar "{_esc(calendar_name)}" then\n'
        f'    delete (every event of calendar "{_esc(calendar_name)}")\n'
        '  end if\n'
        'end tell\n'
    )
    _run_osascript(script)


def purge_past_events(calendar_name="课表"):
    """删除“课表”日历里已经结束的过期课程，返回 (删除数, 剩余数)。"""
    script = (
        'tell application "Calendar"\n'
        f'  set calName to "{_esc(calendar_name)}"\n'
        '  if exists calendar calName then\n'
        '    set targetCal to calendar calName\n'
        '    set nowDate to current date\n'
        '    set oldEvents to (every event of targetCal whose end date < nowDate)\n'
        '    set n to count of oldEvents\n'
        '    if n > 0 then delete oldEvents\n'
        '    return (n as string) & "," & ((count of every event of targetCal) as string)\n'
        '  else\n'
        '    return "-1,-1"\n'
        '  end if\n'
        'end tell\n'
    )
    out = _run_osascript(script)
    try:
        removed, remain = out.split(",")
        return int(removed), int(remain)
    except ValueError:
        return 0, 0


def list_calendars():
    """诊断用：列出所有日历名称（需要日历权限）。返回文本，失败时返回错误提示。"""
    script = (
        'tell application "Calendar"\n'
        '  set out to ""\n'
        '  repeat with c in every calendar\n'
        '    set out to out & (name of c) & "\n"\n'
        '  end repeat\n'
        '  return out\n'
        'end tell\n'
    )
    try:
        return _run_osascript(script)
    except RuntimeError as e:
        return f"[无法列出日历] {e}"
