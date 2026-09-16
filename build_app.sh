#!/bin/bash
# 课表同步 · 打包成「自包含 .app」（可拖进「应用程序」文件夹，像普通 Mac App 一样使用）
# ---------------------------------------------------------------------------
# 双击「打包成App.command」即运行本脚本。结束后生成 课表同步.dmg。
#
# 做的事：
#   1) 检查本机 python3
#   2) 搭好 .app 骨架（Info.plist + MacOS/launcher 启动器）
#   3) 把所有源码拷进 .app/Contents/Resources/app
#   4) 在包内装依赖 + Chromium（PLAYWRIGHT_BROWSERS_PATH 指向包内，整包自包含）
#   5) 去掉「隔离标记」（不签名：签名会被运行时的浏览器缓存写入弄坏 Gatekeeper）
#   6) 打成 DMG（含「应用程序」快捷方式，拖动即安装）
#   7) 拷贝 DMG 到 桌面 / 下载
#
# 注意：本脚本只需在本机跑一次。生成的 .dmg 给「最终用户」用——
#       最终用户只需「打开 DMG → 拖进应用程序 → 双击」，全程不需要终端。
set -e
cd "$(dirname "$0")"
SRC="$(pwd)"

echo "============================================"
echo " 课表同步 · 打包自包含 App"
echo "============================================"

# ---- 1) 检查 python3 ----
PY="${PYTHON:-$(command -v python3 || true)}"
if [ -z "$PY" ]; then
  echo "✗ 这台 Mac 还没有 python3。"
  echo "  请先在「终端」执行： xcode-select --install   装完 Python 再回来双击一次。"
  exit 1
fi
if ! "$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)'; then
  echo "✗ 需要 Python 3.8 以上，当前是 $("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
  exit 1
fi
echo "✓ Python $("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"

# ---- 2) 搭 .app 骨架 ----
APP="$SRC/课表同步.app"
CONTENTS="$APP/Contents"
RES="$CONTENTS/Resources/app"
rm -rf "$APP"
mkdir -p "$CONTENTS/MacOS" "$RES"

cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>              <string>课表同步</string>
    <key>CFBundleDisplayName</key>       <string>课表同步</string>
    <key>CFBundleIdentifier</key>        <string>local.sendelta.scheduler</string>
    <key>CFBundleExecutable</key>        <string>launcher</string>
    <key>CFBundlePackageType</key>       <string>APPL</string>
    <key>CFBundleVersion</key>           <string>1.0</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>LSMinimumSystemVersion</key>    <string>10.13</string>
    <key>NSHighResolutionCapable</key>   <true/>
    <key>NSRequiresAquaSystemAppearance</key><true/>
</dict>
</plist>
PLIST

# 启动器：弹出系统 WebKit 原生窗口（不开浏览器），数据写到「应用程序支持」
cat > "$CONTENTS/MacOS/launcher" <<'LAUNCH'
#!/bin/bash
# 课表同步：原生窗口启动器（自包含 .app 版）
DIR="$(cd "$(dirname "$0")/../Resources/app" && pwd)"
cd "$DIR" || exit 1

# 已在运行？交给系统把已开的窗口提到最前，这里直接退出
if pgrep -f "main.py --windowed" >/dev/null 2>&1; then
  exit 0
fi

# 运行数据（配置/课表/日志/账号回退）放到「应用程序支持」，保持 .app 本身只读、不乱改
SUPPORT="$HOME/Library/Application Support/课表同步"
mkdir -p "$SUPPORT"
export SENDELTA_DATA_DIR="$SUPPORT"
# Chromium 已打进 .app，运行时从这里找（与打包时一致）
export PLAYWRIGHT_BROWSERS_PATH="$DIR/.playwright-browsers"

PY="$DIR/.venv/bin/python"
if [ ! -x "$PY" ]; then
  osascript -e 'display alert "课表同步" message "运行环境缺失（.venv 不在包内），请用「打包成App.command」重新打包。"' >/dev/null 2>&1 &
  exit 1
fi

# exec：让 App 进程本身就是 python，Dock 图标与窗口绑定，关窗口即退出
exec "$PY" "$DIR/main.py" --windowed
LAUNCH
chmod +x "$CONTENTS/MacOS/launcher"

# ---- 3) 拷源码进包（不含 .venv / data / config.json 等运行期产物）----
SRCS="main.py app.py auth.py config.py pipeline.py scraper.py calendar_sync.py reminders_sync.py notes.py"
DOCS="README.md 安装说明-小白版.md requirements.txt requirements-lock.txt config.example.json com.sendelta.scheduler.plist.template"
cp $SRCS "$RES/"
cp $DOCS "$RES/"
cp install.sh "$RES/"

# ---- 4) 在包内装依赖 + Chromium ----
echo "→ [1/3] 在包内创建运行环境并安装依赖（约 1–2 分钟）"
export PLAYWRIGHT_BROWSERS_PATH="$RES/.playwright-browsers"
( cd "$RES" && SENDELTA_BUILD=1 bash install.sh )

# install.sh 在构建时会在包内生成运行期产物（data/、com.sendelta.scheduler.plist）；
# 这些应属于用户机器（运行时写到“应用程序支持”），不能打进 .app，这里清除。
rm -rf "$RES/data" "$RES/com.sendelta.scheduler.plist"

# ---- 5) 去隔离标记（不签名，避免运行时浏览器缓存写入弄坏 Gatekeeper）----
echo "→ [2/3] 去掉隔离标记"
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
# 顺手做一次轻量签名（仅加快本机打开；非公证，分发到别的 Mac 可能需右键「打开」一次）
codesign -s - --force "$APP" >/dev/null 2>&1 || true

# ---- 6) 打成 DMG（含「应用程序」快捷方式）----
echo "→ [3/3] 生成 DMG 安装盘"
DMG="$SRC/课表同步.dmg"
STAGE="$(mktemp -d)/课表同步"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
rm -f "$DMG"
hdiutil create -volname "课表同步" -srcfolder "$STAGE" -ov "$DMG" -format UDZO >/dev/null

# ---- 7) 拷贝到桌面/下载 ----
for d in ~/Desktop ~/Downloads; do
  [ -d "$d" ] && cp "$DMG" "$d/" 2>/dev/null || true
done
echo
echo "============================================"
echo "✓ 打包完成！"
echo "============================================"
echo "安装盘：$DMG  ($(du -h "$DMG" | awk '{print $1}'))"
echo "已拷贝到：桌面、下载"
echo
echo "给最终用户的使用方法："
echo "  1) 打开「课表同步.dmg」"
echo "  2) 把「课表同步.app」拖进里面的「Applications」文件夹"
echo "  3) 双击「课表同步.app」→ 原生窗口直接弹出，全程不需要终端"
echo
echo "⚠️ 分发到别的 Mac 时，对方第一次打开若提示「无法验证开发者」，"
echo "   右键「课表同步.app」→ 打开，即可（只需一次）。"
