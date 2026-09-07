#!/bin/bash
# Duong dan theo $HOME, khong go cung /home/donniechu (sua 06/09/2026):
# doi ten user Unix hoac chay thu tren may khac la gay im lang.
# Theo doi suc khoe model, canh bao Telegram khi trang thai doi.
# Khong goi LLM, chi la HTTP probe, gan nhu khong ton gi.
cd $HOME/content-team || exit 1
exec venv/bin/python model_watch.py --quiet
