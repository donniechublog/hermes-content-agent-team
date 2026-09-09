#!/bin/bash
# cai_dat.sh — dung moi truong cho content-team tren mot may moi, CHAY LAI DUOC
# bao nhieu lan cung khong sao (audit_content_team D3).
#
# Vi sao can: cac buoc cai dat truoc gio nam rai trong comment — requirements.txt
# ghi `playwright install chromium`, bob_nop.py ghi `cd <skill> && npm ci`, con
# font va model YuNet thi khong ai noi la da nam san trong git. Dung may moi
# phai doc ba cho roi tu ghep lai, va thieu mot buoc thi hong CAM: thieu cv2 la
# cong mat nguoi tu tat, thieu Chromium la moi buoc browser chet giua chung.
#
# Ba buoc THAT (font + YuNet onnx da nam trong git, khong phai tai gi):
#   1. pip install -r requirements.txt
#   2. playwright install chromium        (goi Python co roi van phai tai browser)
#   3. npm ci trong skill url-mascot-frame (chi Bob dung; --khong-node de bo qua)
# Ket thuc bang kiem_moi_truong.py — no moi la cho noi that may nay da san sang chua.
#
# Dung:
#     hermes/scripts/../cai_dat.sh          # hoac: bash cai_dat.sh
#     bash cai_dat.sh --khong-node          # may khong lam viec cua Bob
#     bash cai_dat.sh --thu                 # chi xem se lam gi, khong cai
set -uo pipefail
cd "$(dirname "$0")" || exit 2

KHONG_NODE=0
THU=0
for co in "$@"; do
  case "$co" in
    --khong-node) KHONG_NODE=1 ;;
    --thu) THU=1 ;;
    *) echo "Tham so la: $co (chi nhan --khong-node, --thu)" >&2; exit 2 ;;
  esac
done

chay() {
  if [ "$THU" -eq 1 ]; then
    echo "  [thu] $*"
    return 0
  fi
  echo "  \$ $*"
  "$@"
}

# --- 1. Python -------------------------------------------------------------
# venv la symlink toi ~/hermes-agent/venv (dung chung voi hermes) — xem dau
# requirements.txt. Khong tu tao venv o day: doi venv rieng la viec cua D1, va
# lam nua voi la de lai hai venv ma khong ai biet cai nao dang chay.
PY=venv/bin/python
if [ ! -x "$PY" ]; then
  echo "[LOI] khong thay $PY." >&2
  echo "      venv cua content-team la symlink toi ~/hermes-agent/venv. Tren may moi:" >&2
  echo "        ln -s ~/hermes-agent/venv venv" >&2
  echo "      (venv rieng la viec cua D1 trong audit, chua lam.)" >&2
  # --thu VAN chay tiep: xem truoc se lam gi la thu can nhat khi may CHUA dung xong.
  [ "$THU" -eq 1 ] || exit 2
fi
echo "[1/3] goi Python"
chay "$PY" -m pip install -q -r requirements.txt || {
  echo "[LOI] pip install that bai — xem dong tren." >&2; exit 1; }

# --- 2. Chromium cho Playwright --------------------------------------------
# Cai goi playwright KHONG keo theo browser. `playwright install` tu bo qua khi
# ban dung da co, nen chay lai vo hai.
echo "[2/3] Chromium cho Playwright"
chay "$PY" -m playwright install chromium || {
  echo "[LOI] khong tai duoc Chromium. Tren server toi gian co the con thieu thu vien he" >&2
  echo "      thong: thu '$PY -m playwright install-deps chromium' (can sudo)." >&2; exit 1; }

# --- 3. Node cho skill cua Bob ---------------------------------------------
SKILL=hermes/skills/url-mascot-frame
if [ "$KHONG_NODE" -eq 1 ]; then
  echo "[3/3] bo qua Node (--khong-node) — Bob se khong dong khung anh duoc"
elif ! command -v npm >/dev/null 2>&1; then
  echo "[3/3] KHONG co npm -> bo qua. Chi vai Bob can (frame.js/screenshot.js);"
  echo "      cac vai khac khong dung Node. Cai Node roi chay lai neu can Bob."
else
  echo "[3/3] Node cho $SKILL"
  # `npm ci` doi package-lock.json va tu xoa node_modules cu -> idempotent san.
  ( cd "$SKILL" && chay npm ci --silent ) || {
    echo "[LOI] npm ci that bai trong $SKILL." >&2; exit 1; }
fi

# --- Kiem ------------------------------------------------------------------
# Font (assets/fonts) va model YuNet (assets/*.onnx) DA nam trong git, khong co
# buoc tai nao. kiem_moi_truong.py noi ro cai nao thieu.
echo
if [ "$THU" -eq 1 ]; then
  echo "[thu] xong — khong cai gi. Bo --thu de chay that."
  exit 0
fi
echo "[kiem] chay kiem_moi_truong.py"
"$PY" kiem_moi_truong.py
ma=$?
echo
if [ $ma -eq 0 ]; then
  echo "[OK] may nay san sang."
else
  echo "[THIEU] con muc chua san sang o tren. Khoa API (OPENAI_API_KEY," >&2
  echo "        TELEGRAM_BOT_TOKEN) khong phai viec cua script nay — dat trong" >&2
  echo "        secret.common.env / secret.<brand>.env, xem env_load.py." >&2
fi
exit $ma
