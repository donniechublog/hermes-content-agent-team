#!/usr/bin/env python3
"""Nấc CHỤP TRANG NGUỒN ở khung mobile (LOW-22, Ông Chủ 06/09/2026 → 12/09/2026).

Luật "vào trang nào chụp thì cũng duyệt theo kích thước mobile, vì hình luôn đang
ở ratio 4:5" chốt từ 06/09 nhưng chỉ sống trong `xep_hang.py`; thang ảnh của tin
thường nhảy thẳng từ ảnh thương hiệu xuống ảnh khái niệm Commons. Tệp này khoá ba
thứ: hằng số mobile chỉ có MỘT bản, nấc mới đứng TRƯỚC nấc khái niệm, và ảnh chụp
được phép làm bìa (Ông Chủ 12/09: "cắt lấy khối lead rồi làm bìa").

Chạy:  venv/bin/python tests/test_nac_chup_nguon.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import chup_trang  # noqa: E402
import luat_anh  # noqa: E402
import phien_browser  # noqa: E402
import xep_hang  # noqa: E402
from chuan_bi import vong_bu  # noqa: E402


def test_hang_so_mobile_chi_co_mot_ban():
    """Chép đôi thì một ngày nào đó hai chỗ lệch nhau mà không ai thấy."""
    assert xep_hang.MOBILE_VIEWPORT is phien_browser.MOBILE_VIEWPORT
    assert chup_trang.MOBILE_VIEWPORT is phien_browser.MOBILE_VIEWPORT
    assert phien_browser.MOBILE_VIEWPORT["width"] == 414
    assert phien_browser.MOBILE_DPR == 3
    assert "iPhone" in phien_browser.MOBILE_UA


def test_nac_chup_nguon_dung_TRUOC_nac_khai_niem():
    """Thứ tự là cả nội dung của ticket: khối lead là vật THẬT của tin, ảnh khái
    niệm thì không. Đảo thứ tự là quay về đúng lỗi 12/09."""
    src = (ROOT / "anh_chuan_bi.py").read_text(encoding="utf-8")
    i_chup = src.index("_vong_chup_nguon(anh")
    i_kn = src.index("_vong_khai_niem(anh")
    assert i_chup < i_kn, "vòng chụp nguồn phải gọi trước vòng khái niệm"


def test_bi_chan_nhan_ra_tuong_chan_bot():
    """Tường chặn bot vẫn có <h1> và vẫn chụp ra ảnh — không nhận ra thì tấm
    "Let's confirm you are human" của arstechnica lên thẳng bìa (12/09/2026)."""
    assert phien_browser.bi_chan("Just a moment...")
    assert phien_browser.bi_chan("", 403)
    assert phien_browser.bi_chan("", None, "Let's confirm you are human. Begin >")
    # Tiêu đề thật của bài vẫn qua, kể cả bài VIẾT VỀ chặn bot (trang dài).
    assert not phien_browser.bi_chan("Mecka AI nears $500M valuation", 200)
    assert not phien_browser.bi_chan("How Cloudflare blocks bots", 200,
                                     "verify you are human " + "x" * 1300)


def _anh_gia(path: Path, seed: int = 0):
    """Một PNG dọc có vân — `phan_loai` đọc được, không phải ảnh rỗng.
    `seed` (13/09/2026, sau khi thêm loại trùng dHash vào `_vong_chup_nguon`):
    lệch pha hoạ tiết để hai lần gọi khác seed ra ảnh THẬT SỰ khác nhau, không
    bị chính cổng loại trùng mới coi là cùng một tấm."""
    from PIL import Image
    im = Image.new("RGB", (414 * 3, 520 * 3))
    px = im.load()
    for y in range(0, im.height, 3):
        for x in range(0, im.width, 3):
            c = (((x + seed * 97) * 7) % 255, ((y + seed * 53) * 5) % 255,
                 ((x + y + seed * 71) * 3) % 255)
            for dy in range(3):
                for dx in range(3):
                    if x + dx < im.width and y + dy < im.height:
                        px[x + dx, y + dy] = c
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def test_anh_chup_duoc_phep_lam_bia_va_khong_hoi_vision():
    """`phan_loai` đọc ảnh chụp trang là "chart/screenshot" rồi dán KHÔNG LÀM BÌA.
    Đúng cho chart của người khác, sai cho khối lead của chính bài.

    LOW-45 (13/09/2026): vòng THỬ HẾT các URL thay vì dừng ở trang đầu — cả
    bài gốc lẫn "báo khác" đều được chụp, và bài gốc (thử TRƯỚC, không mặt
    người) lên bìa; tấm còn lại giữ làm thân, không tấm nào bị bỏ phí."""
    goi = []

    def gia(url, ra, phien=None):
        goi.append(url)
        _anh_gia(Path(ra), seed=len(goi))   # moi URL mot anh KHAC NHAU (cong loai trung dHash)
        return {"anh": url, "trang": url, "tu": "chup_nguon", "chup_nguon": True,
                "alt": "khối lead", "ly_do": "khối lead của trang nguồn"}

    that = chup_trang.chup_lead_mobile
    chup_trang.chup_lead_mobile = gia
    try:
        with tempfile.TemporaryDirectory() as d:
            wd = Path(d)
            anh, dung_duoc, _ = vong_bu._vong_chup_nguon(
                [], "https://vidu.com/bai-toan", [{"url": "https://bao-khac.com/x"}], wd)
    finally:
        chup_trang.chup_lead_mobile = that

    assert goi[0] == "https://vidu.com/bai-toan", "phải thử bài gốc trước"
    assert goi == ["https://vidu.com/bai-toan", "https://bao-khac.com/x"], \
        "phải thử HẾT các URL, không dừng ở trang đầu qua cổng"
    assert len(anh) == 2, anh
    for a in anh:
        assert a["lien_quan"] is True, "ảnh của chính trang tin: không phải hỏi vision"
        assert not any("KHÔNG làm bìa" in g for g in a["ghi_chu"]), a["ghi_chu"]
        # Da dem nen thanh khung 4:5 -> dung MOT MINH duoc, khong dinh luat ghep doi
        assert abs(a["w"] / a["h"] - 0.8) < 0.03, f'{a["ma"]}: {a["w"]}x{a["h"]} chua dem ve 4:5'
    a = anh[0]
    assert any(d.startswith("bìa") for d in a["dung"]), a["dung"]
    assert anh[1]["dung"] == ["thân"], "trang thứ hai qua cổng vẫn giữ làm thân, không lên bìa"
    assert dung_duoc == anh, "cả hai đều dùng được (bìa + thân), không tấm nào bị bỏ phí"


def test_khong_browser_thi_bo_qua_nac_nay():
    """Nấc này cần Chromium; `--khong-browser` phải đi qua mà không nổ."""
    with tempfile.TemporaryDirectory() as d:
        anh, dung_duoc, chua_nhin = vong_bu._vong_chup_nguon(
            [], "https://vidu.com/x", [], Path(d), khong_browser=True)
    assert anh == [] and dung_duoc == [] and chua_nhin == []

def test_khong_co_anh_hero_thi_chup_khoi_tit():
    """Ông Chủ 12/09/2026: "tin ko có tên riêng thì capture màn hình, ko phải đã
    nói rồi sao?" — bài tiểu luận không ảnh hero KHÔNG được trả rỗng rồi rơi
    xuống khái niệm (nơi con mắt nhận bừa phòng máy cho tin toán). Phải chụp
    khối tít ở khung điện thoại."""
    src = (ROOT / "chup_trang.py").read_text(encoding="utf-8")
    assert "co_anh: false" in src, "JS phai tra khoi tit khi khong co anh hero"
    assert 'clip = {"x": 0, "y": max(0, r["top"]), "width": r["w"], "height": r["w"]}' in src
    assert '"kieu": "hero" if r["co_anh"] else "tit"' in src


def test_khoi_tit_la_nac_cuoi_sau_khai_niem():
    """Ông Chủ 12/09/2026 xem bìa tin toán ra toàn chữ: "AI giải toán giỏi hoàn
    toàn có thể dùng hình bảng đen... thiếu idea đến thế à?". Khối tít (trang
    không ảnh hero) chỉ làm bìa khi thực thể + khái niệm đều rỗng."""
    src = (ROOT / "anh_chuan_bi.py").read_text(encoding="utf-8")
    assert src.index("_vong_khai_niem(anh") < src.index("nang_khoi_tit(anh)")
    a = {"ma": "A1", "kieu": "tit", "dung": [], "lien_quan": True, "ghi_chu": []}
    b = {"ma": "A2", "kieu": "tit", "dung": [], "lien_quan": True, "mat": True, "ghi_chu": []}
    anh, dung, _ = vong_bu.nang_khoi_tit([b, a])
    assert dung == [a] and a["dung"][0].startswith("bìa"), (a, b)
    assert b["dung"] == [], "co mat nguoi thi khong len bia"


def test_bang_khai_niem_co_toan_khoa_hoc_lop_hoc():
    import anh_khai_niem
    tk = [x["tu_khoa"] for x in anh_khai_niem.tu_khoa_heuristic(
        "AI is getting good at math. Mathematicians worry about what that means")]
    assert "blackboard mathematical formulas" in tk, tk
    tk = [x["tu_khoa"] for x in anh_khai_niem.tu_khoa_heuristic("AlphaFold predicts new protein structures")]
    assert "laboratory bench scientist" in tk, tk
    tk = [x["tu_khoa"] for x in anh_khai_niem.tu_khoa_heuristic("Students use ChatGPT for homework")]
    assert "classroom students" in tk, tk


def test_anh_co_mat_khong_len_bia_du_thu_truoc_anh_khong_mat_thu_sau():
    """LOW-45 (13/09/2026, Ông Chủ: "bộ logo/founder khó kiếm lắm hay sao mà
    phải dùng cờ China?"). Đo thật: trang ĐẦU tiên (TechCrunch) rớt chất lượng,
    trang THỨ HAI qua cổng ngay là một ảnh minh hoạ chung chung — vòng cũ DỪNG
    NGAY ở đó, chưa bao giờ thử tới các trang còn lại (có thể có ảnh founder
    thật). Vòng mới: thử HẾT, và trong các ảnh qua cổng, ảnh KHÔNG MẶT NGƯỜI
    được ưu tiên lên bìa dù được thử SAU — ảnh có mặt (founder vô danh với
    Kite, thiếu "nhan_vat") giữ làm thân thay vì bị bỏ phí hay ép lên bìa sai
    luật (LUAT_ANH §6)."""
    thu = []

    def gia(url, ra, phien=None):
        thu.append(url)
        _anh_gia(Path(ra), seed=len(thu))   # moi URL mot anh KHAC NHAU (cong loai trung dHash)
        return {"anh": url, "trang": url, "tu": "chup_nguon", "chup_nguon": True,
                "alt": "khối lead", "ly_do": "khối lead của trang nguồn"}

    goc_dem_mat = luat_anh.dem_mat

    def dem_mat_gia(path):
        # Trang DAU (vidu.com, thu truoc) CO mat nguoi; trang SAU (bao-khac.com)
        # KHONG mat — dung nguoc voi thu tu thu de kiem chung uu tien dung, khong
        # phai chi trung hop do thu tu.
        return 1 if "A1" in str(path) else 0

    that = chup_trang.chup_lead_mobile
    chup_trang.chup_lead_mobile, luat_anh.dem_mat = gia, dem_mat_gia
    try:
        with tempfile.TemporaryDirectory() as d:
            wd = Path(d)
            anh, dung_duoc, _ = vong_bu._vong_chup_nguon(
                [], "https://vidu.com/bai-toan", [{"url": "https://bao-khac.com/x"}], wd)
    finally:
        chup_trang.chup_lead_mobile, luat_anh.dem_mat = that, goc_dem_mat

    assert thu == ["https://vidu.com/bai-toan", "https://bao-khac.com/x"], thu
    assert len(anh) == 2, anh
    a1, a2 = anh
    assert a1["mat"] == 1 and a1["dung"] == ["thân"], \
        "ảnh có mặt người (dù thử trước) không được lên bìa"
    assert a2["mat"] == 0 and any(d.startswith("bìa") for d in a2["dung"]), \
        "ảnh không mặt người lên bìa dù được thử SAU"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
