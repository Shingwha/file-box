# 📂 共享文件箱 — File Box

一个简单、轻量的文件共享服务。上传、下载、删除文件，支持密码保护和存储空间查看。

**在线演示：** 无需注册，部署即可使用

---

## 功能

- ✅ 上传文件（拖拽或点击，最多 50 个文件同时上传，单文件最大 500 MB）
- ✅ 下载文件（支持中文文件名）
- ✅ 删除文件（带确认弹窗，防止误删）
- ✅ 密码保护（可选，设密码后页面需要登录才能使用）
- ✅ 存储空间显示（实时查看已用空间、文件数量）
- ✅ 暗色主题，移动端适配
- ✅ CLI 工具（终端管理文件）

---

## 一键部署

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template?referralCode=)

或手动部署：

### 1. 部署到 Railway

[Railway](https://railway.app) 是一个云平台，免费计划每月 $1 额度，跑这个项目绰绰有余。

**步骤：**

1. 点击右上角 **Fork** 按钮，把本项目复制到你的 GitHub 账号
2. 打开 [Railway](https://railway.app) → 用 GitHub 登录
3. 点击 **New Project** → **Deploy from GitHub repo**
4. 选择你 fork 后的 `file-box` 仓库
5. Railway 自动检测 Node.js，开始部署

### 2. 配置存储（可选但推荐）

Railway 的磁盘是临时的，重新部署后文件会丢失。要持久保存文件，需要挂载 Volume：

1. 在 Railway 项目页面，**右键点击你的服务** → **Create Volume**
2. Mount Path 填写：`/app/data`
3. 系统自动重新部署

> **不加 Volume 也能用**，只是每次重新部署文件会清空。

### 3. 设置密码（可选）

在 Railway 项目 → **Variables** → **New Variable**：

| 变量名 | 值 | 说明 |
|--------|---|------|
| `PASSWORD` | 你的密码 | 不设置则完全公开 |

### 4. 完成

部署后 Railway 会分配一个 `https://你的项目.up.railway.app` 域名，打开即可使用。

---

## 自定义域名

1. 在 Railway → 你的服务 → **Settings** → **Domains** → **Custom Domain**
2. 输入你的域名
3. 在域名 DNS 管理处添加 CNAME 记录指向 Railway 分配的地址

---

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PORT` | `3000` | 服务端口（Railway 自动设置） |
| `PASSWORD` | 无（公开） | 访问密码 |
| `UPLOAD_DIR` | `./data` | 文件存储路径（一般不需要改） |
| `STORAGE_LIMIT` | 自动检测 | 存储上限（字节），有 Volume 自动识别 500 MB |

---

## 本地运行

```bash
git clone https://github.com/你的用户名/file-box.git
cd file-box
npm install
npm start
```

然后打开 http://localhost:3000

---

## CLI 工具

项目附带一个命令行工具，可以在终端管理文件。

### 安装

```bash
# 直接从 GitHub 安装
uv tool install git+https://github.com/Shingwha/file-box.git

# 或从本地安装
cd cli
uv tool install .
```

### 使用

```bash
# 首次配置（只需一次）
file-box config login https://你的项目.up.railway.app 你的密码

# 常用命令
file-box ls            # 列出文件
file-box dl "文件名"   # 下载文件
file-box up ./文件     # 上传文件
file-box rm "文件名"   # 删除文件
file-box df            # 查看存储空间
file-box config get    # 查看当前配置
```

---

## 技术栈

- **后端：** Node.js + Express + Multer
- **前端：** 纯 HTML + CSS + JavaScript（无框架）
- **存储：** 本地文件系统 / Railway Volume
- **部署：** Railway / 任意 Node.js 环境

---

## License

MIT
