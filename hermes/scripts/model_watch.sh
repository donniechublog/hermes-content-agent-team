#!/bin/bash
# Theo doi suc khoe model, canh bao Telegram khi trang thai doi.
# Khong goi LLM, chi la HTTP probe, gan nhu khong ton gi.
cd /home/donniechu/content-team || exit 1
exec venv/bin/python model_watch.py --quiet
