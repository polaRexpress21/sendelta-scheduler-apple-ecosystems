"""账号密码存储：优先使用 macOS 钥匙串（keyring），不可用时回退到本地加密文件。"""
import keyring
import base64
import os
from pathlib import Path

SERVICE = "sendelta-scheduler"
_FALLBACK = Path(__file__).resolve().parent / "credentials.enc"


def _obfuscate(data: str) -> str:
    # 仅做轻量混淆，避免明文落在磁盘；真正安全仍建议用钥匙串
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def _deobfuscate(token: str) -> str:
    return base64.b64decode(token.encode("utf-8")).decode("utf-8")


def save_credentials(username: str, password: str):
    try:
        keyring.set_password(SERVICE, "username", username)
        keyring.set_password(SERVICE, "password", password)
        # 同步清掉可能存在的回退文件
        if _FALLBACK.exists():
            _FALLBACK.unlink()
    except Exception:
        # 钥匙串不可用（如某些服务器环境）：写本地混淆文件，权限收窄
        payload = _obfuscate(f"{username}\n{password}")
        with open(_FALLBACK, "w", encoding="utf-8") as f:
            f.write(payload)
        os.chmod(_FALLBACK, 0o600)


def get_credentials():
    try:
        user = keyring.get_password(SERVICE, "username")
        pw = keyring.get_password(SERVICE, "password")
        if user is not None and pw is not None:
            return user, pw
    except Exception:
        pass
    if _FALLBACK.exists():
        with open(_FALLBACK, "r", encoding="utf-8") as f:
            raw = _deobfuscate(f.read().strip())
        lines = raw.split("\n", 1)
        return lines[0], lines[1] if len(lines) > 1 else ""
    return None, None


def has_credentials():
    u, _ = get_credentials()
    return u is not None
