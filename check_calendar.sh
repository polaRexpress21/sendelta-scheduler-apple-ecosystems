#!/bin/bash
# 检查「课表」日历是否在 iCloud（云端）账户下。
# 若在“我的 Mac / On My Mac”本地账户，则不会同步到 iPhone / Apple Watch。
#
# 注意：~/Library/Calendars 受 macOS TCC 保护，读取它需要给“终端”授予
#       「系统设置 → 隐私与安全性 → 完全磁盘访问权限」。若未授予，本脚本会走到下方提示。
#       （更省事的验证：直接看 iPhone「日历」App 是否出现“课表”——无需任何权限。）
set -u
CAL_DIR="$HOME/Library/Calendars"

if [ ! -d "$CAL_DIR" ]; then
  echo "目录不存在: $CAL_DIR"
  echo "→ 你可能是纯 iCloud 账户且尚未生成本地缓存。"
  echo "→ 最可靠的确认：打开 iPhone「日历」App，看是否出现“课表”（周末手机在线时应已同步）。"
  exit 0
fi

# 试探是否有权读取（TCC 可能拦截）
if ! find "$CAL_DIR" -maxdepth 4 -name "*.calendar" -type d >/dev/null 2>&1; then
  echo "无法读取 $CAL_DIR（可能被 TCC 拦截）。"
  echo "解决：系统设置 → 隐私与安全性 → 完全磁盘访问权限 → 勾选“终端”，然后重跑本脚本。"
  echo "或：直接看 iPhone「日历」App 是否出现“课表”（更省事、无需权限）。"
  exit 0
fi

found=0
while IFS= read -r d; do
  title=$(plutil -extract Title raw "$d/Info.plist" 2>/dev/null)
  if [ "$title" = "课表" ]; then
    found=1
    parent=$(dirname "$d"); pname=$(basename "$parent")
    echo "「课表」日历目录: $d"
    if echo "$pname" | grep -q "\.caldav$"; then
      acct=$(plutil -extract DisplayName raw "$parent/Info.plist" 2>/dev/null)
      echo "✅ 位于云端账户：${acct:-（.caldav）} —— 会同步到 iPhone / Apple Watch"
    else
      echo "⚠️ 位于本地（On My Mac）—— 不会同步到手机/手表！"
      echo "   修复：系统设置 → 日历 → 默认日历账户 改为 iCloud；删掉本“课表”后重跑 --push"
    fi
  fi
done < <(find "$CAL_DIR" -maxdepth 4 -name "*.calendar" -type d 2>/dev/null)

[ "$found" -eq 0 ] && echo "未在 $CAL_DIR 找到名为「课表」的日历目录（可能缓存尚未生成，稍等片刻或重跑 --push）。"
