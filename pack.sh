#!/bin/bash
# 重新打包为可分发版本：当前目录下的 ../课表同步-Mac安装包.zip
#   排除：虚拟环境 .venv、运行数据 data/、生成的 .app、__pycache__ 等
#   包含：源码 + 依赖清单 + 一键安装脚本 + 双击启动器 + 定时任务模板 + 说明文档
set -e
cd "$(dirname "$0")"
NAME="课表同步-Mac安装包"
STAGE="$(mktemp -d)/pkg"
mkdir -p "$STAGE"

SRCS="main.py app.py auth.py config.py pipeline.py scraper.py calendar_sync.py"
DOCS="README.md 安装说明-小白版.md requirements.txt requirements-lock.txt config.example.json"
SCRIPTS="install.sh install.command start.command make_app.sh pack.sh diagnose_calendars.sh check_calendar.sh 双击安装.command 双击启动.command 创建快捷方式.command 停止服务.command"

cp $SRCS "$STAGE/"
cp $DOCS "$STAGE/"
cp $SCRIPTS "$STAGE/"
cp com.sendelta.scheduler.plist.template "$STAGE/"

chmod +x "$STAGE"/install.sh "$STAGE"/start.command "$STAGE"/pack.sh \
         "$STAGE"/make_app.sh "$STAGE"/install.command \
         "$STAGE"/diagnose_calendars.sh "$STAGE"/check_calendar.sh \
         "$STAGE"/双击安装.command "$STAGE"/双击启动.command "$STAGE"/创建快捷方式.command "$STAGE"/停止服务.command

ZIP="$(cd .. && pwd)/$NAME.zip"
rm -f "$ZIP"
( cd "$STAGE" && zip -rq -X "$ZIP" . \
    -x '*.DS_Store' '*__pycache__*' '*.pyc' '*/.venv/*' '*/课表同步.app/*' 'data/*' )

echo "== 打包完成 =="
echo "$ZIP  ($(du -h "$ZIP" | awk '{print $1}'))"
unzip -l "$ZIP"
