# 硬盘小浣熊 🦝 Disk Raccoon

<p align="center">
  <a href="./README.md">简体中文</a> ｜ <a href="./README.en.md">English</a>
</p>

一个帮你清理 Mac 缓存的 AI skill。给你的 AI 编程助手装上它，它就能帮你找到硬盘里那些偷偷占了几十个 G 的缓存文件，判断哪些能安全删掉，然后帮你清理。

苹果的固态硬盘焊死在主板上，升一档 512G 加价 **¥1500**。小浣熊第一次出手，一晚清出 **135+ GB**，零翻车。如果你的盘是被缓存塞满的，清一次就省了一笔升配钱。**大概是你 agent 里最值钱的 skill，¥1500 起。**

## 缘起

我用 [Mole](https://github.com/tw93/Mole) 扫了一下硬盘，找出几个很大的文件夹，每个都几十个 G。

删不删呢？

飞书那个目录，一半是文档缓存，删了没事；另一半是登录态，删了要重新扫码。Chrome 也一样，Service Worker 能删，旁边的 IndexedDB 删了网页应用数据就没了。

同一个文件夹里，一半是垃圾，一半是状态。扫帚能扫出大小，扫不出答案。

于是让 AI 来判断。它逐个去查每个目录属于什么应用、存的是什么、删了会怎样，查完列了一张单子给我。照着清，一晚清出 **135+ GB**，零翻车。

既然这么好用，我想到我还有一台电脑，不如把这套判断做成一个 skill，还能分享给朋友。就有了这个项目。

## 为什么叫浣熊

浣熊是自然界唯一吃东西前先把食物洗一洗的动物。

它不是不吃，是不瞎吃。

大多数清理工具扫全盘，把大的列出来让你勾。但 macOS 真正的问题是：**大的不一定该删，该删的不一定大。**

- 飞书看文档攒下 42G 缓存，藏在 `LarkShell/aha` 深处，Finder 看不见
- Chrome 的 Service Worker 吃掉 30G，但旁边的 IndexedDB 删了会丢数据
- Telegram 媒体缓存能涨到 100G，官方 issue 骂了八年没修
- `~/.cache/uv` 静悄悄吃掉 56G

**小浣熊的重点不是删，是分得清什么能删。** 先洗，再吃。

## 只做缓存

卸载应用、管后台、优化系统，这些 [Mole](https://github.com/tw93/Mole) 🐹 已经做得很好了，开源免费。

小浣熊只管缓存，但管到底。核心是一份缓存地图（`references/cache-map.md`），每条路径标了安全等级：

- ✅ **放心删**：`~/.cache/uv`、浏览器 Service Worker、Telegram 媒体缓存……
- ⚠️ **小心删**：飞书 `LarkShell/aha`（只删 `profile_explorer`，`profile_main` 有登录态）、微信（建议走 app 内清理）……
- 🚫 **不要碰**：消息数据库、钥匙串、带"状态"的目录

地图上没有的路径？查清楚再说，查不清楚就不动。

## 特性亮点

- ⚡ **2 秒极速体检**：内置多线程并发探针（`scripts/fast-scan.py`），打满 Apple Silicon NVMe 队列，彻底告别传统 `du` 单线程卡顿与重复遍历。
- 🎯 **精准分级（缓存地图）**：基于 `references/cache-map.md`，区分「✅ 放心删」、「⚠️ 小心删（保留登录态）」与「🚫 别碰（数据库/状态）」。
- 🛡️ **严格第一轮只读**：没收到用户明确确认前，绝不删除任何一个字节。
- 🌐 **双模使用**：既支持在 20+ 款主流 AI Agent 中通过自然语言调用，也支持在终端直接当作原生 CLI 运行。

## 安全设计

| 原则 | 说明 |
|---|---|
| 默认只读 | 第一轮只看不删，先出报告 |
| 先认清再删 | 地图上没有的路径，查清楚之前不动 |
| 可恢复优先 | 能进废纸篓就不直接删 |
| 状态不碰 | 登录态、聊天记录、钥匙串，永远不动 |
| 先退出再动手 | app 还在跑就先关掉，避免边删边重建 |
| sudo 交给你 | 系统级删除只生成命令，你自己跑 |

## 安装

你可以根据偏好选择以下任一方式：

### 方式一：Skills CLI（推荐给 Agent 用户）

通过 [skills.sh](https://skills.sh) 官方包管理器一键安装到所有支持的 AI Agent（Claude Code、Antigravity、Cursor、Codex、Cline 等 20+ 款）：

```bash
npx skills add tasselx/disk-raccoon -g
```

> 💡 如果只想在当前项目生效，去掉 `-g` 即可：`npx skills add tasselx/disk-raccoon`

### 方式二：一键全功能脚本（推荐，兼具终端全局 CLI 与 PATH 自愈）

自动检测并软链接到所有 Agent，同时将 `disk-raccoon` 和 `raccoon` 注册为系统原生终端命令（自动校验并自愈 PATH）：

```bash
curl -fsSL https://raw.githubusercontent.com/tasselx/disk-raccoon/main/install.sh | bash
```

### 方式三：npm 全局安装（推荐给 Node.js 开发者）

自动将命令软链接到 npm 全局 bin 环境变量：

```bash
npm install -g tasselx/disk-raccoon
```

> 💡 免安装直接体验：也可以直接执行 `npx tasselx/disk-raccoon` 瞬时查看体检报告！

### 方式四：手动克隆与安装

```bash
git clone https://github.com/tasselx/disk-raccoon.git ~/.config/disk-raccoon
cd ~/.config/disk-raccoon && ./install.sh
```

## 用法

安装完成后，支持 **AI Agent 对话** 和 **终端全局命令** 两种方式：

### 1. 在 AI Agent 中（推荐）

在任意目录下，直接跟 Agent（Claude Code / Antigravity / Codex 等）说：

- "帮我看看缓存"
- "磁盘满了，能清点什么"
- "Chrome 怎么占了 60G"

### 2. 在终端直接作为 CLI 使用

无需进入 Agent，在任意终端输入全局命令秒级查看体检报告：

```bash
disk-raccoon              # 极速输出当前缓存体检报告
raccoon --min-mb=200      # 仅查看大于 200MB 的大头缓存
disk-raccoon --json       # 以 JSON 格式输出供脚本解析
```

**体检报告输出示例：**

```markdown
# 🦝 小浣熊高速只读体检报告 (v0.2.0)

**磁盘总览**：总量 460Gi ｜ 已用 12Gi (35%) ｜ 剩余可用 23Gi
**发现可释放目标**：预估 19.9 GB（仅统计 ≥ 50MB 的有效缓存项）

### 🎯 待确认清理项（Actionable Targets）
| 占用大小 | 安全等级 | 所属应用 / 项目 | 路径 | 清理建议 / 影响 |
| :--- | :--- | :--- | :--- | :--- |
| **8.5 GB** | ✅ 安全 | Frida | `~/.cache/frida` | 可安全清理 |
| **2.6 GB** | ✅ 安全 | Xcode | `~/Library/Developer/Xcode/DerivedData` | 下次构建自动重建索引 |
| **2.4 GB** | ✅ 安全 | npm | `~/.npm` | 执行 npm cache clean --force |
| **1.8 GB** | ✅ 安全 | 飞书 (Lark) | `~/.../profile_explorer` | 文档纯缓存；保留 profile_main 登录态 |
| **952 MB** | ✅ 安全 | Edge/Chrome | `~/.../Service Worker` | 离线网页缓存，需先退出浏览器 |
```

## 实战记录

| 缓存 | 释放 |
|---|---|
| `~/.cache/uv`（Python 包缓存） | ~56G |
| Chrome Service Worker + ChromeDebug | ~51G |
| 飞书 `LarkShell/aha` 文档缓存 | ~38G |
| **合计** | **135+ GB** |

## 参与

缓存地图是活的，我们每清一次新缓存就补一条进去。如果你也踩过新的坑，欢迎提 issue 或 PR，把更多缓存加进来，让这只浣熊越来越懂你的硬盘 🦝

## License

MIT
