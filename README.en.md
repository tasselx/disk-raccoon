# Disk Raccoon 🦝 硬盘小浣熊

<p align="center">
  <a href="./README.md">简体中文</a> ｜ <a href="./README.en.md">English</a>
</p>

An AI skill and ultra-fast terminal CLI that cleans up caches on your Mac. Install it for your AI coding assistant, and it will find the cache folders quietly eating tens of gigabytes of your disk, figure out which ones are safe to delete, and clean them up safely.

Apple solders the SSD to the logic board. Adding 512 GB costs **~$200 (¥1500)**. The first time this skill ran, it cleared **135+ GB** overnight, nothing broke. If caches were what filled your disk, one cleanup saves you that upgrade fee. **Probably the most valuable skill in your agent's toolbox.**

## Origin

I ran [Mole](https://github.com/tw93/Mole) on my disk. It found several huge folders, tens of GB each.

Should I delete them?

Inside Lark's cache directory, half was document cache — safe to delete, re-downloads on demand. The other half was login state — delete it and every account needs re-authentication. Chrome was the same: the Service Worker cache was safe, but the IndexedDB right next to it held real web-app data.

Same folder. Half garbage, half state. A broom can tell you what's big. It can't tell you what's safe.

So I let the AI decide. It checked each directory — what app it belongs to, what it stores, what happens if you delete it — and gave me a list. I followed the list, cleared **135+ GB** overnight, nothing broke.

It worked so well, I turned this into a dual-mode project featuring both an **AI Agent Skill** and a **Native Terminal CLI**.

## Why a raccoon

Raccoons wash their food before eating. They're the only animal that does this.

They don't refuse to eat. They refuse to eat blind.

Most cleanup tools scan your whole disk, sort by size, and let you tick boxes. The real problem on macOS is different: **big doesn't mean garbage, and garbage doesn't mean big.**

- Lark piles up 42 GB of document cache, buried deep in `LarkShell/aha`, invisible in Finder
- Chrome's Service Worker eats 30 GB, but the IndexedDB next door holds real data
- Telegram's media cache grows past 100 GB — the GitHub issue has been open eight years
- `~/.cache/uv` quietly eats 56 GB; `~/.gradle/caches` builds up 40+ GB of historical jars
- `pnpm store` unpruned packages and `Bun` cache fill up small SSDs

**This tool isn't about deleting. It's about knowing what's safe to delete.** Wash first, eat second.

## It does one thing: caches, done properly

Uninstalling apps, managing background processes, system optimization — [Mole](https://github.com/tw93/Mole) 🐹 already does all that, open source and free.

Disk Raccoon only does caches, but does them properly. Powered by a single structured truth (`data/rules.json`) and cache map (`references/cache-map.md`), it marks clear safety levels:

- ✅ **Safe to delete**: `uv`, `pnpm store`, `Gradle`, browser Service Workers, Telegram media, Xcode builds, Hugging Face Hub models, Cargo source…
- ⚠️ **Delete with care**: Lark `LarkShell/aha` (only delete `profile_explorer`; `profile_main` holds login sessions), Xcode Archives, Ollama (clean by model), WeChat (in-app cleanup recommended)…
- 🚫 **Never touch**: message databases, Keychains, session stores (enforced by a built-in Kill Switch)

Path not on the map? Look it up first. If you can't figure out what it is, leave it alone.

## Highlights (v0.3.0 Ultimate)

- ⚡ **2-Second Ultra-Fast Scan**: Multi-threaded probe (`scripts/fast-scan.py`) saturates Apple Silicon NVMe I/O queues.
- 📸 **APFS Local Snapshots Insight**: Automatically detects Time Machine local snapshots locking disk space.
- 🎯 **Single Source of Truth (No Blind Spots)**: Powered by `data/rules.json`, covering AI/LLMs (HF/Ollama), modern frontend (pnpm/Bun), mobile/backend (Gradle/Xcode/SwiftPM/Cargo), and Application Support depths.
- 🛡️ **Military-Grade Safety Defenses**:
  - **Native Finder "Put Back" Support**: Moves items via Finder AppleScript, allowing one-click **"Put Back"** from the macOS Trash.
  - **Symlink Traversal Protection**: Symlinks are strictly unlinked without recursing into target directories.
  - **Deep Content Guard**: Automatically halts and alerts if directories secretly contain `.pem`, `.key`, `.env`, or credential files.
  - **Kill Switch & Concurrency Lock**: Hardcoded physical blockage for Keychains/databases, with process mutex locks.
  - **Native First**: Prioritizes official CLI cleanup tools (`pnpm store prune`, `uv cache clean`, etc.).
- 💻 **Adaptive Dual-Mode Output**: High-quality ANSI color output with wide-character (CJK) alignment in interactive terminals; standard GFM Markdown for AI Agents.
- 💰 **Savings Calculator & Battle Log**: Converts freed space into estimated hardware cost savings ($200 per 512GB), tracked via `raccoon history`.

## Safety

| Rule | What it means |
|---|---|
| Read-only first | First pass only looks, never deletes. Detailed audit report comes first |
| Single source of truth | Known rules guide every action; unknown paths stay untouched |
| Native commands first | Runs official cleanup commands (e.g. `pnpm store prune`) whenever available |
| Native Trash with Put Back | Items go through Finder Trash and can be restored with "Put Back" |
| Anti-traversal | Symlinks are unlinked without deleting target contents |
| Deep Content Guard | Subdirectories with `.env` or private keys trigger immediate safety aborts |
| State is off limits | Login sessions, chat history, Keychain — hardcoded Kill Switch |
| Quit before cleaning | Close the app first so it doesn't rebuild while you delete |
| sudo is yours | System-level commands are generated, not executed — you run them |

## Install

### Option 1: Smart Installer (Recommended — Agent Symlinks & Native Terminal CLI)

Installs across 20+ detected AI agents (Claude Code, Antigravity, Cursor, Windsurf, Codex, Cline, etc.) and registers `raccoon` into your shell PATH:

```bash
curl -fsSL https://raw.githubusercontent.com/tasselx/disk-raccoon/main/install.sh | bash
```

### Option 2: Skills CLI (For AI Agents)

```bash
npx skills add tasselx/disk-raccoon -g
```

### Option 3: Global npm Install

```bash
npm install -g tasselx/disk-raccoon
```

### Option 4: Manual Clone & Install

```bash
git clone https://github.com/tasselx/disk-raccoon.git ~/.config/disk-raccoon
cd ~/.config/disk-raccoon && ./install.sh
```

## Usage

### 1. In AI Agents (Recommended)

In any project or terminal, tell your agent:

- *"Check my caches, disk is full"*
- *"Why is Chrome taking so much space?"*
- *"Confirm cleaning targets 1, 3, 5"*

### 2. Directly as a Terminal CLI

```bash
# Instant cache audit report (includes APFS snapshots)
raccoon

# Interactive terminal cleanup
raccoon clean

# Clean all items marked as ✅ Safe
raccoon clean --all-safe

# Dry-run mode (preview without deleting)
raccoon clean --dry-run

# View cumulative battle log and money saved
raccoon history

# Only show items >= 200MB
raccoon --min-mb=200
```

## Contributing

The cache map is a living document. If you hit a new cache folder or caveat, add it to `data/rules.json` and submit a PR — help this raccoon learn more about your disk 🦝!

## License

MIT
