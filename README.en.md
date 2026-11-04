# Disk Raccoon 🦝 硬盘小浣熊

<p align="center">
  <a href="./README.md">简体中文</a> ｜ <a href="./README.en.md">English</a>
</p>

An AI skill that cleans up caches on your Mac. Install it for your AI coding assistant, and it will find the cache folders quietly eating tens of gigabytes of your disk, figure out which ones are safe to delete, and clean them up.

Apple solders the SSD to the logic board. Adding 512 GB costs **~$200**. The first time this skill ran, it cleared **135+ GB** overnight, nothing broke. If caches were what filled your disk, one cleanup saves you that upgrade fee. **Probably the most valuable skill in your agent's toolbox.**

## Origin

I ran [Mole](https://github.com/tw93/Mole) on my disk. It found several huge folders, tens of GB each.

Should I delete them?

Inside Lark's cache directory, half was document cache — safe to delete, re-downloads on demand. The other half was login state — delete it and every account needs re-authentication. Chrome was the same: the Service Worker cache was safe, but the IndexedDB right next to it held real web-app data.

Same folder. Half garbage, half state. A broom can tell you what's big. It can't tell you what's safe.

So I let the AI decide. It checked each directory — what app it belongs to, what it stores, what happens if you delete it — and gave me a list. I followed the list, cleared **135+ GB** overnight, nothing broke.

It worked so well, I thought: I have another Mac, and my friends have Macs too. Why not turn this into a skill I can share? That's how this project was born.

## Why a raccoon

Raccoons wash their food before eating. They're the only animal that does this.

They don't refuse to eat. They refuse to eat blind.

Most cleanup tools scan your whole disk, sort by size, and let you tick boxes. The real problem on macOS is different: **big doesn't mean garbage, and garbage doesn't mean big.**

- Lark piles up 42 GB of document cache, buried deep in `LarkShell/aha`, invisible in Finder
- Chrome's Service Worker eats 30 GB, but the IndexedDB next door holds real data
- Telegram's media cache grows past 100 GB — the GitHub issue has been open eight years
- `~/.cache/uv` quietly eats 56 GB

**This skill isn't about deleting. It's about knowing what's safe to delete.** Wash first, eat second.

## It does one thing: caches

Uninstalling apps, managing background processes, system optimization — [Mole](https://github.com/tw93/Mole) 🐹 already does all that, open source and free.

Disk Raccoon only does caches, but does them properly. The core is a cache map (`references/cache-map.md`) that tags every path with a safety level:

- ✅ **Safe to delete**: `~/.cache/uv`, browser Service Workers, Telegram media cache…
- ⚠️ **Delete with care**: Lark `LarkShell/aha` (only delete `profile_explorer`; `profile_main` holds login state), WeChat (use the in-app cleanup instead)…
- 🚫 **Do not touch**: message databases, Keychain, anything that holds state

Path not on the map? Look it up first. If you can't figure out what it is, leave it alone.

## Safety

| Rule | What it means |
|---|---|
| Read-only first | First pass only looks, never deletes. Report comes first |
| Know before you cut | Unknown paths stay untouched until identified |
| Trash over delete | If it can go to Trash, it goes to Trash |
| State is off limits | Login sessions, chat history, Keychain — never touched |
| Quit before cleaning | Close the app first so it doesn't rebuild while you delete |
| sudo is yours | System-level commands are generated, not executed — you run them |

## Install

### Option 1: Skills CLI (Recommended)

Install globally across all supported AI coding agents (Claude Code, Antigravity, Cursor, Codex, Cline, and 20+ more via [skills.sh](https://skills.sh)):

```bash
npx skills add tasselx/disk-raccoon -g
```

> 💡 Omit `-g` if you only want to install it for the current repository: `npx skills add tasselx/disk-raccoon`

### Option 2: Smart Installer (Includes Native Terminal CLI)

Installs across all detected AI agents and registers `disk-raccoon` and `raccoon` commands directly into your shell PATH:

```bash
curl -fsSL https://raw.githubusercontent.com/tasselx/disk-raccoon/main/install.sh | bash
```

### Option 3: Manual Clone & Install

```bash
git clone https://github.com/tasselx/disk-raccoon.git ~/.config/disk-raccoon
cd ~/.config/disk-raccoon && ./install.sh
```

## Usage

Once installed, use it via **AI Agent** or directly as a **Global Terminal CLI**:

### 1. In AI Agents (Recommended)

In any project or terminal, tell your agent (Claude Code / Antigravity / Codex, etc.):

- "Check my caches"
- "Disk is full, what can I clean?"
- "Why is Chrome taking 60GB?"

### 2. Directly as a Terminal CLI

No AI agent required. Run anytime in any terminal for instant reports:

```bash
disk-raccoon              # Instant cache audit report
raccoon --min-mb=200      # Only show items >= 200MB
disk-raccoon --json       # Output JSON for scripts
```
- "Disk is full, what can I clean?"
- "Why is Chrome using 60 GB?"

## Battle log

| Cache | Freed |
|---|---|
| `~/.cache/uv` (Python package cache) | ~56 GB |
| Chrome Service Worker + ChromeDebug | ~51 GB |
| Lark `LarkShell/aha` document cache | ~38 GB |
| **Total** | **135+ GB** |

## Contributing

The cache map is a living document. Every time we clean a new type of cache, we add it. If you've hit a cache folder we haven't covered, open an issue or submit a PR — help this raccoon learn more about your disk 🦝

## License

MIT
