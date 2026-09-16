#!/bin/bash
# 👉 双击这个文件即可启动课表同步（弹出原生窗口，不再打开浏览器）
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "还没有安装，请先双击「双击安装.command」。"
  read -r -p "按回车键关闭本窗口…" _
  exit 1
fi
# 原生窗口模式：弹出系统 WebKit 窗口，不再打开浏览器
exec .venv/bin/python main.py --windowed
