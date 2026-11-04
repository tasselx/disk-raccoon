#!/usr/bin/env python3
"""
disk-raccoon fast-scan.py (v0.2.1)
极速 macOS 缓存只读分析探针。
采用细粒度原子并发任务 + 动态快照缓存，全盘大头缓存毫秒级响应。
"""

import os
import sys
import time
import glob
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

VERSION = "0.2.1"
DEFAULT_MIN_MB = 50
CACHE_TTL_SECONDS = 120  # 快照默认有效时间 2 分钟
CACHE_FILE = os.path.expanduser("~/.cache/disk-raccoon/scan_cache.json")

# 匹配 cache-map.md 的规则库
RULES = [
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

def du_single_path(path):
    """单个叶子路径的极速探查，带超时保护"""
    try:
        res = subprocess.run(["du", "-sk", path], capture_output=True, text=True, timeout=8)
        if res.returncode == 0 and res.stdout:
            kb = int(res.stdout.split()[0])
            return path, kb * 1024
    except Exception:
        pass
    return path, 0

def match_rule_for_path(path):
    for r in RULES:
        pat = os.path.expanduser(r["pattern"])
        if glob.fnmatch.fnmatch(path, pat) or path == pat or path.startswith(pat + "/"):
            return r

    # 针对 ~/.cache/*
    home_cache = os.path.expanduser("~/.cache")
    if path.startswith(home_cache + "/"):
        sub = path[len(home_cache) + 1:].split("/")[0]
        return {
            "app": f".cache/{sub}",
            "level": "✅/⚠️ 分项",
            "desc": f"CLI 缓存子项 ({sub})",
            "suggest": "按应用评估后清理",
        }

    # 针对 ~/Library/Caches/*
    lib_caches = os.path.expanduser("~/Library/Caches")
    if path.startswith(lib_caches + "/"):
        sub = path[len(lib_caches) + 1:].split("/")[0]
        return {
            "app": f"Caches/{sub}",
            "level": "✅/⚠️ 分项",
            "desc": f"应用缓存子项 ({sub})",
            "suggest": "应用退出后可清理",
        }

    return {
        "app": "未知 / 其它缓存",
        "level": "⚠️ 注意",
        "desc": "未在已知安全清单中，需查明应用后操作",
        "suggest": "先确认应用可否重新生成该缓存",
    }

def read_snapshot_cache(min_mb):
    """尝试读取有效时间内的本地快照"""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cached_time = data.get("timestamp", 0)
        age = time.time() - cached_time
        if age < CACHE_TTL_SECONDS:
            data["from_cache"] = True
            data["cache_age_sec"] = int(age)
            return data
    except Exception:
        pass
    return None

def write_snapshot_cache(data):
    """保存快照"""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        data_to_save = dict(data)
        data_to_save["timestamp"] = time.time()
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False)
    except Exception:
        pass

def collect_all_leaf_targets():
    """极速收集所有需要扫描的叶子目录（不把大聚合目录作为单线程黑盒）"""
    targets = set()

    # 1. 明确的已知目标
    for r in RULES:
        pat = os.path.expanduser(r["pattern"])
        for p in glob.glob(pat):
            if os.path.exists(p):
                targets.add(p)

    # 2. 细粒度拆解 ~/.cache 和 ~/Library/Caches 的一级子目录
    for container in [os.path.expanduser("~/.cache"), os.path.expanduser("~/Library/Caches")]:
        if os.path.exists(container):
            try:
                with os.scandir(container) as it:
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                targets.add(entry.path)
                        except OSError:
                            pass
            except OSError:
                pass

    return list(targets)

def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print(f"🦝 disk-raccoon v{VERSION} - macOS 极速缓存体检工具\n")
        print("用法:")
        print("  disk-raccoon [选项]\n")
        print("选项:")
        print("  --min-mb=<MB>    设置报告的最小体积阈值（默认 50MB）")
        print("  --refresh, -r    强制刷新，跳过本地 2 分钟快照")
        print("  --json           以 JSON 格式输出")
        print("  -h, --help       显示此帮助信息\n")
        print("示例:")
        print("  disk-raccoon              # 极速输出（命中快照时毫秒级返回）")
        print("  disk-raccoon --refresh    # 强制重新全盘并发扫描")
        print("  raccoon --min-mb=200      # 仅查看 ≥ 200MB 的项")
        return

    json_output = "--json" in sys.argv
    force_refresh = "--refresh" in sys.argv or "-r" in sys.argv
    min_mb = DEFAULT_MIN_MB
    for arg in sys.argv:
        if arg.startswith("--min-mb="):
            try:
                min_mb = int(arg.split("=")[1])
            except ValueError:
                pass

    min_bytes = min_mb * 1024 * 1024

    # 1. 优先检查快照缓存（实现毫秒级瞬间输出）
    if not force_refresh:
        cached = read_snapshot_cache(min_mb)
        if cached:
            # 过滤大于等于当前 min_mb 的项
            filtered_items = [it for it in cached["actionable_items"] if it["bytes"] >= min_bytes]
            total_bytes = sum(x["bytes"] for x in filtered_items)
            cached["actionable_items"] = filtered_items
            cached["total_actionable_bytes"] = total_bytes
            cached["total_actionable_str"] = format_size(total_bytes)

            if json_output:
                print(json.dumps(cached, ensure_ascii=False, indent=2))
                return

            print_report(cached, min_mb, from_cache_sec=cached.get("cache_age_sec"))
            return

    # 2. 毫秒级收集所有原子扫描目标
    t_start = time.time()
    targets = collect_all_leaf_targets()
    disk_info = get_disk_info()

    # 3. 24 线程极致并发扫描（NVMe 多队列全开）
    raw_results = []
    with ThreadPoolExecutor(max_workers=24) as executor:
        futures = {executor.submit(du_single_path, p): p for p in targets}
        for f in as_completed(futures):
            path, bytes_val = f.result()
            if bytes_val >= min_bytes:
                raw_results.append((path, bytes_val))

    scan_elapsed = time.time() - t_start

    # 4. 结果整理与去重
    raw_results.sort(key=lambda x: x[1], reverse=True)
    actionable = []
    seen = set()

    for path, bytes_val in raw_results:
        if path in seen:
            continue
        seen.add(path)
        rule = match_rule_for_path(path)
        actionable.append({
            "path": path,
            "path_display": path.replace(os.path.expanduser("~"), "~"),
            "bytes": bytes_val,
            "size_str": format_size(bytes_val),
            "app": rule["app"],
            "level": rule["level"],
            "desc": rule["desc"],
            "suggest": rule["suggest"],
        })

    total_actionable_bytes = sum(x["bytes"] for x in actionable)

    result_data = {
        "version": VERSION,
        "disk": disk_info,
        "threshold_mb": min_mb,
        "scan_time_sec": round(scan_elapsed, 2),
        "total_actionable_bytes": total_actionable_bytes,
        "total_actionable_str": format_size(total_actionable_bytes),
        "actionable_items": actionable,
    }

    # 写入快照缓存
    write_snapshot_cache(result_data)

    if json_output:
        print(json.dumps(result_data, ensure_ascii=False, indent=2))
        return

    print_report(result_data, min_mb, elapsed_sec=scan_elapsed)

def print_report(data, min_mb, from_cache_sec=None, elapsed_sec=None):
    disk_info = data.get("disk", {})
    actionable = data.get("actionable_items", [])
    total_str = data.get("total_actionable_str", "0 B")

    print(f"# 🦝 小浣熊高速只读体检报告 (v{VERSION})\n")

    if disk_info:
        print(f"**磁盘总览**：总量 `{disk_info.get('total')}` ｜ 已用 `{disk_info.get('used')}` ({disk_info.get('use_pct')}) ｜ 剩余可用 `{disk_info.get('free')}`")

    perf_info = ""
    if from_cache_sec is not None:
        perf_info = f" *(⚡ 命中 {from_cache_sec} 秒前快照，耗时 < 0.01s，加 `--refresh` 可强制重扫)*"
    elif elapsed_sec is not None:
        perf_info = f" *(⚡ 24 线程全速扫描耗时 {elapsed_sec:.2f}s)*"

    print(f"**发现可释放目标**：预估 **{total_str}**（仅统计 ≥ {min_mb}MB 的有效缓存项）{perf_info}\n")

    print("### 🎯 待确认清理项（Actionable Targets）")
    print("| 占用大小 | 安全等级 | 所属应用 / 项目 | 路径 | 清理建议 / 影响 |")
    print("| :--- | :--- | :--- | :--- | :--- |")

    for item in actionable:
        print(f"| **{item['size_str']}** | {item['level']} | {item['app']} | `{item['path_display']}` | {item['suggest']} ({item['desc']}) |")

    print("\n> 🛡️ **安全提示**：当前为**只读分析**，未执行任何删除。请确认要清理的项，我再为您安全执行。")

if __name__ == "__main__":
    main()
