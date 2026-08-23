#!/bin/bash
# Soi usage that tu 9router: bat fallback am tham va model tut cache.
# Khong goi LLM, chi doc SQLite cuc bo, khong ton mot dong nao.
cd /home/donniechu/content-team || exit 1
exec venv/bin/python usage_audit.py --gio 6 --canh-bao
