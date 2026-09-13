#!/bin/bash
# 👉 双击这个文件即可启动课表同步网页（浏览器会自动打开）
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "还没有安装，请先双击「双击安装.command」。"
  read -r -p "按回车键关闭本窗口…" _
  exit 1
fi
# 端口由 main.py 自动挑选（5000 被“隔空播放接收器”占用时会自动换一个）
exec .venv/bin/python main.py
