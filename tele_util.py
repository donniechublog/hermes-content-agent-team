#!/usr/bin/env python3
"""Chia mot tin nhan dai thanh nhieu tin cho vua gioi han Telegram.

Telegram tu choi (loi 400) neu `sendMessage` dai qua 4096 ky tu. Truoc day
moi cho gui trong content-team tu cat cut (`text[:4000]`, `text[:LIMIT] + "…"`)
lam MAT phan cuoi. Module nay tach tin dai thanh nhieu phan de gui lien tiep
thay vi cat.

Uu tien cat o ranh gioi xuong dong roi khoang trang, va khong bao gio cat vao
giua mot the HTML `<...>` hay thuc the `&...;` — nen dung an toan cho ca tin
plain-text (chat reply) lan tin `parse_mode="HTML"` (bao cao usage / model /
teaser). Voi cac bao cao theo dong (moi the `<b>..</b>` gon trong mot dong),
cat o xuong dong giu moi the can bang.
"""
import re

# Duoi 4096 cua Telegram: chua bien cho sai lech UTF-16 (emoji dem 2 don vi)
# va cho hau to neu nguoi goi muon them.
GIOI_HAN = 4000

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def bo_ansi(text: str) -> str:
    """Bo ma mau ANSI (stdout cua CLI hay lot vao khi chay agent)."""
    return _ANSI.sub("", text or "")


def _diem_cat_an_toan(khuc: str, cat: int) -> int:
    """Neu `cat` roi vao giua mot the <...> hoac thuc the &...; thi lui ve
    truoc no, tranh gui HTML vo doi khien Telegram tu choi ca tin."""
    truoc = khuc[:cat]
    mo_the = truoc.rfind("<")
    if mo_the > truoc.rfind(">") and mo_the > 0:
        return mo_the
    amp = truoc.rfind("&")
    if amp > truoc.rfind(";") and amp > 0 and cat - amp <= 12:   # &...; toi da ~10
        return amp
    return cat


def chia_tin(text, gioi_han: int = GIOI_HAN) -> list:
    """Chia `text` thanh danh sach cac phan, moi phan <= `gioi_han` ky tu.

    Luon tra ve list co it nhat MOT phan tu (co the la chuoi rong) de nguoi
    goi cu lap la gui du. Khong mat ky tu noi dung (chi bo whitespace o ranh
    gioi cat)."""
    text = (text or "").rstrip()
    if len(text) <= gioi_han:
        return [text]

    phan = []
    con = text
    while len(con) > gioi_han:
        cua_so = con[:gioi_han]
        cat = cua_so.rfind("\n")
        if cat < gioi_han // 2:                 # xuong dong qua som -> thu khoang trang
            cat = cua_so.rfind(" ")
        if cat < 1:                             # khoi lien khong co ranh gioi -> cat cung
            cat = gioi_han
        cat = _diem_cat_an_toan(cua_so, cat)
        if cat < 1:                             # phong khi lui the ve 0
            cat = gioi_han
        phan.append(con[:cat].rstrip())
        con = con[cat:].lstrip()
    if con:
        phan.append(con)
    return phan
