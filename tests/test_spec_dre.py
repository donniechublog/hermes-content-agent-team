#!/usr/bin/env python3
"""Cong chan spec carousel cua Dre (`dre_nop.giai_spec`).

Audit 06/09/2026 do: ham nay 166 dong, 36 nhanh, va gan nhu KHONG co test —
`test_cong_chan` nhac `bob_nop` 19 lan, `dre_nop` mot lan. No la cho duy nhat
kiem spec cua Dre truoc khi ve, va phan lon luat trong do la luat Ong Chu tu
dat sau mot su co that: khong dung lai anh, khong ghep hai anh lech tone,
khong lay chart lam bia, mat nguoi phai khai ten co trong bai.

Cong nay bao loi THAY VI ve sai, nen no hong theo hai chieu deu dat:
  - bao oan  -> Dre sua kieu gi cung khong nop duoc (da xay ra voi cong xep
                hang, xem chu thich dai o dre_nop.py:97)
  - bo sot   -> anh sai len thang Telegram

Chay:  venv/bin/python tests/test_spec_dre.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

from tam import so_tam  # noqa: E402


# ------------------------------------------------------------------ do gia
def _ve(w, h, tone=(60, 70, 90)):
    """Anh co van, tone chi dinh — `lech_tone` do do sang va mau trung binh."""
    im = Image.new("RGB", (w, h), tone)
    d = ImageDraw.Draw(im)
    b = 7
    for x in range(0, w, 29):
        for y in range(0, h, 31):
            b = (b * 1103515245 + 12345) % 2147483648
            d.ellipse([x, y, x + 14, y + 14],
                      fill=tuple(min(255, c + b % 40) for c in tone))
    return im


def _anh(wd, ma, w, h, loai="anh", tone=(60, 70, 90), **k):
    """Mot dong manifest anh, dung cac khoa ma `anh_chuan_bi` that su ghi ra."""
    import luat_anh
    goc = wd / "goc" / f"{ma}.png"
    goc.parent.mkdir(parents=True, exist_ok=True)
    _ve(w, h, tone).save(goc)
    san = wd / "san" / f"{ma}.png"
    san.parent.mkdir(parents=True, exist_ok=True)
    _ve(min(w, h), min(w, h), tone).save(san)               # ban da cat san
    a = {"ma": ma, "goc": str(goc), "san": str(san), "w": w, "h": h,
         "ti_le": round(w / h, 2), "loai": loai, "ngang": w / h >= luat_anh.NGANG_RO,
         "mat": 0, "lien_quan": True, "mo_ta": f"anh thu {ma}", "alt": "", "dung": []}
    a.update(k)
    return a


def _m(wd, anh, **k):
    m = {"anh": anh, "draft_id": "tin-thu", "link": "https://vi.du/bai",
         "chu_bai": "Nvidia mở kho mô hình Nemotron cho mọi nhà phát triển",
         "tu_lieu": {}, "toi_thieu": 5, "cap_ghep": None, "goi_y_bia": []}
    m.update(k)
    return m


def _spec(cover, slides, **k):
    d = {"cover": cover, "slides": slides}
    d.update(k)
    return d


def _bia(ma="A1", **k):
    d = {"anh": ma, "hook": "Nvidia mở kho mô hình", "category": "MODEL RELEASE"}
    d.update(k)
    return d


def _slide(ma, text="Một câu nội dung cho slide này", **k):
    d = {"anh": ma, "text": text}
    d.update(k)
    return d


def _du_slide(anh_ma):
    """Bon slide hop le, hai trong so do co quote — du qua cong so luong."""
    return [_slide(anh_ma[0], quote="Chúng tôi mở kho mô hình", attrib="Jensen Huang"),
            _slide(anh_ma[1], quote="Ai cũng tải được", attrib="Nvidia"),
            _slide(anh_ma[2]), _slide(anh_ma[3])]


def _chay(spec, m, wd):
    import dre_nop
    return dre_nop.giai_spec(spec, m, Path(wd))


def _co(loi, *manh):
    """Co dong loi nao chua het cac manh chuoi khong."""
    return any(all(x in l for x in manh) for l in loi)


def _du(tmp):
    """Bo do day du: 5 anh doc, spec hop le. Tra ve (spec, m, wd)."""
    wd = Path(tmp)
    anh = [_anh(wd, f"A{i}", 1000, 1250) for i in range(1, 6)]
    return _spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])), _m(wd, anh), wd


# ------------------------------------------------------------ duong hop le
def test_spec_du_thi_khong_mot_loi_nao():
    """Chot chieu con lai: cong nay bao oan la Dre khong bao gio nop duoc."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        ra, loi, _canh, dung = _chay(*_du(t))
        assert loi == [], loi
        assert ra["cover"]["hook"] == "Nvidia mở kho mô hình"
        assert len(ra["slides"]) == 4
        assert [n for n, _ in dung] == ["bìa", "slide 2", "slide 3", "slide 4", "slide 5"]


def test_giu_nguyen_cac_truong_chu_cua_vai():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][0].update({"label": "SỐ LIỆU", "nhan_vat": "Jensen Huang"})
        ra, loi, _c, _d = _chay(spec, m, wd)
        assert ra["slides"][0]["label"] == "SỐ LIỆU"
        assert ra["slides"][0]["quote"] == "Chúng tôi mở kho mô hình"


def test_thieu_cover_hoac_slides_bao_ro():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        m = _m(wd, [_anh(wd, "A1", 1000, 1250)])
        _ra, loi, _c, _d = _chay(_spec(None, []), m, wd)
        assert _co(loi, "thiếu", "cover") and _co(loi, "thiếu", "slides"), loi


# ------------------------------------------------------------ ma anh
def test_ma_anh_khong_ton_tai_thi_liet_ke_ma_co_that():
    """Bao "khong ton tai" ma khong noi co nhung ma nao thi vai doan tiep."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][0]["anh"] = "A99"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "A99", "A1"), loi


def test_mot_anh_dung_hai_slide_bi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][1]["anh"] = spec["slides"][0]["anh"]
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "đã dùng ở", "slide 2"), loi


def test_thieu_ca_anh_lan_ghep_thi_bao_ca_hai_duong():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][0].pop("anh")
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "anh", "ghep"), loi


def test_anh_bi_danh_dau_khong_lien_quan_thi_chan():
    """`lien_quan: False` la ket luan cua buoc nhin anh — dung no la dang bai
    mot tam anh khong dinh gi toi tin."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, f"A{i}", 1000, 1250) for i in range(1, 6)]
        anh[1]["lien_quan"] = False
        anh[1]["mo_ta"] = "một con mèo trên ghế sofa"
        _ra, loi, _c, _d = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])),
                                 _m(wd, anh), wd)
        assert _co(loi, "KHÔNG LIÊN QUAN", "A2", "con mèo"), loi


# ------------------------------------------------------------ chart / xep hang
def test_chart_khong_duoc_lam_bia_va_goi_y_bia_khac():
    """Hook de len nua duoi chart la mat nua duoi bang so."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1200, 900, loai="chart")] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(2, 6)]
        _ra, loi, _c, _d = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])),
                                 _m(wd, anh, goi_y_bia=["A3", "A4"]), wd)
        assert _co(loi, "bìa", "A1", "CHART"), loi
        assert _co(loi, "A3"), "khong goi y bia thay the"


def test_chart_lam_slide_thi_dan_nguyen_full_be_ngang():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + \
              [_anh(wd, "A2", 1200, 900, loai="chart")] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(3, 6)]
        ra, loi, _c, _d = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])),
                                _m(wd, anh), wd)
        assert loi == [], loi
        assert ra["slides"][0].get("chart") is True, ra["slides"][0]


def test_anh_xep_hang_duoc_lam_bia_con_lam_slide_thi_la_chart():
    """Anh xep hang la chart nhung DUOC lam bia — bang o nua tren, hook nua duoi."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        xh = _anh(wd, "XH", 1200, 900, loai="chart", xep_hang={"site": "LMArena"})
        anh = [xh] + [_anh(wd, f"A{i}", 1000, 1250) for i in range(2, 6)]
        m = _m(wd, anh, tin_xep_hang=True, xep_hang={"kieu": "chup"})
        ra, loi, _c, _d = _chay(_spec(_bia("XH"), _du_slide(["A2", "A3", "A4", "A5"])), m, wd)
        assert loi == [], loi
        assert "chart" not in ra["cover"], "bia xep hang khong duoc dan kieu chart"


def test_tin_xep_hang_ma_bia_khong_phai_bang_thi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        xh = _anh(wd, "XH", 1200, 900, loai="chart", xep_hang={"site": "LMArena"})
        anh = [xh] + [_anh(wd, f"A{i}", 1000, 1250) for i in range(2, 6)]
        m = _m(wd, anh, tin_xep_hang=True, xep_hang={"kieu": "chup", "site": "LMArena",
                                                     "bang": "text", "model": "GPT"})
        _ra, loi, _c, _d = _chay(_spec(_bia("A2"), _du_slide(["A3", "A4", "A5", "XH"])), m, wd)
        assert _co(loi, "bìa", "TIN XẾP HẠNG"), loi


def test_khong_co_anh_xep_hang_that_thi_KHONG_ep_bia_dung_XH():
    """Hoi quy 06/09/2026 chieu: cong nay tung chan ca khi engine khong chup
    duoc bang, tuc bao vai dung ma "XH" trong khi ma do khong ton tai — vai sua
    kieu gi cung sai va khong bao gio nop duoc."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, f"A{i}", 1000, 1250) for i in range(1, 6)]
        m = _m(wd, anh, tin_xep_hang=True, xep_hang=None)
        _ra, loi, _c, _d = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])), m, wd)
        assert loi == [], loi


# ------------------------------------------------------------ anh ngang
def test_anh_ngang_di_mot_minh_thi_bao_dung_hai_duong_ra():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + [_anh(wd, "A2", 1920, 1080)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(3, 6)]
        _ra, loi, _c, _d = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])),
                                 _m(wd, anh, cap_ghep=["A2", "A3"]), wd)
        assert _co(loi, "slide 2", "NGANG", "ghep", "cat_ngang"), loi


def test_cat_ngang_anh_qua_thap_thi_chan():
    """Cat doc 4:5 roi phong len 1080 se nhoe."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + [_anh(wd, "A2", 1600, 600)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(3, 6)]
        spec = _spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"]))
        spec["slides"][0]["cat_ngang"] = True
        _ra, loi, _c, _d = _chay(spec, _m(wd, anh), wd)
        assert _co(loi, "slide 2", "600px"), loi


def test_cat_ngang_hop_le_thi_ra_tep_da_cat():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + [_anh(wd, "A2", 1920, 1080)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(3, 6)]
        spec = _spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"]))
        spec["slides"][0].update({"cat_ngang": True, "tam": [0.5, 0.4]})
        ra, loi, _c, _d = _chay(spec, _m(wd, anh), wd)
        assert loi == [], loi
        assert Path(ra["slides"][0]["image"]).exists()
        assert ra["slides"][0]["image"].endswith("A2.ngang.png")


# ------------------------------------------------------------ ghep doc
def test_ghep_phai_dung_hai_ma():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][0] = {"ghep": ["A2"], "text": "x"}
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "đúng 2 mã ảnh"), loi


def test_ghep_ra_ti_le_ngoai_dai_thi_chan():
    """Hai anh cao ghep doc ra tam anh rat cao — ngoai dai 4:5..1:1."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + \
              [_anh(wd, "A2", 800, 1600), _anh(wd, "A3", 800, 1600)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(4, 7)]
        spec = _spec(_bia("A1"), [{"ghep": ["A2", "A3"], "text": "x", "quote": "Một câu", "attrib": "X"},
                                  _slide("A4", quote="Câu hai", attrib="Y"),
                                  _slide("A5"), _slide("A6")])
        _ra, loi, _c, _d = _chay(spec, _m(wd, anh, cap_ghep=["A4", "A5"]), wd)
        assert _co(loi, "slide 2", "ngoài dải 4:5..1:1"), loi


def test_ghep_hai_anh_lech_tone_thi_chan():
    """Ong Chu chot 03/09: ghep lech tone doc ra hai vung rieng biet."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + \
              [_anh(wd, "A2", 1600, 900, tone=(15, 15, 20)),
               _anh(wd, "A3", 1600, 900, tone=(235, 235, 240))] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(4, 7)]
        spec = _spec(_bia("A1"), [{"ghep": ["A2", "A3"], "text": "x", "quote": "Một câu", "attrib": "X"},
                                  _slide("A4", quote="Câu hai", attrib="Y"),
                                  _slide("A5"), _slide("A6")])
        _ra, loi, _c, _d = _chay(spec, _m(wd, anh), wd)
        assert _co(loi, "slide 2", "lệch tone"), loi


def test_ghep_dung_lai_anh_da_dung_o_slide_khac():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + \
              [_anh(wd, "A2", 1600, 900), _anh(wd, "A3", 1600, 900)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(4, 7)]
        spec = _spec(_bia("A2"), [{"ghep": ["A2", "A3"], "text": "x", "quote": "Một câu", "attrib": "X"},
                                  _slide("A4", quote="Câu hai", attrib="Y"),
                                  _slide("A5"), _slide("A6")])
        _ra, loi, _c, _d = _chay(spec, _m(wd, anh), wd)
        assert _co(loi, "đã dùng ở", "bìa"), loi


# ------------------------------------------------------------ cong bien tap
def test_bia_thieu_hook_hoac_category():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["cover"].update({"hook": "  ", "category": ""})
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "bìa", "hook") and _co(loi, "bìa", "category"), loi


def test_slide_thieu_ca_text_lan_quote():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][3]["text"] = "   "
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 5", "text", "quote"), loi


def test_it_hon_toi_thieu_slide_thi_chan_va_goi_y_chia_tang():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, f"A{i}", 1000, 1250) for i in range(1, 6)]
        spec = _spec(_bia("A1"), [_slide("A2", quote="Câu một", attrib="X"),
                                  _slide("A3", quote="Câu hai", attrib="Y")])
        _ra, loi, _c, _d = _chay(spec, _m(wd, anh, toi_thieu=5), wd)
        assert _co(loi, "chỉ 3 slide", "tối thiểu 5"), loi


def test_duoi_hai_quote_thi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][1].pop("quote")
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "chỉ 1 slide quote"), loi


def test_quote_con_nguyen_tieng_anh_thi_chan():
    """card.tim_mat_dau CO Y bo qua tieng Anh, nen quote chua dich lot thang
    len Telegram neu cong nay khong bat (06/09/2026)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][0]["quote"] = "We are opening the model zoo to every developer out there"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2"), loi
        assert any("dịch" in l.lower() or "tiếng việt" in l.lower() for l in loi), loi


# ------------------------------------------------------------ nen / tam co
def test_nen_khong_hop_le_thi_liet_ke_lua_chon():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["nen"] = "cau vong"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "nen", "cau vong"), loi


def test_nen_hop_le_di_thang_sang_carousel():
    import carousel
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["nen"] = list(carousel.NEN)[0].upper()
        ra, loi, _c, _d = _chay(spec, m, wd)
        assert loi == [], loi
        assert ra["nen"] == list(carousel.NEN)[0]


def test_flagship_cua_manifest_thanh_tam_co():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        m["flagship"] = True
        ra, _l, _c, _d = _chay(spec, m, wd)
        assert ra["tam_co"] == "flagship"
        spec2, m2, wd2 = _du(t)
        assert "tam_co" not in _chay(spec2, m2, wd2)[0]


# ------------------------------------------------------------ khong dung lai anh
def test_anh_da_gui_o_bai_khac_thi_chan():
    """Ong Chu chot 06/09: bang tỉ số giải golf lên hai thẻ của hai tin khác
    nhau trong cùng một ngày."""
    import luat_anh
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        luat_anh.ghi_da_dung(m["anh"][1]["goc"], "tin-khac", "dre",
                             "https://vi.du/mot-tin-khac-han")
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "TRUNG anh da dung", "tin-khac"), loi


def test_lam_lai_chinh_bai_nay_thi_khong_bi_coi_la_dung_lai():
    """Lam lai mot bai thi duoc giu anh — chan la vai khong bao gio lam lai duoc."""
    import luat_anh
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        luat_anh.ghi_da_dung(m["anh"][1]["goc"], m["draft_id"], "dre", m["link"])
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert loi == [], loi


def test_cung_tin_nhung_vai_khac_thi_khong_chan():
    """Mot tin giao ca Dre lan Ethan ra hai draft_id nhung dung CHUNG bo anh
    engine tai ve; chan la vai nop sau khong con anh nao (do 06/09/2026)."""
    import luat_anh
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        luat_anh.ghi_da_dung(m["anh"][1]["goc"], "tin-thu-ethan", "ethan", m["link"])
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert loi == [], loi


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
