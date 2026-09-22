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
#     tests/run.sh              # tat ca
#     tests/run.sh cong_chan    # chi cac tep khop chuoi
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
  [ -n "$PY" ] || { echo "[LOI] khong tim thay Python nao co httpx+PIL (chay setup.sh?)" >&2; exit 2; }
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

# Tran thoi gian MOI tep (22/09/2026): test_round_brand_always_run lot mot pha
# goi mang that, treo qua 180s tren may chu, va mot `tests/run.sh` chay nen chet o
# tep 119/187 khong kip in dong ket — tuc khong ai biet tep nao hong. Co tran thi
# tep treo bao HONG va run chay tiep toi dong "N/M". Tat: TEST_TIMEOUT=0. May
# khong co `timeout` (macOS tron) thi chay khong tran, nhu truoc.
TEST_TIMEOUT="${TEST_TIMEOUT:-300}"
TRAN=()
if [ "$TEST_TIMEOUT" != 0 ] && command -v timeout >/dev/null 2>&1; then
  TRAN=(timeout "$TEST_TIMEOUT")
fi

hong=0
tong=0
for f in tests/test_*.py; do
  case "$f" in *"$LOC"*) ;; *) continue ;; esac
  tong=$((tong + 1))
  ra=$(${TRAN[@]+"${TRAN[@]}"} "$PY" $PYFLAGS "$f" 2>&1)
  ma=$?
  cuoi=$(printf '%s\n' "$ra" | grep -E '[0-9]+/[0-9]+ test qua' | tail -1)
  if [ $ma -eq 0 ]; then
    printf '%-34s %s\n' "$(basename "$f")" "${cuoi:-OK}"
  else
    hong=$((hong + 1))
    if [ ${#TRAN[@]} -gt 0 ] && [ $ma -eq 124 ]; then
      printf '%-34s HONG (qua %ss, bi dung — treo/goi mang that?)\n' "$(basename "$f")" "$TEST_TIMEOUT"
    else
      printf '%-34s HONG (ma %d)\n' "$(basename "$f")" "$ma"
    fi
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
