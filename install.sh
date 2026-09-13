#!/bin/bash
# 课表同步 · 一键安装（macOS）
#   bash install.sh             安装依赖（venv + pip + Chromium），生成本机专用的定时任务文件
#   bash install.sh --launchd   额外把“每周日 20:00 自动同步”装载到本机
# 双击「双击安装.command」等价于运行本文件。
set -e
cd "$(dirname "$0")"
PROJ="$(pwd)"

echo "============================================"
echo " 课表同步 · 安装程序"
echo "============================================"
echo "安装位置：$PROJ"
echo "全程需要联网，约 2–5 分钟，请保持窗口打开。"
echo

# 1) 检查 Python
PY="${PYTHON:-$(command -v python3 || true)}"
if [ -z "$PY" ]; then
  echo "这台 Mac 还没有 Python，正在帮你打开苹果官方安装器…"
  echo "（弹窗里点「安装」，装完再回来双击一次「双击安装.command」）"
  xcode-select --install 2>/dev/null || true
  echo
  echo "如果弹窗没出现，请手动在终端执行： xcode-select --install"
  exit 1
fi
VER="$("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
echo "✓ Python $VER（无需你做任何操作）"
case "$VER" in
  3.8|3.9|3.10|3.11|3.12|3.13|3.14) ;;
  *) echo "✗ 需要 Python 3.8 以上，当前是 $VER"; exit 1;;
esac

# 2) 虚拟环境（不影响系统里其它 Python 程序）
if [ ! -d ".venv" ]; then
  echo "→ [1/4] 创建独立运行环境 .venv"
  "$PY" -m venv .venv
else
  echo "✓ [1/4] 环境已存在，跳过"
fi

# 3) 依赖
echo "→ [2/4] 安装 Flask / Playwright / keyring 等组件"
.venv/bin/python -m pip install --upgrade pip -q
.venv/bin/python -m pip install -r requirements.txt

# 4) Playwright Chromium（约 150MB）
echo "→ [3/4] 下载无头浏览器 Chromium（约 150MB，较慢，请耐心）"
.venv/bin/playwright install chromium

# 5) 生成本机专用定时任务文件
mkdir -p "$PROJ/data"
sed -e "s#__PROJECT_DIR__#$PROJ#g" com.sendelta.scheduler.plist.template > "$PROJ/com.sendelta.scheduler.plist"
echo "✓ [4/4] 已生成定时任务配置文件"

if [ "$1" = "--launchd" ]; then
  echo "→ 装载“每周日 20:00 自动同步”"
  if launchctl list | grep -q "com.sendelta.scheduler"; then
    launchctl unload ~/Library/LaunchAgents/com.sendelta.scheduler.plist 2>/dev/null || true
  fi
  cp "$PROJ/com.sendelta.scheduler.plist" ~/Library/LaunchAgents/
  launchctl load ~/Library/LaunchAgents/com.sendelta.scheduler.plist
  echo "✓ 已装载：每周日 20:00 自动同步"
fi

echo
echo "============================================"
echo " 安装完成！"
echo "============================================"
echo "接下来只需两步："
echo "  1) 双击文件夹里的「双击启动.command」打开网页"
echo "  2) 填学校账号密码 → 点「同步」"
echo
echo "⚠️ 第一次务必再做一次（只需一次）："
echo "   打开 Mac 自带的「终端」App，输入 cd + 空格，把这个文件夹拖进终端窗口，"
echo "   回车后粘贴："
echo "     .venv/bin/python main.py --run"
echo "   弹出“想要访问日历”时点「允许」，否则到时候自动同步会没权限。"
echo
read -r -p "按回车键关闭本窗口…" _
