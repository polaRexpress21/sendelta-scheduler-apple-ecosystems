"""配置读写：config.json 保存在项目根目录。"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
DATA_DIR = BASE_DIR / "data"
if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "school_base_url": "https://sendeltastudent.schoolis.cn/",
    # 课表页 URL：留空则登录后自动在页面中寻找“课表/课程表”入口并点击
    "schedule_url": "",
    "calendar_name": "课表",
    "reminder_lead_minutes": 5,           # 上课前多少分钟提醒（0–10）
    "timezone": "Asia/Shanghai",
    "week_start_mode": "next_monday",     # auto(从页面解析日期) | next_monday | explicit
    "week_start_date": "",                # explicit 模式下的起始日期 YYYY-MM-DD
    "school_days_per_week": 6,
    "headless": True,                     # 无头浏览器；调试时可设 False 看界面
    "selectors": {
        # 登录表单选择器；留空则自动探测
        "login": {"username": "", "password": "", "submit": ""},
        # 课表表格解析选择器；配置后按列映射解析，未配置则进入“探测”流程
        "schedule": {
            "container": "",   # 课表容器，例如 table 或某个 div 的 CSS 选择器
            "date_header": "", # 日期表头所在行/元素
            "cols": {          # 列索引或表头关键字 -> 字段
                "subject": "", "time": "", "location": "", "date": ""
            }
        }
    }
}


def load_config():
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    # 合并嵌套的 selectors，避免旧配置缺字段
    sel = dict(DEFAULT_CONFIG["selectors"])
    sel.update(cfg.get("selectors", {}))
    sel["login"] = {**DEFAULT_CONFIG["selectors"]["login"], **cfg.get("selectors", {}).get("login", {})}
    sel["schedule"] = {**DEFAULT_CONFIG["selectors"]["schedule"], **cfg.get("selectors", {}).get("schedule", {})}
    merged["selectors"] = sel
    return merged


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
