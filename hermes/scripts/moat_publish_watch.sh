#!/bin/bash
# Hoi moat xem cac bai da duyet len social chua, bao vao topic writer.
# Khong goi LLM, chi HTTP poll, gan nhu khong ton gi. Im lang khi khong co gi moi.
#
# NHIP CHAY: dat cron 5 PHUT, dung 1 phut. moat_publish.py tu ghi chu 10 phut
# la du nhanh; 1 phut = 1440 lan/ngay chi de sinh file output roi lai phai don
# (dong find duoi). 5 phut giu UX y het, bot 80% lan chay.

# Hermes ghi MOT file .md cho moi lan chay (ke ca lan im lang) va khong tu don.
# Chay moi phut = 1440 file/ngay, nen job tu don phan cua minh. Chi thu muc cua
# job nay (a4a246946091), khong dung vao output cua job khac.
find "$HERMES_HOME/cron/output" -maxdepth 2 -name "*.md" -mtime +3 -delete 2>/dev/null

cd /home/donniechu/content-team || exit 1
exec venv/bin/python moat_publish.py
