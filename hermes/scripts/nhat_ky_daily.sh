#!/bin/bash
# Duong dan theo $HOME, khong go cung /home/donniechu (sua 06/09/2026):
# doi ten user Unix hoac chay thu tren may khac la gay im lang.
# Cron 6h sang VN: chot nhat ky NGAY HOM QUA (da tron ven) va mo trang hom nay.
# Chay thang script tat dinh, KHONG qua agent, chi ghep du lieu, khong can LLM.
cd $HOME/content-team || exit 1
HOM_QUA=$(TZ=Asia/Ho_Chi_Minh date -d yesterday +%F)
HOM_NAY=$(TZ=Asia/Ho_Chi_Minh date +%F)
# KHONG nuot stderr (sua 06/09/2026): `>/dev/null 2>&1` cong voi viec nhat_ky.py
# doc thang bang noi bo cua hermes bang SQL tho nghia la mot lan `hermes update`
# doi schema se lam nhat ky chet hoan toan im lang. Giu stdout gon bang `tail`,
# nhung de stderr chay ra output cua cron — do la cho dung de thay loi.
venv/bin/python nhat_ky.py --ngay "$HOM_QUA" >/dev/null
venv/bin/python nhat_ky.py --ngay "$HOM_NAY" >/dev/null
# Nhat ky 9router (model/token/$/lat model/model la/cache thap) cua hom qua: chung cho moi brand,
# idempotent nen hai brand cung goi khong sao. --gui: tom tat + link (nhat_ky_web) -> analyst,
# CHI brand blog gui de khoi trung tin (9router chung, so lieu y het).
if [ "${CT_BRAND:-blog}" = "blog" ]; then GUI=--gui; else GUI=; fi
venv/bin/python theo_doi_9router.py --ngay "$HOM_QUA" --im $GUI 2>&1 | tail -3
echo "nhat ky: da chot $HOM_QUA, mo trang $HOM_NAY"
