#!/bin/bash
# Soi usage that tu 9router: bat fallback am tham va model tut cache.
# Khong goi LLM, chi doc SQLite cuc bo, khong ton mot dong nao.
cd /home/donniechu/content-team || exit 1
# --gio 24: chay 1 lan/ngay thi phai nhin du 24h. Truoc day --gio 6 nghia la
# request tu 06:00-24:00 khong bao gio duoc soi — diem mu dung cai script nay
# sinh ra de bit.
exec venv/bin/python usage_audit.py --gio 24 --canh-bao
