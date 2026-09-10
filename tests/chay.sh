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

# Chon interpreter: venv cua du an; khong co thi cai dau tien CO thu vien du an
# (tren Windows `python3` co the la stub cua Store hoac mot Python khac khong co
# PIL/httpx — 31/38 tep "hong" chi vi chon nham interpreter, khong phai vi ma).
PY="${PY:-}"
if [ -z "$PY" ]; then
  for ung in venv/bin/python python3 python; do
    if "$ung" -c "import httpx, PIL" >/dev/null 2>&1; then PY=$ung; break; fi
  done
  [ -n "$PY" ] || { echo "[LOI] khong tim thay Python nao co httpx+PIL (chay cai_dat.sh?)" >&2; exit 2; }
fi
LOC="${1:-}"

# Cach ly state MAC DINH (audit lượt 2, E-r2-1): khong dat bien thi
# env_load.state_dir() tro ve state/ THAT cua repo, va bao ve chi con trong
# vao tung test tu monkeypatch — hai test subprocess cua test_cong_chan da
# khong. Tu dat o day de "xanh" nghia la xanh trong cach ly, khong phai xanh
# nho ghi tam vao state that roi xoa di.
export CT_STATE_DIR="${CT_STATE_DIR:-$(mktemp -d)}"
# Console Windows cp1252 lam UnicodeEncodeError o dong in ket qua — tuc test
# qua ma tep bao hong. -X utf8 vo hai tren Linux.
PYFLAGS="-X utf8"

hong=0
tong=0
for f in tests/test_*.py; do
  case "$f" in *"$LOC"*) ;; *) continue ;; esac
  tong=$((tong + 1))
  ra=$("$PY" $PYFLAGS "$f" 2>&1)
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
