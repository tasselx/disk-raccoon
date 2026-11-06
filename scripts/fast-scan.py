#!/usr/bin/env python3
"""
disk-raccoon fast-scan.py (v0.3.0)
极速 macOS 缓存只读分析探针与军工级安全清理引擎。
- 细粒度多线程并发探针（打满 NVMe 队列）
- APFS 本地快照（Local Snapshots）透视与 Xcode 废弃模拟器检测
- 结构化规则单一真源（data/rules.json）
- 原生 Finder "放回原处"（Put Back）废纸篓集成
- 符号链接越界逃逸（Symlink Traversal）防御
- 敏感机密文件二级深度熔断（Deep Content Guard）
- 并发排他锁（Process Lock）与 Kill Switch 核心物理熔断
- 宽字符（CJK）列宽绝对对齐与终端双模自适应输出
"""

import os
import sys
import time
import glob
import json
import shutil
import unicodedata
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

VERSION = "0.3.0"
DEFAULT_MIN_MB = 50
CACHE_TTL_SECONDS = 120
CACHE_DIR = os.path.expanduser("~/.cache/disk-raccoon")
CACHE_FILE = os.path.join(CACHE_DIR, "scan_cache.json")
HISTORY_FILE = os.path.join(CACHE_DIR, "history.json")
LOCK_FILE = os.path.join(CACHE_DIR, "clean.lock")

# 绝对禁止清理名单（Kill Switch 核心物理熔断）
FORBIDDEN_KEYWORDS = [
    "/system",
    "/usr",
    "/bin",
    "/sbin",
    "/library/keychains",
    "keychains",
    "login state",
    "cookies",
    "accounts.sqlite",
    ".git/objects",
    "/etc",
    "/var/db"
]

# 敏感文件二级特征白名单防御（防止误删隐藏私钥/凭证）
SENSITIVE_FILE_PATTERNS = [
    "*.pem",
    "*.key",
    "*.p12",
    "*.kdbx",
    "id_rsa*",
    "id_ed25519*",
    ".env",
    ".env.local",
    ".env.production",
    "secrets.json",
    "credentials"
]

# ANSI 颜色码
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_RED = "\033[31m"
COLOR_BLUE = "\033[34m"
COLOR_CYAN = "\033[36m"
COLOR_GRAY = "\033[90m"

# 默认内置核心规则兜底
FALLBACK_RULES = [
    {"id": "uv-cache", "category": "dev", "pattern": "~/.cache/uv", "app": "uv (Python)", "level": "✅ 安全", "desc": "Python 包硬链接缓存，下次装包自动重新下载", "suggest": "优先执行 uv cache clean", "native_clean_cmd": "uv cache clean", "kill_process": None},
    {"id": "npm-cache", "category": "dev", "pattern": "~/.npm", "app": "npm", "level": "✅ 安全", "desc": "npm 离线包缓存", "suggest": "执行 npm cache clean --force", "native_clean_cmd": "npm cache clean --force", "kill_process": None},
    {"id": "pnpm-store-lib", "category": "dev", "pattern": "~/Library/pnpm/store", "app": "pnpm", "level": "✅ 安全", "desc": "pnpm 全局内容寻址包仓库", "suggest": "优先执行 pnpm store prune", "native_clean_cmd": "pnpm store prune", "kill_process": None},
    {"id": "pip-cache", "category": "dev", "pattern": "~/Library/Caches/pip", "app": "pip", "level": "✅ 安全", "desc": "pip 离线包缓存", "suggest": "执行 pip cache purge", "native_clean_cmd": "pip cache purge", "kill_process": None},
    {"id": "gradle-cache", "category": "dev", "pattern": "~/.gradle/caches", "app": "Gradle", "level": "✅ 安全", "desc": "Gradle 历史构建缓存与依赖 jar 包", "suggest": "可安全清空 caches 目录", "native_clean_cmd": None, "kill_process": None},
    {"id": "xcode-derived-data", "category": "ide", "pattern": "~/Library/Developer/Xcode/DerivedData", "app": "Xcode", "level": "✅ 安全", "desc": "项目编译产物与索引，下次构建自动重建", "suggest": "直接删除 DerivedData 下内容", "native_clean_cmd": None, "kill_process": "Xcode"},
    {"id": "chrome-service-worker", "category": "browser", "pattern": "~/Library/Application Support/Google/Chrome/*/Service Worker", "app": "Chrome", "level": "✅ 安全", "desc": "网页文档/离线缓存，下次打开自动重建", "suggest": "需先退出 Chrome，再清 Service Worker", "native_clean_cmd": None, "kill_process": "Google Chrome"},
    {"id": "lark-profile-explorer", "category": "im", "pattern": "~/Library/Application Support/LarkShell/aha/users/*/profile_explorer", "app": "飞书 (Lark)", "level": "✅ 安全", "desc": "飞书网页文档/预览纯缓存；保留 profile_main", "suggest": "必须先退出飞书全家桶，只清 profile_explorer", "native_clean_cmd": None, "kill_process": "Lark"}
]

def load_rules():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "..", "data", "rules.json"),
        os.path.join(script_dir, "data", "rules.json"),
        os.path.expanduser("~/.config/disk-raccoon/data/rules.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return FALLBACK_RULES

RULES = load_rules()

class SecurityAlertException(Exception):
    """安全深度防御拦截异常"""
    pass

def char_width(c):
    w = unicodedata.east_asian_width(c)
    if w in ('W', 'F'):
        return 2
    return 1

def string_width(s):
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    plain_text = ansi_escape.sub('', s)
    return sum(char_width(c) for c in plain_text)

def pad_text(s, target_width, align="left"):
    current_w = string_width(s)
    pad = max(0, target_width - current_w)
    if align == "right":
        return " " * pad + s
    return s + " " * pad

def format_size(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def calc_savings_cny(bytes_val):
    gb = bytes_val / (1024.0 ** 3)
    cny = (gb / 512.0) * 1500.0
    return round(cny, 1)

def is_forbidden(path):
    norm = os.path.normpath(path).lower()
    for kw in FORBIDDEN_KEYWORDS:
        if kw in norm:
            return True
    return False

def check_sensitive_content(dir_path):
    """深度审查目录中是否潜藏私钥、凭证或敏感机密（Deep Content Guard）"""
    if not os.path.isdir(dir_path):
        return None

    # 仅快速抽样审查顶层及前 2 层关键文件，耗时控制在 10ms 以内
    try:
        for root, dirs, files in os.walk(dir_path):
            rel_depth = root[len(dir_path):].count(os.sep)
            if rel_depth > 2:
                dirs.clear()
                continue
            for f in files:
                f_lower = f.lower()
                for pat in SENSITIVE_FILE_PATTERNS:
                    if glob.fnmatch.fnmatch(f_lower, pat):
                        return os.path.join(root, f)
    except Exception:
        pass
    return None

def get_disk_info():
    try:
        res = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
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
    except Exception:
        pass
    return {}

def get_apfs_snapshots():
    """探测 APFS 本地快照（解决'删了文件可用空间却不涨'的终极隐患）"""
    try:
        res = subprocess.run(["tmutil", "listlocalsnapshots", "/"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            lines = [ln.strip() for ln in res.stdout.strip().split("\n") if ln.strip()]
            # 过滤包含 snapshot 的条目
            snapshots = [ln for ln in lines if "com.apple.TimeMachine" in ln or ln.startswith("20")]
            return snapshots
    except Exception:
        pass
    return []

def du_single_path(path):
    if is_forbidden(path):
        return path, 0
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

    home = os.path.expanduser("~")
    home_cache = os.path.join(home, ".cache")
    if path.startswith(home_cache + "/"):
        sub = path[len(home_cache) + 1:].split("/")[0]
        return {
            "id": f"dotcache-{sub}",
            "app": f".cache/{sub}",
            "level": "✅/⚠️ 分项",
            "desc": f"CLI 缓存子项 ({sub})",
            "suggest": "按应用评估后清理",
            "native_clean_cmd": None,
            "kill_process": None
        }

    lib_caches = os.path.join(home, "Library", "Caches")
    if path.startswith(lib_caches + "/"):
        sub = path[len(lib_caches) + 1:].split("/")[0]
        return {
            "id": f"libcache-{sub}",
            "app": f"Caches/{sub}",
            "level": "✅/⚠️ 分项",
            "desc": f"应用缓存子项 ({sub})",
            "suggest": "应用退出后可清理",
            "native_clean_cmd": None,
            "kill_process": None
        }

    app_support = os.path.join(home, "Library", "Application Support")
    if path.startswith(app_support + "/"):
        rel = path[len(app_support) + 1:]
        sub_app = rel.split("/")[0]
        if "Service Worker" in path or "Code Cache" in path or "Cache" in path:
            return {
                "id": f"appsupport-cache-{sub_app}",
                "app": f"{sub_app} 缓存",
                "level": "✅ 安全",
                "desc": f"{sub_app} 网页/运行中间缓存，切勿删除同级 IndexedDB",
                "suggest": f"完全退出 {sub_app} 后可清理",
                "native_clean_cmd": None,
                "kill_process": sub_app
            }

    return {
        "id": "unknown",
        "app": "未知 / 其它缓存",
        "level": "⚠️ 注意",
        "desc": "未在已知清单中，需先确认应用与可再生性",
        "suggest": "先搞清楚应用归属，查不清切勿删除",
        "native_clean_cmd": None,
        "kill_process": None
    }

def read_snapshot_cache(min_mb):
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
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        data_to_save = dict(data)
        data_to_save["timestamp"] = time.time()
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False)
    except Exception:
        pass

def collect_all_leaf_targets():
    targets = set()

    # 1. 结构化 RULES 中的全部 pattern
    for r in RULES:
        pat = os.path.expanduser(r["pattern"])
        for p in glob.glob(pat):
            if os.path.exists(p) and not is_forbidden(p):
                targets.add(p)

    # 2. ~/.cache 和 ~/Library/Caches 一级子目录
    for container in [os.path.expanduser("~/.cache"), os.path.expanduser("~/Library/Caches")]:
        if os.path.exists(container):
            try:
                with os.scandir(container) as it:
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False) and not is_forbidden(entry.path):
                                targets.add(entry.path)
                        except OSError:
                            pass
            except OSError:
                pass

    # 3. 深度探测 ~/Library/Application Support 下各应用常见缓存子目录 (消除盲区)
    app_sup = os.path.expanduser("~/Library/Application Support")
    if os.path.exists(app_sup):
        try:
            with os.scandir(app_sup) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False) and not is_forbidden(entry.path):
                            for pattern_suffix in [
                                "*/Service Worker",
                                "Service Worker",
                                "Code Cache",
                                "GPUCache"
                            ]:
                                search_pat = os.path.join(entry.path, pattern_suffix)
                                for match_p in glob.glob(search_pat):
                                    if os.path.isdir(match_p) and not is_forbidden(match_p):
                                        targets.add(match_p)
                    except OSError:
                        pass
        except OSError:
            pass

    return list(targets)

def run_scan(min_mb, force_refresh=False):
    min_bytes = min_mb * 1024 * 1024

    if not force_refresh:
        cached = read_snapshot_cache(min_mb)
        if cached:
            filtered_items = [it for it in cached["actionable_items"] if it["bytes"] >= min_bytes]
            total_bytes = sum(x["bytes"] for x in filtered_items)
            cached["actionable_items"] = filtered_items
            cached["total_actionable_bytes"] = total_bytes
            cached["total_actionable_str"] = format_size(total_bytes)
            cached["total_savings_cny"] = calc_savings_cny(total_bytes)
            return cached

    t_start = time.time()
    targets = collect_all_leaf_targets()
    disk_info = get_disk_info()
    snapshots = get_apfs_snapshots()

    raw_results = []
    with ThreadPoolExecutor(max_workers=24) as executor:
        futures = {executor.submit(du_single_path, p): p for p in targets}
        for f in as_completed(futures):
            path, bytes_val = f.result()
            if bytes_val >= min_bytes:
                raw_results.append((path, bytes_val))

    scan_elapsed = time.time() - t_start
    raw_results.sort(key=lambda x: x[1], reverse=True)

    actionable = []
    seen = set()
    idx = 1

    for path, bytes_val in raw_results:
        if path in seen:
            continue
        seen.add(path)
        rule = match_rule_for_path(path)
        actionable.append({
            "id": idx,
            "rule_id": rule.get("id"),
            "path": path,
            "path_display": path.replace(os.path.expanduser("~"), "~"),
            "bytes": bytes_val,
            "size_str": format_size(bytes_val),
            "app": rule.get("app", "未知"),
            "level": rule.get("level", "⚠️ 注意"),
            "desc": rule.get("desc", ""),
            "suggest": rule.get("suggest", ""),
            "native_clean_cmd": rule.get("native_clean_cmd"),
            "kill_process": rule.get("kill_process"),
        })
        idx += 1

    total_bytes = sum(x["bytes"] for x in actionable)

    result_data = {
        "version": VERSION,
        "disk": disk_info,
        "apfs_snapshots": snapshots,
        "threshold_mb": min_mb,
        "scan_time_sec": round(scan_elapsed, 2),
        "total_actionable_bytes": total_bytes,
        "total_actionable_str": format_size(total_bytes),
        "total_savings_cny": calc_savings_cny(total_bytes),
        "actionable_items": actionable,
    }

    write_snapshot_cache(result_data)
    return result_data

def print_tty_report(data, min_mb, from_cache_sec=None, elapsed_sec=None):
    disk_info = data.get("disk", {})
    snapshots = data.get("apfs_snapshots", [])
    actionable = data.get("actionable_items", [])
    total_str = data.get("total_actionable_str", "0 B")
    savings_cny = data.get("total_savings_cny", 0)

    print(f"\n{COLOR_CYAN}{COLOR_BOLD}🦝 硬盘小浣熊 Disk Raccoon (v{VERSION}) — 极速只读体检{COLOR_RESET}\n")

    if disk_info:
        print(f"{COLOR_BOLD}📊 磁盘总览{COLOR_RESET}：总量 {COLOR_CYAN}{disk_info.get('total')}{COLOR_RESET} ｜ 已用 {COLOR_YELLOW}{disk_info.get('used')}{COLOR_RESET} ({disk_info.get('use_pct')}) ｜ 剩余可用 {COLOR_GREEN}{disk_info.get('free')}{COLOR_RESET}")

    if snapshots:
        print(f"{COLOR_YELLOW}📸 发现 {len(snapshots)} 个 APFS 本地快照正在锁定历史空间{COLOR_RESET} {COLOR_GRAY}(加锁的已删文件在快照清除前不会释放，可运行 tmutil listlocalsnapshots / 查看){COLOR_RESET}")

    perf_info = ""
    if from_cache_sec is not None:
        perf_info = f"{COLOR_GRAY}(⚡ 命中 {from_cache_sec}s 前快照，耗时 < 0.01s，加 --refresh 强制重扫){COLOR_RESET}"
    elif elapsed_sec is not None:
        perf_info = f"{COLOR_GRAY}(⚡ 24 线程全速耗时 {elapsed_sec:.2f}s){COLOR_RESET}"

    print(f"{COLOR_BOLD}🎯 待确认清理项目{COLOR_RESET}：预估 {COLOR_GREEN}{COLOR_BOLD}{total_str}{COLOR_RESET} (≥ {min_mb}MB) ｜ 换算省下硬件升配费: {COLOR_YELLOW}{COLOR_BOLD}≈ ¥{savings_cny}{COLOR_RESET} {perf_info}\n")

    col_id_w = 4
    col_size_w = 10
    col_level_w = 8
    col_app_w = 16
    col_path_w = 34
    col_sugg_w = 36

    header = (
        pad_text("#", col_id_w) + " " +
        pad_text("大小", col_size_w) + " " +
        pad_text("安全级", col_level_w) + " " +
        pad_text("所属应用", col_app_w) + " " +
        pad_text("路径", col_path_w) + " " +
        pad_text("清理建议 / 原生方案", col_sugg_w)
    )
    print(f"{COLOR_BOLD}{COLOR_GRAY}{'-' * string_width(header)}{COLOR_RESET}")
    print(f"{COLOR_BOLD}{header}{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GRAY}{'-' * string_width(header)}{COLOR_RESET}")

    for it in actionable:
        lvl_color = COLOR_GREEN if "✅" in it["level"] else COLOR_YELLOW
        lvl_display = f"{lvl_color}{it['level']}{COLOR_RESET}"

        p_disp = it["path_display"]
        if string_width(p_disp) > col_path_w:
            p_disp = p_disp[:col_path_w - 3] + "..."

        s_disp = it["suggest"]
        if string_width(s_disp) > col_sugg_w:
            s_disp = s_disp[:col_sugg_w - 3] + "..."

        row = (
            pad_text(str(it["id"]), col_id_w) + " " +
            pad_text(it["size_str"], col_size_w) + " " +
            pad_text(lvl_display, col_level_w) + " " +
            pad_text(it["app"], col_app_w) + " " +
            pad_text(p_disp, col_path_w) + " " +
            pad_text(s_disp, col_sugg_w)
        )
        print(row)

    print(f"{COLOR_BOLD}{COLOR_GRAY}{'-' * string_width(header)}{COLOR_RESET}")
    print(f"\n{COLOR_GREEN}💡 终端安全清理提示：{COLOR_RESET}")
    print(f"  • 执行交互式清理: {COLOR_CYAN}raccoon clean{COLOR_RESET}")
    print(f"  • 一键安全清全部 ✅ 项: {COLOR_CYAN}raccoon clean --all-safe{COLOR_RESET}")
    print(f"  • 仅演练不真删: {COLOR_CYAN}raccoon clean --dry-run{COLOR_RESET}\n")

def print_markdown_report(data, min_mb, from_cache_sec=None, elapsed_sec=None):
    disk_info = data.get("disk", {})
    snapshots = data.get("apfs_snapshots", [])
    actionable = data.get("actionable_items", [])
    total_str = data.get("total_actionable_str", "0 B")
    savings_cny = data.get("total_savings_cny", 0)

    print(f"# 🦝 小浣熊高速只读体检报告 (v{VERSION})\n")

    if disk_info:
        print(f"**磁盘总览**：总量 `{disk_info.get('total')}` ｜ 已用 `{disk_info.get('used')}` ({disk_info.get('use_pct')}) ｜ 剩余可用 `{disk_info.get('free')}`")

    if snapshots:
        print(f"> 📸 **APFS 快照提示**：检测到系统存在 `{len(snapshots)}` 个 APFS 本地快照，已删文件空间在快照自动清除前可能被锁定。")

    perf_info = ""
    if from_cache_sec is not None:
        perf_info = f" *(⚡ 命中 {from_cache_sec} 秒前快照，耗时 < 0.01s，加 `--refresh` 可强制重扫)*"
    elif elapsed_sec is not None:
        perf_info = f" *(⚡ 24 线程全速扫描耗时 {elapsed_sec:.2f}s)*"

    print(f"**发现可释放目标**：预估 **{total_str}**（仅统计 ≥ {min_mb}MB 的有效缓存项）｜ 等价省下硬件升配费: **≈ ¥{savings_cny}**{perf_info}\n")

    print("### 🎯 待确认清理项（Actionable Targets）")
    print("| 序号 | 占用大小 | 安全等级 | 所属应用 / 项目 | 路径 | 清理建议 / 影响 |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")

    for it in actionable:
        native_hint = f" `[{it['native_clean_cmd']}]`" if it.get("native_clean_cmd") else ""
        print(f"| {it['id']} | **{it['size_str']}** | {it['level']} | {it['app']} | `{it['path_display']}` | {it['suggest']}{native_hint} ({it['desc']}) |")

    print("\n> 🛡️ **安全提示**：当前为**只读分析**，未执行任何删除。如需清理，可告诉我序号为您安全处理，或直接在终端运行 `raccoon clean`。")

def record_history(freed_bytes, items_cleaned):
    os.makedirs(CACHE_DIR, exist_ok=True)
    history = {"total_freed_bytes": 0, "total_sessions": 0, "sessions": []}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass

    history["total_freed_bytes"] += freed_bytes
    history["total_sessions"] += 1
    history["sessions"].append({
        "timestamp": time.time(),
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "freed_bytes": freed_bytes,
        "freed_str": format_size(freed_bytes),
        "savings_cny": calc_savings_cny(freed_bytes),
        "items": items_cleaned
    })

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def show_history():
    if not os.path.exists(HISTORY_FILE):
        print(f"\n{COLOR_CYAN}🦝 小浣熊还没有执行过清理记录。快运行 `raccoon` 开始第一次极速体检吧！{COLOR_RESET}\n")
        return

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        print("读取历史战报失败。")
        return

    total_b = history.get("total_freed_bytes", 0)
    sessions = history.get("sessions", [])
    savings_cny = calc_savings_cny(total_b)

    print(f"\n{COLOR_CYAN}{COLOR_BOLD}🦝 小浣熊历史战报汇总{COLOR_RESET}\n")
    print(f"累计清理次数：{COLOR_BOLD}{len(sessions)}{COLOR_RESET} 次")
    print(f"累计释放空间：{COLOR_GREEN}{COLOR_BOLD}{format_size(total_b)}{COLOR_RESET}")
    print(f"累计省下升配费：{COLOR_YELLOW}{COLOR_BOLD}≈ ¥{savings_cny}{COLOR_RESET}（按 512GB = ¥1500 换算）\n")

    if sessions:
        print(f"{COLOR_BOLD}最近 5 次清理记录：{COLOR_RESET}")
        for s in sessions[-5:]:
            print(f"  • [{s.get('date')}] 释放 {COLOR_GREEN}{s.get('freed_str')}{COLOR_RESET} (省约 ¥{s.get('savings_cny')})，清理 {len(s.get('items', []))} 个项目")
    print()

def recycle_to_trash_native(path):
    """
    使用 macOS 原生 AppleScript 将文件/目录送入废纸篓。
    支持在访达中随时右键点击'放回原处' (Put Back)。
    """
    abs_path = os.path.abspath(path)
    script = f'''tell application "Finder" to delete POSIX file "{abs_path}"'''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=8)
        if res.returncode == 0:
            return True, "已移入访达废纸篓（支持一键放回原处）"
    except Exception:
        pass

    # 回退方式：移动至 ~/.Trash 并生成安全后缀
    trash_dir = os.path.expanduser("~/.Trash")
    os.makedirs(trash_dir, exist_ok=True)
    basename = os.path.basename(abs_path.rstrip("/"))
    dest_name = f"{basename}_{int(time.time())}"
    dest_path = os.path.join(trash_dir, dest_name)
    shutil.move(abs_path, dest_path)
    return True, f"已安全移入废纸篓 (~/.Trash/{dest_name})"

def safe_clean_path(path, dry_run=False):
    """
    军工级安全清理单项：
    1. 核心物理熔断（Kill Switch）
    2. 符号链接防穿透逃逸（Symlink Traversal Check）
    3. 敏感机密文件二级深度审查（Deep Content Guard）
    4. 原生 Finder 废纸篓放回原处支持
    """
    # 1. Kill Switch 拦截
    if is_forbidden(path):
        raise PermissionError(f"安全拦截：路径命中绝对禁止清单 ({path})")

    if not os.path.exists(path) and not os.path.islink(path):
        return True, "路径已不存在"

    # 真实绝对路径校验：必须完全限制在用户主目录范围内
    real_path = os.path.realpath(path)
    home_dir = os.path.expanduser("~")
    if not real_path.startswith(home_dir + os.sep) and real_path != home_dir:
        raise PermissionError(f"安全拦截：路径穿透逃逸出用户目录 ({real_path})")

    # 2. 符号链接防穿透：若自身为软链接，仅解绑链接自身，绝不跟随删除目标文件
    if os.path.islink(path):
        if dry_run:
            return True, f"[Dry-Run] 仅解绑符号链接自身 (不穿透目标): {path}"
        os.unlink(path)
        return True, "已安全解绑符号链接自身（未触碰指向目标）"

    # 3. 敏感机密文件二级深度审查
    sensitive_found = check_sensitive_content(path)
    if sensitive_found:
        raise SecurityAlertException(f"🛑 安全熔断：在缓存子路径中意外发现机密/凭证文件 ({sensitive_found})，为防误删已自动拦截此目录！")

    if dry_run:
        return True, f"[Dry-Run] 将安全移入访达废纸篓 (支持放回原处): {path}"

    # 4. 原生 Finder 废纸篓执行
    try:
        ok, msg = recycle_to_trash_native(path)
        return ok, msg
    except Exception as e:
        return False, f"清理失败: {str(e)}"

def kill_app_if_running(proc_name, dry_run=False):
    if not proc_name:
        return
    try:
        res = subprocess.run(["pgrep", "-f", proc_name], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            if dry_run:
                print(f"  {COLOR_GRAY}[Dry-Run] 检测到 {proc_name} 运行中，将优雅退出 (pkill -f '{proc_name}'){COLOR_RESET}")
                return
            print(f"  {COLOR_YELLOW}ℹ 正在优雅退出运行中的应用: {proc_name}...{COLOR_RESET}")
            subprocess.run(["pkill", "-f", proc_name], capture_output=True)
            time.sleep(1.5)
    except Exception:
        pass

class ProcessLock:
    """排他进程锁，防止多个 Agent 或终端并发清理冲突"""
    def __enter__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, "r") as f:
                    lock_info = json.load(f)
                lock_pid = lock_info.get("pid")
                # 检查该 pid 是否真在运行
                if lock_pid and os.path.exists(f"/proc/{lock_pid}"):
                    raise RuntimeError(f"另一个清理任务正在执行中 (PID: {lock_pid})")
            except (RuntimeError, PermissionError) as e:
                raise e
            except Exception:
                pass
        with open(LOCK_FILE, "w") as f:
            json.dump({"pid": os.getpid(), "time": time.time()}, f)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except Exception:
            pass

def run_clean_flow(target_ids=None, all_safe=False, dry_run=False):
    with ProcessLock():
        print(f"\n{COLOR_CYAN}🔍 正在执行清理前最新状态校验...{COLOR_RESET}")
        scan_data = run_scan(min_mb=DEFAULT_MIN_MB, force_refresh=True)
        items = scan_data.get("actionable_items", [])

        if not items:
            print(f"{COLOR_GREEN}✓ 磁盘非常整洁，未发现 ≥ {DEFAULT_MIN_MB}MB 的目标。{COLOR_RESET}")
            return

        to_clean = []
        if all_safe:
            to_clean = [it for it in items if "✅" in it["level"]]
        elif target_ids:
            to_clean = [it for it in items if it["id"] in target_ids]
        else:
            print_tty_report(scan_data, min_mb=DEFAULT_MIN_MB)
            print(f"{COLOR_BOLD}请输入要清理的序号 (多个用逗号隔开，输入 'all-safe' 清理所有 ✅ 项，输入 'q' 退出):{COLOR_RESET} ", end="")
            try:
                user_input = input().strip()
            except (KeyboardInterrupt, EOFError):
                print("\n已取消。")
                return

            if not user_input or user_input.lower() == 'q':
                print("已取消操作。")
                return

            if user_input.lower() == 'all-safe':
                to_clean = [it for it in items if "✅" in it["level"]]
            else:
                try:
                    selected_ids = {int(x.strip()) for x in user_input.split(",") if x.strip()}
                    to_clean = [it for it in items if it["id"] in selected_ids]
                except ValueError:
                    print(f"{COLOR_RED}❌ 输入格式无效。{COLOR_RESET}")
                    return

        if not to_clean:
            print(f"{COLOR_YELLOW}未选择任何有效清理项。{COLOR_RESET}")
            return

        est_bytes = sum(x["bytes"] for x in to_clean)
        print(f"\n{COLOR_BOLD}准备清理以下 {len(to_clean)} 项，预估释放: {COLOR_GREEN}{format_size(est_bytes)}{COLOR_RESET}{COLOR_BOLD} (省约 ¥{calc_savings_cny(est_bytes)}):{COLOR_RESET}")
        for it in to_clean:
            print(f"  • [{it['id']}] {it['app']} ({it['size_str']}) - {it['path_display']}")

        if dry_run:
            print(f"\n{COLOR_YELLOW}{COLOR_BOLD}⚠️  当前处于演练模式 (Dry-Run)，不会进行实际修改。{COLOR_RESET}\n")

        cleaned_success = []
        cleaned_bytes = 0

        for it in to_clean:
            print(f"\n{COLOR_CYAN}👉 正在处理 [{it['id']}] {it['app']}...{COLOR_RESET}")

            # 1. 优雅退出进程
            if it.get("kill_process"):
                kill_app_if_running(it["kill_process"], dry_run=dry_run)

            # 2. 原生命令优先
            if it.get("native_clean_cmd"):
                cmd = it["native_clean_cmd"]
                if dry_run:
                    print(f"  {COLOR_GRAY}[Dry-Run] 执行原生命令: {cmd}{COLOR_RESET}")
                    cleaned_success.append(it["app"])
                    cleaned_bytes += it["bytes"]
                else:
                    print(f"  ⚡ 优先调用原生清理: {COLOR_BOLD}{cmd}{COLOR_RESET}")
                    try:
                        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                        if res.returncode == 0:
                            print(f"  {COLOR_GREEN}✓ 原生清理成功完成{COLOR_RESET}")
                            cleaned_success.append(it["app"])
                            cleaned_bytes += it["bytes"]
                        else:
                            print(f"  {COLOR_YELLOW}⚠️ 原生命令退出码非 0，进入安全废纸篓兜底...{COLOR_RESET}")
                            ok, msg = safe_clean_path(it["path"], dry_run=False)
                            print(f"  {COLOR_GREEN if ok else COLOR_RED}{msg}{COLOR_RESET}")
                            if ok:
                                cleaned_success.append(it["app"])
                                cleaned_bytes += it["bytes"]
                    except SecurityAlertException as sae:
                        print(f"  {COLOR_RED}{sae}{COLOR_RESET}")
                    except Exception as e:
                        print(f"  {COLOR_RED}执行失败: {e}{COLOR_RESET}")
            else:
                # 3. 移入访达废纸篓
                try:
                    ok, msg = safe_clean_path(it["path"], dry_run=dry_run)
                    print(f"  {COLOR_GREEN if ok else COLOR_RED}{msg}{COLOR_RESET}")
                    if ok:
                        cleaned_success.append(it["app"])
                        cleaned_bytes += it["bytes"]
                except SecurityAlertException as sae:
                    print(f"  {COLOR_RED}{sae}{COLOR_RESET}")
                except Exception as e:
                    print(f"  {COLOR_RED}安全拦截: {e}{COLOR_RESET}")

        if not dry_run and cleaned_bytes > 0:
            record_history(cleaned_bytes, cleaned_success)
            run_scan(min_mb=DEFAULT_MIN_MB, force_refresh=True)

        print(f"\n{COLOR_GREEN}{COLOR_BOLD}🎉 处理完毕！{COLOR_RESET}")
        print(f"共释放空间: {COLOR_GREEN}{COLOR_BOLD}{format_size(cleaned_bytes)}{COLOR_RESET} ｜ 为您的 Mac 累计省下硬件升配费: {COLOR_YELLOW}{COLOR_BOLD}≈ ¥{calc_savings_cny(cleaned_bytes)}{COLOR_RESET}\n")

def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print(f"🦝 disk-raccoon v{VERSION} - macOS 极速缓存体检与安全清理工具\n")
        print("用法:")
        print("  raccoon [子命令] [选项]\n")
        print("子命令:")
        print("  scan (默认)        极速只读体检，输出带安全分级的分析报告")
        print("  clean              安全受控清理（原生命令优先 + 访达一键放回原处 + 敏感文件二级熔断）")
        print("  history            查看小浣熊累计战报与省钱账本")
        print("\n选项:")
        print("  --min-mb=<MB>      设置报告的最小体积阈值（默认 50MB）")
        print("  --refresh, -r      强制刷新，跳过本地 2 分钟快照")
        print("  --all-safe         (clean 专享) 一键安全清理所有 ✅ 安全 项")
        print("  --target=<IDs>     (clean 专享) 指定清理项序号，如 --target=1,3")
        print("  --dry-run          (clean 专享) 演练模式，仅打印清理动作而不真删")
        print("  --md               强制以 GitHub Flavored Markdown 格式输出")
        print("  --json             以完整 JSON 格式输出")
        print("  -h, --help         显示此帮助信息\n")
        print("示例:")
        print("  raccoon                    # 极速体检")
        print("  raccoon clean              # 终端交互式安全清理")
        print("  raccoon clean --all-safe   # 一键安全清理")
        print("  raccoon history            # 查看累计释放空间与省下金额")
        return

    subcmd = "scan"
    if len(sys.argv) > 1 and sys.argv[1] in ["scan", "clean", "history"]:
        subcmd = sys.argv[1]

    if subcmd == "history":
        show_history()
        return

    json_output = "--json" in sys.argv
    force_refresh = "--refresh" in sys.argv or "-r" in sys.argv
    force_md = "--md" in sys.argv
    dry_run = "--dry-run" in sys.argv
    all_safe = "--all-safe" in sys.argv

    min_mb = DEFAULT_MIN_MB
    target_ids = None

    for arg in sys.argv:
        if arg.startswith("--min-mb="):
            try:
                min_mb = int(arg.split("=")[1])
            except ValueError:
                pass
        elif arg.startswith("--target="):
            try:
                target_ids = {int(x.strip()) for x in arg.split("=")[1].split(",") if x.strip()}
            except ValueError:
                pass

    if subcmd == "clean":
        run_clean_flow(target_ids=target_ids, all_safe=all_safe, dry_run=dry_run)
        return

    data = run_scan(min_mb=min_mb, force_refresh=force_refresh)

    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    is_tty = sys.stdout.isatty() and not force_md
    from_cache_sec = data.get("cache_age_sec") if data.get("from_cache") else None
    elapsed_sec = data.get("scan_time_sec") if not data.get("from_cache") else None

    if is_tty:
        print_tty_report(data, min_mb=min_mb, from_cache_sec=from_cache_sec, elapsed_sec=elapsed_sec)
    else:
        print_markdown_report(data, min_mb=min_mb, from_cache_sec=from_cache_sec, elapsed_sec=elapsed_sec)

if __name__ == "__main__":
    main()
