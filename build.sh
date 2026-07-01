#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════╗
# ║         CipherOS ISO Master Build Script                     ║
# ║         Version: XLVII — Phantom Signal                      ║
# ╚══════════════════════════════════════════════════════════════╝
set -euo pipefail
IFS=$'\n\t'
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/lb"
OUTPUT_DIR="${SCRIPT_DIR}/output"
LOG_FILE="${SCRIPT_DIR}/build.log"
ISO_NAME="CipherOS-XLVII-amd64.iso"
BUILD_START=$(date +%s)

log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*" | tee -a "${LOG_FILE}"; }
ok()   { echo -e "${GREEN}[  OK]${NC} $*" | tee -a "${LOG_FILE}"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "${LOG_FILE}"; }
err()  { echo -e "${RED}[FAIL]${NC} $*" | tee -a "${LOG_FILE}"; exit 1; }

banner() {
cat <<'BANNER'
  ██████╗██╗██████╗ ██╗  ██╗███████╗██████╗  ██████╗ ███████╗
 ██╔════╝██║██╔══██╗██║  ██║██╔════╝██╔══██╗██╔═══██╗██╔════╝
 ██║     ██║██████╔╝███████║█████╗  ██████╔╝██║   ██║███████╗
 ██║     ██║██╔═══╝ ██╔══██║██╔══╝  ██╔══██╗██║   ██║╚════██║
 ╚██████╗██║██║     ██║  ██║███████╗██║  ██║╚██████╔╝███████║
  ╚═════╝╚═╝╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
          XLVII — Phantom Signal — Autonomous AI OS
BANNER
}

check_deps() {
    log "Checking build dependencies..."
    apt-get update >> "${LOG_FILE}" 2>&1 || warn "apt-get update failed — package index may be stale."
    local deps=(live-build debootstrap squashfs-tools xorriso isolinux
                syslinux-utils genisoimage curl git python3 python3-pip
                apt-transport-https gnupg wget kali-archive-keyring)
    for dep in "${deps[@]}"; do
        dpkg -l "$dep" &>/dev/null || apt-get install -y "$dep" >> "${LOG_FILE}" 2>&1 \
            || err "Failed to install dependency: $dep (if this is kali-archive-keyring and you're not on Kali, see README.md 'Build prerequisites')"
    done
    ok "All build dependencies satisfied."
}

setup_lb() {
    log "Configuring live-build for CipherOS XLVII..."

    mkdir -p "${BUILD_DIR}" "${OUTPUT_DIR}"
    cd "${BUILD_DIR}"

    # Start from a completely clean live-build state
    lb clean --purge || true
    rm -rf config cache .build

    chmod +x auto/config

    log "Running lb/auto/config directly..."
    ./auto/config

    log "Verifying configuration..."
    if ! grep -R "kali-rolling" . >/dev/null 2>&1; then
        err "live-build was not configured for kali-rolling."
    fi

    ok "live-build configured."
}

build_iso() {
    log "Starting ISO build — this will take 45-120 minutes..."
    cd "${BUILD_DIR}"
    lb build noauto 2>&1 | tee -a "${LOG_FILE}"
    local iso
    iso=$(find "${BUILD_DIR}" -maxdepth 2 -name "*.iso" | head -1)
    [[ -z "$iso" ]] && err "ISO not produced. Check ${LOG_FILE}"
    mv "$iso" "${OUTPUT_DIR}/${ISO_NAME}"
    cd "${OUTPUT_DIR}"
    sha256sum "${ISO_NAME}" > "${ISO_NAME}.sha256"
    sha512sum "${ISO_NAME}" > "${ISO_NAME}.sha512"
    md5sum    "${ISO_NAME}" > "${ISO_NAME}.md5"
    local size elapsed
    size=$(du -sh "${OUTPUT_DIR}/${ISO_NAME}" | cut -f1)
    elapsed=$(( $(date +%s) - BUILD_START ))
    ok "══════════════════════════════════════════════"
    ok " ISO: ${OUTPUT_DIR}/${ISO_NAME}"
    ok " Size: ${size}"
    ok " SHA256: $(cut -d' ' -f1 "${OUTPUT_DIR}/${ISO_NAME}.sha256")"
    ok " Build time: $((elapsed/60))m $((elapsed%60))s"
    ok "══════════════════════════════════════════════"
}

write_usb() {
    local dev="${1:-}"
    [[ -z "$dev" ]] && { echo "Usage: $0 write /dev/sdX"; exit 1; }
    warn "This will ERASE ${dev}. Press Ctrl+C within 5 seconds to abort..."
    sleep 5
    dd if="${OUTPUT_DIR}/${ISO_NAME}" of="$dev" bs=4M status=progress oflag=sync
    sync && ok "Written to $dev"
}

main() {
    banner
    [[ "$(id -u)" -ne 0 ]] && err "Run as root: sudo bash build.sh"
    case "${1:-build}" in
        build)  check_deps; setup_lb; build_iso ;;
        clean)  cd "${BUILD_DIR}" && lb clean --purge ;;
        write)  write_usb "${2:-}" ;;
        *)      echo "Usage: $0 [build|clean|write /dev/sdX]" ;;
    esac
}
main "$@"
