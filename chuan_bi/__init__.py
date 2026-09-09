#!/usr/bin/env python3
"""Goi `chuan_bi`: engine chuan bi anh/tu lieu, tach theo PHA (audit A1).

anh_chuan_bi.py o goc van la diem vao (chay/CLI) de cron, SOUL va cac vai KHONG
phai doi lenh. Thu tu phu thuoc mot chieu:
    chung <- nguon, browser, tai_loc <- nhin <- vong_bu;  manifest <- chung
"""
import sys
from pathlib import Path

# Goc du an phai nam tren sys.path truoc khi cac module con `import env_load`.
_GOC = str(Path(__file__).resolve().parent.parent)
if _GOC not in sys.path:
    sys.path.insert(0, _GOC)
