# Disk Raccoon 🦝 硬盘小浣熊

<p align="center">
  <a href="./README.md">简体中文</a> ｜ <a href="./README.en.md">English</a>
</p>

> macOS cache-cleaning agent. It washes its food before it eats.

Apple's SSD is soldered to the logic board. Upgrading one tier (512 GB) costs **¥1500** (~$200).

The first time this skill ran, it cleared **135+ GB** of caches from my machine — overnight, with zero incidents.

When caches fill up your disk, you eventually do what Apple wants: pay for the next storage tier. That's exactly what this raccoon saves you. **It might be the most valuable skill in your agent's toolbox — from ¥1500 up.**

## Origin

I ran [Mole](https://github.com/tw93/Mole) on my disk. It found several huge folders, a few GB each.

Now — delete, or not?

Inside Lark's cache directory, one part is document cache: safe to delete, re-downloads on demand. Another part is login state: delete it and every account needs re-authentication. Same with Chrome: the Service Worker cache is safe to remove, but the IndexedDB next door holds web-app data. One folder, half garbage, half state.

A broom can measure size. It can't tell you what's safe to touch.

So I let the AI make the call. This skill is that judgment, written down: where each type of cache lives, how far you can delete, which app to quit first, and what re-downloads afterwards. First run: **135+ GB cleared overnight**, zero incidents.

## Why a raccoon

The raccoon is the only animal that washes its food before eating.

It doesn't refuse to eat. It refuses to eat blindly.

Most cleanup tools work like this: scan everything, list the big stuff, let the user check boxes. But the real problem on macOS is: **big ≠ garbage, and garbage ≠ big.**

- Lark accumulates 42 GB of document cache, buried deep in `LarkShell/aha`, invisible in Finder
- Chrome's Service Worker eats 30 GB — but the IndexedDB next door loses web-app data if deleted
- Telegram's media cache grows past 100 GB; the official issue has been open for eight years
- `~/.cache/uv` quietly consumes 56 GB

**The soul of this skill isn't deleting — it's knowing what can be deleted.** Wash first, then eat.

## It does one thing: caches

No app uninstalling, no background management, no system tweaks — that's [Mole](https://github.com/tw93/Mole) 🐹 territory: a great broom, open source, free.

Disk Raccoon does caches, all the way down: **where every cache lives, how far it can be deleted, which app to quit first, and what re-downloads afterwards.** The judgment lives in a continuously maintained cache map (`references/cache-map.md`), with every path tagged at one of three safety levels:

- ✅ **Safe**: `~/.cache/uv`, browser Service Workers, Telegram media cache…
- ⚠️ **Caution**: Lark `LarkShell/aha` (delete only `profile_explorer`; `profile_main` holds login state), WeChat (prefer in-app cleanup)…
- 🚫 **Hands off**: message databases, Keychain, anything holding "state"

What about a path that's not on the map? Figure out what it is first. Until then, not a single byte moves.

## Safety design

| Principle | Meaning |
|---|---|
| Read-only by default | First pass touches nothing; report comes first |
| Identify before deleting | Paths not on the map stay untouched until verified |
| Recoverable first | Anything that can go to Trash, goes to Trash |
| State is sacred | Login state, message databases, Keychain — never touched |
| No cutting while running | Quit the app first; never delete while it rebuilds |
| sudo separation | System-level deletions become commands for the user to run |

## Install

Drop this repo into your agent's skills directory:

```bash
git clone https://github.com/orange2ai/disk-raccoon ~/.claude/skills/disk-raccoon
```

Works with any agent that supports the SKILL.md protocol (Claude Code, Cola, etc.).

## Usage

Tell your agent:

- "Run a cache health check"
- "My disk is full — what caches can be cleared?"
- "Why is Chrome taking up 60 GB?"

## Battle record

| Cache | Freed |
|---|---|
| `~/.cache/uv` (Python package cache) | ~56 GB |
| Chrome Service Worker + ChromeDebug leftovers | ~51 GB |
| Lark `LarkShell/aha` document cache | ~38 GB |
| **Total** | **135+ GB** |

At Apple's upgrade pricing (512 GB per tier, ¥1500), that 135 GB is a decent chunk of flash-money. If your disk was filled to the point of forcing an upgrade, this skill saves you the whole tier.

## License

MIT
