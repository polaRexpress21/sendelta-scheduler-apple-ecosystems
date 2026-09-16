#!/bin/bash
# 双击即可启动（英文文件名版，任何解压工具都能正常识别）
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "还没有安装，请先双击 install.command 。"
  read -r -p "按回车键关闭本窗口…" _
  exit 1
fi
# 原生窗口模式：弹出系统 WebKit 窗口，不再打开浏览器
exec .venv/bin/python main.py --windowed
