#!/bin/bash
# MOT script cho ca ba vai di tim tin (gop 06/09/2026 dot 2).
#
# Truoc do la ba tep 55 dong trung nhau ~90%: finn_daily_scan.sh,
# nova_daily_scan.sh, vera_daily_scan.sh. Khac dung bon thu — tien to khoa
# chong trung, tieu de task, assignee, va MOT cau "Viec cua ban". Phan con lai
# (BODY ba buoc, khoi kiem "kanban tra ve task cu") duoc chep ba lan, va da bat
# dau lech: audit 05/09 do trung ~50%, den 06/09 la ~90% vi BODY duoc mo rong
# giong nhau o ca ba ban. Sua mot cho ma quen hai cho kia la chuyen da xay ra.
#
# Dung:  daily_scan.sh finn|nova|vera
#
# Tham so la SLUG PROFILE (ten nhan vat, LOW-14), va chinh no la assignee.
# Truoc LOW-20 tham so la role cu (scout|market) va assignee di theo no: sang
# 11/09 cutover doi `--vai` trong BODY ma quen `--assignee`, task giao cho
# profile khong ton tai, dispatcher lang le bo qua (khong bao "stuck"), cron
# van "ok" — Vera va Finn im ca sang ma khong ai hay. Nen o day khong con hai
# ten cho mot vai nua, va co cong kiem profile TON TAI truoc khi tao task.
#
# Thoat KHAC 0 khi hong: hermes chi coi job la loi khi returncode != 0
# (cron/scheduler.py). Ban cu chi `echo` roi ket thuc binh thuong -> last_status
# "ok", failure_streak 0, va vi moi job deu `deliver: local` nen khong ai duoc
# bao gi ca.
set -uo pipefail

VAI="${1:-}"
case "$VAI" in
  finn)  TIEU_DE="Quet tin sang"
         VIEC="cham hai thanh phan diem con lai (suc nang ky thuat 0-30, lien quan 0-20) va viet summary_vi theo dung khung BUOC 1 in ra" ;;
  nova)  TIEU_DE="Quet model sang"
         VIEC="noi ra Y NGHIA (manh/re hon cai gi, bang nao, gia vao/ra, thay duoc vai nao) cho tung model bat buoc, xep thu tu, va cham hai diem (tac dong 0-50, lien quan 0-50) theo dung khung BUOC 1 in ra" ;;
  vera)  TIEU_DE="Quet tin kinh doanh"
         VIEC="loc tin co HE QUA (IPO, thau tom, ha tang, chinh sach, lao dong, kien tung), ghi muc chac chan theo so bao, viet tom tat co so, va cham hai diem (he qua 0-50, lien quan 0-50) theo dung khung BUOC 1 in ra" ;;
  qinn)  TIEU_DE="Quet X luot"
         VIEC="loc tin KY THUAT DUNG DUOC LAU (tool/repo, bao mat, kien truc, cach lam), bo thong bao phat hanh / benchmark / hype, toi da 6 tin, va bao ngay neu brief noi CRAWLER DUNG" ;;
  *) echo "Dung: $(basename "$0") finn|nova|vera|qinn (slug profile, khong phai role cu)" >&2; exit 2 ;;
esac

# Cong LOW-20: profile phai co that trong home dang chay. Cron cua hermes chay
# voi HERMES_HOME cua brand (systemd Environment=HERMES_HOME=%h/.hermes-%i);
# khong dat thi hermes dung ~/.hermes. Kanban `create` nhan assignee bat ky nen
# chi o day moi chan duoc, va thoat 1 de failure_streak tang thay vi "ok".
NHA="${HERMES_HOME:-$HOME/.hermes}"
if [ ! -d "$NHA/profiles/$VAI" ]; then
  echo "${VAI}_daily_scan LOI: khong co profile '$VAI' trong $NHA/profiles — task se khong ai nhan" >&2
  exit 1
fi

H=$HOME/hermes-agent/venv/bin/python
# Ngay lay theo GIO VN, khong phai UTC. Cron chay 22:00 UTC = 05:00 VN hom sau,
# nen `date -u` tra ve ngay HOM TRUOC — khoa chong trung trung voi lan chay cu,
# kanban tra ve task cu thay vi tao moi, va script im lang tuong da thanh cong.
# Da dinh dung loi nay sang 23/08: ba vai deu khong chay.
KEY="$VAI-daily-$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d)"
DAY=$(TZ=Asia/Ho_Chi_Minh date +%Y-%m-%d)

# Vai chay NHIEU LAN trong ngay phai co LUOT trong khoa chong trung va trong
# tieu de. Khong co thi luot sau trung khoa cua luot dau: kanban tra ve task CU
# (da done), khoi kiem ben duoi thoat 1, va luot sau im lang khong chay.
# KHUNG_GIO phai khop scan_prepare.FRAME_HOURS va cron expr cua job qinn-scan:
# 12 = hai luot/ngay (05:00 va 17:00 VN).
case "$VAI" in
  qinn)
    KHUNG_GIO=12
    GIO=$(TZ=Asia/Ho_Chi_Minh date +%H)
    LUOT=$(( ((10#$GIO - 5 + 24) % 24) / KHUNG_GIO ))
    KEY="$KEY-p$LUOT"
    DAY="$DAY luot $((LUOT + 1))/$((24 / KHUNG_GIO))"
    ;;
esac

BODY="Nhiem vu quet tin sang $DAY (chay theo lich cron). Phan CO HOC — chay script quet, loc
trung, cham diem co hoc, ghep manifest danh so, viet bao cao, gui topic — DA LA SCRIPT.
Viec cua ban chi co MOT: $VIEC. Lam dung BA BUOC, khong them lenh nao khac.

BUOC 1 — doc ban chuan bi (danh sach ung vien mot dong/tin, muc BAT BUOC, khung tep nop):
cd \$HOME/content-team && venv/bin/python scan_prepare.py --vai $VAI

BUOC 2 — viet MOT tep JSON vao dung duong dan in o cuoi BUOC 1, THEO DUNG khung
va luat ma BUOC 1 in ra (khung do la NGUON SU THAT — cron nay khong nhac lai
luat nop, vi nhac lai la de troi). KHONG cat/grep tep JSON goc, KHONG web_search,
KHONG chay scan_*/manifest_*/publish.py tay.

BUOC 3 — nop:
cd \$HOME/content-team && venv/bin/python scan_submit.py --vai $VAI
Khong tin nao dat nguong thi chay: scan_submit.py --vai $VAI --khong-co (script gui dong
'hom nay khong co gi' kem so tin da quet — Ong Chu can phan biet voi 'co gi do hong').
Script bao [LOI] thi sua tep JSON roi chay lai DUNG lenh (toi da 2 lan). Xong: ket
thuc task bang dong 'Ket qua task' script in ra. KHONG tao task kanban nao.

TUYET DOI KHONG DOI \`--vai\`. Script tu choi \`--vai\` cua ban (invalid choice, exit 2)
thi day la SU CO TRIEN KHAI: DUNG LAI, ket thuc task bang dong bao dung loi do.
Khong chay \`--vai\` cua vai khac, khong nop ho vai khac. Sang 13/09/2026 da co
mot lan lam dung the: \`--vai qinn\` bao exit 2, vai tu chay \`--vai finn\` roi nop
\`--vai scout\` — ghi de manifest cua Finn va gui bao cao thu hai vao topic Finn,
con Ong Chu thi khong thay tin nao o topic cua minh."

OUT=$($H -m hermes_cli.main kanban create "$TIEU_DE $DAY" \
  --assignee "$VAI" --max-runtime 20m \
  --idempotency-key "$KEY" --body "$BODY" --json 2>&1)

# Kiem tra HAI muc, khong chi mot:
#  1. co tao duoc task khong
#  2. task tra ve co phai task MOI khong. Trung khoa chong trung thi kanban tra
#     ve TASK CU voi tieu de cu, ma van co truong "id" — grep cu chi nhin "id"
#     nen im lang, tuong da chay. Sang 23/08 ca ba vai deu khong chay vi loi nay.
if ! echo "$OUT" | grep -q '"id"'; then
  echo "${VAI}_daily_scan LOI: khong tao duoc task"
  echo "$OUT" | head -5
  exit 1
elif ! echo "$OUT" | grep -qF "\"title\": \"$TIEU_DE $DAY\""; then
  echo "${VAI}_daily_scan CANH BAO: kanban tra ve task CU (trung idempotency-key)."
  echo "  Task hom nay KHONG duoc tao. Kiem tra khoa: $KEY"
  echo "$OUT" | grep '"title"' | head -2
  exit 1
fi
