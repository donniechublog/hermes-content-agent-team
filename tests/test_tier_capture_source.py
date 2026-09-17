#!/usr/bin/env python3
"""Nấc CHỤP TRANG NGUỒN ở khung mobile (LOW-22, Ông Chủ 06/09/2026 → 12/09/2026).

Luật "vào trang nào chụp thì cũng duyệt theo kích thước mobile, vì hình luôn đang
ở ratio 4:5" chốt từ 06/09 nhưng chỉ sống trong `ranking.py`; thang ảnh của tin
thường nhảy thẳng từ ảnh thương hiệu xuống ảnh khái niệm Commons. Tệp này khoá ba
thứ: hằng số mobile chỉ có MỘT bản, nấc mới đứng TRƯỚC nấc khái niệm, và ảnh chụp
được phép làm bìa (Ông Chủ 12/09: "cắt lấy khối lead rồi làm bìa").

Chạy:  venv/bin/python tests/test_tier_capture_source.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import capture_page  # noqa: E402
import manifest_values  # noqa: E402
import image_rules_ethan as image_rules  # noqa: E402
import browser_session  # noqa: E402
import ranking  # noqa: E402
from prepare import fallback_rounds  # noqa: E402
from prepare import vision  # noqa: E402


def test_rank_count_mobile_only_has_one_copy():
    """Chép đôi thì một ngày nào đó hai chỗ lệch nhau mà không ai thấy."""
    assert ranking.MOBILE_VIEWPORT is browser_session.MOBILE_VIEWPORT
    assert capture_page.MOBILE_VIEWPORT is browser_session.MOBILE_VIEWPORT
    assert browser_session.MOBILE_VIEWPORT["width"] == 414
    assert browser_session.MOBILE_DPR == 3
    assert "iPhone" in browser_session.MOBILE_UA


def test_tier_capture_source_use_before_tier_concept():
    """Thứ tự là cả nội dung của ticket: khối lead là vật THẬT của tin, ảnh khái
    niệm thì không. Đảo thứ tự là quay về đúng lỗi 12/09."""
    src = (ROOT / "image_prepare.py").read_text(encoding="utf-8")
    i_chup = src.index("_round_capture_source(anh")
    i_kn = src.index("_round_concept(anh")
    assert i_chup < i_kn, "vòng chụp nguồn phải gọi trước vòng khái niệm"


def test_got_block_label_out_wall_block_bot():
    """Tường chặn bot vẫn có <h1> và vẫn chụp ra ảnh — không nhận ra thì tấm
    "Let's confirm you are human" của arstechnica lên thẳng bìa (12/09/2026)."""
    assert browser_session.got_block("Just a moment...")
    assert browser_session.got_block("", 403)
    assert browser_session.got_block("", None, "Let's confirm you are human. Begin >")
    # Tiêu đề thật của bài vẫn qua, kể cả bài VIẾT VỀ chặn bot (trang dài).
    assert not browser_session.got_block("Mecka AI nears $500M valuation", 200)
    assert not browser_session.got_block("How Cloudflare blocks bots", 200,
                                     "verify you are human " + "x" * 1300)


def _image_fake(path: Path, seed: int = 0):
    """Một PNG dọc có vân — `classify` đọc được, không phải ảnh rỗng.
    `seed` (13/09/2026, sau khi thêm loại trùng dHash vào `_round_capture_source`):
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


def test_image_capture_ok_permission_make_cover_and_no_ask_vision():
    """`classify` đọc ảnh chụp trang là "chart/screenshot" rồi dán KHÔNG LÀM BÌA.
    Đúng cho chart của người khác, sai cho khối lead của chính bài.

    LOW-45 (13/09/2026): vòng THỬ HẾT các URL thay vì dừng ở trang đầu — cả
    bài gốc lẫn "báo khác" đều được chụp, và bài gốc (thử TRƯỚC, không mặt
    người) lên bìa; tấm còn lại giữ làm thân, không tấm nào bị bỏ phí."""
    goi = []

    def gia(url, ra, phien=None):
        goi.append(url)
        _image_fake(Path(ra), seed=len(goi))   # moi URL mot anh KHAC NHAU (cong loai trung dHash)
        return {"image_url": url, "page_url": url, "source": "capture_source", "capture_source": True,
                "alt": "khối lead", "score_reason": "khối lead của trang nguồn"}

    that = capture_page.capture_lead_mobile
    capture_page.capture_lead_mobile = gia
    try:
        with tempfile.TemporaryDirectory() as d:
            wd = Path(d)
            anh, dung_duoc, _ = fallback_rounds._round_capture_source(
                [], "https://vidu.com/bai-toan", [{"url": "https://bao-khac.com/x"}], wd)
    finally:
        capture_page.capture_lead_mobile = that

    assert goi[0] == "https://vidu.com/bai-toan", "phải thử bài gốc trước"
    assert goi == ["https://vidu.com/bai-toan", "https://bao-khac.com/x"], \
        "phải thử HẾT các URL, không dừng ở trang đầu qua cổng"
    assert len(anh) == 2, anh
    for a in anh:
        assert a["relevant"] is True, "ảnh của chính trang tin: không phải hỏi vision"
        assert not any("KHÔNG làm bìa" in g for g in a["notes"]), a["notes"]
        # Da dem nen thanh khung 4:5 -> dung MOT MINH duoc, khong dinh luat ghep doi
        assert abs(a["w"] / a["h"] - 0.8) < 0.03, f'{a["id"]}: {a["w"]}x{a["h"]} chua dem ve 4:5'
    a = anh[0]
    assert any(manifest_values.use_label(d).startswith("bìa") for d in a["uses"]), a["uses"]
    assert anh[1]["uses"] == ["body"], "trang thứ hai qua cổng vẫn giữ làm thân, không lên bìa"
    assert dung_duoc == anh, "cả hai đều dùng được (bìa + thân), không tấm nào bị bỏ phí"


def test_capture_source_fail_quality_no_write_no_relevant():
    """LOW-192: `chup_nguon=True` (LOW-45) không hỏi lại "có liên quan bài
    không" — câu hỏi thực tế chỉ về CHẤT LƯỢNG (rõ nét, không phải chụp lại
    một màn hình khác). Do that: khối lead của bài "Anthropic ra tích hợp
    Salesforce" là một bản chụp dở dang (còn spinner "Loading chart...", chữ
    bị cắt cụt), vision trả lien_quan=khong vì lý do CHẤT LƯỢNG đó — nhưng
    ghi_chu cũ luôn in cứng "KHÔNG LIÊN QUAN BÀI" bất kể lý do thật, khiến
    người đọc brief/manifest hiểu lầm là hệ thống coi ảnh sai chủ đề."""
    def _gia(path, tieu_de, hang="", **k):
        return ("ảnh chụp lại màn hình, logo Claude, còn dở dang (loading)", False)

    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        p = wd / "A1.png"
        _image_fake(p)
        a = {"id": "A1", "original_path": str(p)}
        with mock.patch.object(vision, "description_image", side_effect=_gia), \
                mock.patch.object(image_rules, "count_faces", return_value=0):
            vision.classify(a, wd, "Anthropic ra tích hợp Salesforce", chup_nguon=True)
    assert a["relevant"] is False
    assert not any("KHÔNG LIÊN QUAN BÀI" in g for g in a["notes"]), a["notes"]
    assert a["notes"][0].startswith("❌ ẢNH HERO TRANG NGUỒN"), a["notes"]


def test_no_browser_then_skip_tier_this():
    """Nấc này cần Chromium; `--khong-browser` phải đi qua mà không nổ."""
    with tempfile.TemporaryDirectory() as d:
        anh, dung_duoc, chua_nhin = fallback_rounds._round_capture_source(
            [], "https://vidu.com/x", [], Path(d), khong_browser=True)
    assert anh == [] and dung_duoc == [] and chua_nhin == []

def test_no_has_image_hero_then_capture_block_headline():
    """Ông Chủ 12/09/2026: "tin ko có tên riêng thì capture màn hình, ko phải đã
    nói rồi sao?" — bài tiểu luận không ảnh hero KHÔNG được trả rỗng rồi rơi
    xuống khái niệm (nơi con mắt nhận bừa phòng máy cho tin toán). Phải chụp
    khối tít ở khung điện thoại."""
    src = (ROOT / "capture_page.py").read_text(encoding="utf-8")
    assert "co_anh: false" in src, "JS phai tra khoi tit khi khong co anh hero"
    assert 'clip = {"x": 0, "y": max(0, r["top"]), "width": r["w"], "height": r["w"]}' in src
    assert '"capture_kind": "hero" if r["co_anh"] else "headline"' in src


def test_block_headline_is_tier_last_after_concept():
    """Ông Chủ 12/09/2026 xem bìa tin toán ra toàn chữ: "AI giải toán giỏi hoàn
    toàn có thể dùng hình bảng đen... thiếu idea đến thế à?". Khối tít (trang
    không ảnh hero) chỉ làm bìa khi thực thể + khái niệm đều rỗng."""
    src = (ROOT / "image_prepare.py").read_text(encoding="utf-8")
    assert src.index("_round_concept(anh") < src.index("capability_block_headline(anh)")
    a = {"id": "A1", "capture_kind": "headline", "uses": [], "relevant": True, "notes": []}
    b = {"id": "A2", "capture_kind": "headline", "uses": [], "relevant": True, "faces": True, "notes": []}
    anh, dung, _ = fallback_rounds.capability_block_headline([b, a])
    assert dung == [a] and manifest_values.use_label(a["uses"][0]).startswith("bìa"), (a, b)
    assert b["uses"] == [], "co mat nguoi thi khong len bia"


def test_board_concept_has_whole_lock_geometry_layer_geometry():
    import image_concept
    tk = [x["tu_khoa"] for x in image_concept.keyword_heuristic(
        "AI is getting good at math. Mathematicians worry about what that means")]
    assert "blackboard mathematical formulas" in tk, tk
    tk = [x["tu_khoa"] for x in image_concept.keyword_heuristic("AlphaFold predicts new protein structures")]
    assert "laboratory bench scientist" in tk, tk
    tk = [x["tu_khoa"] for x in image_concept.keyword_heuristic("Students use ChatGPT for homework")]
    assert "classroom students" in tk, tk


def test_image_has_face_no_len_cover_enough_try_before_image_no_face_try_after():
    """LOW-45 (13/09/2026, Ông Chủ: "bộ logo/founder khó kiếm lắm hay sao mà
    phải dùng cờ China?"). Đo thật: trang ĐẦU tiên (TechCrunch) rớt chất lượng,
    trang THỨ HAI qua cổng ngay là một ảnh minh hoạ chung chung — vòng cũ DỪNG
    NGAY ở đó, chưa bao giờ thử tới các trang còn lại (có thể có ảnh founder
    thật). Vòng mới: thử HẾT, và trong các ảnh qua cổng, ảnh KHÔNG MẶT NGƯỜI
    được ưu tiên lên bìa dù được thử SAU — ảnh có mặt (founder vô danh với
    Kite, thiếu "nhan_vat") giữ làm thân thay vì bị bỏ phí hay ép lên bìa sai
    luật (IMAGE_RULES §6)."""
    thu = []

    def gia(url, ra, phien=None):
        thu.append(url)
        _image_fake(Path(ra), seed=len(thu))   # moi URL mot anh KHAC NHAU (cong loai trung dHash)
        return {"image_url": url, "page_url": url, "source": "capture_source", "capture_source": True,
                "alt": "khối lead", "score_reason": "khối lead của trang nguồn"}

    goc_dem_mat = image_rules.count_faces

    def dem_mat_gia(path):
        # Trang DAU (vidu.com, thu truoc) CO mat nguoi; trang SAU (bao-khac.com)
        # KHONG mat — dung nguoc voi thu tu thu de kiem chung uu tien dung, khong
        # phai chi trung hop do thu tu.
        return 1 if "A1" in str(path) else 0

    that = capture_page.capture_lead_mobile
    capture_page.capture_lead_mobile, image_rules.count_faces = gia, dem_mat_gia
    try:
        with tempfile.TemporaryDirectory() as d:
            wd = Path(d)
            anh, dung_duoc, _ = fallback_rounds._round_capture_source(
                [], "https://vidu.com/bai-toan", [{"url": "https://bao-khac.com/x"}], wd)
    finally:
        capture_page.capture_lead_mobile, image_rules.count_faces = that, goc_dem_mat

    assert thu == ["https://vidu.com/bai-toan", "https://bao-khac.com/x"], thu
    assert len(anh) == 2, anh
    a1, a2 = anh
    assert a1["faces"] == 1 and a1["uses"] == ["body"], \
        "ảnh có mặt người (dù thử trước) không được lên bìa"
    assert a2["faces"] == 0 and any(manifest_values.use_label(d).startswith("bìa") for d in a2["uses"]), \
        "ảnh không mặt người lên bìa dù được thử SAU"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
