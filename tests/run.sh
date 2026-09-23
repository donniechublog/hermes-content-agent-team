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
else
  _tmp_run="${TMPDIR:-/tmp}"
fi

# LOP 2 (LOW-390) — trong goc tren, MOI TEP TEST mot TMPDIR rieng, dem xem tep
# nao bo lai gi roi CHAN neu con.
#
# Vi sao can ca hai lop: lop 1 lam rac khong con tich luy, nhung khong tra loi
# duoc "AI bo lai" va khong ngan ro ri MOI len tau. Va lan chay NGOAI run.sh
# (vai tu go `venv/bin/python tests/test_x.py`) thi lop 1 khong che duoc — chi
# viec sua tan goc cac cho goi moi che. Do duoc 23/09 tren may chu: mot luot bo
# lai 160 thu muc truoc khi va, 0 sau khi va.
#
# Do bang THU MUC THAT chu khong grep `mkdtemp` (CLAUDE.md muc 6: khoa bang cong
# do tren vat that) — nen bat duoc ca ro ri cua thu vien lan cua ma minh viet.

# CT_STATE_DIR nam TRONG goc do de cung duoc don; KHONG tinh la rac vi day la
# thu minh CO Y tao.
export CT_STATE_DIR="${CT_STATE_DIR:-$_tmp_run/state}"
mkdir -p "$CT_STATE_DIR"
# Console Windows cp1252 lam UnicodeEncodeError o dong in ket qua — tuc test
# qua ma tep bao hong. -X utf8 vo hai tren Linux.
PYFLAGS="-X utf8"

hong=0
tong=0
trash_total=0
trash_outside=0
trash_by_file=""
for f in tests/test_*.py; do
  case "$f" in *"$LOC"*) ;; *) continue ;; esac
  tong=$((tong + 1))
  tmpf="$_tmp_run/tmp-$(basename "$f" .py)"
  mkdir -p "$tmpf"
  ra=$(TMPDIR="$tmpf" "$PY" $PYFLAGS "$f" 2>&1)
  ma=$?
  # Tach RAC CUA TA khoi rac cua THU VIEN. Chromium/playwright thinh thoang bo
  # lai `.org.chromium.Chromium.XXXXXX` (do duoc: 1/3 lan chay
  # test_low345_kicker_contrast tren may chu) — ta khong sua duoc, va do mot thu
  # muc that thuong ma bao ca bo test hong thi chi day nguoi ta bo qua cong.
  # Van DEM va van IN ra de no khong bien mat khoi tam mat, nhung khong chan.
  con=$(find "$tmpf" -mindepth 1 -maxdepth 1         ! -name '.org.chromium.*' ! -name 'playwright*' ! -name '.com.google.Chrome*'         2>/dev/null | wc -l)
  ngoai=$(find "$tmpf" -mindepth 1 -maxdepth 1           \( -name '.org.chromium.*' -o -name 'playwright*' -o -name '.com.google.Chrome*' \)           2>/dev/null | wc -l)
  if [ "$con" -gt 0 ]; then
    trash_total=$((trash_total + con))
    trash_by_file="$trash_by_file$(basename "$f") $con"$'
'
  fi
  [ "$ngoai" -gt 0 ] && trash_outside=$((trash_outside + ngoai))
  [ -z "${CT_KEEP_TMP:-}" ] && rm -rf "$tmpf"
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
if [ "$trash_outside" -gt 0 ]; then
  echo "[rac thu vien] $trash_outside thu muc cua Chromium/playwright — KHONG chan"
  echo "    (ro ri cua thu vien, ta khong sua duoc; da xoa, chi bao de theo doi)"
fi
if [ "$trash_total" -gt 0 ]; then
  echo "[RAC TAM] $trash_total thu muc/tep bi bo lai trong TMPDIR — tep nao bo lai:"
  printf '%s' "$trash_by_file" | sort -k2 -rn | head -20 | sed 's/^/    /'
  echo "    Dung tam.temp_dir() thay cho tempfile.mkdtemp() tran; doi bien moi"
  echo "    truong thi nho tra lai o finally. Xem LOW-390 va tests/test_temp_cleanup.py."
fi
if [ "$hong" -eq 0 ] && [ "$trash_total" -eq 0 ]; then
  echo "$tong/$tong tep test qua"
  exit 0
fi
[ "$hong" -gt 0 ] && echo "$hong/$tong tep test HONG"
[ "$hong" -eq 0 ] && echo "$tong/$tong tep test qua, NHUNG con rac tam — xem [RAC TAM] o tren"
exit 1
