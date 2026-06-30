#!/usr/bin/env bash
# CipherOS — bash -n syntax check for all shell scripts (build infra + hooks)
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
total=0
errors=0

check() {
    local f="$1"
    total=$((total + 1))
    if bash -n "$f" 2>/tmp/bnerr.txt; then
        echo -e "  ${GREEN}OK${NC}  $f"
    else
        echo -e "  ${RED}FAIL${NC} $f"
        cat /tmp/bnerr.txt
        errors=$((errors + 1))
    fi
}

echo "=== Top-level build scripts ==="
check build.sh
check clean.sh
check build_all.sh
check verify_python.sh

echo ""
echo "=== lb/auto/ scripts ==="
check lb/auto/config
check lb/auto/build
check lb/auto/clean

echo ""
echo "=== Chroot hooks (lb/config/hooks/live/) ==="
while IFS= read -r -d '' f; do
    check "$f"
done < <(find lb/config/hooks/live -name "*.hook.chroot" -print0 | sort -z)

rm -f /tmp/bnerr.txt

echo ""
echo "================================================"
echo "Checked: $total   Errors: $errors"
if [[ $errors -eq 0 ]]; then
    echo -e "${GREEN}All shell scripts passed syntax validation.${NC}"
    exit 0
else
    echo -e "${RED}$errors file(s) failed validation.${NC}"
    exit 1
fi
