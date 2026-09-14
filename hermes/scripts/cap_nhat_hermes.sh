#!/bin/bash
# cap_nhat_hermes.sh — cap nhat hermes-agent AN TOAN: kiem truoc, kiem sau,
# hong thi LUI LAI dung commit cu (audit_content_team C2).
#
# Vi sao can (nhat ky su co): content-team dung RUOT cua hermes-agent — import
# hermes_cli, doc thang kanban.db, va dung CHUNG venv voi no. `hermes update`
# vi vay khong phai chuyen cua rieng hermes: da tung xoa mat pymupdf, va doi
# da mat ban va vendor (dist/index.js, plugin_api.py) BA LAN. Cai dat xong moi
# phat hien thi da muon — dich vu duyet bai chet giua ngay.
#
# Script nay dat ba cai chan:
#   1. CHUA CAP NHAT neu hermes-agent con thay doi chua commit. Do gan nhu luon
#      la ban va cua doi, va `git reset --hard` o buoc lui se xoa sach chung.
#      Day la cai chan quan trong nhat — dung cai da mat ba lan.
#   2. Ghi lai HEAD truoc khi cap nhat, roi chay check_hermes.py (cac cho lien
#      quan ruot hermes) va check_env.py (cv2/Chromium/khoa API).
#   3. Kiem hong -> `git reset --hard` ve dung HEAD da ghi, roi kiem lai de xac
#      nhan da lui sach.
#
# GIOI HAN da biet: lui git KHONG phuc hoi duoc goi pip da bi go khoi venv
# (venv dung chung — xem D1 trong audit, tach venv rieng moi dut diem duoc).
# Vi vay buoc kiem co chay check_env.py: no noi ro goi nao dang thieu.
#
# Dung:
#     hermes/scripts/cap_nhat_hermes.sh            # cap nhat + kiem + tu lui khi hong
#     hermes/scripts/cap_nhat_hermes.sh --thu      # chi kiem hien trang, KHONG cap nhat
#     hermes/scripts/cap_nhat_hermes.sh --khong-lui  # hong thi bao, KHONG tu lui
#
# Cron sang (audit C2 de nghi): dang ky mot job goi script nay hoac chi rieng
# `check_hermes.py` moi sang. Job cron cua hermes nam trong HOME dang chay
# (~/.hermes-<brand>/cron/jobs.json, id do hermes sinh) nen dang ky bang CLI
# cua hermes chu dung sua tay tep JSON — sync_hermes.py chi CHEP home ve repo.
set -uo pipefail

CT="$HOME/content-team"
AGENT="$HOME/hermes-agent"
AGENT_PY="$AGENT/venv/bin/python"
# Lenh cap nhat THAT cua doi la `hermes update` (binary wrapper) — moi tai lieu
# trong repo (hermes/README.md, MEMORY_ARCH.md, journal.py) deu goi dung chu do.
# Ban dau script nay bia ra `python -m hermes_cli.main update` ma khong co bang
# chung `update` la mot subcommand Python; voi mot script AN TOAN, lenh mac dinh
# sai nghia la no vo o buoc 2 moi lan chay va duong cap nhat co kiem khong bao
# gio duoc dung (review Fable 09/09/2026). Doi bang bien moi truong neu can.
LENH_CAP_NHAT="${LENH_CAP_NHAT:-hermes update}"

THU=0
TU_LUI=1
for co in "$@"; do
  case "$co" in
    --thu) THU=1 ;;
    --khong-lui) TU_LUI=0 ;;
    *) echo "Tham so la: $co" >&2; exit 2 ;;
  esac
done

[ -d "$AGENT/.git" ] || { echo "[LOI] $AGENT khong phai repo git" >&2; exit 2; }
[ -x "$AGENT_PY" ] || { echo "[LOI] khong thay python cua hermes: $AGENT_PY" >&2; exit 2; }

kiem() {
  # Tra 0 khi CA HAI buoc kiem deu qua. check_env co the bao THIEU vi ly
  # do khong lien quan lan cap nhat nay (vd chua dat khoa API tren may moi) nen
  # in ro ca hai ma khong gop lan ket qua.
  local ma_h ma_m
  cd "$CT" || return 1
  echo "--- check_hermes.py ---"
  venv/bin/python check_hermes.py; ma_h=$?
  echo "--- check_env.py ---"
  venv/bin/python check_env.py; ma_m=$?
  [ $ma_h -eq 0 ] && [ $ma_m -eq 0 ]
}

if [ "$THU" -eq 1 ]; then
  echo "[thu] chi kiem hien trang, khong cap nhat gi."
  kiem && { echo "[OK] hien trang lanh."; exit 0; }
  echo "[THIEU] xem chi tiet o tren." >&2
  exit 1
fi

# --- Chan 1: ban va chua commit ------------------------------------------
ban_va=$(git -C "$AGENT" status --porcelain --untracked-files=no)
if [ -n "$ban_va" ]; then
  echo "[DUNG] hermes-agent con thay doi CHUA COMMIT — gan nhu chac la ban va" >&2
  echo "cua doi. Cap nhat bay gio, roi lui bang 'git reset --hard', la xoa sach" >&2
  echo "chung (da mat ba lan vi dung cho nay). Commit hoac stash truoc da:" >&2
  echo "$ban_va" | sed 's/^/    /' >&2
  exit 3
fi

truoc=$(git -C "$AGENT" rev-parse HEAD) || exit 2
echo "[moc] HEAD truoc khi cap nhat: $truoc"

# --- Cap nhat -------------------------------------------------------------
# Kiem lenh o DAY chu khong o dau script: `--thu` chi kiem hien trang, khong can
# lenh update, va phai chay duoc ca tren may khong co `hermes` tren PATH.
command -v "${LENH_CAP_NHAT%% *}" >/dev/null 2>&1 \
  || { echo "[LOI] khong thay lenh '${LENH_CAP_NHAT%% *}' tren PATH — dat LENH_CAP_NHAT=... roi chay lai" >&2; exit 2; }
echo "[chay] $LENH_CAP_NHAT"
if ! $LENH_CAP_NHAT; then
  echo "[LOI] lenh cap nhat thoat khac 0 — kiem lai hien trang truoc khi lam gi tiep." >&2
  kiem || true
  exit 1
fi

sau=$(git -C "$AGENT" rev-parse HEAD)
if [ "$sau" = "$truoc" ]; then
  echo "[moc] HEAD khong doi ($sau) — khong co gi moi."
else
  echo "[moc] HEAD moi: $sau"
fi

# --- Kiem sau cap nhat ----------------------------------------------------
if kiem; then
  echo "[OK] cap nhat xong, cac cho lien quan ruot hermes van lanh."
  exit 0
fi

echo "[HONG] kiem sau cap nhat KHONG qua." >&2
if [ "$TU_LUI" -eq 0 ] || [ "$sau" = "$truoc" ]; then
  echo "Khong tu lui (--khong-lui hoac HEAD khong doi). Lui tay:" >&2
  echo "    git -C $AGENT reset --hard $truoc" >&2
  exit 1
fi

echo "[lui] git reset --hard $truoc" >&2
if ! git -C "$AGENT" reset --hard "$truoc"; then
  echo "[LOI] LUI KHONG DUOC — hermes-agent dang o $sau, phai xu ly tay ngay." >&2
  exit 1
fi

echo "--- kiem lai sau khi lui ---" >&2
if kiem; then
  echo "[OK] da lui ve $truoc va moi thu lanh lai. Ban cap nhat co van de, dung" >&2
  echo "chay lai cho toi khi biet no hong cho nao." >&2
  exit 1
fi
echo "[LOI] lui roi ma VAN hong — nghia la nguyen nhan khong nam o lan cap nhat" >&2
echo "nay (rat co the goi pip trong venv dung chung da bi go: xem" >&2
echo "check_env.py o tren, va D1 trong audit ve venv rieng)." >&2
exit 1
