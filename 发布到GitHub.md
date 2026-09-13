# 发布到 GitHub（两种办法，选一种）

仓库已经在本地准备好了，目录在：

```
/Users/xionghaoran/WorkBuddy/2026-09-12-21-16-32/sendelta-scheduler
```

已经做了两次提交，252K，包含 25 个源文件。
`.gitignore` 已排除 `.venv/`、`data/`、`config.json`、生成的 App 和打包产物，**账号密码不会被上传**（它只存在本机钥匙串里）。

> 建议仓库设为 **Private（私有）**，因为里面有学校内网的网址。

---

## 办法 A：GitHub Desktop（最省事，不用记命令）

1. 下载安装：<https://desktop.github.com>
2. 打开后 **Sign in to GitHub.com**，用浏览器登录授权
3. 菜单 **File → Add Local Repository…**，选上面那个目录（如果提示 “create a repository”，直接确认）
4. 左上角或右上角点 **Publish repository**
   - Name：`sendelta-scheduler`
   - ⚠️ **勾上 “Keep this code private”**（私有）
   - 去掉 “Initialize this repository with a README”（我们已经有 README）
5. 点 **Publish Repository** 即完成，之后改完代码在 Desktop 里填个 Summary → **Commit to main** → **Push origin** 就能同步

---

## 办法 B：用终端（需要先生成一个令牌）

### 第 1 步：生成 GitHub 令牌（密码用）

1. 登录 GitHub → 右上角头像 → **Settings**
2. 左下角 **Developer settings → Personal access tokens → Tokens (classic)**
3. **Generate new token (classic)**
   - Note 随便填，比如 `mac`
   - Expiration 选 90 days 或 No expiration
   - 勾选 **`repo`**（这一项就够）
4. 点 **Generate token**，把生成的 `ghp_...` 字符串**复制保存好**（关掉后就看不到了）

### 第 2 步：在 GitHub 上建一个空仓库

右上角 **+ → New repository**
- Repository name：`sendelta-scheduler`
- 选 **Private**
- **不要**勾 "Add a README file"（本地已经有了）

### 第 3 步：推送（在「终端」App 里粘贴）

```bash
cd /Users/xionghaoran/WorkBuddy/2026-09-12-21-16-32/sendelta-scheduler
git remote add origin https://github.com/<你的GitHub用户名>/sendelta-scheduler.git
git branch -M main
git push -u origin main
```

提示输用户名密码时：
- 用户名 = 你的 GitHub 账号名
- 密码 = **粘贴刚才那个 ghp_ 令牌**（终端里不显示字符是正常的，回车即可）

macOS 会把它存进钥匙串，以后 `git push` 不用再输。

---

## 以后怎么更新

改完代码后，在这个目录下执行三条：

```bash
git add -A
git commit -m "写一句改了什么"
git push
```

（用 GitHub Desktop 的话就是：填 Summary → Commit → Push）

## 别人怎么用你的仓库

README 和《安装说明-小白版.md》都写在仓库里了。对方要么：
- GitHub 页面 → 右侧 **Releases / Code → Download ZIP**，解压后照小白说明做
- 或者 `git clone https://github.com/<用户名>/sendelta-scheduler.git`（私有仓库需要授权）
