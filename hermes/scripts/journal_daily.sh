#!/bin/bash
# Duong dan theo $HOME, khong go cung /home/dc-group (sua 06/09/2026):
# doi ten user Unix hoac chay thu tren may khac la gay im lang.
# Cron 6h sang VN: chot nhat ky NGAY HOM QUA (da tron ven) va mo trang hom nay.
# Chay thang script tat dinh, KHONG qua agent, chi ghep du lieu, khong can LLM.
#
# THOAT KHAC 0 KHI HONG (sua 06/09/2026 dot 2). Hermes chi coi mot job cron la
# loi khi returncode != 0. Ban truoc:
#   - hai lenh journal.py khong ai xem ma thoat;
#   - lenh cuoi la `... | tail -3`, ma mac dinh bash tra ve ma cua `tail`, tuc
#     LUON 0 du monitor_9router chet;
#   - va `echo` cuoi cung lai reset ma thoat ve 0 mot lan nua.
# Ket qua: nhat ky chet ca tuan van hien last_status "ok", failure_streak 0.
set -uo pipefail
cd "$HOME/content-team" || exit 1
HOM_QUA=$(TZ=Asia/Ho_Chi_Minh date -d yesterday +%F)
HOM_NAY=$(TZ=Asia/Ho_Chi_Minh date +%F)
loi=0

# KHONG nuot stderr (sua 06/09/2026): `>/dev/null 2>&1` cong voi viec journal.py
# doc thang bang noi bo cua hermes bang SQL tho nghia la mot lan `hermes update`
# doi schema se lam nhat ky chet hoan toan im lang. Giu stdout gon bang `tail`,
# nhung de stderr chay ra output cua cron — do la cho dung de thay loi.
venv/bin/python journal.py --ngay "$HOM_QUA" >/dev/null || { echo "LOI: journal.py $HOM_QUA"; loi=1; }
venv/bin/python journal.py --ngay "$HOM_NAY" >/dev/null || { echo "LOI: journal.py $HOM_NAY"; loi=1; }

# Nhat ky 9router (model/token/$/lat model/model la/cache thap) cua hom qua: chung cho moi brand,
# idempotent nen hai brand cung goi khong sao. --gui: tom tat + link (journal_web) -> analyst,
# CHI brand blog gui de khoi trung tin (9router chung, so lieu y het).
if [ "${CT_BRAND:-blog}" = "blog" ]; then GUI=--gui; else GUI=; fi
# `| tail -3` che ma thoat, nen lay ma cua chinh python qua PIPESTATUS.
venv/bin/python monitor_9router.py --ngay "$HOM_QUA" --im $GUI 2>&1 | tail -3
ma9=${PIPESTATUS[0]}
[ "$ma9" -eq 0 ] || { echo "LOI: monitor_9router.py $HOM_QUA (ma $ma9)"; loi=1; }

echo "nhat ky: da chot $HOM_QUA, mo trang $HOM_NAY"
exit $loi
