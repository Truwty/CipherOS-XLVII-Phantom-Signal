#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════╗
# ║   CipherOS XLVII — Final Assembly & Verification Script      ║
# ║   Run this to verify the build tree is complete              ║
# ╚══════════════════════════════════════════════════════════════╝
set -euo pipefail
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

pass=0; fail=0
check() {
    local label="$1" path="$2"
    if [[ -e "${BASE}/${path}" ]]; then
        echo -e "  ${GREEN}✔${NC}  ${label}"
        pass=$((pass+1))
    else
        echo -e "  ${RED}✘${NC}  ${label}  → ${path}"
        fail=$((fail+1))
    fi
}

echo -e "\n${BOLD}${CYAN}CipherOS XLVII — Build Tree Verification${NC}\n"

echo "Build scripts:"
check "build.sh"                          "build.sh"
check "clean.sh"                          "clean.sh"
check "lb/auto/config"                    "lb/auto/config"
check "lb/auto/build"                     "lb/auto/build"
check "lb/auto/clean"                     "lb/auto/clean"

echo "Package lists:"
for f in kali cipher-base cipher-wayland cipher-ai cipher-dev cipher-security; do
    check "$f.list.chroot" "lb/config/package-lists/$f.list.chroot"
done

echo "Chroot hooks:"
for h in 0010 0020 0030 0040 0050 0060 0070 0080 0090 0100 0110 0120 0130 0140 9999; do
    count=$(ls "${BASE}/lb/config/hooks/live/${h}-"*.hook.chroot 2>/dev/null | wc -l)
    if [[ $count -gt 0 ]]; then
        echo -e "  ${GREEN}✔${NC}  Hook ${h}"
        pass=$((pass+1))
    else
        echo -e "  ${RED}✘${NC}  Hook ${h} missing"
        fail=$((fail+1))
    fi
done

echo "Systemd units:"
SD="${BASE}/lb/config/includes.chroot/etc/systemd/system"
for svc in cipher-ai-core.service cipher-voice.service cipher-screen-reader.service \
           cipher-system-monitor.service cipher-self-repair.service ollama.service \
           cipher-morning-briefing.service cipher-morning-briefing.timer \
           cipher-memory-consolidate.service cipher-memory-consolidate.timer; do
    check "$svc" "lb/config/includes.chroot/etc/systemd/system/$svc"
done

echo "Config files:"
for cfg in cipher.conf voice.conf memory.conf monitor.conf repair.conf search.conf; do
    check "/etc/cipher/$cfg" "lb/config/includes.chroot/etc/cipher/$cfg"
done

echo "Python AI core:"
LIB="${BASE}/lb/config/includes.chroot/usr/local/lib/cipher"
for f in core/ai_core.py core/agent.py core/context_manager.py core/tool_registry.py \
         core/event_bus.py voice/audio_pipeline.py voice/stt_engine.py \
         voice/tts_engine.py voice/wake_word.py vision/screen_reader.py \
         control/system_control.py memory/memory_store.py memory/consolidator.py \
         search/search_engine.py monitor/system_monitor.py repair/self_repair.py \
         briefing/morning_briefing.py hud/hud_server.py \
         utils/logger.py utils/config_loader.py utils/lang_detect.py; do
    check "$f" "lb/config/includes.chroot/usr/local/lib/cipher/$f"
done

echo "CLI tools:"
for b in cipher piper-speak cipher-voice cipher-status cipher-setup; do
    check "/usr/local/bin/$b" "lb/config/includes.chroot/usr/local/bin/$b"
done

echo "Desktop configs:"
HC="${BASE}/lb/config/includes.chroot/home/cipher/.config/hypr"
check "hyprland.conf"  "lb/config/includes.chroot/home/cipher/.config/hypr/hyprland.conf"
check "keybinds.conf"  "lb/config/includes.chroot/home/cipher/.config/hypr/keybinds.conf"
check "hyprpaper.conf" "lb/config/includes.chroot/home/cipher/.config/hypr/hyprpaper.conf"
check "hypridle.conf"  "lb/config/includes.chroot/home/cipher/.config/hypr/hypridle.conf"
check "hyprlock.conf"  "lb/config/includes.chroot/home/cipher/.config/hypr/hyprlock.conf"
check "kitty.conf"     "lb/config/includes.chroot/home/cipher/.config/kitty/kitty.conf"
check "dunstrc"        "lb/config/includes.chroot/home/cipher/.config/dunst/dunstrc"
check "fuzzel.ini"     "lb/config/includes.chroot/home/cipher/.config/fuzzel/fuzzel.ini"
check "starship.toml"  "lb/config/includes.chroot/home/cipher/.config/starship.toml"
check ".zshrc"         "lb/config/includes.chroot/home/cipher/.zshrc"
check ".zprofile"      "lb/config/includes.chroot/home/cipher/.zprofile"

echo "AGS shell:"
for f in config.ts widgets/Bar.tsx widgets/CipherHUD.tsx widgets/Notifications.tsx \
          style.scss package.json tsconfig.json; do
    check "$f" "lb/config/includes.chroot/home/cipher/.config/ags/$f"
done

echo "SDDM theme:"
check "Main.qml"    "lb/config/includes.chroot/usr/share/sddm/themes/cipheros/Main.qml"
check "theme.conf"  "lb/config/includes.chroot/usr/share/sddm/themes/cipheros/theme.conf"

echo "GitHub / repo hygiene:"
check ".github/workflows/build-iso.yml"  ".github/workflows/build-iso.yml"
check ".gitignore"                        ".gitignore"
check "docs/wallpaper-preview.png"        "docs/wallpaper-preview.png"
check "README.md"                          "README.md"

echo ""
TOTAL=$((pass + fail))
echo -e "${BOLD}Results: ${GREEN}${pass}/${TOTAL} files present${NC}"
[[ $fail -gt 0 ]] && echo -e "${YELLOW}Missing: ${fail} files${NC}" || \
    echo -e "${GREEN}Build tree is complete.${NC}"
echo ""
echo -e "Next step:  ${CYAN}sudo bash build.sh${NC}"
echo ""
