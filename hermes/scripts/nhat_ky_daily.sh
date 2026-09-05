#!/bin/bash
# Cron 6h sang VN: chot nhat ky NGAY HOM QUA (da tron ven) va mo trang hom nay.
# Chay thang script tat dinh, KHONG qua agent, chi ghep du lieu, khong can LLM.
cd /home/donniechu/content-team || exit 1
HOM_QUA=$(TZ=Asia/Ho_Chi_Minh date -d yesterday +%F)
HOM_NAY=$(TZ=Asia/Ho_Chi_Minh date +%F)
venv/bin/python nhat_ky.py --ngay "$HOM_QUA" >/dev/null 2>&1
venv/bin/python nhat_ky.py --ngay "$HOM_NAY" >/dev/null 2>&1
# Nhat ky 9router (model/token/$/lat model/model la/cache thap) cua hom qua: chung cho moi brand,
# idempotent nen hai brand cung goi khong sao. --gui: tom tat + link (nhat_ky_web) -> analyst,
# CHI brand blog gui de khoi trung tin (9router chung, so lieu y het).
if [ "${CT_BRAND:-blog}" = "blog" ]; then GUI=--gui; else GUI=; fi
venv/bin/python theo_doi_9router.py --ngay "$HOM_QUA" --im $GUI 2>&1 | tail -3
echo "nhat ky: da chot $HOM_QUA, mo trang $HOM_NAY"
