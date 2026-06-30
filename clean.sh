#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/lb"
echo "[CipherOS] Cleaning build environment..."
cd "${BUILD_DIR}" || { echo "Cannot enter lb dir"; exit 1; }
if [[ "${1:-}" == "--full" ]]; then
    echo "[CipherOS] Full clean — removing all cached packages and chroot"
    lb clean --all 2>/dev/null || true
    lb clean --purge 2>/dev/null || true
else
    echo "[CipherOS] Standard clean"
    lb clean 2>/dev/null || true
fi
echo "[CipherOS] Clean complete."
