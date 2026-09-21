#!/bin/bash
# Dang cac bai da toi gio trong hang doi xep lich (publish_schedule.run_due).
#
# NHIP CHAY: MOI PHUT. Khac moat_publish_watch (5 phut) vi o day nhip chinh la
# DO TRE ma Ong Chu nhin thay: hang vang thi slot la "bay gio", tuc bam Duyet
# xong ngoi cho dung mot vong cron. 5 phut la ngoi nhin man hinh.
# Vong nao khong co bai toi gio thi run_due() tra rong -> stdout rong -> im.
#
# Duong dan theo $HOME, khong go cung /home/dc-group: doi ten user Unix hoac
# chay thu tren may khac la gay im lang (cung ly do voi moat_publish_watch.sh).

# Hermes ghi MOT file .md cho moi lan chay (ke ca lan im lang) va khong tu don.
# Moi phut = 1440 file/ngay, nen job tu don phan cua minh -- CHI thu muc cua
# job nay, khong dung vao output cua finn/nova/vera/daily-log.
#
# Id cua job KHAC NHAU giua hai HERMES_HOME (hermes sinh id luc tao, khong phai
# bam tu ten), ma script nay chi co MOT ban dung chung. Tra id tu jobs.json
# thay vi go cung mot so roi don nham thu muc cua home kia.
JOB=$(grep -B1 '"name": "publish-due"' "$HERMES_HOME/cron/jobs.json" 2>/dev/null \
      | grep '"id"' | head -1 | cut -d'"' -f4)
if [ -n "$JOB" ] && [ -d "$HERMES_HOME/cron/output/$JOB" ]; then
  find "$HERMES_HOME/cron/output/$JOB" -maxdepth 1 -name "*.md" -mtime +3 -delete 2>/dev/null
fi

cd $HOME/content-team || exit 1
exec venv/bin/python publish_schedule.py
