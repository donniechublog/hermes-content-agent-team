#!/bin/bash
# setup.sh — dung moi truong cho content-team tren mot may moi, CHAY LAI DUOC
# bao nhieu lan cung khong sao (audit_content_team D3).
#
# Vi sao can: cac buoc cai dat truoc gio nam rai trong comment — requirements.txt
# ghi `playwright install chromium`, con font va model YuNet thi khong ai noi la
# da nam san trong git. Dung may moi phai doc nhieu cho roi tu ghep lai, va thieu
# mot buoc thi hong CAM: thieu cv2 la cong mat nguoi tu tat, thieu Chromium la
# moi buoc browser chet giua chung.
#
# HAI buoc THAT (font + YuNet onnx da nam trong git, khong phai tai gi):
#   1. pip install -r requirements.txt
#   2. playwright install chromium        (goi Python co roi van phai tai browser)
# Node da BO han 09/09/2026 (audit A6): frame.js/screenshot.js viet lai bang PIL
# + Playwright cua Python, server khong con `npm ci` nao.
# Ket thuc bang check_env.py — no moi la cho noi that may nay da san sang chua.
#
# Dung:
#     hermes/scripts/../setup.sh          # hoac: bash setup.sh
#     bash setup.sh --thu                 # chi xem se lam gi, khong cai
set -uo pipefail
cd "$(dirname "$0")" || exit 2

THU=0
for co in "$@"; do
  case "$co" in
    --thu) THU=1 ;;
    *) echo "Tham so la: $co (chi nhan --thu)" >&2; exit 2 ;;
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
echo "[1/2] goi Python"
chay "$PY" -m pip install -q -r requirements.txt || {
  echo "[LOI] pip install that bai — xem dong tren." >&2; exit 1; }

# --- 2. Chromium cho Playwright --------------------------------------------
# Cai goi playwright KHONG keo theo browser. `playwright install` tu bo qua khi
# ban dung da co, nen chay lai vo hai.
echo "[2/2] Chromium cho Playwright"
chay "$PY" -m playwright install chromium || {
  echo "[LOI] khong tai duoc Chromium. Tren server toi gian co the con thieu thu vien he" >&2
  echo "      thong: thu '$PY -m playwright install-deps chromium' (can sudo)." >&2; exit 1; }

# --- Kiem ------------------------------------------------------------------
# Font (assets/fonts) va model YuNet (assets/*.onnx) DA nam trong git, khong co
# buoc tai nao. check_env.py noi ro cai nao thieu.
echo
if [ "$THU" -eq 1 ]; then
  echo "[thu] xong — khong cai gi. Bo --thu de chay that."
  exit 0
fi
echo "[kiem] chay check_env.py"
"$PY" check_env.py
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
