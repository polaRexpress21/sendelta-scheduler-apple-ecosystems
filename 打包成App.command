#!/bin/bash
# 👉 双击这个文件，即可把课表同步打包成一个可拖拽安装的「课表同步.app / .dmg」
#    （自包含：Python 依赖 + Chromium 都打进包里，发给别人也不用再装环境）
cd "$(dirname "$0")"
bash build_app.sh
echo
read -r -p "按回车键关闭本窗口…" _
