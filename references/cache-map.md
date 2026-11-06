# 缓存地图（Cache Map v0.3.0）

macOS 缓存知识库。每条路径标注：所属类别、安全等级、为什么大、清理建议、原生清理命令与避坑事项。

安全等级说明：
- ✅ **安全**：可再生缓存、包下载缓存或离线资源，清理后应用按需自动重建或重新拉取。
- ⚠️ **注意**：包含部分关键配置、本地权重或易混淆目录（如数据库与登录态混在同级），需按指定范围操作。
- 🚫 **别碰**：绝对禁止清单，包含登录态、本地消息数据库、钥匙串等核心数据。

> 🦝 **小浣熊原则**：这张地图由 `data/rules.json` 结构化驱动。未在地图上且查不清的应用目录，查清楚之前坚决不动。

---

## 1. 🤖 AI / 深度学习框架

### ✅ ~/.cache/huggingface/hub — Hugging Face Hub 权重
- **是什么**：Transformers / Diffusers 预训练模型与数据集权重缓存，单模型动辄数 GB 到数十 GB。
- **怎么清**：可安全清理不需要的模型权重目录；也可使用 `huggingface-cli delete-cache` 交互式清理。
- **后果**：下次调用该模型时会自动从 Hub 重新下载。

### ⚠️ ~/.ollama/models — Ollama 本地模型
- **是什么**：Ollama 本地大模型权重（blob 文件集合），体积通常在 20GB ~ 100GB+。
- **怎么清**：**切勿直接暴力删除 blob 目录**，优先执行 `ollama list` 查看模型，使用 `ollama rm <模型名>` 精确卸载废弃模型。
- **后果**：删掉的模型无法离线运行，需重新 `ollama pull`。

### ✅ ~/.cache/torch — PyTorch 权重缓存
- **是什么**：torchvision、torchaudio 模型权重与 Hub 扩展缓存。
- **怎么清**：可安全清空 `checkpoints` 或 hub 目录。

---

## 2. 🛠️ 开发工具链与包管理器

### ✅ ~/.cache/uv — uv (Python) 包缓存
- **实战战果**：单机最高释放 56GB。
- **怎么清**：优先调用 `uv cache clean`；若不在 PATH 中可清理该目录。
- **后果**：下次安装包重新在线拉取，无状态丢失。

### ✅ npm / pnpm / yarn / Bun / pip
- **pnpm** (`~/Library/pnpm/store` / `~/.local/share/pnpm/store`)：优先执行 `pnpm store prune`，安全清理全局未被引用的包。
- **npm** (`~/.npm`)：执行 `npm cache clean --force`。
- **pip** (`~/Library/Caches/pip`)：执行 `pip cache purge`。
- **Yarn** (`~/.yarn/berry/cache` 或 `~/Library/Caches/Yarn`)：执行 `yarn cache clean`。
- **Bun** (`~/.bun/install/cache`)：可直接删除缓存目录。

### ✅ Gradle / Maven / Go / Rust / SwiftPM / CocoaPods
- **Gradle** (`~/.gradle/caches`)：Android/Java 构建大户，常年累积几十 GB。清空后下次构建会自动重新拉取 wrapper 和 jar 包。
- **Maven** (`~/.m2/repository`)：⚠️ 本地依赖仓库。仅建议在磁盘极度紧张或依赖包损坏时选择性清理。
- **Go** (`~/Library/Caches/go-build`)：执行 `go clean -cache`。
- **Rust Cargo** (`~/.cargo/registry/cache` 与 `~/.cargo/registry/src`)：压缩包与解压后的依赖源码，删后按需重新拉取/解压。
- **SwiftPM** (`~/Library/Caches/org.swift.swiftpm`)：Swift Package Manager 依赖克隆与二进制工件。
- **CocoaPods** (`~/Library/Caches/CocoaPods`)：执行 `pod cache clean --all`。
- **Homebrew** (`~/Library/Caches/Homebrew`)：执行 `brew cleanup -s`。

---

## 3. 💻 IDE 与移动端开发

### ✅ Xcode DerivedData — ~/Library/Developer/Xcode/DerivedData
- **是什么**：项目编译产物、模块中间缓存与索引，Xcode 动辄几十 GB 的常客。
- **后果**：下次构建重新生成索引，首次构建稍慢。
- **连带安全项**：`~/Library/Developer/CoreSimulator/Caches`（模拟器运行时缓存）。

### ⚠️ Xcode Archives — ~/Library/Developer/Xcode/Archives
- **是什么**：历史打包归档，包含 dSYM 调试符号。已发版且废弃的老项目归档可选择性清理。

### ⚠️ Xcode iOS DeviceSupport — ~/Library/Developer/Xcode/iOS DeviceSupport
- **是什么**：连接过的实体 iPhone 符号表。每个旧系统版本都会留下数 GB 符号文件。
- **怎么清**：可安全删除旧机型/旧版本 iOS 符号目录。

### ✅ Cursor / VS Code workspaceStorage
- **路径**：`~/Library/Application Support/Cursor/User/workspaceStorage` 与 `~/Library/Application Support/Code/User/workspaceStorage`。
- **是什么**：历史打开过的所有项目的语言服务器索引与临时状态。
- **前提**：必须先退出编辑器再清理。

---

## 4. 🌐 浏览器与 Chromium 系应用

### ✅ Chrome / Edge / Arc / Brave Service Worker
- **路径**：`~/Library/Application Support/<Browser>/<Profile>/Service Worker`
- **是什么**：网页应用（文档站、Figma、Notion 等）离线网页缓存。
- **⚠️ 同级禁动**：`IndexedDB` 存放网页本地草稿和状态，绝对不可删除！
- **前提**：浏览器必须先完全退出，避免边删边重建。

### ✅ ChromeDebug — ~/Library/Application Support/Google/ChromeDebug
- **是什么**：自动化脚本或 Agent 独立启动调试浏览器留下的孤立配置目录。
- **怎么清**：确认无调试实例后可整体删除。

---

## 5. 💬 办公通讯与音视频应用

### ✅ Telegram 媒体缓存
- **路径**：`~/Library/Group Containers/*Telegram*/account-*/postbox/media`
- **是什么**：查看过的群组图片与视频缓存。
- **🚫 绝对别碰**：旁边的 `postbox/db`（本地消息数据库）。

### ⚠️ 飞书 (Lark) — aha / Cache
- **路径**：`~/Library/Application Support/LarkShell/aha/users/*/profile_explorer`
- **核心避坑**：只删 `profile_explorer`（纯文档预览缓存）；**切勿删除 `profile_main`**（包含登录凭证）；**切勿碰 `sdk_storage` 与 `database`**。
- **前提**：飞书全家桶进程必须先全部退出 (`pkill -9 -f Lark`)。

### ⚠️ 微信 (WeChat)
- **路径**：`~/Library/Containers/com.tencent.xinWeChat/Data/Library/Caches`
- **原则**：**强烈建议优先走微信 App 内【设置 -> 通用 -> 存储空间】清理**。
- **小程序安全项**：`WeChatApp` 离线小程序包在退出微信后可安全清理。
- **🚫 绝对别碰**：任何 hash 命名的消息数据库与聊天记录。

---

## 6. 🛑 军工级防误删防护体系

小浣熊内置四重安全防线：
1. **Kill Switch 核心物理熔断**：坚决拒绝碰触 `~/Library/Keychains`、`Cookies`、`Login State`、数据库文件及系统目录。
2. **符号链接防穿透（Symlink Traversal Check）**：对软链接本身仅做解除绑定，绝对不跟随软链接递归删除真实目标文件。
3. **敏感机密二级熔断（Deep Content Guard）**：清理前抽样审查，若发现目录内潜藏 `.pem`、`.key`、`.env`、`credentials` 等凭证文件，立即自动阻断保护。
4. **访达原生“放回原处”支持**：普通目录移入废纸篓采用 macOS 原生 Finder 动作，用户可在废纸篓随时右键“放回原处”。
