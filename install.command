#!/bin/bash
# 双击即可安装（英文文件名版，任何解压工具都能正常识别）
cd "$(dirname "$0")"
bash install.sh
RC=$?
echo
if [ $RC -ne 0 ]; then
  echo "安装过程中出错了，请把上面红色的报错文字截图发给作者。"
  read -r -p "按回车键关闭本窗口…" _
  exit $RC
fi
printf "是否现在启动课表同步网页？（直接回车=启动，输入 n 回车=稍后再说） "
read -r ans
case "$ans" in
  n|N) echo "好的，稍后双击 "start.command" 即可。"
       read -r -p "按回车键关闭本窗口…" _ ;;
  *)   exec ./start.command ;;
esac
