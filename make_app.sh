#!/bin/bash
# 课表同步 · 生成「自包含 .app」（可拖进应用程序文件夹，像普通 Mac App 一样使用）
# 现在统一交给 build_app.sh 完成打包（包含依赖 + Chromium，整包自包含）。
# 双击「创建快捷方式.command」或本文件，都会走到 build_app.sh。
set -e
cd "$(dirname "$0")"
bash build_app.sh
