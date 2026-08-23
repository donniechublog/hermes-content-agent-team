#!/bin/bash
# Cron 6h sang VN: chot nhat ky NGAY HOM QUA (da tron ven) va mo trang hom nay.
# Chay thang script tat dinh, KHONG qua agent, chi ghep du lieu, khong can LLM.
cd /home/donniechu/content-team || exit 1
HOM_QUA=$(TZ=Asia/Ho_Chi_Minh date -d yesterday +%F)
HOM_NAY=$(TZ=Asia/Ho_Chi_Minh date +%F)
venv/bin/python nhat_ky.py --ngay "$HOM_QUA" >/dev/null 2>&1
venv/bin/python nhat_ky.py --ngay "$HOM_NAY" >/dev/null 2>&1
echo "nhat ky: da chot $HOM_QUA, mo trang $HOM_NAY"
