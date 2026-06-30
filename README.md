<!-- Replace OWNER/REPO below with your actual GitHub path once this is pushed. -->

# CipherOS XLVII — Phantom Signal

[![Build CipherOS ISO](https://github.com/OWNER/REPO/actions/workflows/build-iso.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/build-iso.yml)
![Base](https://img.shields.io/badge/base-Kali%20Linux%20(rolling)-557C94)
![Desktop](https://img.shields.io/badge/desktop-Hyprland%20%2F%20Wayland-89B4FA)

AI-integrated Kali Linux live distribution: Hyprland Wayland desktop, a local-first
LLM core via Ollama, voice control, screen-aware AI, persistent memory, and a
self-repairing daemon stack — all wrapped around a standard Kali base so the
usual toolset is still there underneath.

<img src="docs/wallpaper-preview.png" alt="CipherOS default wallpaper" width="720">

## Contents

- [What's in the image](#whats-in-the-image)
- [Building the ISO](#building-the-iso)
- [First boot](#first-boot)
- [Key bindings](#key-bindings-hyprland)
- [CLI reference](#cli-reference)
- [Services](#services)
- [AI models](#ai-models)
- [Project structure](#project-structure)
- [Responsible use](#responsible-use)
- [License](#license)

## What's in the image

```
CipherOS XLVII
├── Base        Kali Linux (kali-rolling)
├── Desktop     Hyprland (Wayland) + AGS v2 shell, SDDM login
├── Terminal    Kitty + ZSH + Starship
├── AI core     Ollama — llama3.1:8b, phi3:mini, moondream, codellama:7b
├── Voice       faster-whisper STT + Piper TTS + openWakeWord
├── Vision      grim + tesseract OCR (background screen reading)
├── Memory      SQLite + ChromaDB vector store, nightly consolidation
└── Daemons     5 systemd services + 2 timers, with a self-repair watchdog
```

The AI core runs as a socket-based daemon (`cipher-ai-core`) that a ReAct-style
agent loop drives against a registered tool set — shell, file I/O, web search,
clipboard, screenshots, input simulation, memory recall/store, and TTS. Voice
goes through wake-word detection → VAD-gated capture → faster-whisper → the
agent → Piper, end to end. A background OCR pass keeps a rolling text capture
of the screen so `cipher screen-ask` has context without an explicit
screenshot step.

## Building the ISO

Building a Kali respin needs three things this can't get from a typical
restricted environment: unrestricted network access to the Kali mirror,
Ollama's registry, and Hugging Face; a live-build version recent enough to
support the flags Kali's own build process uses; and the `kali-archive-keyring`
package so apt can verify the Kali repo's signatures during bootstrap. Two
ways to get there:

### Option A — GitHub Actions (recommended, no Kali box needed)

This repo includes [`.github/workflows/build-iso.yml`](.github/workflows/build-iso.yml),
which runs the build inside the official `kalilinux/kali-rolling` container on
a GitHub-hosted runner — which has the unrestricted internet access the build
needs.

1. Push this repo to GitHub.
2. Go to **Actions → Build CipherOS ISO → Run workflow**.
3. Leave **full_build** unchecked (default) and run it.
4. When it finishes, download the `cipheros-xlvii-iso` artifact from the run
   summary. Pushing a `v*` tag also attaches the ISO to a GitHub Release.

GitHub-hosted runners only have about 14GB of free disk by default, so the
workflow defaults to a **lightweight build**: same desktop, same AI core,
but Ollama models are pulled from the registry on first use instead of being
baked into the image. For a fully offline-ready image with all models
pre-loaded (~13GB extra), check **full_build** and point the workflow at a
self-hosted runner with 40GB+ free disk — edit `runs-on:` in the workflow
file accordingly.

A full build comfortably exceeds GitHub's free-tier minutes on private repos;
on public repos hosted-runner minutes are free. Either way, expect this to
take somewhere between 45 minutes and several hours depending on which path
you take and how busy the Kali mirrors are.

### Option B — Build locally

Run this **on Kali Linux itself** (simplest — the keyring and a current
live-build are already there), or on a Debian host where you've separately
installed `kali-archive-keyring`.

```bash
sudo apt update
sudo apt install -y live-build debootstrap squashfs-tools xorriso \
    isolinux syslinux-utils genisoimage curl git python3 python3-pip \
    apt-transport-https gnupg wget kali-archive-keyring

git clone <your-repo-url> cipheros
cd cipheros
sudo bash build.sh
```

The ISO lands in `output/CipherOS-XLVII-amd64.iso` alongside `.sha256`,
`.sha512`, and `.md5` checksums. `build.sh` calls `apt-get update` and checks
dependencies itself, so the explicit `apt install` above is optional but
saves a round-trip if anything's missing.

```bash
# write it to a USB drive
sudo bash build.sh write /dev/sdX   # replace sdX — this WILL erase the device

# or by hand
sudo dd if=output/CipherOS-XLVII-amd64.iso of=/dev/sdX bs=4M status=progress
```

`bash clean.sh` (or `clean.sh --full`) resets the `lb/` working directory
between builds.

### Build flags

`lb/auto/config` is the single source of truth for live-build flags —
`build.sh` just calls `lb config noauto`, which auto-detects and runs it.
Edit that file, not `build.sh`, if you need to change distro options, boot
parameters, or mirror URLs. The flags there were checked against the current
`lb_config(1)` manpage and a working Kali live-build reference; if you're
running an unusually old live-build (anything pre-dating `--bootloaders`,
`--bootappend-live-failsafe`, or `--debootstrap-options` as plural/long-form
flags), you'll need a newer package — this is a known gap in some
distro-archived `live-build` builds that predate Kali's own conventions by
roughly a decade.

## First boot

1. Log in as `cipher` (default password: `cipher` — **change it immediately**:
   `passwd`).
2. Run `cipher-setup` to personalize (name, language preference).
3. Run `cipher status` to confirm all services are up.
4. Say "Cipher" to activate voice, or press `Super + Space` for push-to-talk.

## Key bindings (Hyprland)

| Binding | Action |
|---|---|
| `Super + Space` | Push-to-talk voice input |
| `Super + A` | Open AI chat in Kitty |
| `Super + /` | Quick ask (fuzzel popup) |
| `Super + Z` | Ask about current screen |
| `Super + Shift + Z` | Read screen aloud |
| `Super + Shift + A` | Open memory viewer |
| `Super + Return` | New Kitty terminal |
| `Super + P` | App launcher (fuzzel) |
| `Print` | Area screenshot |

Full bindings, including window/workspace management and media keys, are in
[`lb/config/includes.chroot/home/cipher/.config/hypr/keybinds.conf`](lb/config/includes.chroot/home/cipher/.config/hypr/keybinds.conf).

## CLI reference

```bash
cipher chat               # Interactive AI chat REPL
cipher chat "your query"  # Single query
cipher voice               # Trigger voice capture
cipher speak "text"        # TTS output
cipher screen-ask          # Ask the AI about the current screen
cipher memory show         # View all memories
cipher memory search foo   # Search memories
cipher memory add "..."    # Store a memory
cipher briefing             # Print today's briefing
cipher briefing --force    # Generate and speak the briefing
cipher status               # Service health check
cipher-setup                # First-boot personalization
```

## Services

| Service | Description |
|---|---|
| `cipher-ai-core` | Main AI daemon — ReAct agent loop over a Unix socket |
| `cipher-voice` | Wake word → VAD capture → STT → AI → TTS pipeline |
| `cipher-screen-reader` | Background OCR every 8s into a shared text buffer |
| `cipher-system-monitor` | CPU/RAM/disk/temp polling → HUD metrics + alerts |
| `cipher-self-repair` | Watchdog that restarts failed CipherOS/system services |
| `cipher-morning-briefing.timer` | Daily spoken briefing at 07:00 |
| `cipher-memory-consolidate.timer` | Nightly memory pruning at 03:00 |
| `ollama` | Local LLM API server (127.0.0.1:11434) |

## AI models

| Model | Role | Size |
|---|---|---|
| `llama3.1:8b` | Primary reasoning | ~5 GB |
| `phi3:mini` | Fast tasks, self-diagnosis | ~2 GB |
| `moondream` | Vision / image analysis | ~1.7 GB |
| `codellama:7b` | Code generation | ~4 GB |
| `nomic-embed-text` | Memory embeddings | ~300 MB |

Skipped entirely on lightweight CI builds (see above) and pulled on first use
instead — `ollama pull <model>` works exactly the same post-install either way.

## Project structure

```
cipheros-build/
├── build.sh                    Master build script
├── clean.sh                    Reset the lb/ working directory
├── build_all.sh                Verify the build tree is complete
├── .github/workflows/
│   └── build-iso.yml           CI build → artifact / Release
└── lb/
    ├── auto/
    │   ├── config               live-build configuration (source of truth)
    │   ├── build                 live-build build trigger
    │   └── clean                  live-build clean trigger
    └── config/
        ├── package-lists/        APT package lists
        ├── hooks/live/            Chroot hooks — Ollama, Piper, Whisper,
        │                          Hyprland, AGS, fonts, branding, SDDM,
        │                          model pre-pull, permissions, cleanup
        └── includes.chroot/
            ├── etc/
            │   ├── cipher/        TOML configs (ai, voice, memory, monitor,
            │   │                  repair, search)
            │   └── systemd/system/   Service + timer units
            ├── usr/local/
            │   ├── bin/            cipher, piper-speak, cipher-voice,
            │   │                   cipher-status, cipher-setup
            │   ├── lib/cipher/     Python AI core (agent, memory, voice,
            │   │                   vision, control, search, monitor, repair,
            │   │                   briefing, HUD)
            │   └── share/cipher/   Wallpaper generator, Piper voice models
            └── home/cipher/
                ├── .zshrc / .zprofile
                └── .config/
                    ├── hypr/        Hyprland — main config, keybinds,
                    │                hyprpaper/hypridle/hyprlock
                    ├── ags/         AGS shell — bar, HUD overlay,
                    │                notifications, SCSS theme
                    ├── kitty/ dunst/ fuzzel/   Terminal, notifications, launcher
                    └── starship.toml
```

## Responsible use

This is a Kali Linux derivative and ships Kali's standard tool metapackages
alongside the AI layer. As with any Kali-based system, only point its tools
at systems and networks you own or are explicitly authorized to test. The
AI core can execute shell commands and simulate input on your own machine
when you ask it to — review `lb/config/includes.chroot/etc/cipher/cipher.conf`
(`[agent]` section) for the permission flags around terminal access, file
operations, and input simulation if you want to tighten or loosen what it's
allowed to do unattended.

## License

No license is currently specified for the CipherOS-specific code in this
repo (everything under `lb/config/includes.chroot/usr/local/`,
`lb/config/hooks/`, and the desktop configs) — add one
(see [choosealicense.com](https://choosealicense.com/)) before treating this
as open source in practice. Kali Linux, Debian, and the upstream projects
this pulls in (Hyprland, AGS/Astal, Ollama, Piper, faster-whisper, and
everything in the Kali package lists) retain their own original licenses
regardless.

---

*CipherOS XLVII — Phantom Signal*
