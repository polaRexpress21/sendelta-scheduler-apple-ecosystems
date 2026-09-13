#!/bin/bash
# 盘点所有日历及其事件数（走已授予的“终端 → 日历”自动化权限，不需要文件系统/TCC）。
# 用途：定位“课表”的 58 节课到底写进了哪个日历（尤其排查同名日历/未勾选等情况）。
osascript -e 'tell application "Calendar"
  set out to ""
  repeat with c in every calendar
    set out to out & (name of c) & "  =>  事件数: " & (count of events of c) & linefeed
  end repeat
  return out
end tell'
