"""LOW-405: vai viet (Miles/Jika) viet MOT caption cho ca ban tin van cua Hiro.

Giu:
  1. miles_prepare KHONG goi engine anh cho ban tin (engine chay tren link tin #1 trong
     thu muc Hiro, ghi de contact_sheet, 0 anh thi chuyen draft sang Kite).
  2. Tu lieu = cac slide da duyet (dung thu tu, bo tin skipped) — so cua tin 2..N khong
     bi bao "khong co trong tu lieu".
  3. Caption dung khuon (mo bai + moi slide mot dong "• " + ket) qua TOAN BO caption_check;
     sai so dong liet ke thi cong nop chan.
  4. Draft mang co digest; canh bao "trung link" bo qua draft Hiro.

Chay:  python tests/test_low405_hiro_writer.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import caption_check                                          # noqa: E402
import digest_writer                                          # noqa: E402
import state_paths                                            # noqa: E402
import tam                                                    # noqa: E402


def _wd():
    wd = Path(tam.temp_dir(prefix="low405_"))
    job = {"scan_role": "vera", "brand": "dcgr", "items": [
        {"index": 1, "title": "Oracle tuyên bố bất khả kháng", "summary_vi": "Stargate gặp trở ngại.",
         "link": "https://a.test/1"},
        {"index": 2, "title": "DeepSeek đạt doanh thu 1 tỷ USD", "summary_vi": "Tăng giá API 30%.",
         "link": "https://a.test/2"},
        {"index": 3, "title": "Tin không có ảnh", "summary_vi": "Bị bỏ.", "link": "https://a.test/3"},
        {"index": 4, "title": "TSMC nâng giá wafer 3-6%", "summary_vi": "Áp dụng năm 2027.",
         "link": "https://a.test/4"}]}
    spec = {"slides": [
        {"index": 1, "image": "1A", "title": "Oracle tuyên bố bất khả kháng với Stargate",
         "summary": "Siêu dự án hạ tầng AI gặp trở ngại pháp lý."},
        {"index": 2, "image": "2A", "title": "DeepSeek đạt doanh thu quy năm 1 tỷ USD",
         "summary": "Doanh thu tăng sau đợt tăng giá API."},
        {"index": 4, "image": "4A", "title": "TSMC nâng giá gia công wafer thêm 3-6%",
         "summary": "Nhu cầu chip AI siết chặt công suất năm 2027."}],
        "skipped": [{"index": 3, "reason": "không có ảnh"}]}
    (wd / state_paths.HIRO_JOB_FILE).write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    (wd / "spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return wd


GOOD = """Ba tin hạ tầng AI hôm nay cho thấy tiền và công suất vẫn là nút thắt lớn nhất.

Điểm nhanh:
• Oracle tuyên bố bất khả kháng với Stargate tại New Mexico, siêu dự án gặp trở ngại pháp lý.
• DeepSeek chạm doanh thu quy năm 1 tỷ USD nhờ tăng giá API.
• TSMC nâng giá gia công wafer thêm 3-6% từ năm 2027 vì chip AI chiếm hết công suất.

Bạn nghĩ chi phí phần cứng sẽ đẩy giá dịch vụ AI lên tới đâu?"""


def test_slides_follow_album_order_and_drop_skipped():
    s = digest_writer.load_slides(_wd())
    assert [(x["slide"], x["index"]) for x in s] == [(1, 1), (2, 2), (3, 4)]
    assert s[2]["link"] == "https://a.test/4" and s[1]["source_summary"] == "Tăng giá API 30%."


def test_material_covers_every_slide_numbers():
    tl = digest_writer.material_text(digest_writer.load_slides(_wd()))
    for so in ("1 tỷ USD", "3-6%", "2027", "30%"):
        assert so in tl, so
    assert "Tin không có ảnh" not in tl, "tin skipped khong co slide thi khong vao tu lieu"


def test_good_digest_caption_passes_every_gate():
    wd = _wd()
    tl = digest_writer.material_text(digest_writer.load_slides(wd))
    loi, canh, _ = caption_check.check(GOOD, tl)
    assert loi == [], loi
    assert not [c for c in canh if "1 tỷ" in c or "3-6" in c or "2027" in c], canh
    assert digest_writer.check_caption(GOOD, wd) == []


JIKA = """🔥 Ba tin hạ tầng AI hôm nay cho thấy tiền và công suất vẫn là nút thắt lớn nhất.

Điểm nhanh:
• Oracle tuyên bố bất khả kháng với Stargate tại New Mexico, siêu dự án gặp trở ngại pháp lý.
• DeepSeek chạm doanh thu quy năm 1 tỷ USD nhờ tăng giá API.
• TSMC nâng giá gia công wafer thêm 3-6% từ năm 2027 vì chip AI chiếm hết công suất.

🤔 Quý đạo hữu nghĩ chi phí phần cứng sẽ đẩy giá dịch vụ AI lên tới đâu?"""


def test_jika_voiced_digest_passes_jika_gate_and_brief_says_so():
    wd = _wd()
    tl = digest_writer.material_text(digest_writer.load_slides(wd))
    assert caption_check.check(JIKA, tl)[0] == []
    assert caption_check.check_jika_voice(JIKA) == []
    assert digest_writer.check_caption(JIKA, wd) == []
    brief = digest_writer.prepare({"title": "x", "brand": "dcgr"}, wd, "d", "jika", "v", ROOT)
    assert "GIỌNG JIKA" in brief and "quý đạo hữu" in brief
    assert "GIỌNG JIKA" not in digest_writer.prepare({"title": "x"}, wd, "d", "miles", "v", ROOT)


def test_wrong_line_count_is_blocked():
    wd = _wd()
    thieu = GOOD.replace("• DeepSeek chạm doanh thu quy năm 1 tỷ USD nhờ tăng giá API.\n", "")
    assert digest_writer.check_caption(thieu, wd)
    van_xuoi = GOOD.replace("• ", "")
    assert digest_writer.check_caption(van_xuoi, wd), "khong bullet thi khong dem duoc dong"


def test_prepare_writes_material_and_brief_without_engine():
    wd = _wd()
    brief = digest_writer.prepare({"title": "Bản tin Vera", "brand": "dcgr"}, wd, "hiro-vera-1",
                                  "jika", "dân kinh doanh", ROOT)
    assert (wd / state_paths.MATERIAL_FILE).exists()
    assert "Đúng 3 dòng liệt kê" in brief and "jika_submit.py hiro-vera-1" in brief
    assert brief.index("Oracle") < brief.index("DeepSeek") < brief.index("TSMC")


def test_prepare_script_skips_engine_for_digest():
    src = (ROOT / "miles_prepare.py").read_text(encoding="utf-8")
    main = src[src.index("def main("):]
    assert main.index("digest_writer.is_digest(") < main.index("cb.run("), \
        "ban tin phai re nhanh TRUOC khi goi engine anh"
    sub = (ROOT / "miles_submit.py").read_text(encoding="utf-8")
    assert "digest_writer.check_caption(cap, wd)" in sub
    dw = (ROOT / "draft_write.py").read_text(encoding="utf-8")
    assert '"digest_links": meta.get("digest_links")' in dw


def test_same_link_warning_ignores_hiro_digest():
    import approve_pick as pick
    tmp = Path(tam.temp_dir(prefix="low405_d_"))
    for ma, vai in (("hiro-vera-1", "hiro"), ("tin-1-dre-dcgr", "dre")):
        (tmp / f"{ma}.img.json").write_text(json.dumps({"image_role": vai, "link": "https://a.test/1"}),
                                            encoding="utf-8")
        (tmp / f"{ma}.meta.json").write_text(json.dumps({"brand": "dcgr"}), encoding="utf-8")
    saved = pick.DRAFTS
    pick.DRAFTS = tmp
    try:
        got = pick.live_drafts_same_link("https://a.test/1", "dcgr")
    finally:
        pick.DRAFTS = saved
    assert got == [("tin-1-dre-dcgr", "dre")], got


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
