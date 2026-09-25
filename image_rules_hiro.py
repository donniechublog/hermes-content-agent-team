#!/usr/bin/env python3
"""image_rules_hiro.py — bo tieu chi anh cua Hiro (carousel ban tin van, LOW-404).

Slide Hiro la slide THAN cua Dre doi chu: mot anh that phu khung 4:5, chu o duoi, overlay
chi khi do tren pixel can (LOW-286). Nen "anh nay co DUOC DUNG khong" hom nay trung het
luat cua Dre — nguong kho, loc logo/rac, dhash, so anh da dung.

UY QUYEN CHO `image_rules_dre`, KHONG CHEP: LOW-182 tach moi vai mot tep doc lap de luat
mot vai doi khong ap nham sang vai khac. Hiro chua co luat nao cua rieng minh de doi, nen
chep 760 dong ra la hai ban giong het phai sua tay cung nhau. Ngay Ong Chu chot mot luat
anh RIENG cho Hiro, thay dong `__getattr__` duoi bang ban chep cua image_rules_dre roi sua
tren do — `role.rules_module("hiro")` van tro ve dung module nay, khong ai phai doi.
"""
import image_rules_dre as _dre


def __getattr__(name):                   # PEP 562: moi ten chua khai o day lay cua Dre
    return getattr(_dre, name)
