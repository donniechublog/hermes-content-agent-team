#!/bin/bash
# Chay TAT CA test va tra ve ma thoat KHAC 0 neu bat ky tep nao hong.
#
# Vi sao can: README truoc 06/09/2026 huong dan
#     for f in tests/*.py; do venv/bin/python $f; done
# Vong nay tra ve ma thoat cua tep CUOI CUNG. test_cong_chan hong ma
# test_tai_lieu qua thi ca lenh van "thanh cong" — dung loai im lang ma cac
# cong chan sinh ra de chan. Khong CI, khong pytest, nen day la luoi duy nhat.
#
# Dung:
#     tests/chay.sh              # tat ca
#     tests/chay.sh cong_chan    # chi cac tep khop chuoi
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

PY=venv/bin/python
[ -x "$PY" ] || PY=python3
LOC="${1:-}"

hong=0
tong=0
for f in tests/test_*.py; do
  case "$f" in *"$LOC"*) ;; *) continue ;; esac
  tong=$((tong + 1))
  ra=$("$PY" "$f" 2>&1)
  ma=$?
  cuoi=$(printf '%s\n' "$ra" | grep -E '[0-9]+/[0-9]+ test qua' | tail -1)
  if [ $ma -eq 0 ]; then
    printf '%-34s %s\n' "$(basename "$f")" "${cuoi:-OK}"
  else
    hong=$((hong + 1))
    printf '%-34s HONG (ma %d)\n' "$(basename "$f")" "$ma"
    printf '%s\n' "$ra" | grep -E '^FAIL|Error|Traceback|  File ' | head -8 | sed 's/^/    /'
  fi
done

if [ "$tong" -eq 0 ]; then
  echo "Khong tep test nao khop ${LOC:-*}"
  exit 2
fi
echo
if [ "$hong" -eq 0 ]; then
  echo "$tong/$tong tep test qua"
  exit 0
fi
echo "$hong/$tong tep test HONG"
exit 1
