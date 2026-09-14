#!/usr/bin/env python3
"""Goi `prepare`: engine chuan bi anh/tu lieu, tach theo PHA (audit A1).

image_prepare.py o goc van la diem vao (run/CLI) de cron, SOUL va cac vai KHONG
phai doi lenh. Thu tu phu thuoc mot chieu:
    common <- source, browser, download_filter <- vision <- fallback_rounds;  manifest <- common
"""
import sys
from pathlib import Path

# Goc du an phai nam tren sys.path truoc khi cac module con `import env_load`.
_GOC = str(Path(__file__).resolve().parent.parent)
if _GOC not in sys.path:
    sys.path.insert(0, _GOC)
