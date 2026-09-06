#!/bin/bash
# Duong dan theo $HOME, khong go cung /home/donniechu (sua 06/09/2026):
# doi ten user Unix hoac chay thu tren may khac la gay im lang.
# Hoi moat xem cac bai da duyet len social chua, bao vao topic writer.
# Khong goi LLM, chi HTTP poll, gan nhu khong ton gi. Im lang khi khong co gi moi.
#
# NHIP CHAY: dat cron 5 PHUT, dung 1 phut. moat_publish.py tu ghi chu 10 phut
# la du nhanh; 1 phut = 1440 lan/ngay chi de sinh file output roi lai phai don
# (dong find duoi). 5 phut giu UX y het, bot 80% lan chay.

# Hermes ghi MOT file .md cho moi lan chay (ke ca lan im lang) va khong tu don.
# Chay moi 5 phut = 288 file/ngay, nen job tu don phan cua minh.
#
# CHI thu muc cua job NAY. Ban truoc ghi chu thich dung ("chi thu muc cua job
# nay (a4a246946091)") nhung duong dan lai la ca `cron/output`, tuc xoa luon
# output cua finn/nova/vera/daily-log sau 3 ngay — ma theo cach cron bao loi
# hien nay (khong deliver di dau), may tep .md do la BANG CHUNG DUY NHAT khi
# mot job quet hong. Don nham chinh cho de tra loi "sang nay Nova co chay khong".
JOB=a4a246946091
if [ -d "$HERMES_HOME/cron/output/$JOB" ]; then
  find "$HERMES_HOME/cron/output/$JOB" -maxdepth 1 -name "*.md" -mtime +3 -delete 2>/dev/null
fi

cd $HOME/content-team || exit 1
exec venv/bin/python moat_publish.py
