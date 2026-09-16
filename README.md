# 课表同步到 Apple Watch · 使用教程

![打包安装包](https://github.com/polaRexpress21/sendelta-scheduler-apple-ecosystems/actions/workflows/build-zip.yml/badge.svg)
![平台](https://img.shields.io/badge/platform-macOS-blue)
![许可](https://img.shields.io/badge/license-MIT-green)

把学校学生端（Delta Student）上的每周课表自动抓取，写入 **iCloud 日历** 与 **提醒事项**（带「上课前 N 分钟」提醒），
从而在 iPhone 与 Apple Watch 上收到提醒。**周中手机不在书包里也没关系**——周末同步一次，手表整周离线提醒。

> 提醒功能主要靠「**提醒事项**」实现：它的“到期提醒”是系统级通知，到点一定弹，且会同步到 Apple Watch 表盘；
> 日历事件同时写入，方便在「日历」里查看整周排布。两者都写（默认），也可在设置里只留其一。

**仓库**：https://github.com/polaRexpress21/sendelta-scheduler-apple-ecosystems
**不想看长教程**：直接看 [《安装说明-小白版》](安装说明-小白版.md)，解压后双击两个文件就能用。

**怎么拿到安装文件**（两种方式）

1. **Releases**：仓库右侧 [Releases](../../releases) → 下载 `sendelta-scheduler-mac.zip`（最稳）
2. **Actions 产物**：点 [Actions](../../actions) → 最新一次 `打包安装包` → 底部 Artifacts 下载 `sendelta-scheduler-mac`
   > 每次推送代码，GitHub 都会自动跑一次语法检查并重新打包，不用手动传文件。

**能做什么**

| 功能 | 说明 |
|------|------|
| 自动登录抓取 | Playwright 无头浏览器登录学生端，解析 FullCalendar 周视图课表 |
| 写入 iCloud 日历 | AppleScript 写入「日历」App，事件标题为「科目 · 地点」 |
| 写入提醒事项 | AppleScript 写入「提醒事项」App，到点弹系统通知（手表也会震） |
| 同步目标可切换 | 设置里选「日历 + 提醒事项 / 仅提醒事项 / 仅日历」 |
| 每周自动同步 | launchd 定时任务，每周日 20:00 自动跑一次 |
| 原生窗口控制台 | 弹出系统原生 WebKit 窗口（**不再打开浏览器**）；360° 圆环选提醒分钟数、一键同步、清理已上完的过期课表、本周课表简明预览 |
| 课程备注 | 两种范围：①「科目备注」对该科目所有课生效；②「指定某节课备注」只作用于选中的那一节。备注随同步写进日历/提醒事项的备注字段 |
| Mac App 快捷方式 | 生成 `课表同步.app`，可拖到 Dock 一键打开 |
| 每次同步结果 | 窗口内原地弹窗提示，不跳转；同时更新「上次更新时间」 |

**📝 课程备注（两种范围）**
- **科目备注**：在「科目备注」面板里给某科目填一条，会显示在该科目**每一节课**下方，并随同步写进日历/提醒。适合「数学：记得带计算器」这类通用提醒。
- **指定某节课备注**：在本周课表里点某节课右侧的「📝 备注」，只作用于**这一节**（按 日期 + 时间 + 科目 精确定位）。适合「今天月考」「换教室到 B305」这类一次性提醒。
- 备注不会塞进事件标题（标题仍保持「科目 · 地点」简洁，方便手表小屏一眼看清），而是写进日历事件的「备注」/提醒事项的「正文」。

> 运行环境：**仅 macOS**（依赖钥匙串、日历 App 的 AppleScript、launchd 定时任务）。Windows / Linux / iPhone 均不能运行本程序。

---

## 目录

1. [三分钟上手](#1-三分钟上手)
2. [全新一台 Mac：安装](#2-全新一台-mac安装)
3. [日常使用：原生窗口控制台](#3-日常使用网页控制台)
4. [让手表真的收到提醒（关键）](#4-让手表真的收到提醒关键)
5. [每周日自动同步](#5-每周日自动同步)
6. [常见问题与排错](#6-常见问题与排错)
7. [进阶用法](#7-进阶用法)
8. [卸载 / 换机](#8-卸载--换机)
9. [文件说明与数据安全](#9-文件说明与数据安全)

---

## 1. 三分钟上手

> **最省事的办法（推荐）**：下载解压后，在「终端」里粘贴下面这一整段（改成你的目录名），
> 它先去掉 macOS 的“隔离标记”（否则双击 `.command` 会被拦截、要反复点允许），再一键安装并启动：
>
> ```bash
> cd ~/Downloads/sendelta-scheduler-apple-ecosystems-main && \
> xattr -dr com.apple.quarantine . && \
> bash install.sh && \
> ./start.command
> ```
>
> 之后要再打开，直接双击 `课表同步.app`（或 `start.command`）即可，不用再敲命令。

传统分步版：

```bash
# ① 解压后进入目录（例如放在“下载”里）
cd ~/Downloads/sendelta-scheduler

# ② 一键安装：建虚拟环境 → 装依赖 → 下载 Chromium（约 150MB，只需一次，需联网）
bash install.sh

# ③ 启动网页
./start.command          # 也可以直接双击这个文件
```

会弹出**原生窗口**（系统 WebKit 渲染，不再是浏览器标签页；默认 <http://127.0.0.1:5057>，端口被占会自动顺延）→ 填学校账号密码 → 点「**同步**」→ 完成。

**第一次只多一步（只需一次）**：系统会弹出「终端 / Python 想要访问“日历”和“提醒事项”」的授权框，**两个都点「允许」**。
因为本程序只监听本机 `127.0.0.1`，所以**不会**触发“是否允许传入连接”的防火墙弹窗。
若不小心点了“拒绝”，去 系统设置 → 隐私与安全性 → 自动化，把「终端 / Python」访问「日历」「提醒事项」重新勾上即可。

---

## 2. 全新一台 Mac：安装

| 步骤 | 命令 | 说明 |
|------|------|------|
| ① 解压 | `unzip sendelta-scheduler-mac.zip` | 放**任何目录**都行，路径会自动适配 |
| ② 安装 | `bash install.sh` | 自动做下面 4 件事，约 2–5 分钟 |
| ③ 装定时任务（可选） | `bash install.sh --launchd` | 每周日 20:00 自动同步一次 |
| ④ 启动 | `./start.command` | 双击也行 |

`install.sh` 具体做了这些：

1. 检查 Python ≥ 3.8（没有就先装 Xcode 命令行工具：`xcode-select --install`）
2. 在本目录建独立虚拟环境 `.venv`（不污染系统 Python）
3. `pip install -r requirements.txt`（Flask / Playwright / keyring）
4. `playwright install chromium`（下载无头浏览器，约 150MB）
5. 用**当前解压路径**生成 `com.sendelta.scheduler.plist`（定时任务配置文件）

> 想完全复现同一套依赖版本：`pip install -r requirements-lock.txt`。
> 安装卡住多半是网络问题；换网络后重跑 `bash install.sh` 即可，它支持断点续跑。

### 方式三（推荐给纯小白）：打包成「可拖拽安装」的自包含 App

不想碰命令、想像下载别的 Mac 软件一样「把图标拖进应用程序」？在本机跑一次打包脚本即可：

```bash
bash build_app.sh        # 或双击「打包成App.command」
```

它会：① 在本目录生成自包含 `课表同步.app`（Python 依赖 + Chromium 全打进包里）；
② 再用 `hdiutil` 打成 `课表同步.dmg`（含「Applications」快捷方式）。
生成的 `.dmg` 会同时拷到「桌面 / 下载」。

最终用户：**打开 DMG → 把 `课表同步.app` 拖进 Applications → 双击**，原生窗口直接弹出，全程不需要终端、不需要再装环境。
包体自包含，可直接 AirDrop / 微信发给同学用（前提：对方 Mac 也有 `python3`）。
分发到别的 Mac 时，对方首次打开若提示「无法验证开发者」，右键 `课表同步.app` → 打开（只需一次）。

> 打包后的运行数据（配置 / 课表 / 备注 / 日志）会自动写到
> `~/Library/Application Support/课表同步`，不会改动 `.app` 包体本身。

---

## 3. 日常使用：网页控制台

打开控制页后，页面由三部分组成：

### ① 顶部：账号与状态 + 同步按钮

- 左侧卡片显示已登录账号，以及「**上次更新时间** · 写入 N 节课」。
- 右侧大按钮 **同步** = 完整流程：登录 → 抓课表 → 写入日历（约 20–40 秒）。
- 按钮下方的小三角 **▾** 是更多操作：

| 菜单项 | 作用 | 什么时候用 |
|--------|------|-----------|
| 仅补推课表 | 不重新登录，把上次抓好的 `data/schedule.json` 重推一遍（日历 + 提醒事项） | 刚修好日历/提醒分组、或清空后想快速恢复 |
| 仅探测页面 | 只登录并把页面 HTML / 截图存到 `data/`，不写日历 | 学校网站改版、抓不到课时排错用 |
| 清空专用日历 | 删除“课表”日历里的全部事件 | 想彻底重来一次 |

页面**右下角**还有一个常驻按钮 **「清理过期课表」**：删除已经上完的课程（结束时间早于现在），
保留未上的课，弹窗会告诉你删了几节、还剩几节。嫌日历里历史课太多时点一下即可。

### ② 提醒与日历设置

- **上课前提醒**：360° 圆环选择器，右侧方框内的数字就是当前设定值，**上下拖动圆环或滚动鼠标滚轮**调整，范围 **0–10 分钟**（默认 5）。
- **同步到**：默认「日历 + 提醒事项」都写。
  - 想**最稳地收到提醒**就选「仅提醒事项」（系统通知一定弹，且同步到手表）；
  - 只在「日历」里看整周排布就选「仅日历」。
- **专用日历名称**：默认 `课表`，写入哪个日历就填哪个名字。
- **提醒事项列表名**：默认 `课表`，写入提醒事项的哪个列表就填哪个名字。
- **周起始策略**：
  - `下周一`（推荐）：周末同步下一周的课；
  - `指定日期`：在下方「更多」里填具体起始日 `YYYY-MM-DD`。

改完点 **保存设置**。

> 网页里「**本周课表**」卡片会按天列出 `HH:MM–HH:MM 科目 · 地点`（24 小时制、不写上午/下午），
> 与写进手表的内容一致，方便你同步前后核对。

### ③ 更多（高级设置）

- 指定起始日期：`指定日期` 模式下生效。
- 无头浏览器：默认「是」。改成「否（调试）」会显示真实浏览器窗口，便于看抓取过程。

---

## 4. 让手表真的收到提醒（关键）

提醒主要靠「**提醒事项**」：它的到期提醒是系统级通知，到点一定弹，且会自动同步到 Apple Watch。
要点：

1. **提醒事项列表要同步到 iCloud**：默认“提醒事项”列表就是 iCloud 同步的；
   若你改了 `提醒事项列表名` 且新建了独立列表，请确认它在 iCloud 分组下（不是「我的 Mac」）。
2. **日历（可选）也要在 iCloud 下**：若选了「日历 + 提醒事项」或「仅日历」，
   “课表”日历必须落在 iCloud 账户，否则不会同步到手机和手表。

二选一（推荐 A）：

- **A**：系统设置 → 日历 → **默认日历账户 = iCloud**，然后删除旧的“课表”日历 → 回到网页点「同步」。
- **B**：在「日历」App 左侧 **iCloud** 分组下，手动新建一个名为「课表」的日历；程序检测到有同名日历会直接往里写。

然后：

- **iPhone**：设置 → 提醒事项 → 账户 → iCloud → 打开「提醒事项」开关；设置 → 日历 → 账户 → iCloud → 打开「日历」开关。
- **Apple Watch**：iPhone 上的 Watch App → 提醒事项 → 打开；表盘可加「提醒事项」复杂功能，到点会抬手即见。

```bash
# 排查用：列出所有日历及其事件数（确认“课表”到底在哪个账户下）
bash diagnose_calendars.sh
```

> 若存在**两个**同名“课表”日历（本地一个、iCloud 一个），程序会直接报错拒绝写入，
> 这是故意的安全护栏——按提示在日历 App 里删到只剩一个再重跑。
> 「提醒事项」同理：若同名列表出现两个，程序也会拒绝，去提醒事项 App 删到只剩一个即可。

---

## 5. 每周日自动同步

```bash
bash install.sh --launchd     # 推荐：自动生成路径并装载定时任务
```

- 触发时间：**每周日 20:00**，自动抓取下一周课表并写入日历。
- 前提：Mac 在该时刻开机且未休眠；错过了就在网页点「同步」补一下。
- 日志：`data/launchd.out.log`、`data/launchd.err.log`。

手动管理：

```bash
launchctl list | grep sendelta                                        # 查看是否装载
launchctl unload ~/Library/LaunchAgents/com.sendelta.scheduler.plist  # 停掉
launchctl load  ~/Library/LaunchAgents/com.sendelta.scheduler.plist   # 重新启用
```

---

## 6. 常见问题与排错

| 现象 | 原因 | 解决 |
|------|------|------|
| 报 `-10004 权限违例` | 没有给「终端 / Python」日历自动化权限 | 系统设置 → 隐私与安全性 → 自动化 → 勾选「终端 / Python」访问「日历」；并在终端 App 里重跑一次 |
| 报「发现多个名为『课表』的日历」 | 本地与 iCloud 各有一个同名日历 | 在日历 App 里删到只剩一个（iCloud 那个） |
| Mac 日历里有课、手机没有 | 日历落在「我的 Mac」分组 | 见[第 4 节](#4-让手表真的收到提醒关键)：默认账户改 iCloud 后删掉重建 |
| 「同步」后事件数为 0 | 本学期课表为空，或已全部过期（程序只同步**未来**的课） | 换下一周试；或用「仅探测页面」检查抓取结果 |
| 打不开网页 / 显示 403 | 5000 端口常被 macOS「隔空播放接收器」占用 | 本程序默认已从 **5057** 起步并会自动顺延到空闲端口，终端里会写真实地址；想用 5000 需到系统设置关闭「隔空播放接收器」 |
| 抓取失败 / 需要选择器 | 学校网站改版 | 点「仅探测页面」，把 `data/schedule_probe.html` / `.png` 交给作者修 |
| Chromium 下载失败 | 网络问题 | 换网络重跑 `bash install.sh` |
| 想换账号 | 钥匙串里存的是旧账号 | 在网页首页重新登录就会覆盖；彻底清除见[第 8 节](#8-卸载--换机) |

---

## 7. 进阶用法

### 命令行等价一批产出

```bash
.venv/bin/python main.py            # 启动网页（默认 127.0.0.1:5057，被占自动顺延）
.venv/bin/python main.py --port 5001
.venv/bin/python main.py --run      # 直接抓+同步一次（launchd 就是调这个）
.venv/bin/python main.py --push     # 仅补推 data/schedule.json 到日历
.venv/bin/python main.py --probe    # 仅探测并保存页面
```

### 用 iPhone 远程点「同步」

同一 WiFi 下，让 Mac 对外提供页面（**无鉴权，用完记得 Ctrl+C 退出**）：

```bash
SENDELTA_HOST=0.0.0.0 .venv/bin/python main.py
# iPhone Safari 打开 http://<Mac 的局域网 IP>:5057  （IP 在系统设置 → 网络里看）
```

### 配置文件 `config.json`

| 键 | 含义 | 默认 |
|----|------|------|
| `school_base_url` | 学生端地址 | `https://sendeltastudent.schoolis.cn/` |
| `calendar_name` | 写入的日历名 | `课表` |
| `reminders_list` | 写入的提醒事项列表名 | `课表` |
| `sync_target` | 同步目标：`both` / `reminders` / `calendar` | `both` |
| `reminder_lead_minutes` | 上课前提醒分钟（0–10） | `5` |
| `week_start_mode` | `next_monday` / `explicit` | `next_monday` |
| `week_start_date` | `explicit` 模式起始日 | 空 |
| `school_days_per_week` | 每周上课天数 | `6` |
| `headless` | 是否无头浏览器 | `true` |

抓取结果存在 `data/schedule.json`（结构化 JSON），可直接给其它程序用。

---

## 8. 卸载 / 换机

```bash
# ① 停掉定时任务
launchctl unload ~/Library/LaunchAgents/com.sendelta.scheduler.plist
rm ~/Library/LaunchAgents/com.sendelta.scheduler.plist

# ② 删除目录（含虚拟环境）
rm -rf <项目目录>

# ③ 清除钥匙串里的账号密码
security delete-generic-password -s "sendelta-scheduler" -a "username"
security delete-generic-password -s "sendelta-scheduler" -a "password"

# ④ 可选：删掉日历里的“课表”（日历 App 手动删，或网页点“清空专用日历”）
```

**换到另一台 Mac**：把 `sendelta-scheduler-mac.zip` 拷过去，按[第 2 节](#2-全新一台-mac安装)重新装一遍即可，
路径和用户名会自动适配，不用改任何写死的地址。

---

## 9. 文件说明与数据安全

| 文件 | 作用 |
|------|------|
| `main.py` | 命令行入口（网页 / 同步 / 探测） |
| `app.py` | Flask 网页（登录、控制台、圆环选择器） |
| `scraper.py` | Playwright 登录与课表抓取（自动适配 FullCalendar 周视图） |
| `pipeline.py` | 编排：登录 → 解析 → 存 JSON → 推日历 / 提醒事项 |
| `calendar_sync.py` | 生成 AppleScript 写入 iCloud 日历 |
| `reminders_sync.py` | 生成 AppleScript 写入「提醒事项」列表 |
| `auth.py` | 账号密码存 macOS 钥匙串 |
| `config.py` | 读写 `config.json` |
| `install.sh` / `start.command` / `pack.sh` | 一键安装 / 双击启动 / 重新打包 |
| `com.sendelta.scheduler.plist.template` | 定时任务模板（`install.sh` 自动生成本机版本） |
| `diagnose_calendars.sh` | 诊断：列出日历与事件数 |
| `data/schedule.json` | 最终结构化课表 |
| `data/last_sync.json` | 上次同步时间与节数 |

**安全**：账号密码只存本机 macOS 钥匙串（Keychain），不上传任何第三方；
网络请求只发往 `schoolis.cn` 与 Apple iCloud。
`data/` 里是本机运行数据，不包含密码，也不会被提交到仓库（见 `.gitignore`）。

---

## 10. 开源与许可

- 许可证：**MIT**，见 [LICENSE](LICENSE) — 可自由使用、修改、分发，欢迎提 Issue / PR。
- 免责声明：本项目是**个人学习用途**的自动化小工具，与学校或任何官方平台**无关**；
  请遵守学校相关规定，勿用于超出个人学习范围的用途。
- 隐私：仓库中**不含**任何账号密码与个人课表数据（已在 `.gitignore` 中排除 `data/`、`config.json`）。
  如果你 fork 后要提交，请确认不要把 `data/`、`config.json`、`credentials.enc` 加进去。

### 想二次开发？

```bash
git clone https://github.com/polaRexpress21/sendelta-scheduler-apple-ecosystems.git
cd sendelta-scheduler-apple-ecosystems
bash install.sh
```

改动后提交：`git add -A && git commit -m "说明" && git push`
