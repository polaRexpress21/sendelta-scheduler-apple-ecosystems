#!/bin/bash
# 双击即可启动（英文文件名版，任何解压工具都能正常识别）
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "还没有安装，请先双击 install.command 。"
  read -r -p "按回车键关闭本窗口…" _
  exit 1
fi
# 端口由 main.py 自动挑选（5000 被“隔空播放接收器”占用时会自动换一个）
exec .venv/bin/python main.py
