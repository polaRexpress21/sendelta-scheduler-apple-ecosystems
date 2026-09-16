"""课程备注存储：支持两种范围
  1) 科目备注(subject_notes)：对该科目「所有」课生效（如「数学：记得带计算器」）
  2) 指定某节课备注(session_notes)：按「日期|开始时间|科目」精确定位某一节课
     （如「2026-09-15 08:00 数学：今天月考」）

备注会随课表同步写进「日历 / 提醒事项」的备注字段；事件标题仍保持简洁的
「科目 · 地点」，保证 Apple Watch 小屏一眼看清时间地点。
"""
import json
from pathlib import Path
from config import DATA_DIR

NOTES_PATH = DATA_DIR / "notes.json"
DEFAULT_NOTES = {"subject_notes": {}, "session_notes": {}}


def load_notes():
    if not NOTES_PATH.exists():
        return dict(DEFAULT_NOTES)
    try:
        d = json.loads(NOTES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_NOTES)
    d.setdefault("subject_notes", {})
    d.setdefault("session_notes", {})
    # 清理空值，避免越积越多
    d["subject_notes"] = {k: v for k, v in d["subject_notes"].items() if v and v.strip()}
    d["session_notes"] = {k: v for k, v in d["session_notes"].items() if v and v.strip()}
    return d


def save_notes(notes):
    notes.setdefault("subject_notes", {})
    notes.setdefault("session_notes", {})
    NOTES_PATH.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")


def session_key(ev):
    """从单节课事件生成稳定 key：日期|开始时间|科目。"""
    return (f"{int(ev['year'])}-{int(ev['month']):02d}-{int(ev['day']):02d}"
            f"|{int(ev['start_h']):02d}:{int(ev['start_m']):02d}|{ev.get('subject', '')}")


def set_subject_note(subject, text):
    """设置/删除某科目的统一备注；text 为空则删除。"""
    subject = (subject or "").strip()
    if not subject:
        return
    notes = load_notes()
    if text and text.strip():
        notes["subject_notes"][subject] = text.strip()
    else:
        notes["subject_notes"].pop(subject, None)
    save_notes(notes)


def set_session_note(key, text):
    """设置/删除某节课的专属备注；text 为空则删除。"""
    if not key:
        return
    notes = load_notes()
    if text and text.strip():
        notes["session_notes"][key] = text.strip()
    else:
        notes["session_notes"].pop(key, None)
    save_notes(notes)


def note_for_event(ev):
    """返回 (科目备注, 本节课专属备注)，供界面展示。"""
    notes = load_notes()
    subj = ev.get("subject", "")
    s_note = notes["subject_notes"].get(subj, "")
    sess_note = notes["session_notes"].get(session_key(ev), "")
    return s_note, sess_note


def combined_note(ev):
    """写进日历/提醒的备注正文：优先本节课专属备注，否则用科目备注。"""
    s_note, sess_note = note_for_event(ev)
    if sess_note:
        return sess_note
    if s_note:
        return s_note
    return ""


def subjects_in_schedule():
    """从 schedule.json 取出本周出现过的科目名（去重、保序），供科目备注面板用。"""
    p = DATA_DIR / "schedule.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    events = data.get("classes") or data.get("events") or []
    seen = []
    for ev in events:
        s = (ev.get("subject") or "").strip()
        if s and s not in seen:
            seen.append(s)
    return seen
