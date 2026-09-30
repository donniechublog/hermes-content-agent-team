#!/bin/sh
# notify-fail.sh <ten-unit> — do notify-fail@.service goi (xem tep do).
#
# Khong bao gio thoat khac 0: day la duong bao loi, bao loi hong thi khong duoc keo
# them mot unit failed nua len.
unit="$1"
[ -n "$unit" ] || exit 0

# `<3>` la tien to muc syslog: systemd doc no o dau dong stdout (SyslogLevelPrefix mac
# dinh bat) nen dong nay ra muc err, `journalctl --user -p err` loc duoc.
echo "<3>notify-fail: unit $unit da that bai han (het gioi han khoi dong lai) va dang DUNG — can nguoi xem"

# Telegram chi cho approve@<brand>: brand lay tu ten unit, publish.py tu nap
# secret.<brand>.env qua CT_BRAND. Thieu python/publish.py (may la, chua deploy) thi bo qua.
case "$unit" in
  hermes-approve@*.service) ;;
  *) exit 0 ;;
esac
brand=${unit#hermes-approve@}
brand=${brand%.service}
py="$HOME/hermes-agent/venv/bin/python"
[ -x "$py" ] && [ -f "$HOME/content-team/publish.py" ] || exit 0

CT_BRAND="$brand" "$py" "$HOME/content-team/publish.py" \
  --text "Dich vu duyet bai $unit da that bai han va DANG DUNG. Xem: journalctl --user -u $unit -e. Khoi dong lai: systemctl --user reset-failed $unit && systemctl --user start $unit" \
  --to-env TELEGRAM_GROUP_ID --thread-name ada \
  || echo "<4>notify-fail: khong gui duoc Telegram cho $unit"
exit 0
