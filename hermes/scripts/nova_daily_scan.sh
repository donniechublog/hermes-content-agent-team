#!/bin/bash
# Cron: Nova quet model moi ra mat, gui bao cao vao topic nova. Khong tao task khac.
H=/home/donniechu/hermes-agent/venv/bin/python
# Ngay lay theo GIO VN, khong phai UTC. Cron chay 22:00 UTC = 05:00 VN hom sau,
# nen `date -u` tra ve ngay HOM TRUOC — khoa chong trung trung voi lan chay cu,
# kanban tra ve task cu thay vi tao moi, va script im lang tuong da thanh cong.
# Da dinh dung loi nay sang 23/08: ba vai deu khong chay.
KEY="nova-daily-$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d)"
DAY=$(TZ=Asia/Ho_Chi_Minh date +%Y-%m-%d)

BODY="Nhiem vu quet model sang $DAY (chay theo lich cron). Lam dung huong dan trong SOUL.

Buoc 1, chay script tat dinh:
cd /home/donniechu/content-team && venv/bin/python scan_models.py --ngay 7 --top 10

Buoc 2, truoc khi khuyen nghi bat cu model nao, doc lai thu da bi loai:
cat /home/donniechu/content-team/state/${CT_BRAND}/model_health.json

Buoc 2b, GHI MANIFEST + BAO CAO. Bat buoc khi CO tin dang len kenh.

  cat > /tmp/nova_ds.json <<HET
  [{\"title\": \"...\", \"link\": \"...\", \"summary_vi\": \"...\",
     \"source_note\": \"...\"}]
  HET
  cd /home/donniechu/content-team && venv/bin/python manifest_ghi.py \\
    --vai nova --in /tmp/nova_ds.json --bao-cao /tmp/nova_baocao.txt

Script tu danh so, tu suy via tu ten mien, VA tu viet luon ban bao cao danh so.
KHONG tu go lai so vao tin nhan: go lai la co hoi lech, so trong tin nhan mot
dang con so trong manifest mot dang, Ong Chu tra loi so lai ra bai khac.

Gui thang ban script vua viet:
  /home/donniechu/hermes-agent/venv/bin/python /home/donniechu/content-team/publish.py \\
    --to-env TELEGRAM_GROUP_ID --thread-name nova --file /tmp/nova_baocao.txt

KHONG co tin nao dang len kenh thi bo qua manifest, nhung VAN phai gui mot dong
noi ro la hom nay khong co gi, kem so tin da quet. Ong Chu can phan biet duoc
\"hom nay khong co gi\" voi \"co gi do hong\".

Buoc 3, gui bao cao vao topic cua ban. GHI RA TEP TRUOC roi dung --file
DUNG nhet ca bao cao vao mot tham so --text: nhet mot dong thi ca bai dinh
lien nhau, khong xuong dong duoc.

  cat > /tmp/bao_cao_$$.txt <<'HET'
  <bao cao, xuong dong that, dong trong giua cac doan>
  HET
  /home/donniechu/hermes-agent/venv/bin/python /home/donniechu/content-team/publish.py \\
    --to-env TELEGRAM_GROUP_ID --thread-name nova --file /tmp/bao_cao_$$.txt

Dinh dang: chi dung <b>, <i>, <code>, <a href>. KHONG dung <br>, <p>, <ul>
<li>, markdown ** hay ##. Xuong dong bang xuong dong THAT.

Khong co gi dang noi thi gui mot dong bao khong co gi. KHONG tao task kanban nao."

OUT=$($H -m hermes_cli.main kanban create "Quet model sang $DAY" \
  --assignee nova --max-runtime 20m \
  --idempotency-key "$KEY" --body "$BODY" --json 2>&1)
# Kiem tra HAI muc, khong chi mot:
#  1. co tao duoc task khong
#  2. task tra ve co phai task MOI khong. Trung khoa chong trung thi kanban tra
#     ve TASK CU voi tieu de cu, ma van co truong "id" — grep cu chi nhin "id"
#     nen im lang, tuong da chay. Sang 23/08 ca ba vai deu khong chay vi loi nay.
if ! echo "$OUT" | grep -q '"id"'; then
  echo "nova_daily_scan LOI: khong tao duoc task"
  echo "$OUT" | head -5
elif ! echo "$OUT" | grep -qF "\"title\": \"Quet model sang $DAY\""; then
  echo "nova_daily_scan CANH BAO: kanban tra ve task CU (trung idempotency-key)."
  echo "  Task hom nay KHONG duoc tao. Kiem tra khoa: $KEY"
  echo "$OUT" | grep '"title"' | head -2
fi
