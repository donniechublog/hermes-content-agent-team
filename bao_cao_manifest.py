#!/usr/bin/env python3
"""Dung ban BAO CAO danh so tu manifest — dung chung cho MOI vai di tim tin.

Vi sao tach rieng: truoc day Finn dung manifest_build.py roi TU GO lai so vao
tin nhan, con Nova va Vera dung manifest_ghi.py. Moi noi mot kieu, va cho nao
agent tu go lai so thi cho do co the lech — so trong tin nhan mot dang, so trong
manifest mot dang, Ong Chu tra loi so lai ra bai khac.

Nay ca ba vai deu goi ham nay. Bao cao va manifest sinh ra tu CUNG mot nguon nen
khong the lech, va ba vai hien cung mot dinh dang nen Ong Chu doc quen mat.
"""
import sys
from datetime import datetime
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parent))
import quet_chung                                            # noqa: E402

# Mot ban duy nhat cho ca doi — xem quet_chung. Truoc 06/09/2026 moi tep tu khai
# lai mui gio VN va bang ten vai, nen sua mot cho la phai nho sua ca cum.
VN = quet_chung.VN
TEN_VAI = quet_chung.TEN_VAI

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
        d.append(f"{dau} {it.get('title', '')}" + (f" <i>({phu})</i>" if phu else "")
                 + (" <i>(vai bỏ sót, script tự thêm)</i>" if it.get("tu_them") else ""))
    d.append("")

    d.append(NHAC)
    return "\n".join(d)


