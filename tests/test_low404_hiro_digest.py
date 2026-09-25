"""LOW-404: Hiro dung carousel ban tin van — moi headline mot slide (anh + tieu de + tom tat).

Giu:
  1. Khoi chu (tieu de + tom tat) <= 20% chieu cao khung, do tren pixel that; nen chu qua
     cong overlay LOW-286 cua carousel; chu qua dai thi DUNG (khong tu cat).
  2. Cong spec: moi tin co slide hoac `skipped` kem ly do, dung thu tu, ma anh dung tin,
     tieng Viet co dau.
  3. Bo > 10 slide gui HAI album, nut Duyet chi o album cuoi.
  4. Chua co topic `hiro` o brand thi KHONG tao gi (merge code truoc khi dung profile).
  5. Sidecar meta/img/writer du cho nut Duyet/Lam lai; Lam lai khong chay engine cua Dre.

Chay:  python tests/test_low404_hiro_digest.py
"""
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from PIL import Image, ImageDraw                               # noqa: E402

import digest_slide                                            # noqa: E402
import hiro_pick                                               # noqa: E402
import hiro_prepare                                            # noqa: E402
import hiro_submit                                             # noqa: E402
import role                                                    # noqa: E402
import tam                                                     # noqa: E402

role.set_active_role("hiro")

TITLE = "Nvidia đầu tư 5 tỷ USD vào Intel, bắt tay làm chip AI cho PC"
SUMMARY = ("Thương vụ biến Nvidia thành cổ đông lớn của Intel; hai bên cùng phát triển CPU x86 "
           "tích hợp GPU RTX cho laptop và trung tâm dữ liệu.")


def _photo(path, size=(1600, 900), seed=3):
    """Anh 'chup' gia: nhieu mang mau, khong phang (khong roi vao nhanh nen phang LOW-341)."""
    import random
    rnd = random.Random(seed)
    im = Image.new("RGB", size, (60, 80, 110))
    d = ImageDraw.Draw(im)
    for _ in range(400):
        x, y = rnd.randint(0, size[0]), rnd.randint(0, size[1])
        c = tuple(rnd.randint(0, 255) for _ in range(3))
        d.ellipse((x, y, x + 70, y + 70), fill=c)
    im.save(path)
    return str(path)


# ---- 1. khoi chu + dung slide ------------------------------------------------

def test_text_block_stays_within_20_percent():
    d = ImageDraw.Draw(Image.new("RGB", (digest_slide.W, digest_slide.H)))
    lay = digest_slide.fit_text(d, TITLE, SUMMARY)
    assert lay.total <= digest_slide.TEXT_MAX_H == round(digest_slide.H * 0.20)
    assert len(lay.title_lines) <= digest_slide.TITLE_MAX_LINES
    assert lay.summary_font.size < lay.title_font.size, "tom tat phai nho hon tieu de"


def test_too_long_text_is_refused_not_cut():
    assert digest_slide.check_text(TITLE, SUMMARY) == ""
    assert "rut gon" in digest_slide.check_text(TITLE * 3, SUMMARY * 4)


def test_build_all_names_slides_and_passes_overlay_gate():
    tmp = Path(tam.temp_dir(prefix="low404_"))
    img = _photo(tmp / "p.png")
    slides = [{"image": img, "title": TITLE, "summary": SUMMARY},
              {"image": img, "title": "OpenAI ra mắt GPT-5.5", "summary": "Mô hình mới, giá giảm một nửa."},
              {"image": img, "title": "Anthropic gọi vốn", "summary": "Định giá tăng gấp đôi."}]
    paths, errors = digest_slide.build_all(slides, tmp / "d.png", "donniechublog")
    assert errors == [], errors
    assert [p.name for p in paths] == ["d.png", "d_2.png", "d_3.png"]
    for p in paths:
        with Image.open(p) as im:
            assert im.size == (1080, 1350)


# ---- 2. cong spec -------------------------------------------------------------

def _job(n=3):
    return {"scan_role": "vera", "brand": "dcgr",
            "items": [{"index": i, "title": f"Tin {i}", "link": f"https://x.test/{i}",
                       "summary_vi": f"Tóm tắt {i}"} for i in range(1, n + 1)]}


def _images(tmp, n=3):
    img = _photo(tmp / "p.png")
    return {i: [{"code": f"{i}A", "path": img, "w": 1600, "h": 900, "chart": False, "domain": "x.test"},
                {"code": f"{i}B", "path": img, "w": 1600, "h": 900, "chart": False, "domain": "x.test"}]
            for i in range(1, n + 1)}


def _slide(i, code=None, title=None, summary="Tóm tắt ngắn gọn về tin này."):
    return {"index": i, "image": code or f"{i}A", "title": title or f"Tiêu đề tin số {i}",
            "summary": summary}


def test_valid_spec_resolves_in_order():
    tmp = Path(tam.temp_dir(prefix="low404_"))
    spec = {"slides": [_slide(1), _slide(2, "2B"), _slide(3)]}
    ra, loi = hiro_submit.resolve(spec, _job(), _images(tmp))
    assert loi == [], loi
    assert [s["code"] for s in ra] == ["1A", "2B", "3A"]


def test_spec_gates():
    tmp = Path(tam.temp_dir(prefix="low404_"))
    job, imgs = _job(), _images(tmp)
    cases = {
        "thieu tin":       {"slides": [_slide(1), _slide(2)]},
        "anh tin khac":    {"slides": [_slide(1), _slide(2, "1A"), _slide(3)]},
        "lech thu tu":     {"slides": [_slide(2), _slide(1), _slide(3)]},
        "skip khong ly do": {"slides": [_slide(1), _slide(2)], "skipped": [{"index": 3}]},
        "mat dau":         {"slides": [_slide(1, title="Nvidia dau tu vao Intel"), _slide(2), _slide(3)]},
        "qua dai":         {"slides": [_slide(1, summary="x " * 200), _slide(2), _slide(3)]},
        "trung tin":       {"slides": [_slide(1), _slide(1), _slide(2), _slide(3)]},
    }
    for ten, spec in cases.items():
        _, loi = hiro_submit.resolve(spec, job, imgs)
        assert loi, f"{ten}: cong phai chan"
    ok = {"slides": [_slide(1), _slide(2)], "skipped": [{"index": 3, "reason": "không có ảnh"}]}
    assert hiro_submit.resolve(ok, job, imgs)[1] == []


def test_skeleton_moves_imageless_items_to_skipped():
    job = _job()
    sk = hiro_prepare.spec_skeleton(job, {1: [{"code": "1A"}], 2: [], 3: [{"code": "3A"}]})
    assert [s["index"] for s in sk["slides"]] == [1, 3]
    assert sk["skipped"] == [{"index": 2, "reason": "không tìm được ảnh thật"}]


def test_prepare_item_crops_photo_keeps_chart_full_width():
    tmp = Path(tam.temp_dir(prefix="low404_"))
    photo = io.BytesIO()
    Image.open(_photo(tmp / "src.png")).save(photo, "PNG")
    chart = Image.new("RGB", (1600, 900), "white")
    d = ImageDraw.Draw(chart)
    for x in range(100, 1500, 120):
        d.rectangle((x, 900 - (x % 700) - 50, x + 60, 850), fill=(30, 90, 200))
        d.text((x, 860), "Q%d" % (x // 120), fill="black")
    for y in range(100, 850, 75):
        d.line((80, y, 1520, y), fill=(200, 200, 200))
    cb = io.BytesIO()
    chart.save(cb, "PNG")
    blobs = {"https://a/photo.png": photo.getvalue(), "https://a/photo-copy.png": photo.getvalue(),
             "https://a/chart.png": cb.getvalue(), "https://a/tiny.png": _png_bytes((200, 120))}

    class R:
        def __init__(self, b):
            self.status_code, self.content = 200, b
    import article_images
    saved = (hiro_prepare._candidate_urls, article_images._download)
    hiro_prepare._candidate_urls = lambda it: [(u, "https://a/page", "") for u in blobs]
    article_images._download = lambda u, timeout=15: R(blobs[u])
    try:
        got = hiro_prepare.prepare_item({"index": 4, "title": "t", "link": "https://a/page"}, tmp / "h")
    finally:
        hiro_prepare._candidate_urls, article_images._download = saved
    by = {a["image_url"]: a for a in got}
    assert "https://a/tiny.png" not in by, "anh qua nho phai bi bo"
    assert "https://a/photo-copy.png" not in by, "cung mot anh o URL khac phai bi bo (dhash)"
    assert [a["code"] for a in got] == ["4A", "4B"]
    with Image.open(by["https://a/photo.png"]["path"]) as im:
        assert abs(im.size[0] / im.size[1] - 0.8) < 0.01, im.size
    assert by["https://a/chart.png"]["chart"] and not by["https://a/photo.png"]["chart"]
    with Image.open(by["https://a/chart.png"]["path"]) as im:
        assert im.size == (1600, 900), "chart giu full be ngang"


def test_same_image_in_two_items_is_a_publisher_placeholder():
    tmp = Path(tam.temp_dir(prefix="low404_"))
    a = _photo(tmp / "a.png", seed=1)
    b = _photo(tmp / "b.png", seed=2)
    logo = _photo(tmp / "logo.png", seed=9)
    images = {9: [{"code": "9A", "path": logo}, {"code": "9B", "path": a}],
              12: [{"code": "12A", "path": logo}],
              13: [{"code": "13A", "path": b}]}
    got = hiro_prepare.drop_shared_placeholders(images)
    assert [x["code"] for x in got[9]] == ["9B"] and got[12] == [] and len(got[13]) == 1
    sheet = hiro_prepare.contact_sheet(got, tmp / "sheet.png")
    assert sheet and sheet.exists()


def _png_bytes(size):
    b = io.BytesIO()
    Image.new("RGB", size, (120, 30, 30)).save(b, "PNG")
    return b.getvalue()


# ---- 3. gui album ------------------------------------------------------------

def test_more_than_ten_slides_go_as_two_albums_button_on_last():
    import send_telegram
    calls = []

    def fake_post(vai, files, mo_ta="", reply_to=None, duyet=None):
        calls.append((vai, len(files), duyet, mo_ta))
        return {"ok": True, "result": [{"message_id": 100 + len(calls)}]}
    saved = send_telegram.post
    send_telegram.post = fake_post
    try:
        mid = hiro_submit.send([f"f{i}.png" for i in range(13)], "Bản tin", "hiro-vera-x")
    finally:
        send_telegram.post = saved
    assert [(c[0], c[1], c[2]) for c in calls] == [("hiro", 10, None), ("hiro", 3, "hiro-vera-x")]
    assert "slide 11–13" in calls[1][3] and mid == 101


# ---- 4-5. chot topic, sidecar, lam lai ---------------------------------------

def test_not_enabled_without_hiro_topic():
    import env_load
    saved = env_load.topics
    env_load.topics = lambda brand=None: {"vera": 5, "dre": 6}
    try:
        assert not hiro_pick.enabled()
        env_load.topics = lambda brand=None: {"vera": 5, "hiro": 9}
        assert hiro_pick.enabled()
    finally:
        env_load.topics = saved


def test_disabled_brand_creates_nothing():
    sent, created = [], []
    saved = (hiro_pick.enabled, hiro_pick._send_text, hiro_pick.kanban_create)
    hiro_pick.enabled = lambda: False
    hiro_pick._send_text = lambda *a, **k: sent.append(a[2])
    hiro_pick.kanban_create = lambda *a, **k: created.append(a) or ("t", None)
    try:
        hiro_pick.process_hiro("tok", "-1", 7, "vera", hiro_pick.HiroCommand(), None)
    finally:
        hiro_pick.enabled, hiro_pick._send_text, hiro_pick.kanban_create = saved
    assert created == [] and "chưa bật" in sent[0]


def test_sidecars_feed_approve_buttons():
    tmp = Path(tam.temp_dir(prefix="low404_"))
    saved = hiro_pick.DRAFTS
    hiro_pick.DRAFTS = tmp
    try:
        items = _job(3)["items"]
        writer = hiro_pick.write_sidecars("hiro-vera-1", "vera", items, "dcgr", "Bản tin Vera", "BODY", "t_9")
    finally:
        hiro_pick.DRAFTS = saved
    meta = json.loads((tmp / "hiro-vera-1.meta.json").read_text(encoding="utf-8"))
    img = json.loads((tmp / "hiro-vera-1.img.json").read_text(encoding="utf-8"))
    w = json.loads((tmp / "hiro-vera-1.writer.json").read_text(encoding="utf-8"))
    assert meta["digest"] and meta["digest_links"] == [it["link"] for it in items]
    assert meta["source_url"] == items[0]["link"] and meta["brand"] == "dcgr"
    assert img["image_role"] == "hiro" and img["carousel"] and img["body"] == "BODY"
    assert w["writer_role"] == writer == role.writer_for("vera", "dcgr") and not w["created"]
    assert "1. Tin 1" in w["body"] and "3. Tin 3" in w["body"] and f"{writer}_prepare.py hiro-vera-1" in w["body"]


def test_role_wiring():
    assert role.rules_module("hiro").AREA_DOWNLOAD == role.rules_module("dre").AREA_DOWNLOAD
    assert "hiro" not in role.ROLE_CAROUSEL and "hiro" not in role.ROLE_IMAGE
    src = (ROOT / "approve_post.py").read_text(encoding="utf-8")
    assert 'im.get("image_role") == "hiro" else _refresh_images_for_redo(draft_id)' in src, \
        "Lam lai bo Hiro khong duoc chay engine anh cua Dre"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
