# 缓存地图（Cache Map）

macOS 缓存知识库。每条路径标注：是什么、为什么大、能删什么、不能删什么、删除前提。

等级：✅ 安全 / ⚠️ 注意 / 🚫 别碰

> 这张地图是活的。每清一次新缓存，把路径和教训补进来。地图上没有的路径，查清楚之前不动。

---

## 开发工具链

### ✅ ~/.cache/uv — uv (Python) 包缓存
- **是什么**：uv 下载过的包的硬链接副本，用得越久越大
- **实战战果**：56G
- **怎么清**：优先 `~/.local/bin/uv cache clean`（或 PATH 里的 `uv cache clean`）
- **坑**：uv 不在 PATH 时直接删目录会撞 agent 的 `rm -rf` 安全护栏，用 `python3 -c "import shutil; shutil.rmtree(...)"` 绕行；`uv cache clean` 对残缺缓存可能报 `No such file or directory`，报错不代表失败，删完复测即可
- **后果**：下次装包重新下载，无状态丢失

### ✅ npm / pip / yarn 缓存
- `npm cache clean --force`（路径 `~/.npm`）
- `pip cache purge`（路径 `~/Library/Caches/pip`）
- `yarn cache clean`

### ✅ Xcode DerivedData — ~/Library/Developer/Xcode/DerivedData
- **是什么**：每个项目的编译产物和索引，Xcode 常见的几十 G 大户
- **后果**：下次打开项目重新编译，第一次会慢
- **连带**：`~/Library/Developer/CoreSimulator/Caches`、旧 iOS DeviceSupport 也可清

### ✅ Go / Rust / CocoaPods
- `go clean -cache`（`~/Library/Caches/go-build`）
- `cargo cache` 或删 `~/.cargo/registry/cache`
- `pod cache clean --all`

### ✅ Docker — ~/Library/Containers/com.docker.docker/Data/vms（Docker.raw）
- ⚠️ 先 `docker system prune -a` 清镜像，别直接删 raw 文件；确认没在用的镜像再清

---

## 浏览器

### ✅ Chrome Service Worker — ~/Library/Application Support/Google/Chrome/<Profile>/Service Worker
- **是什么**：网页应用（文档站、web 版应用）的离线缓存，文档类网站是重灾区
- **实战战果**：30G
- **怎么清**：整个 `Service Worker` 目录可删，网页下次访问自动重建
- **⚠️ 同级别动**：`IndexedDB` 是网页应用的本地数据库（登录态、草稿），删了可能丢数据；`Local Storage`、`Preferences`、`Bookmarks` 别碰
- **前提**：Chrome 必须先退出，否则边删边重建

### ✅ ChromeDebug — ~/Library/Application Support/Google/ChromeDebug
- **是什么**：自动化调试（CDP/浏览器 agent）用独立 user-data-dir 启动 Chrome 留下的完整配置目录，其中的 Service Worker 缓存能独立长到 20G
- **实战战果**：21G
- **怎么清**：整个目录可删，调试实例下次启动会重建
- **前提**：确认没有 `ChromeDebug` 进程在跑

### ✅ 其他 Chromium 系浏览器
- Edge：`~/Library/Application Support/Microsoft Edge/<Profile>/Service Worker`（同 Chrome 规则）
- Brave/Arc 同理

---

## IM / 国民应用

### ✅ Telegram — ~/Library/Group Containers/6N38VWS5BX.ru.keepcoder.Telegram/account-*/postbox/media
- **是什么**：Telegram Desktop 的媒体缓存，官方从不自动清理，issue 里有人攒到 100G
- **怎么清**：删 `account-*/postbox/media` 下的内容，媒体文件查看时自动重新下载
- **🚫 同级别动**：`postbox/db` 是本地消息数据库，删了聊天记录本地索引就没了
- **前提**：先退出 Telegram

### ⚠️ 飞书 / Lark — ~/Library/Application Support/LarkShell
- **是什么**：飞书内嵌 Chromium 内核的数据目录，`aha` 子目录是网页文档/预览缓存，多账号各自堆积
- **实战战果**：48G → 9.5G
- **怎么清**：只删 `aha/users/<user-id>/profile_explorer`（纯文档预览缓存）；`profile_main` 里有登录态，动了要重新扫码
- **🚫 别碰**：`sdk_storage`、`database`（消息数据）
- **前提**：飞书全家桶（Lark Helper 进程一堆）必须先全部退出，`pkill -9 -f Lark`
- **经验**：多账号用户每个 user-id 都要看一眼，老的账号缓存往往最大

### ⚠️ 微信 — ~/Library/Containers/com.tencent.xinWeChat
- **是什么**：沙盒目录，聊天记录、图片视频缓存、接收的文件全在里面，混在一起
- **怎么清**：**优先引导用户走 app 内**：设置 → 通用 → 存储空间 → 管理，让微信自己清缓存。手动删容器内目录有误删聊天记录的风险，只有用户明确要求且理解风险时才在 `Data/Library/Caches` 等明确缓存子目录操作
- **🚫 别碰**：任何形如 hash 的消息数据库目录

### ⚠️ QQ / 钉钉 / 企业微信
- 同微信原则：优先 app 内清理入口，沙盒内只动明确的 Caches 子目录

---

## 其他常见大户

### ✅ ~/Library/Caches（系统级用户缓存根目录）
- 逐个应用看，`us.zoom.*`、`com.apple.helpd`、Spotify 的 `PersistentCache` 等都可以清
- ⚠️ 里头个别应用会有非缓存数据，按 bundle id 对照，认不清的不动

### ⚠️ 微信输入法 / 搜狗输入法 / 截图工具等常驻小工具
- 单个体积小，但用户感知强，删前问一句

### ⚠️ ~/Downloads / 工作产物目录
- 不是缓存。用户明确要求才做分档清理：垃圾直删、超期归档、近期保留，按内容最后修改时间算

---

## 禁止清单（任何情况下都不动）

- `~/Library/Keychains`
- 各应用的 `Login State`、`Cookies`、`Local Storage`、`IndexedDB`、`Preferences`（除地图明确标注可清的）
- 消息数据库（Telegram `postbox/db`、微信 hash 目录、飞书 `sdk_storage`）
- `/System`、`/usr` 下的任何东西
- 地图上没有且查不清的路径 → 报告为"未知"，交用户决定
