# Disk Raccoon 🦝 硬盘小浣熊

<p align="center">
  <a href="./README.md">简体中文</a> ｜ <a href="./README.en.md">English</a>
</p>

> macOS cache-cleaning agent. It washes its food before it eats.

Apple solders the SSD to the logic board. Adding 512 GB costs **~$200**.

First time this skill ran, it cleared **135+ GB** of caches from my machine. One evening, nothing broke.

When caches fill your disk, you end up paying Apple for a bigger one. That's the money this raccoon saves you. **Probably the most valuable skill in your agent's toolbox.**

## Origin

I ran [Mole](https://github.com/tw93/Mole) on my disk. It found several huge folders, a few GB each.

Should I delete them?

Inside Lark's cache directory, half was document cache — safe to delete, re-downloads on demand. The other half was login state — delete it and every account needs re-authentication. Chrome was the same story: the Service Worker cache was safe, but the IndexedDB right next to it held web-app data.

Same folder. Half garbage, half state. A broom can tell you what's big. It can't tell you what's safe.

So I let the AI decide. This skill is that decision, written down: what's safe to delete, how far to go, and what to quit first. First run cleared **135+ GB**, nothing broke.

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

Disk Raccoon only does caches, but it does them properly. The core is a cache map (`references/cache-map.md`) that tags every path with a safety level:

- ✅ **Safe**: `~/.cache/uv`, browser Service Workers, Telegram media cache…
- ⚠️ **Careful**: Lark `LarkShell/aha` (only delete `profile_explorer`; `profile_main` holds login state), WeChat (use the in-app cleanup instead)…
- 🚫 **Don't touch**: message databases, Keychain, anything that holds state

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

```bash
git clone https://github.com/orange2ai/disk-raccoon ~/.claude/skills/disk-raccoon
```

Works with any agent that supports SKILL.md (Claude Code, Cola, etc.).

## Usage

Tell your agent:

- "Check my caches"
- "Disk is full, what can I clean?"
- "Why is Chrome using 60 GB?"

## Battle log

| Cache | Freed |
|---|---|
| `~/.cache/uv` (Python package cache) | ~56 GB |
| Chrome Service Worker + ChromeDebug | ~51 GB |
| Lark `LarkShell/aha` document cache | ~38 GB |
| **Total** | **135+ GB** |

Apple charges ~$200 per 512 GB storage upgrade. If caches were what filled your disk, one cleanup saves you that money.

## License

MIT
