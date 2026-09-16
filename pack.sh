#!/bin/bash
# 重新打包为可分发版本：../课表同步-Mac安装包.zip
#   排除：虚拟环境 .venv、运行数据 data/、生成的 .app、__pycache__ 等
#   包含：源码 + 依赖清单 + 一键安装脚本 + 双击启动器 + 定时任务模板 + 说明文档
#
# 用 Python zipfile 打包（而非系统 zip），自动带上 UTF-8 文件名标记，
# 这样别人解压后「双击安装.command」等中文名文件不会变成乱码。
set -e
cd "$(dirname "$0")"
NAME="课表同步-Mac安装包"
STAGE="$(mktemp -d)/pkg"
mkdir -p "$STAGE"

SRCS="main.py app.py auth.py config.py pipeline.py scraper.py calendar_sync.py reminders_sync.py notes.py"
DOCS="README.md 安装说明-小白版.md requirements.txt requirements-lock.txt config.example.json"
SCRIPTS="install.sh install.command start.command make_app.sh build_app.sh pack.sh diagnose_calendars.sh check_calendar.sh 双击安装.command 双击启动.command 创建快捷方式.command 打包成App.command 停止服务.command"

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

# 用 Python 重新打包：排除 .DS_Store / __pycache__ / .pyc / .venv / 课表同步.app / data
PYBIN="/Users/xionghaoran/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
if [ ! -x "$PYBIN" ]; then PYBIN="python3"; fi
"$PYBIN" - "$STAGE" "$ZIP" <<'PY'
import sys, os, zipfile
stage, zip_path = sys.argv[1], sys.argv[2]
EXCLUDE_DIRS = {'.venv', '__pycache__', '课表同步.app', 'data', '.git', '.github'}
EXCLUDE_FILES = {'.DS_Store'}
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(stage):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fn in files:
            if fn in EXCLUDE_FILES or fn.endswith('.pyc'):
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, stage)
            z.write(full, rel)
print("打包条目数：", len(z.namelist()))
PY

echo "== 打包完成 =="
echo "$ZIP  ($(du -h "$ZIP" | awk '{print $1}'))"
unzip -l "$ZIP"
