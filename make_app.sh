#!/bin/bash
# 生成一个真正的 Mac App「课表同步.app」，可以拖到 Dock 当快捷方式
# 双击 App 不会出现终端窗口；点 Dock 图标后浏览器会自动打开控制页。
set -e
cd "$(dirname "$0")"
PROJ="$(pwd)"
APP="$PROJ/课表同步.app"
CONTENTS="$APP/Contents"

echo "============================================"
echo " 生成快捷方式：课表同步.app"
echo "============================================"

if [ ! -x "$PROJ/.venv/bin/python" ]; then
  echo "还没安装完，请先双击「双击安装.command」。"
  read -r -p "按回车键关闭本窗口…" _
  exit 1
fi

rm -rf "$APP"
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Resources"

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
</dict>
</plist>
PLIST

# 启动器要点：macOS 对「已在运行」的 App 再点 Dock 不会重新执行它，
# 所以本脚本干完活就退出，让 Dock 图标不长期挂在“运行中”，每次点击都能重新生效。
{
  echo '#!/bin/bash'
  echo '# 课表同步：后台起服务 → 等它就绪 → 打开浏览器 → 退出'
  echo "DIR=\"$PROJ\""
  cat <<'SH'
if [ ! -x "$DIR/.venv/bin/python" ]; then          # 文件夹被移动过时退回相对定位
  DIR="$(cd "$(dirname "$0")/../.." && pwd)"
fi
cd "$DIR" || exit 1
mkdir -p "$DIR/data"
PY="$DIR/.venv/bin/python"
LOG="$DIR/data/web.log"
PORT_FILE="$DIR/data/web.port"
if [ ! -x "$PY" ]; then
  osascript -e 'display alert "课表同步" message "运行环境缺失，请回到程序文件夹重新双击「双击安装.command」。"' >/dev/null 2>&1 &
  exit 1
fi

# ① 服务已在后台运行？直接打开页面（必须校验 /ping 内容，别把隔空播放当成自己）
PORT=""
[ -f "$PORT_FILE" ] && PORT=$(cat "$PORT_FILE" 2>/dev/null)
for P in $PORT 5057 5058 5059 5060 5077 8000 8080 8888; do
  [ -z "$P" ] && continue
  case "$(curl -fs --max-time 1 "http://127.0.0.1:$P/ping" 2>/dev/null)" in
    *sendelta-scheduler-ok*) open "http://127.0.0.1:$P"; exit 0 ;;
  esac
done

# ② 后台起服务（脱离本进程，App 退出后服务继续跑）
SENDELTA_NO_OPEN=1 nohup "$PY" "$DIR/main.py" >> "$LOG" 2>&1 &

# ③ 等服务就绪后打开浏览器，然后本 App 正常退出
for i in $(seq 1 80); do
  P=""
  [ -f "$PORT_FILE" ] && P=$(cat "$PORT_FILE" 2>/dev/null)
  if [ -n "$P" ]; then
    case "$(curl -fs --max-time 1 "http://127.0.0.1:$P/ping" 2>/dev/null)" in
      *sendelta-scheduler-ok*) open "http://127.0.0.1:$P"; break ;;
    esac
  fi
  sleep 0.25
done
exit 0
SH
} > "$CONTENTS/MacOS/launcher"

chmod +x "$CONTENTS/MacOS/launcher"

# 清掉“隔离标记”并做本地签名：避免每次打开都被系统安检导致卡顿
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
codesign -s - --deep --force "$APP" >/dev/null 2>&1 && echo "✓ 已做本地签名（打开更快）" || echo "· 本地签名未成功，不影响使用"
touch "$APP"        # 让 Finder 立即把它识别为 App

echo "✓ 已生成：$APP"

# 复制一份到个人的「应用程序」文件夹
mkdir -p ~/Applications
rm -rf ~/Applications/课表同步.app
cp -R "$APP" ~/Applications/ 2>/dev/null || true
if [ -d ~/Applications/课表同步.app ]; then
  xattr -dr com.apple.quarantine ~/Applications/课表同步.app 2>/dev/null || true
  codesign -s - --deep --force ~/Applications/课表同步.app >/dev/null 2>&1 || true
  echo "✓ 已放入 ~/Applications（个人应用程序文件夹）"
else
  echo "· 复制到 ~/Applications 失败，可手动拖进去"
fi

echo
echo "============================================"
echo " 接下来只需一次："
echo " 1) 打开「访达 → 前往 → 个人主目录 → Applications」，"
echo "    把「课表同步.app」拖到屏幕下方的 Dock 上"
echo " 2) 以后点 Dock 里的图标即可，不会弹出终端窗口，"
echo "    服务器就绪后浏览器会自动打开控制页"
echo "============================================"
echo
echo "⚠️ 程序文件夹不要随意移动或改名，否则 Dock 图标会失效；"
echo "   万一移动了，重新双击「创建快捷方式.command」再生成一次即可。"
echo
read -r -p "按回车键关闭本窗口…" _
