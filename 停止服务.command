#!/bin/bash
# 👉 想彻底停掉后台服务时双击它（平时不需要，服务很省电）
cd "$(dirname "$0")"
PORT=""
[ -f data/web.port ] && PORT=$(cat data/web.port 2>/dev/null)
STOPPED=0
if [ -n "$PORT" ]; then
  PIDS=$(lsof -nP -i tcp:"$PORT" 2>/dev/null | awk '$1=="Python"{print $2}' | sort -u)
  if [ -n "$PIDS" ]; then
    kill $PIDS 2>/dev/null && echo "已停止课表同步后台服务（端口 $PORT）。"
    sleep 1
    STOPPED=1
  fi
  rm -f data/web.port
fi
if [ "$STOPPED" = "0" ]; then
  echo "后台服务本来就没有在运行。"
fi
echo "下次打开：点 Dock 里的「课表同步」图标即可重新启动。"
read -r -p "按回车键关闭本窗口…" _
