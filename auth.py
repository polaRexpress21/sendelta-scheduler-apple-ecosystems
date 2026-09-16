"""账号密码存储：保存到本机应用数据目录，不再使用 macOS 钥匙串（keyring）。

原因：未签名 / 自签名的 App 每次读写「登录钥匙串」时，macOS 会弹出
「输入密码以允许 'Python' 访问钥匙串」的系统授权框。改为把账号密码保存在
应用自己的数据目录（打包后即 ~/Library/Application Support/课表同步）下，
避免触发系统密码弹窗，用户只需在软件内输入一次账号密码即可。
"""
import base64
import os
from pathlib import Path

from config import RUNTIME_DIR

# 凭证文件放在运行时数据目录（不写进 .app 包体内部）
_CRED_FILE = RUNTIME_DIR / "credentials.enc"


def _obfuscate(data: str) -> str:
    # 轻量混淆，避免明文直接落在磁盘；文件权限已收紧为仅本人可读（0600）
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def _deobfuscate(token: str) -> str:
    return base64.b64decode(token.encode("utf-8")).decode("utf-8")


def save_credentials(username: str, password: str):
    payload = _obfuscate(f"{username}\n{password}")
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CRED_FILE, "w", encoding="utf-8") as f:
        f.write(payload)
    os.chmod(_CRED_FILE, 0o600)


def get_credentials():
    if _CRED_FILE.exists():
        with open(_CRED_FILE, "r", encoding="utf-8") as f:
            raw = _deobfuscate(f.read().strip())
        lines = raw.split("\n", 1)
        return lines[0], lines[1] if len(lines) > 1 else ""
    return None, None


def has_credentials():
    u, _ = get_credentials()
    return u is not None