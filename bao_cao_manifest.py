#!/usr/bin/env python3
"""Dung ban BAO CAO danh so tu manifest — dung chung cho MOI vai di tim tin.

Vi sao tach rieng: truoc day Finn dung manifest_build.py roi TU GO lai so vao
tin nhan, con Nova va Vera dung manifest_ghi.py. Moi noi mot kieu, va cho nao
agent tu go lai so thi cho do co the lech — so trong tin nhan mot dang, so trong
manifest mot dang, Ong Chu tra loi so lai ra bai khac.

Nay ca ba vai deu goi ham nay. Bao cao va manifest sinh ra tu CUNG mot nguon nen
khong the lech, va ba vai hien cung mot dinh dang nen Ong Chu doc quen mat.
"""
from datetime import datetime, timezone, timedelta

VN = timezone(timedelta(hours=7))
TEN_VAI = {"scout": "Finn", "nova": "Nova", "market": "Vera", "vera": "Vera"}

NHAC = ("Trả lời số thứ tự để tạo bài. Thêm tên vai dựng ảnh nếu muốn:\n"
        "<code>1</code> · <code>1, 2</code> · <code>1, 2 - Ethan</code>")


def dung(items: list, vai: str, ngay: str = None, tieu_de_phu: str = "") -> str:
    """Tra ve ban bao cao HTML danh so, san sang gui bang publish.py --file."""
    ten = TEN_VAI.get(vai, vai)
    ngay = ngay or datetime.now(VN).strftime("%Y-%m-%d")
    d = [f"<b>{ten} — {ngay}</b>"]
    if tieu_de_phu:
        d.append(f"<i>{tieu_de_phu}</i>")
    d.append("")

    # Luat Ong Chu 05/09/2026: bao cao CHI la headline, MOT dong moi tin (so, tieu
    # de, nguon). summary_vi va score_reason van nam trong manifest cho vai viet
    # doc khi tao task, nhung KHONG len bao cao — Ong Chu doc luot 12 tin trong
    # mot man hinh.
    for it in items:
        diem = it.get("score")
        dau = f"<b>{it['index']}.</b>" + (f" [{diem}đ]" if diem is not None else "")
        phu = " · ".join(x for x in (it.get("via"), it.get("source_note")) if x)
        d.append(f"{dau} {it.get('title', '')}" + (f" <i>({phu})</i>" if phu else ""))
    d.append("")

    d.append(NHAC)
    return "\n".join(d)


