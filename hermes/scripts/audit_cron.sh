#!/bin/bash
# Soat cron ca hai brand mot lan moi sang (them 07/09/2026).
#
# Job nay la NGUOI NHIN cho `failure_streak`. Tu 06/09/2026 moi script cron da
# thoat khac 0 khi hong nen hermes dem dung, nhung ca 9 job deu `deliver: local`
# — khong ai duoc bao. Day la cho doc con so do ra thanh mot tin nhan.
#
# CHAY O CA HAI CONTAINER (blog + dcgr), lech nhau 10 phut. Dat mot ban thi
# ngay container do chet la khong con ai bao — dung cai lo hong can bit. Hai
# lan chay khong sinh hai tin: audit_cron.py doc state/cron_audit.json, thay bo
# van de y het da bao trong ngay thi im.
#
# KHONG dung --im: `deliver: local` nghia la stdout roi vao
# <HERMES_HOME>/cron/output/<job>/<ts>.md, va do la ban ghi duy nhat con lai
# khi Telegram khong gui duoc.
set -uo pipefail
cd "$HOME/content-team" || exit 1
exec venv/bin/python audit_cron.py
