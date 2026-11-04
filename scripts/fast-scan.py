#!/usr/bin/env python3
"""
disk-raccoon fast-scan.py
高速只读扫描 macOS 常见缓存大户与开发工具产物。
并发探测、单次下钻、自动匹配 references/cache-map.md 的安全等级。
"""

import os
import sys
import glob
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

VERSION = "0.2.0"
DEFAULT_MIN_MB = 50

# 匹配 cache-map.md 的规则与处置建议
RULES = [
    # 开发工具链
    {
        "pattern": "~/.cache/uv",
        "app": "uv (Python)",
        "level": "✅ 安全",
        "desc": "Python 包硬链接缓存，下次装包自动重新下载",
        "suggest": "优先执行 uv cache clean",
    },
    {
        "pattern": "~/.npm",
        "app": "npm",
        "level": "✅ 安全",
        "desc": "npm 离线包缓存",
        "suggest": "执行 npm cache clean --force",
    },
    {
        "pattern": "~/Library/Caches/pip",
        "app": "pip",
        "level": "✅ 安全",
        "desc": "pip 离线包缓存",
        "suggest": "执行 pip cache purge",
    },
    {
        "pattern": "~/.cargo/registry/cache",
        "app": "Rust Cargo",
        "level": "✅ 安全",
        "desc": "crates.io .crate 压缩包缓存，删后按需重新拉取",
        "suggest": "可安全清空 cache 目录",
    },
    {
        "pattern": "~/Library/Caches/go-build",
        "app": "Go Build",
        "level": "✅ 安全",
        "desc": "Go 编译构建缓存",
        "suggest": "执行 go clean -cache",
    },
    {
        "pattern": "~/Library/Developer/Xcode/DerivedData",
        "app": "Xcode",
        "level": "✅ 安全",
        "desc": "项目编译产物与索引，下次构建自动重建，第一次稍慢",
        "suggest": "直接删除 DerivedData 下内容",
    },
    {
        "pattern": "~/Library/Developer/CoreSimulator/Caches",
        "app": "iOS 模拟器",
        "level": "✅ 安全",
        "desc": "模拟器运行时产生的缓存",
        "suggest": "可直接清理",
    },
    {
        "pattern": "~/Library/Caches/CocoaPods",
        "app": "CocoaPods",
        "level": "✅ 安全",
        "desc": "Pods 规格库与下载缓存",
        "suggest": "执行 pod cache clean --all",
    },
    {
        "pattern": "~/Library/Containers/com.docker.docker/Data/vms",
        "app": "Docker VM",
        "level": "⚠️ 注意",
        "desc": "Docker.raw 虚拟机磁盘文件，包含镜像与容器数据",
        "suggest": "切勿直接删 raw，优先执行 docker system prune -a",
    },

    # 浏览器 Service Worker 与调试实例
    {
        "pattern": "~/Library/Application Support/Google/Chrome/*/Service Worker",
        "app": "Chrome",
        "level": "✅ 安全",
        "desc": "网页文档/离线缓存，下次打开自动重建；切勿删除同级 IndexedDB",
        "suggest": "需先完全退出 Chrome，再清 Service Worker",
    },
    {
        "pattern": "~/Library/Application Support/Google/ChromeDebug",
        "app": "ChromeDebug",
        "level": "✅ 安全",
        "desc": "自动化调试遗留的独立 Chrome 配置目录，可完整清除",
        "suggest": "确认无调试实例运行后可直接删除",
    },
    {
        "pattern": "~/Library/Application Support/Microsoft Edge/*/Service Worker",
        "app": "Edge",
        "level": "✅ 安全",
        "desc": "Edge 网页离线缓存，下次打开自动重建",
        "suggest": "需先退出 Edge",
    },
    {
        "pattern": "~/Library/Application Support/Arc/User Data/*/Service Worker",
        "app": "Arc 浏览器",
        "level": "✅ 安全",
        "desc": "Arc 网页离线缓存",
        "suggest": "需先退出 Arc",
    },

    # IM / 国民应用
    {
        "pattern": "~/Library/Group Containers/*Telegram*/account-*/postbox/media",
        "app": "Telegram",
        "level": "✅ 安全",
        "desc": "Telegram 媒体缓存，查阅时自动重新下载；切勿删除旁边的 postbox/db",
        "suggest": "先退出 Telegram 再清理 media 目录",
    },
    {
        "pattern": "~/Library/Application Support/LarkShell/aha/users/*/profile_explorer",
        "app": "飞书 (Lark)",
        "level": "✅ 安全",
        "desc": "飞书网页文档/预览纯缓存；保留 profile_main（保留登录态）",
        "suggest": "必须先退出飞书全家桶 (pkill -9 -f Lark)，只清 profile_explorer",
    },
    {
        "pattern": "~/Library/Containers/com.tencent.xinWeChat/Data/Library/Caches",
        "app": "微信",
        "level": "⚠️ 注意",
        "desc": "微信临时系统缓存；切勿直接删除聊天数据库",
        "suggest": "优先引导走微信 App 内【设置 -> 通用 -> 存储空间】清理",
    },
    {
        "pattern": "~/Library/Caches/com.spotify.client/Data",
        "app": "Spotify",
        "level": "✅ 安全",
        "desc": "歌曲离线流媒体缓存",
        "suggest": "先退出 Spotify 再清空 Data 目录",
    },

    # 顶层聚合目录（用于探查未收录的大头缓存）
    {
        "pattern": "~/.cache",
        "app": "User .cache",
        "level": "✅/⚠️ 分项",
        "desc": "CLI 工具聚合缓存区，建议按子目录清理",
        "suggest": "逐个子目录排查",
        "expand_depth": 1,
    },
    {
        "pattern": "~/Library/Caches",
        "app": "Library/Caches",
        "level": "✅/⚠️ 分项",
        "desc": "应用级缓存根目录，绝大多数应用缓存可清，个别需核对",
        "suggest": "按 Bundle ID 对应清理",
        "expand_depth": 1,
    },
]

def format_size(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def get_disk_info():
    res = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
    lines = res.stdout.strip().split("\n")
    if len(lines) >= 2:
        parts = lines[1].split()
        return {
            "filesystem": parts[0],
            "total": parts[1],
            "used": parts[2],
            "free": parts[3],
            "use_pct": parts[4]
        }
    return {}

def scan_path_du(path, depth=0):
    """使用 macOS 原生 du 一次性探查指定深度大小（单位 KB）"""
    if not os.path.exists(path):
        return []

    cmd = ["du", "-k"]
    if depth > 0:
        cmd += ["-d", str(depth)]
    else:
        cmd += ["-s"]
    cmd.append(path)

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 and not res.stdout:
        return []

    items = []
    lines = res.stdout.strip().split("\n")
    for line in lines:
        parts = line.split("\t", 1)
        if len(parts) == 2:
            try:
                kb = int(parts[0].strip())
                p = parts[1].strip()
                items.append((p, kb * 1024))
            except ValueError:
                continue
    return items

def match_rule_for_path(path):
    # 先做最精确匹配
    home = os.path.expanduser("~")
    for r in RULES:
        if r.get("expand_depth", 0) > 0:
            continue
        pat = os.path.expanduser(r["pattern"])
        if glob.fnmatch.fnmatch(path, pat):
            return r

    # 再处理深层匹配
    for r in RULES:
        pat = os.path.expanduser(r["pattern"])
        if path == pat or path.startswith(pat + "/"):
            return r

    return {
        "app": "未知 / 其它缓存",
        "level": "⚠️ 注意",
        "desc": "未在已知安全清单中，需查明应用后操作",
        "suggest": "先确认应用可否重新生成该缓存",
    }

def main():
    json_output = "--json" in sys.argv
    min_mb = DEFAULT_MIN_MB
    for arg in sys.argv:
        if arg.startswith("--min-mb="):
            try:
                min_mb = int(arg.split("=")[1])
            except ValueError:
                pass

    disk_info = get_disk_info()
    min_bytes = min_mb * 1024 * 1024

    # 1. 展开所有目标任务
    tasks = []
    registered_roots = set()

    for rule in RULES:
        pattern = os.path.expanduser(rule["pattern"])
        depth = rule.get("expand_depth", 0)
        matches = glob.glob(pattern)
        if not matches and os.path.exists(pattern):
            matches = [pattern]

        for m in matches:
            if m not in registered_roots and os.path.exists(m):
                registered_roots.add(m)
                tasks.append((m, depth, rule))

    # 2. 多线程并发扫描
    raw_results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {
            executor.submit(scan_path_du, p, depth): (p, depth, rule)
            for p, depth, rule in tasks
        }
        for future in as_completed(future_map):
            p, depth, rule = future_map[future]
            try:
                items = future.result()
                for item_path, item_bytes in items:
                    if item_bytes >= min_bytes:
                        raw_results.append((item_path, item_bytes))
            except Exception:
                pass

    # 3. 数据去重与父子层级解耦
    # 如果一个聚合目录（如 ~/.cache）下已经列出了多个子目录（如 ~/.cache/frida 8.5G），
    # 避免用户以为可以无脑删 ~/.cache 导致误删其他配置。
    raw_results.sort(key=lambda x: len(x[0]), reverse=True)
    item_map = {}
    for p, b in raw_results:
        if p not in item_map:
            item_map[p] = b

    # 区分“具体可操作项 (Actionable)” 与 “汇总根目录 (Container)”
    containers = {os.path.expanduser("~/.cache"), os.path.expanduser("~/Library/Caches")}
    actionable = []
    summaries = []

    for path, bytes_val in item_map.items():
        matched = match_rule_for_path(path)
        item_entry = {
            "path": path,
            "path_display": path.replace(os.path.expanduser("~"), "~"),
            "bytes": bytes_val,
            "size_str": format_size(bytes_val),
            "app": matched["app"],
            "level": matched["level"],
            "desc": matched["desc"],
            "suggest": matched["suggest"],
        }
        if path in containers:
            summaries.append(item_entry)
        else:
            actionable.append(item_entry)

    actionable.sort(key=lambda x: x["bytes"], reverse=True)
    summaries.sort(key=lambda x: x["bytes"], reverse=True)

    total_actionable_bytes = sum(x["bytes"] for x in actionable)

    if json_output:
        print(json.dumps({
            "version": VERSION,
            "disk": disk_info,
            "threshold_mb": min_mb,
            "total_actionable_bytes": total_actionable_bytes,
            "total_actionable_str": format_size(total_actionable_bytes),
            "actionable_items": actionable,
            "containers": summaries,
        }, ensure_ascii=False, indent=2))
        return

    # 输出 Markdown 报告
    print(f"# 🦝 小浣熊高速只读体检报告 (v{VERSION})\n")
    if disk_info:
        print(f"**磁盘总览**：总量 `{disk_info.get('total')}` ｜ 已用 `{disk_info.get('used')}` ({disk_info.get('use_pct')}) ｜ 剩余可用 `{disk_info.get('free')}`")
    print(f"**发现可释放目标**：预估 **{format_size(total_actionable_bytes)}**（仅统计 ≥ {min_mb}MB 的有效缓存项）\n")

    print("### 🎯 待确认清理项（Actionable Targets）")
    print("| 占用大小 | 安全等级 | 所属应用 / 项目 | 路径 | 清理建议 / 影响 |")
    print("| :--- | :--- | :--- | :--- | :--- |")

    for item in actionable:
        print(f"| **{item['size_str']}** | {item['level']} | {item['app']} | `{item['path_display']}` | {item['suggest']} ({item['desc']}) |")

    if summaries:
        print("\n### 📦 聚合总览（仅供参考父级总大小）")
        for s in summaries:
            print(f"- `{s['path_display']}`: 总体积 **{s['size_str']}**（已在上方拆解具体大头）")

    print("\n> 🛡️ **安全提示**：当前为**只读分析**，未执行任何删除。请确认要清理的项，我再为您安全执行。")

if __name__ == "__main__":
    main()
