#!/bin/bash
# Vera quet tin dau tu/kinh te — gui bao cao vao topic market. Khong tao task khac.
#
# Vo mong: than script nam o quet_daily_scan.sh, MOT ban cho ca ba vai (gop
# 06/09/2026 dot 2 — ba tep nay tung trung nhau ~90% va da bat dau lech nhau).
# Giu ten tep cu de khong phai sua job cron dang chay tren may chu.
exec "$(dirname "$0")/quet_daily_scan.sh" market
