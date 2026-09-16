#!/usr/bin/env python3
"""命令行入口：
  python3 main.py            # 启动本地网页（自动挑一个空闲端口，优先 5000）
  python3 main.py --run      # 直接抓取并同步到日历（供 launchd 调用）
  python3 main.py --push     # 仅补推已抓取的 schedule.json 到日历
  python3 main.py --probe    # 仅登录并保存页面 HTML/截图，用于锁定选择器

端口说明：macOS 的「隔空播放接收器」会占用 5000 端口，此时本程序会自动顺延到
5057、5058…并在终端打印真实地址，浏览器由程序自动打开，不用手动敲网址。
"""
import argparse
import atexit
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from config import load_config, DATA_DIR
from pipeline import run_pipeline

DEFAULT_PORT = 5057          # 故意避开 5000：macOS「隔空播放接收器」会占用它
FALLBACKS = [5058, 5059, 5060, 5077, 8000, 8080, 8888]


def port_free(port, host):
    """尝试独占绑定一次，判断该端口能否被 Flask 使用。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def pick_port(preferred, host):
    for p in [preferred] + FALLBACKS:
        if p != preferred and p in (preferred,):
            continue
        if port_free(p, host):
            return p, (p != preferred)
    raise SystemExit("找不到可用端口，请关闭占用端口的软件后重试。")


def open_browser(url):
    subprocess.run(["open", url], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _run_windowed(preferred_port):
    """原生窗口模式：在后台线程跑 Flask，再用系统 WebKit 弹出一个真正的 App 窗口，
    而不是打开浏览器。关闭窗口即退出（Flask 随守护线程结束）。"""
    import threading
    try:
        import webview
    except Exception as e:
        print("未能加载原生窗口组件 pywebview：", e)
        print("请先安装：.venv/bin/python -m pip install pywebview")
        return 1
    from app import app
    load_config()
    host = "127.0.0.1"
    port, shifted = pick_port(preferred_port, host)
    port_file = Path(DATA_DIR) / "web.port"
    try:
        port_file.write_text(str(port), encoding="utf-8")
    except Exception:
        pass

    def _serve():
        app.run(host=host, port=port, debug=False, threaded=True)

    threading.Thread(target=_serve, daemon=True).start()

    # 等服务真正就绪再弹窗（比固定 sleep 稳）
    import socket, time
    ready = False
    deadline = time.time() + 20.0
    while time.time() < deadline:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        try:
            if s.connect_ex((host, port)) == 0:
                ready = True
                break
        except OSError:
            pass
        finally:
            s.close()
        time.sleep(0.15)

    print(f"课表同步 · 原生窗口已启动：http://127.0.0.1:{port}")
    if shifted:
        print(f"（{preferred_port} 被占用，已改用 {port}）")
    try:
        webview.create_window("课表同步", f"http://127.0.0.1:{port}", width=920, height=960)
        webview.start()
    finally:
        try:
            port_file.unlink(missing_ok=True)
        except Exception:
            pass
    return 0


def wait_and_open(url, host, port, timeout=20.0):
    """后台线程：等服务器真正能连上了再开浏览器，比固定 sleep 更快也更稳。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.35)
        try:
            if s.connect_ex((host, port)) == 0:
                open_browser(url)
                return
        except OSError:
            pass
        finally:
            s.close()
        time.sleep(0.15)
    try:
        from subprocess import run as _run
        _run(["osascript", "-e",
              f'display notification "请等待几秒后手动刷新浏览器：{url}" with title "课表同步"'],
             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description="Delta Student 课表同步")
    ap.add_argument("--web", action="store_true", help="启动网页服务")
    ap.add_argument("--run", action="store_true", help="抓取并同步到日历")
    ap.add_argument("--push", action="store_true", help="仅把已抓取的 schedule.json 推送到日历（不重新登录）")
    ap.add_argument("--probe", action="store_true", help="探测模式：保存页面 HTML/截图")
    ap.add_argument("--windowed", action="store_true", help="用原生窗口打开（不再调用浏览器）")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()

    if args.run:
        res = run_pipeline(probe=False)
        print(res)
        return 0
    if args.push:
        from pipeline import push_existing_schedule
        res = push_existing_schedule()
        print(res)
        return 0
    if args.probe:
        res = run_pipeline(probe=True)
        print(res)
        return 0

    # 原生窗口模式：Flask 在后台线程跑，界面用系统原生的 WebKit 窗口（不开浏览器）
    if args.windowed:
        return _run_windowed(args.port)

    # 默认启动网页
    import os
    from app import app
    load_config()
    host = os.environ.get("SENDELTA_HOST", "127.0.0.1")
    port, shifted = pick_port(args.port, host)
    url = f"http://127.0.0.1:{port}"

    # 把端口号记下来：再次点 Dock 图标时，App 会先看看服务是不是已经在跑，
    # 在跑就直接打开页面，避免重复启动多个实例。
    port_file = Path(DATA_DIR) / "web.port"
    try:
        port_file.write_text(str(port), encoding="utf-8")
        atexit.register(lambda: port_file.unlink(missing_ok=True))
    except Exception:
        pass

    print("============================================")
    print(" 课表同步网页已启动")
    print("============================================")
    print(f" 本机访问：{url}")
    if host != "127.0.0.1":
        print(f" 局域网：http://<Mac 的 IP>:{port}  （同一 WiFi，用完请 Ctrl+C 关闭）")
    if shifted:
        print(f"\n 提示：{args.port} 端口被其它程序占用，已自动改用 {port}。")
        print("       （macOS 的「隔空播放接收器」常占 5000 端口；")
        print("        想一直用 5000：系统设置 → 通用 → 隔空播放与接续 → 关闭「隔空播放接收器」）")
    print("\n 关闭这个窗口 = 停止服务。")

    # 由 Mac App 启动时（带 SENDELTA_NO_OPEN）不开浏览器，交给启动器统一处理
    if not os.environ.get("SENDELTA_NO_OPEN"):
        threading.Thread(target=wait_and_open, args=(url, host, port), daemon=True).start()
    app.run(host=host, port=port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
