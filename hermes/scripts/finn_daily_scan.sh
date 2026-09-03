#!/bin/bash
# Cron: Finn quet tin, cham diem, liet ke danh so, KHONG tu tao task.# Ong Chu chon bang cach reply so thu tu trong topic scout -> approve_service.py xu ly.
H=/home/donniechu/hermes-agent/venv/bin/python
# Ngay lay theo GIO VN, khong phai UTC. Cron chay 22:00 UTC = 05:00 VN hom sau,
# nen `date -u` tra ve ngay HOM TRUOC — khoa chong trung trung voi lan chay cu,
# kanban tra ve task cu thay vi tao moi, va script im lang tuong da thanh cong.
# Da dinh dung loi nay sang 23/08: ba vai deu khong chay.
KEY="finn-daily-$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d)"
DAY=$(TZ=Asia/Ho_Chi_Minh date +%Y-%m-%d)
MANIFEST="/home/donniechu/content-team/state/${CT_BRAND}/finn_candidates_${DAY}.json"

BODY="Nhiem vu quet tin sang (chay theo lich cron). Lam dung 5 buoc trong SOUL cua ban.

Duong dan ghi manifest: ${MANIFEST}

Ghi manifest KEM ban bao cao, dung mot lenh:

  cd /home/donniechu/content-team && venv/bin/python manifest_build.py \\
    --picks <tep cham diem cua ban> --out ${MANIFEST} \\
    --bao-cao /tmp/finn_baocao.txt

Script tu danh so, tu ghep du lieu tu candidates, VA tu viet luon ban bao cao.
KHONG tu go lai so vao tin nhan: go lai la co hoi lech, so trong tin nhan mot
dang con so trong manifest mot dang, Ong Chu tra loi so lai ra bai khac.

Gui thang ban script vua viet:
  /home/donniechu/hermes-agent/venv/bin/python /home/donniechu/content-team/publish.py \\
    --to-env TELEGRAM_GROUP_ID --thread-name scout --file /tmp/finn_baocao.txt

KHONG co tin nao dat nguong thi van phai gui mot dong noi ro hom nay khong co gi,
kem so tin da quet. Ong Chu can phan biet duoc \"hom nay khong co gi\" voi
\"co gi do hong\".

Chi dung <b>, <i>, <code>, <a href>. KHONG dung <br>, <p>, <li>, markdown.

KHONG tao task kanban nao. Chi quet, ghi manifest, gui bao cao."

OUT=$($H -m hermes_cli.main kanban create "Quet tin sang $DAY" \
  --assignee scout --max-runtime 20m \
  --idempotency-key "$KEY" --body "$BODY" --json 2>&1)
# Kiem tra HAI muc, khong chi mot:
#  1. co tao duoc task khong
#  2. task tra ve co phai task MOI khong. Trung khoa chong trung thi kanban tra
#     ve TASK CU voi tieu de cu, ma van co truong "id" — grep cu chi nhin "id"
#     nen im lang, tuong da chay. Sang 23/08 ca ba vai deu khong chay vi loi nay.
if ! echo "$OUT" | grep -q '"id"'; then
  echo "finn_daily_scan LOI: khong tao duoc task"
  echo "$OUT" | head -5
elif ! echo "$OUT" | grep -qF "\"title\": \"Quet tin sang $DAY\""; then
  echo "finn_daily_scan CANH BAO: kanban tra ve task CU (trung idempotency-key)."
  echo "  Task hom nay KHONG duoc tao. Kiem tra khoa: $KEY"
  echo "$OUT" | grep '"title"' | head -2
fi
