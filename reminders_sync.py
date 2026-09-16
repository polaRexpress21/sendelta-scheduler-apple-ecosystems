"""把课表同步到 macOS「提醒事项」（Reminders），从而经由 iCloud 推送到 iPhone / Apple Watch。

为什么用提醒事项：
  - 日历事件虽然也能带“显示闹钟”，但在部分手表/系统版本上不保证准时弹通知；
  - 提醒事项的“到期提醒”是系统级通知，到点一定弹，且会同步到 Apple Watch 表盘。
  - 每条课建一个提醒：标题=「科目 · 地点」，到期时间=上课时间，
    并在「上课前 N 分钟」设一个触发提醒，确保抬腕就能看到。

权限事实（踩坑结论）：
  - 首次运行会弹“终端/Python 访问提醒事项”的授权框，必须点「允许」。
    若错过：系统设置 → 隐私与安全性 → 自动化 → 勾选「终端/Python」访问「提醒事项」。
  - 日期用『分量赋值』构造，避免中文本地化导致 AppleScript date 解析失败。
"""
import subprocess
import tempfile
from pathlib import Path


def _esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def build_applescript(events, list_name, lead_minutes):
    """events: list of dict{year,month,day,start_h,start_m,end_h,end_m,subject,location,title}"""
    L = []
    L.append('tell application "Reminders"')
    L.append(f'  set listName to "{_esc(list_name)}"')
    # 若已存在多个同名列表则报错，避免写错
    L.append('  set dupCount to count of (every list whose name is listName)')
    L.append('  if dupCount > 1 then')
    L.append('    error "发现多个名为「%s」的提醒列表。请在「提醒事项」里删除多余的，只留一个。"' % _esc(list_name))
    L.append('  end if')
    L.append('  if exists list listName then')
    L.append('    set targetList to list listName')
    L.append('  else')
    L.append('    set targetList to (make new list with properties {name:listName})')
    L.append('  end if')
    # 清空该列表里旧的课表提醒，避免每周堆积重复
    L.append('  delete (every reminder of targetList)')
    for ev in events:
        L.append('  set startDate to current date')
        L.append(f'    set year of startDate to {ev["year"]}')
        L.append(f'    set month of startDate to {ev["month"]}')
        L.append(f'    set day of startDate to {ev["day"]}')
        L.append(f'    set hours of startDate to {ev["start_h"]}')
        L.append(f'    set minutes of startDate to {ev["start_m"]}')
        L.append('    set seconds of startDate to 0')
        L.append('  set newRem to make new reminder at targetList with properties {name:"%s", due date:startDate%s}'
                 % (_esc(ev.get("title", ev.get("subject", "（未命名）"))),
                    (', body:"%s"' % _esc(ev["note"])) if ev.get("note") else ""))
        L.append('  tell newRem')
        # 上课前 N 分钟触发；Reminders 的 alarm 用“触发日期”= 上课时间 - N*分钟
        L.append(f'    make new alarm at end with properties {{trigger date:(startDate - ({int(lead_minutes)} * minutes))}}')
        L.append('  end tell')
    L.append('  return (count of reminders of targetList)')
    L.append('end tell')
    return "\n".join(L)


def _run_osascript(src: str) -> str:
    """写临时文件并执行 osascript，返回 stdout；权限/执行错误抛 RuntimeError。"""
    with tempfile.NamedTemporaryFile("w", suffix=".applescript", delete=False, encoding="utf-8") as f:
        f.write(src)
        path = f.name
    try:
        res = subprocess.run(["osascript", path], capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        Path(path).unlink(missing_ok=True)
        raise RuntimeError(
            "等待“提醒事项”授权超时（约 3 分钟未响应）。\n"
            "请确认 macOS 弹出的“终端/Python 访问提醒事项”对话框已点「允许」，然后重新运行。"
        )
    finally:
        Path(path).unlink(missing_ok=True)
    if res.returncode != 0:
        err = (res.stderr or res.stdout).strip()
        if "-10004" in err or "权限" in err or "not authorized" in err.lower() or "automation" in err.lower():
            raise RuntimeError(
                "macOS 拒绝了“提醒事项”访问权限。请这样授权：\n"
                "  1) 首次运行弹窗要点「允许」；若已错过：\n"
                "  2) 系统设置 → 隐私与安全性 → 自动化 → 勾选「终端 / Python」访问「提醒事项」。\n"
                "授权后重新运行本程序即可。"
            )
        raise RuntimeError(f"AppleScript 执行失败: {err}")
    return res.stdout.strip()


def push_to_reminders(events, list_name, lead_minutes):
    if not events:
        return {"pushed": 0, "note": "没有可同步的课表提醒（本周课表为空或已全部过期）"}
    script = build_applescript(events, list_name, lead_minutes)
    try:
        out = _run_osascript(script)
    except RuntimeError as e:
        return {"pushed": 0, "error": str(e)}
    try:
        count = int(out)
    except ValueError:
        count = len(events)
    note = (
        "已写入「%s」提醒列表（提醒数 %d）。\n"
        "⚠️ 请确认该列表会同步到 iCloud（默认“提醒事项”列表即 iCloud 同步）；\n"
        "  若它在「我的 Mac / On My Mac」分组，则不会同步到手机/手表。\n"
        "  手表上：课表当天会按“上课前 %d 分钟”弹出通知。"
    ) % (list_name, count, int(lead_minutes))
    return {"pushed": count, "note": note}


def clear_reminders(list_name):
    """清空专用提醒列表（调试/重置用）。"""
    script = (
        'tell application "Reminders"\n'
        f'  if exists list "{_esc(list_name)}" then\n'
        f'    delete (every reminder of list "{_esc(list_name)}")\n'
        '  end if\n'
        'end tell\n'
    )
    _run_osascript(script)


def purge_past_reminders(list_name="课表"):
    """删除已过期（到期时间早于现在）的课表提醒，返回 (删除数, 剩余数)。"""
    script = (
        'tell application "Reminders"\n'
        f'  set listName to "{_esc(list_name)}"\n'
        '  if exists list listName then\n'
        '    set targetList to list listName\n'
        '    set nowDate to current date\n'
        '    set oldRems to (every reminder of targetList whose due date < nowDate)\n'
        '    set n to count of oldRems\n'
        '    if n > 0 then delete oldRems\n'
        '    return (n as string) & "," & ((count of every reminder of targetList) as string)\n'
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


def list_reminders():
    """诊断用：列出所有提醒列表名称。"""
    script = (
        'tell application "Reminders"\n'
        '  set out to ""\n'
        '  repeat with l in every list\n'
        '    set out to out & (name of l) & "\n"\n'
        '  end repeat\n'
        '  return out\n'
        'end tell\n'
    )
    try:
        return _run_osascript(script)
    except RuntimeError as e:
        return f"[无法列出提醒列表] {e}"
