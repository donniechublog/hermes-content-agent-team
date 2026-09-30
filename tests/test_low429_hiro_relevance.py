"""LOW-429: anh Hiro phai LIEN QUAN tin — tin AMD/World Labs khong duoc nhan anh logo Meta.

Do that 30/09/2026 (ban tin Vera dcgr): ung vien chi xep theo do net/ty le ('net, ti le dep'),
khong ai kiem anh co noi ve tin. Nay moi anh qua vision (`_judge`); anh lac de duoc giu trong danh
sach kem co `relevant: False` nhung: khong chiem cho MAX_CANDIDATES, skeleton khong chon, brief ghi
'KHONG DUNG', hiro_submit chan.

Chay:  python tests/test_low429_hiro_relevance.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import hiro_prepare                                            # noqa: E402
import hiro_submit                                             # noqa: E402
import role                                                    # noqa: E402

role.set_active_role("hiro")

ITEM = {"index": 4, "title": "AMD thâu tóm World Labs của Fei-Fei Li nhằm mở rộng mô hình không gian 3D",
        "summary_vi": "Thương vụ chiến lược.", "link": "https://x/y"}


def _patch(verdicts, logo=None):
    """Gia lap: moi URL 'u<i>' cho mot anh, vision tra verdicts[i]."""
    saved = (hiro_prepare._candidate_urls, hiro_prepare._save_candidate, hiro_prepare._judge,
             hiro_prepare.logo_for_item)
    hiro_prepare._candidate_urls = lambda it, wide_only=False: [(f"u{i}", "https://news.example/a", "x")
                                                                for i in range(len(verdicts))]
    hiro_prepare._save_candidate = lambda url, out, seen: {"path": str(out), "w": 800, "h": 1000,
                                                           "chart": False, "dhash": int(url[1:])}
    hiro_prepare._judge = lambda path, title: verdicts[_idx(path)]
    hiro_prepare.logo_for_item = lambda it, folder: logo
    return saved


def _idx(path):
    # ma anh 4A, 4B, ... -> chi so theo thu tu chay (A=0)
    return "ABCDEFGH".index(Path(path).stem[-1])


def _restore(saved):
    (hiro_prepare._candidate_urls, hiro_prepare._save_candidate, hiro_prepare._judge,
     hiro_prepare.logo_for_item) = saved


def _v(lq, mo_ta=""):
    return {"relevant": lq, "description": mo_ta}


def test_irrelevant_image_is_flagged_and_does_not_take_a_slot():
    saved = _patch([_v(False, "logo Meta trên tòa nhà kính")] + [_v(True, "Lisa Su")] * 4)
    try:
        got = hiro_prepare.prepare_item(ITEM, Path("/tmp/none"))
    finally:
        _restore(saved)
    ok = [a for a in got if a["relevant"] is True]
    bad = [a for a in got if a["relevant"] is False]
    assert len(ok) == hiro_prepare.MAX_CANDIDATES and len(bad) == 1, [(a["code"], a["relevant"]) for a in got]
    assert bad[0]["description"].startswith("logo Meta")
    assert hiro_prepare.usable(got) == ok


def test_all_irrelevant_falls_back_to_logo_card_for_quote_slide():
    logo = {"code": "4L", "path": "/tmp/l.png", "w": 1200, "h": 1500, "chart": False, "kind": "logo",
            "label": "AMD", "domain": "commons.wikimedia.org", "why": ""}
    saved = _patch([_v(False, "logo Meta")] * hiro_prepare.MAX_REJECTED, logo=logo)
    try:
        got = hiro_prepare.prepare_item(ITEM, Path("/tmp/none"))
    finally:
        _restore(saved)
    assert [a for a in got if a.get("relevant") is False] and got[-1]["code"] == "4L"
    # tin 4 nam o vi tri CHAN (quote) -> phai dung the logo, khong dung anh lac
    sk = hiro_prepare.spec_skeleton({"items": [{"index": 3, "title": "a"}, ITEM]}, {3: [dict(logo, code="3L")], 4: got})
    quote = [s for s in sk["slides"] if s["index"] == 4][0]
    assert quote["style"] == "quote" and quote["image"] == "4L", quote


def test_no_usable_image_at_all_is_skipped_with_reason():
    bad = {"code": "4A", "path": "/tmp/a.png", "w": 800, "h": 1000, "chart": False, "domain": "x",
           "relevant": False, "description": "logo Meta"}
    sk = hiro_prepare.spec_skeleton({"items": [ITEM]}, {4: [bad]})
    assert sk["slides"] == [] and "liên quan" in sk["skipped"][0]["reason"], sk


def test_unknown_vision_result_is_kept_but_brief_says_not_seen():
    a = {"code": "4A", "path": "/tmp/a.png", "w": 800, "h": 1000, "chart": False, "domain": "x",
         "relevant": None, "description": ""}
    job = {"scan_role": "vera", "brand": "dcgr", "items": [ITEM]}
    assert hiro_prepare.usable([a]) == [a]
    brief = hiro_prepare.write_brief("d1", job, {4: [a]}, Path("/tmp/spec.json"))
    assert "CHƯA AI NHÌN" in brief


def test_brief_marks_irrelevant_image_do_not_use():
    bad = {"code": "4A", "path": "/tmp/a.png", "w": 800, "h": 1000, "chart": False, "domain": "infoworld.com",
           "relevant": False, "description": "logo Meta trên tòa nhà kính"}
    job = {"scan_role": "vera", "brand": "dcgr", "items": [ITEM]}
    brief = hiro_prepare.write_brief("d1", job, {4: [bad]}, Path("/tmp/spec.json"))
    assert "`4A` ❌ KHÔNG LIÊN QUAN" in brief and "KHÔNG DÙNG" in brief and "logo Meta" in brief
    assert "KHÔNG có ảnh thật dùng được" in brief


def test_submit_blocks_slide_that_uses_an_irrelevant_image():
    bad = {"code": "4A", "path": "/tmp/a.png", "w": 800, "h": 1000, "chart": False, "domain": "infoworld.com",
           "relevant": False, "description": "logo Meta"}
    spec = {"slides": [{"index": 4, "image": "4A", "title": "AMD thâu tóm World Labs của Fei-Fei Li",
                        "summary": "Thương vụ giúp AMD cạnh tranh công nghệ không gian với Nvidia."}]}
    _ra, loi = hiro_submit.resolve(spec, {"items": [ITEM]}, {4: [bad]}, bo_qua_dau=True)
    assert any("KHONG LIEN QUAN" in x for x in loi), loi
    assert not _ra


def test_judge_fails_open_to_none():
    """Vision ne loi (thieu key / router hong) -> None, khong nem: mot tin hong khong hong ca bo."""
    import prepare.vision as vision
    saved = vision.description_image

    def boom(*a, **k):
        raise RuntimeError("router 503")
    vision.description_image = boom
    try:
        r = hiro_prepare._judge("/tmp/x.png", "AMD thâu tóm World Labs")
    finally:
        vision.description_image = saved
    assert r == {"relevant": None, "description": ""}, r


def _fake_vision(mo_ta, lq):
    import prepare.vision as vision
    saved = vision.description_image
    vision.description_image = lambda *a, **k: (mo_ta, lq)
    return vision, saved


def test_judge_keeps_image_whose_description_names_the_company_in_title():
    """Do that 30/09: 'Bien logo AMD lon ... quay su kien' bi cham khong tren tin AMD -> giu (nhac AMD)."""
    vision, saved = _fake_vision("Biển logo AMD lớn màu trắng trên nền đen tại khu vực quầy sự kiện", False)
    try:
        r = hiro_prepare._judge("/tmp/x.png", ITEM["title"])
    finally:
        vision.description_image = saved
    assert r["relevant"] is True and "AMD" in r["description"], r


def test_judge_rejects_only_when_two_calls_agree():
    """Vision khong on dinh (ChatGPT icon tren tin OpenAI: True roi False): lan hai 'co' thi giu."""
    import prepare.vision as vision
    saved = vision.description_image
    ans = iter([("Biểu tượng ứng dụng ChatGPT", False), ("Biểu tượng ứng dụng ChatGPT", True)])
    vision.description_image = lambda *a, **k: next(ans)
    try:
        r = hiro_prepare._judge("/tmp/x.png", "OpenAI hủy phát hành mô hình GPT-6.1")
    finally:
        vision.description_image = saved
    assert r["relevant"] is True, r


def test_judge_still_rejects_other_companys_logo():
    vision, saved = _fake_vision("Logo và tên công ty Meta màu trắng gắn trên vách kính của tòa nhà", False)
    try:
        r = hiro_prepare._judge("/tmp/x.png", ITEM["title"])
    finally:
        vision.description_image = saved
    assert r["relevant"] is False, r


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
