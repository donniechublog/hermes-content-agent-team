#!/bin/bash
# Cron: Vera quet tin dau tu/kinh te, gui bao cao vao topic market. Khong tao task khac.
export HERMES_HOME=/home/donniechu/.hermes
H=/home/donniechu/hermes-agent/venv/bin/python
# Ngay lay theo GIO VN, khong phai UTC. Cron chay 23:00 UTC = 06:00 VN hom sau,
# nen `date -u` tra ve ngay HOM TRUOC — khoa chong trung trung voi lan chay cu,
# kanban tra ve task cu thay vi tao moi, va script im lang tuong da thanh cong.
# Da dinh dung loi nay sang 23/08: ba vai deu khong chay.
KEY="vera-daily-$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d)"
DAY=$(TZ=Asia/Ho_Chi_Minh date +%Y-%m-%d)

BODY="Nhiem vu quet tin kinh doanh sang $DAY (chay theo lich cron). Lam dung huong dan trong SOUL.

Buoc 1, chay script tat dinh. Khong con cham diem cat top: script dua HET tin trong
cua so 30h cho ban tu xet (tin watchlist luon co, tin thuong cat theo moi nhat neu
qua nhieu). Cua so 30h de khong lot tin ra mat toi hom truoc.
cd /home/donniechu/content-team && venv/bin/python scan_business.py --gio 30

Buoc 2, loc: phan biet tin kiem chung voi thong cao doanh nghiep. Uu tien tin co
he qua, khong chi co con so lon.

Tin co truong "watchlist": true la tin ve top brand nganh AI (OpenAI, Anthropic,
Google, Meta, Nvidia, Apple, Xiaomi, DeepSeek, Qwen, Samsung...). Nhung tin nay
LUON co trong danh sach (khong bao gio bi cat), va PHAI theo sat: mot hang lon ra chip/model/san
pham (Apple ra M6, Xiaomi ra AI Cube) la tac dong ca nganh, gan nhu luon dang len.
Chi bo qua neu that su chi la tin lat vat (co phieu nhich, kien tung nho). Con lai
uu tien chon.

Buoc 2b, GHI MANIFEST + BAO CAO. Bat buoc khi CO tin dang len kenh.

  cat > /tmp/market_ds.json <<HET
  [{\"title\": \"...\", \"link\": \"...\", \"summary_vi\": \"...\",
     \"source_note\": \"...\"}]
  HET
  cd /home/donniechu/content-team && venv/bin/python manifest_ghi.py \\
    --vai market --in /tmp/market_ds.json --bao-cao /tmp/market_baocao.txt

Script tu danh so, tu suy via tu ten mien, VA tu viet luon ban bao cao danh so.
KHONG tu go lai so vao tin nhan: go lai la co hoi lech, so trong tin nhan mot
dang con so trong manifest mot dang, Ong Chu tra loi so lai ra bai khac.

Gui thang ban script vua viet:
  /home/donniechu/hermes-agent/venv/bin/python /home/donniechu/content-team/publish.py \\
    --to -1003763882779 --thread 83 --file /tmp/market_baocao.txt

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
    --to -1003763882779 --thread 83 --file /tmp/bao_cao_$$.txt

Dinh dang: chi dung <b>, <i>, <code>, <a href>. KHONG dung <br>, <p>, <ul>
<li>, markdown ** hay ##. Xuong dong bang xuong dong THAT.

Khong co gi dang noi thi gui mot dong bao khong co gi. KHONG tao task kanban nao."

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
