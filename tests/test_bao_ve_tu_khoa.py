#!/usr/bin/env python3
"""LOW-45 tiếp (13/09/2026) — Ông Chủ: *"bạn đâu cần tìm đúng tin về việc raise,
chỉ cần search tin tức theo từ khóa kimi / moonshot / kimi k3... là cũng đầy
article có ảnh dùng được mà, đã là ảnh khái niệm thì cần gì phải cầu kỳ?"*

Đo thật 13/09/2026: Moonshot AI có QID Wikidata (`Q130270266`) nhưng RỖNG (0 ảnh
công ty/logo/founder) — `anh_hang`/`anh_wikidata` đều ra 0, và trước bản vá này
`_vong_thuong_hieu` bỏ cuộc luôn, rơi thẳng xuống ảnh khái niệm chung chung (cờ
Trung Quốc). Hai việc:

  1. `nguon_bai.bao_ve_tu_khoa`: tìm báo THẬT theo TỪ KHOÁ (tên hãng), KHÔNG đòi
     "cùng một sự kiện" như `bao_khac_bing` — chỉ cần bài NÓI VỀ từ khoá đó.
  2. `_vong_thuong_hieu` gọi hàm này khi Commons/Wikidata của một hãng RỖNG, quét
     ảnh từ các báo tìm được (`browser_pass`, đã sửa LOW-45 phần 1 nên không vớ
     nhầm `<figure>` là chart) thay vì bỏ cuộc.

Chạy:  venv/bin/python tests/test_bao_ve_tu_khoa.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import nguon_bai                                              # noqa: E402
from chuan_bi import vong_bu                                  # noqa: E402
sys.path.insert(0, str(ROOT / "tests"))
from test_spec_dre import _ve                                 # noqa: E402


class _RSS:
    def __init__(self, items, ngay="Fri, 12 Sep 2026 00:00:00 GMT"):
        rows = "".join(f"<item><link>{u}</link><title>{t}</title>"
                       f"<pubDate>{ngay}</pubDate></item>"
                       for u, t in items)
        self.content = f"<rss><channel>{rows}</channel></rss>".encode()

    def raise_for_status(self):
        pass


def test_bao_ve_tu_khoa_khong_doi_cung_su_kien():
    """Khác `bao_khac_bing` (đòi khớp MỘT sự kiện gốc qua `cung_tin(a, b)` — hai
    tham số): thân hàm không gọi `cung_tin(`, chỉ dùng `tu_cung_tin(` (tách từ,
    một tham số) để so với chính từ khoá."""
    import re
    src = (ROOT / "nguon_bai.py").read_text(encoding="utf-8")
    than = src[src.index("def bao_ve_tu_khoa("):src.index("\ndef tim(")]
    assert not re.search(r"(?<!tu_)\bcung_tin\(", than), \
        "bao_ve_tu_khoa không được đòi 'cùng một sự kiện' (cung_tin)"
    assert "tu_cung_tin(tu_khoa)" in than


def test_bao_ve_tu_khoa_loc_theo_tu_khoa_khong_theo_su_kien_goc():
    """Bài THIẾU từ khoá bị loại; bài CÓ đủ từ khoá (dù nói chuyện khác hẳn sự
    kiện gì) vẫn được nhận — đúng tinh thần "chỉ cần liên quan tới hãng"."""
    items = [
        ("https://a.example/1", "Moonshot AI opens new office in Singapore"),
        ("https://b.example/2", "Kimi Räikkönen wins another F1 podium"),  # khong co "moonshot"
        ("https://c.example/3", "Moonshot AI hires new head of safety team"),
    ]

    def _tai_gia(url, timeout=20):
        return _RSS(items)

    def _head_gia(url, headers=None, timeout=None, follow_redirects=None):
        import types
        return types.SimpleNamespace(status_code=200, url=url)

    with mock.patch.object(nguon_bai, "_tai", side_effect=_tai_gia), \
         mock.patch("httpx.head", side_effect=_head_gia), \
         mock.patch("quet_chung.url_an_toan", return_value=True):
        ra = nguon_bai.bao_ve_tu_khoa("Moonshot AI", so=6)

    mien = {r["toa_soan"] for r in ra}
    assert mien == {"https://a.example", "https://c.example"}, ra


def test_bao_ve_tu_khoa_khong_gioi_han_thoi_gian():
    """LUAT_ANH §1.2d (13/09/2026): "được tìm không giới hạn thời gian, sự
    kiện". Một bài rất CŨ (2019) về đúng từ khoá vẫn phải được nhận — mặc định
    `ngay=None` nghĩa là KHÔNG lọc theo ngày (khác `bao_khac_bing`, vẫn lọc
    ngày vì nó tìm 'báo khác CÙNG một sự kiện' — sự kiện thì có mốc thời gian
    thật, khác hẳn 'ảnh minh hoạ về hãng' thì không)."""
    items = [("https://cu.example/1", "Moonshot AI office photos from 2019")]

    def _tai_gia(url, timeout=20):
        return _RSS(items, ngay="Tue, 01 Jan 2019 00:00:00 GMT")

    def _head_gia(url, headers=None, timeout=None, follow_redirects=None):
        import types
        return types.SimpleNamespace(status_code=200, url=url)

    with mock.patch.object(nguon_bai, "_tai", side_effect=_tai_gia), \
         mock.patch("httpx.head", side_effect=_head_gia), \
         mock.patch("quet_chung.url_an_toan", return_value=True):
        ra = nguon_bai.bao_ve_tu_khoa("Moonshot AI", so=6)

    assert {r["toa_soan"] for r in ra} == {"https://cu.example"}, ra


def test_hang_rong_thi_tim_bao_theo_tu_khoa_quet_anh():
    """`_vong_thuong_hieu`: Commons/Wikidata rỗng cho một hãng -> gọi
    `bao_ve_tu_khoa` rồi `browser_pass`, ứng viên tìm được gắn `thuong_hieu`
    và cuối cùng có mặt trong `dung_duoc` (fail trên code cũ: hãng rỗng thì
    dừng, 0 ảnh, dù có báo thật ngoài kia)."""
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        (wd / "goc").mkdir()
        ung_vien = {"anh": "https://x/photo.jpg", "alt": "", "og": False, "tu": "browser",
                   "trang": "https://baomoi.example/moonshot", "rong": 1600, "cao": 1000, "diem": 45}

        def tai_va_loc_gia(cands, wd2):
            ra = []
            for i, c in enumerate(cands, 1):
                tam = wd2 / f"A{i}.png"
                tam.parent.mkdir(parents=True, exist_ok=True)
                _ve(c["rong"], c["cao"]).save(tam)     # anh CO VAN, khong bi doc nham la chart phang
                c2 = dict(c); c2["goc"] = str(tam); c2["tep"] = str(tam)
                ra.append(c2)
            return ra

        import luat_anh
        with mock.patch("anh_thuong_hieu.hang_trong_tin",
                        return_value=[{"hang": "Moonshot AI", "khoa": "moonshot"}]), \
             mock.patch("anh_thuong_hieu.anh_hang", return_value=[]), \
             mock.patch.object(nguon_bai, "bao_ve_tu_khoa",
                              return_value=[{"url": "https://baomoi.example/moonshot",
                                            "loai": "báo", "tieu_de": "Moonshot AI raises",
                                            "toa_soan": "https://baomoi.example"}]), \
             mock.patch.object(vong_bu, "browser_pass",
                              return_value={"cands": [ung_vien], "tieu_de_en": "", "chu": "",
                                           "trang_them": []}), \
             mock.patch.object(vong_bu, "tai_va_loc", side_effect=tai_va_loc_gia), \
             mock.patch.object(luat_anh, "dem_mat", return_value=0), \
             mock.patch.object(luat_anh, "la_chart", return_value=(False, "ảnh chụp thật")), \
             mock.patch.object(luat_anh, "do_chart", return_value=(0.1, 500)), \
             mock.patch.object(vong_bu, "_xep_hang_boi_canh", return_value=None):  # trung mang that
            anh, dung_duoc, _ = vong_bu._vong_thuong_hieu([], "Moonshot AI raises funding", "", wd)

    assert len(anh) == 1, anh
    a = anh[0]
    assert a.get("thuong_hieu", {}).get("hang") == "Moonshot AI", a
    assert a in dung_duoc, "ảnh tìm qua báo phải qua được đến dùng_được (đủ quan/không mặt vô danh v.v.)"


def test_tim_bao_chay_song_song_ke_ca_khi_commons_co_anh():
    """LUAT_ANH §1.2d (13/09/2026, Ông Chủ chốt nguyên tắc nguồn): tìm báo theo
    từ khoá KHÔNG còn là phương án cuối khi Commons rỗng — chạy SONG SONG với
    Commons cho MỌI hãng, kể cả khi Commons ĐÃ có ảnh. Fail trên code cũ (nhánh
    `if not cands_h`): `bao_ve_tu_khoa` không được gọi vì Commons đã có 1 ảnh."""
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d); (wd / "goc").mkdir()
        anh_commons = {"anh": "https://commons.example/hq.jpg", "alt": "", "og": False,
                      "tu": "thuong_hieu", "rong": 1600, "cao": 1000, "diem": 28,
                      "thuong_hieu": {"hang": "Moonshot AI", "khoa": "moonshot", "loai": "anh",
                                     "tu_khoa": "tru so"}}
        goi = {"tim_bao": False}

        def bao_ve_tu_khoa_gia(hang, so=6):
            goi["tim_bao"] = True
            return []

        with mock.patch("anh_thuong_hieu.hang_trong_tin",
                        return_value=[{"hang": "Moonshot AI", "khoa": "moonshot"}]), \
             mock.patch("anh_thuong_hieu.anh_hang", return_value=[anh_commons]), \
             mock.patch.object(nguon_bai, "bao_ve_tu_khoa", side_effect=bao_ve_tu_khoa_gia), \
             mock.patch.object(vong_bu, "_xep_hang_boi_canh", return_value=None):
            vong_bu._vong_thuong_hieu([], "Moonshot AI raises funding", "", wd)

    assert goi["tim_bao"], "tìm báo theo từ khoá phải chạy dù Commons đã có ảnh (không còn là phương án cuối)"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
