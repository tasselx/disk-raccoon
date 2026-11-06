# 硬盘小浣熊 🦝 Disk Raccoon

<p align="center">
  <a href="./README.md">简体中文</a> ｜ <a href="./README.en.md">English</a>
</p>

一个帮你清理 Mac 缓存的 AI Skill 与极速终端 CLI。给你的 AI 编程助手装上它，它就能帮你找到硬盘里那些偷偷占了几十个 G 的缓存文件，判断哪些能安全删掉，然后帮你安全清理。

苹果的固态硬盘焊死在主板上，升一档 512G 加价 **¥1500**。小浣熊第一次出手，一晚清出 **135+ GB**，零翻车。如果你的盘是被缓存塞满的，清一次就省了一笔升配钱。**大概是你 agent 里最值钱的 skill，¥1500 起。**

## 缘起

我用 [Mole](https://github.com/tw93/Mole) 扫了一下硬盘，找出几个很大的文件夹，每个都几十个 G。

删不删呢？

飞书那个目录，一半是文档缓存，删了没事；另一半是登录态，删了要重新扫码。Chrome 也一样，Service Worker 能删，旁边的 IndexedDB 删了网页应用数据就没了。

同一个文件夹里，一半是垃圾，一半是状态。扫帚能扫出大小，扫不出答案。

于是让 AI 来判断。它逐个去查每个目录属于什么应用、存的是什么、删了会怎样，查完列了一张单子给我。照着清，一晚清出 **135+ GB**，零翻车。

既然这么好用，不如把这套判断做成一个兼具 **AI Agent Skill** 与 **终端原生 CLI** 的项目，分享给更多开发者。

## 为什么叫浣熊

浣熊是自然界唯一吃东西前先把食物洗一洗的动物。

它不是不吃，是不瞎吃。

大多数清理工具扫全盘，把大的列出来让你勾。但 macOS 真正的问题是：**大的不一定该删，该删的不一定大。**

- 飞书看文档攒下 42G 缓存，藏在 `LarkShell/aha` 深处，Finder 看不见
- Chrome 的 Service Worker 吃掉 30G，但旁边的 IndexedDB 删了会丢数据
- Telegram 媒体缓存能涨到 100G，官方 issue 骂了八年没修
- `~/.cache/uv` 静悄悄吃掉 56G，`~/.gradle/caches` 历史构件堆积 40G
- `pnpm store` 孤立包和 `Bun` 缓存占满小容量 SSD

**小浣熊的重点不是删，是分得清什么能删。** 先洗，再吃。

## 只做缓存，且管到底

卸载应用、管后台、优化系统，这些 [Mole](https://github.com/tw93/Mole) 🐹 已经做得很好了，开源免费。

小浣熊只管缓存，但管到底。核心是结构化规则库（`data/rules.json`）与缓存地图（`references/cache-map.md`），标明安全等级：

- ✅ **放心删**：`uv`、`pnpm store`、`Gradle`、浏览器 Service Worker、Telegram 媒体缓存、Xcode 编译产物、HuggingFace 权重、Cargo 源码……
- ⚠️ **小心删**：飞书 `LarkShell/aha`（只删 `profile_explorer`，`profile_main` 有登录态）、Xcode Archives（旧版本打包）、Ollama（建议按模型卸载）、微信（优先 app 内清理）……
- 🚫 **不要碰**：消息数据库、钥匙串、带状态与凭证的目录（内建 Kill Switch 熔断拦截）

地图上没有的路径？查清楚再说，查不清楚就不动。

## 特性亮点 (v0.3.0 极致版)

- ⚡ **2 秒极速体检**：多线程并发探针（`scripts/fast-scan.py`），打满 Apple Silicon NVMe 队列，毫秒级响应。
- 📸 **APFS 本地快照透视**：自动探查 Time Machine 本地快照，解决“删了大量文件可用空间却不涨”的玄学痛点。
- 🎯 **单一规则真源（消除盲区）**：由 `data/rules.json` 驱动，全面覆盖 AI/大模型（HF/Ollama）、现代前端（pnpm/Bun）、移动后端（Gradle/Xcode/SwiftPM/Cargo）及 Application Support 深度缓存。
- 🛡️ **军工级防误删防护体系**：
  - **访达原生放回原处**：调用 macOS Finder 原生接口移动废纸篓，在垃圾桶中随时可以**右键一键“放回原处”**。
  - **符号链接防穿透**：严格检查软链接，若目标为符号链接仅做解绑，绝对不跟随递归穿透删除真实物理目标。
  - **机密凭证二级熔断（Deep Content Guard）**：目录中若潜藏 `.pem`、`.key`、`.env`、`credentials` 等敏感文件，立即自动阻断保护。
  - **Kill Switch 核心物理熔断**：底层硬拦截钥匙串、Cookies、登录态、SQLite 数据库及系统目录。
  - **原生优先与优雅停机**：优先调用官方命令，清理前自动退出关联运行中应用。
- 💻 **双模排版自适应**：终端直接运行时呈现自适应宽字符（CJK 绝对对齐）的 ANSI 彩色界面；Agent 模式无缝输出标准 GitHub Flavored Markdown。
- 💰 **省钱换算战报**：内置苹果 SSD 升配等价换算（512GB = ¥1500），支持 `raccoon history` 查看累计清出空间与累计省下的真金白银。

## 安全设计

| 原则 | 说明 |
|---|---|
| 默认只读 | 第一轮只看不删，先出详尽体检报告 |
| 先认清再删 | 规则库单一真源，查清楚之前坚决不动 |
| 原生命令优先 | 有官方命令（如 `pnpm store prune`）绝不粗暴删目录 |
| 可恢复优先 | 普通目录清理默认安全移入访达废纸篓（支持一键放回原处） |
| 状态不碰 | 登录态、聊天记录、钥匙串由 Kill Switch 硬编码绝对拦截 |
| 防穿透保护 | 符号链接绝不递归穿透删除真实文件，严防越界 |
| 二级深度防御 | 潜藏 `.env`/私钥等机密文件的目录自动熔断拒删 |
| 先退出再动手 | app 运行中先执行优雅退出，避免边删边重建 |
| sudo 交给你 | 系统级路径删除只生成命令，你自己跑，绝不代越权 |

## 安装

### 方式一：一键全功能安装（推荐，兼具 Agent 软链接与终端 CLI）

自动探测系统中的所有 AI Agent 环境（Claude Code、Antigravity、Cursor、Windsurf、Codex、Cline 等），并注册 `raccoon` 终端命令（含 PATH 幂等自愈）：

```bash
curl -fsSL https://raw.githubusercontent.com/tasselx/disk-raccoon/main/install.sh | bash
```

### 方式二：Skills CLI（针对 Agent 场景）

```bash
npx skills add tasselx/disk-raccoon -g
```

### 方式三：npm 全局安装

```bash
npm install -g tasselx/disk-raccoon
```

### 方式四：手动克隆与安装

```bash
git clone https://github.com/tasselx/disk-raccoon.git ~/.config/disk-raccoon
cd ~/.config/disk-raccoon && ./install.sh
```

## 用法

### 1. 在 AI Agent 中（推荐）

直接对 Agent（Claude Code / Antigravity / Cursor 等）说：

- *"帮我看看缓存，磁盘满了"*
- *"飞书和浏览器怎么占了那么大空间"*
- *"确认清理序号 1、3、5"*

Agent 会先调用探针出具只读报告，获得你确认后通过受控命令安全清理。

### 2. 在终端直接作为原生 CLI

```bash
# 极速输出当前缓存体检报告（含 APFS 快照状态，命中快照毫秒级返回）
raccoon

# 交互式安全清理（终端多选序号）
raccoon clean

# 一键清理所有标记为 ✅ 安全 的项目
raccoon clean --all-safe

# 仅演练不实际修改
raccoon clean --dry-run

# 查看累计战报与省钱账本
raccoon history

# 仅查看大于 200MB 的项目
raccoon --min-mb=200
```

## 实战记录

| 缓存分类 | 涉及项目 | 典型释放空间 |
|---|---|---|
| **Python / 前端包缓存** | `~/.cache/uv`、`pnpm store`、`npm`、`Bun` | **50 ~ 80 GB** |
| **移动端与后端构建** | `~/.gradle/caches`、Xcode `DerivedData`、Archives、旧模拟器 | **30 ~ 60 GB** |
| **Chromium 离线缓存** | Chrome / Edge / Arc 的 Service Worker | **20 ~ 50 GB** |
| **IM 与办公通讯** | 飞书 `aha/profile_explorer`、Telegram media | **30 ~ 50 GB** |
| **AI / 深度学习框架** | Hugging Face Hub、PyTorch 权重 | **10 ~ 40 GB** |

## 参与贡献

缓存地图是活的。如果你发现了新的流氓缓存大户或避坑指南，欢迎在 `data/rules.json` 中添加规则并提 PR，让这只小浣熊越来越懂 Mac 硬盘 🦝！

## License

MIT
