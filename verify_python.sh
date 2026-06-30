#!/usr/bin/env bash
# CipherOS — Python syntax verification for all shipped modules
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
total=0
errors=0

echo "=== Python syntax validation ==="

while IFS= read -r -d '' f; do
    total=$((total + 1))
    if python3 -m py_compile "$f" 2>/tmp/pyerr.txt; then
        echo -e "  ${GREEN}OK${NC}  $f"
    else
        echo -e "  ${RED}FAIL${NC} $f"
        cat /tmp/pyerr.txt
        errors=$((errors + 1))
    fi
done < <(find lb/config/includes.chroot/usr/local/lib/cipher -name "*.py" -print0)

echo ""
echo "=== Shell-script CLI tools (bash -n syntax check) ==="
for f in lb/config/includes.chroot/usr/local/bin/piper-speak \
         lb/config/includes.chroot/usr/local/bin/cipher-voice \
         lb/config/includes.chroot/usr/local/bin/cipher-status \
         lb/config/includes.chroot/usr/local/bin/cipher-setup; do
    total=$((total + 1))
    if bash -n "$f" 2>/tmp/sherr.txt; then
        echo -e "  ${GREEN}OK${NC}  $f"
    else
        echo -e "  ${RED}FAIL${NC} $f"
        cat /tmp/sherr.txt
        errors=$((errors + 1))
    fi
done

echo ""
echo "=== Python CLI entrypoint (cipher) ==="
total=$((total + 1))
if python3 -m py_compile lb/config/includes.chroot/usr/local/bin/cipher 2>/tmp/pyerr2.txt; then
    echo -e "  ${GREEN}OK${NC}  cipher"
else
    echo -e "  ${RED}FAIL${NC} cipher"
    cat /tmp/pyerr2.txt
    errors=$((errors + 1))
fi

rm -f /tmp/pyerr.txt /tmp/pyerr2.txt /tmp/sherr.txt

echo ""
echo "================================================"
echo "Checked: $total   Errors: $errors"
if [[ $errors -eq 0 ]]; then
    echo -e "${GREEN}All files passed syntax validation.${NC}"
    exit 0
else
    echo -e "${RED}$errors file(s) failed validation.${NC}"
    exit 1
fi
