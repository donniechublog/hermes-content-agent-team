#!/bin/bash
# Cron: Vera quet tin dau tu/kinh te, gui bao cao vao topic market. Khong tao task khac.
H=/home/donniechu/hermes-agent/venv/bin/python
# Ngay lay theo GIO VN, khong phai UTC. Cron chay 22:00 UTC = 05:00 VN hom sau,
# nen `date -u` tra ve ngay HOM TRUOC — khoa chong trung trung voi lan chay cu,
# kanban tra ve task cu thay vi tao moi, va script im lang tuong da thanh cong.
# Da dinh dung loi nay sang 23/08: ba vai deu khong chay.
KEY="vera-daily-$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d)"
DAY=$(TZ=Asia/Ho_Chi_Minh date +%Y-%m-%d)

BODY="Nhiem vu quet tin sang $DAY (chay theo lich cron). Phan CO HOC — chay script quet, loc
trung, cham diem co hoc, ghep manifest danh so, viet bao cao, gui topic — DA LA SCRIPT.
Viec cua ban chi co MOT: loc tin co HE QUA (IPO, thau tom, ha tang, chinh sach, lao dong, kien tung), ghi muc chac chan theo so bao, viet tom tat co so. Lam dung BA BUOC, khong them lenh nao khac.

BUOC 1 — doc ban chuan bi (danh sach ung vien mot dong/tin, muc BAT BUOC, khung tep nop):
cd /home/donniechu/content-team && venv/bin/python quet_chuan_bi.py --vai market

BUOC 2 — viet MOT tep JSON vao dung duong dan in o cuoi BUOC 1. Link phai Y HET
danh sach (khong go lai tu tri nho). MOI muc BAT BUOC phai co mat. KHONG cat/grep
tep JSON goc, KHONG web_search, KHONG chay scan_*/manifest_*/publish.py tay.

BUOC 3 — nop:
cd /home/donniechu/content-team && venv/bin/python quet_nop.py --vai market
Khong tin nao dat nguong thi chay: quet_nop.py --vai market --khong-co (script gui dong
'hom nay khong co gi' kem so tin da quet — Ong Chu can phan biet voi 'co gi do hong').
Script bao [LOI] thi sua tep JSON roi chay lai DUNG lenh (toi da 2 lan). Xong: ket
thuc task bang dong 'Ket qua task' script in ra. KHONG tao task kanban nao."

OUT=$($H -m hermes_cli.main kanban create "Quet tin kinh doanh $DAY" \
  --assignee market --max-runtime 20m \
  --idempotency-key "$KEY" --body "$BODY" --json 2>&1)
# Kiem tra HAI muc, khong chi mot:
#  1. co tao duoc task khong
#  2. task tra ve co phai task MOI khong. Trung khoa chong trung thi kanban tra
#     ve TASK CU voi tieu de cu, ma van co truong "id" — grep cu chi nhin "id"
#     nen im lang, tuong da chay. Sang 23/08 ca ba vai deu khong chay vi loi nay.
if ! echo "$OUT" | grep -q '"id"'; then
  echo "vera_daily_scan LOI: khong tao duoc task"
  echo "$OUT" | head -5
elif ! echo "$OUT" | grep -qF "\"title\": \"Quet tin kinh doanh $DAY\""; then
  echo "vera_daily_scan CANH BAO: kanban tra ve task CU (trung idempotency-key)."
  echo "  Task hom nay KHONG duoc tao. Kiem tra khoa: $KEY"
  echo "$OUT" | grep '"title"' | head -2
fi
