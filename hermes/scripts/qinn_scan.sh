#!/bin/bash
# Qinn doc tin X (home + cac X List), cham diem, liet ke danh so — gui bao cao
# vao topic qinn. Chay 4 lan/ngay (05:00, 11:00, 17:00, 23:00 VN).
#
# Than script nam o quet_daily_scan.sh, MOT ban cho moi vai di tim tin.
exec "$(dirname "$0")/quet_daily_scan.sh" qinn
