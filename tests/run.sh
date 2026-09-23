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
# DON RAC TAM (LOW-382, 23/09/2026). Do tren may chu: /tmp la tmpfs (tuc RAM)
# va dang co ~1800 thu muc `tmp*` moi ngay, 2.2 GB — phan lon la
# `tempfile.mkdtemp()` cua chinh bo test (19 tep, 41 cho goi) khong tu don,
# cong `CT_STATE_DIR` cua moi luot chay. May don cua he (systemd-tmpfiles) chi
# quet theo tuoi moi ngay nen rac nam lai rat lau TRONG RAM.
#
# Dat TMPDIR ve MOT thu muc cua rieng luot chay nay: moi mkdtemp/NamedTemporaryFile
# cua test deu roi vao day (Python doc TMPDIR), don mot lan la sach ca — khong
# phai sua 41 cho goi trong 19 tep. Chi don thu CHINH minh tao ra.
# `CT_KEEP_TMP=1` de giu lai khi can mo xac rac sau mot lan test hong.
if [ -z "${CT_KEEP_TMP:-}" ]; then
  _tmp_run=$(mktemp -d)
  export TMPDIR="$_tmp_run"
  trap 'rm -rf "$_tmp_run"' EXIT INT TERM
fi

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
