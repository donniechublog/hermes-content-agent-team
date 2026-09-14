#!/bin/bash
# Finn quet tin, cham diem, liet ke danh so — gui bao cao vao topic scout. Khong tao task khac.
#
# Vo mong: than script nam o daily_scan.sh, MOT ban cho ca ba vai (gop
# 06/09/2026 dot 2 — ba tep nay tung trung nhau ~90% va da bat dau lech nhau).
# Giu ten tep cu de khong phai sua job cron dang chay tren may chu.
# Tham so la slug profile (LOW-14 doi scout -> finn; LOW-20: assignee di theo no).
exec "$(dirname "$0")/daily_scan.sh" finn
