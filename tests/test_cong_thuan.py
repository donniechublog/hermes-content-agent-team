#!/usr/bin/env python3
"""Cac HAM CONG THUAN da tung hong im lang (audit 06/09/2026).

Day la nhung ham khong dung mang, khong dung DB, nhan chuoi tra ra cau truc —
tuc la re nhat de kiem, va cung la cho hoi quy nhieu nhat theo nhat ky su co:
lenh chon sai vai, nut Duyet bien mat vi callback_data qua dai, tin dai bi cat
giua the HTML. Truoc dot nay ca ba deu khong co lay mot test.

Chay:  venv/bin/python tests/test_cong_thuan.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ------------------------------------------------------------- lenh chon tin
def test_doc_lenh_chon_ten_vai_ap_cho_moi_so_truoc_no():
    """Quy tac: ten vai ap cho MOI SO dung truoc no, tinh tu ten vai gan nhat;
    so khong co ten vai nao phia sau ve mac dinh (Ethan/designer)."""
    from duyet_chon_tin import doc_lenh_chon
    ca = [
        ("1", [(1, "ethan")]),
        ("1, 3 - Ethan, 2 - Dre", [(1, "ethan"), (3, "ethan"), (2, "dre")]),
        ("2 - Dre", [(2, "dre")]),
        ("1 2 3", [(1, "ethan"), (2, "ethan"), (3, "ethan")]),
    ]
    for lenh, mong in ca:
        ra = doc_lenh_chon(lenh)
        assert ra is not None, f"{lenh!r} phai doc duoc"
        rut = [(s, v) for s, v, *_ in ra]
        assert rut == mong, f"{lenh!r} -> {rut}, mong {mong}"


def test_doc_lenh_chon_nhan_so_nhieu_tieng_anh():
    """Su co 06/09/2026: "3, 4 - Kites" (Ong Chu go so nhieu) bi doc_lenh_chon tu
    choi CA lenh vi "kites" khong khop TEN_SANG_CAP -> roi ve hoi thoai, gui
    nham cho Finn (topic scout) thay vi tao task cho Kite."""
    from duyet_chon_tin import doc_lenh_chon
    ra = doc_lenh_chon("1 - Ethan 3, 4 - Kites")
    assert ra is not None, "'kites' (so nhieu) phai duoc hieu nhu 'kite'"
    rut = [(s, v) for s, v, *_ in ra]
    assert rut == [(1, "ethan"), (3, "kite"), (4, "kite")], rut


def test_doc_lenh_chon_bo_qua_cau_khong_phai_lenh():
    """Chat thuong khong duoc bien thanh lenh giao viec."""
    from duyet_chon_tin import doc_lenh_chon
    for text in ("", "chào Finn", "hôm nay có gì hay không", "ok"):
        assert not doc_lenh_chon(text), f"{text!r} khong duoc coi la lenh chon"


# ----------------------------------------------------- draft_id <= 55 ky tu
def test_draft_id_luon_vua_callback_data_cua_telegram():
    """draft_id di vao callback_data ("imgredo:" + draft_id). Telegram chan
    callback_data > 64 byte va LANG LE tu choi ca ban phim — anh dang len khong
    co nut nao. Nen draft_id phai <= 55 ky tu ASCII trong MOI truong hop."""
    from duyet_chon_tin import _draft_id
    dai = ("Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench Verified và đồng thời "
           "rẻ hơn bốn mươi lần so với bản trước đó của chính hãng")
    ca = [
        {"title": dai, "index": 1},
        {"title": "AI", "index": 7},
        {"title": "", "index": 3},
        {"title": "———", "index": 4},
    ]
    for it in ca:
        for vai in ("ethan", "dre", "kite"):
            for brand in ("donniechublog", "dcgr"):
                d = _draft_id(it, brand, vai)
                assert d, f"draft_id rong: {it['title'][:20]!r}"
                assert len(d.encode()) <= 55, (
                    f"draft_id {len(d.encode())} byte (> 55): {d!r} — nut Duyet se "
                    "bien mat im lang")
                assert d == d.strip("-"), f"draft_id thua dau gach: {d!r}"
                # role phai con nguyen: hai vai khac nhau khong duoc ra cung khoa
                assert vai[:6] in d, f"draft_id mat phan vai: {d!r}"


def test_draft_id_khac_nhau_theo_vai_va_brand():
    """Mot tin hot giao cho NHIEU role: moi lan giao phai co draft_id rieng,
    neu khong hai san pham song song dung chung png/meta/sidecar va nut Duyet."""
    from duyet_chon_tin import _draft_id
    it = {"title": "Claude Opus 4.6 dat 82% SWE-bench Verified", "index": 2}
    ds = {_draft_id(it, b, v) for b in ("donniechublog", "dcgr")
          for v in ("ethan", "dre", "kite")}
    assert len(ds) == 6, f"draft_id bi trung giua cac vai/brand: {sorted(ds)}"


# ------------------------------------------------------- chia tin nhan dai
def test_chia_tin_khong_cat_giua_the_html():
    """Telegram tu choi tin co the HTML ho. Cat giua "<b>...</b>" la ca tin bi
    tra ve loi, va nguoi goi chi thay "gui that bai"."""
    import re
    from tele_util import chia_tin
    tho = "".join(f"<b>Muc {i}</b> mot doan van dai vua du de day qua gioi han. "
                  for i in range(1, 200))
    phan = chia_tin(tho)
    assert len(phan) > 1, "van ban thu phai dai hon mot phan"
    for i, p in enumerate(phan, 1):
        mo = len(re.findall(r"<b>", p))
        dong = len(re.findall(r"</b>", p))
        assert mo == dong, f"phan {i}: {mo} the mo vs {dong} the dong — cat giua the"
    # khong mat noi dung (bo khoang trang o ranh gioi cat)
    assert "".join(phan).replace(" ", "") == tho.replace(" ", "").rstrip()


def test_chia_tin_luon_tra_it_nhat_mot_phan():
    from tele_util import chia_tin
    for t in ("", None, "ngan"):
        ra = chia_tin(t)
        assert isinstance(ra, list) and len(ra) >= 1, f"{t!r} -> {ra!r}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
