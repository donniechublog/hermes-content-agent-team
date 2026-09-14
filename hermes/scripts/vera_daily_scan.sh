#!/bin/bash
# Vera quet tin dau tu/kinh te — gui bao cao vao topic market. Khong tao task khac.
#
# Vo mong: than script nam o daily_scan.sh, MOT ban cho ca ba vai (gop
# 06/09/2026 dot 2 — ba tep nay tung trung nhau ~90% va da bat dau lech nhau).
# Giu ten tep cu de khong phai sua job cron dang chay tren may chu.
# Tham so la slug profile (LOW-14 doi market -> vera; LOW-20: assignee di theo no).
exec "$(dirname "$0")/daily_scan.sh" vera
