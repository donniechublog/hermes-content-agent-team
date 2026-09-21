#!/usr/bin/env python3
"""LOW-248: spec.json của Dre / Ethan / Kite đổi khoá + giá trị sang English.

Vai tự viết spec theo brief nên đổi tên là đổi hợp đồng giữa prompt và code. Spec
viết trước deploy (máy chủ 17/09/2026: 141 tệp) không migrate: mỗi vai MỘT hàm
chuẩn hoá ở `role_spec.py`. Tệp này khoá ba điều:

  1. spec tên CŨ (qua role_spec) và spec tên MỚI ra ĐÚNG MỘT kết quả giải
     (carousel.spec.json / tham số card.py / render_edu.spec.json), kể cả thứ tự khoá;
  2. CLI `carousel.py --nen`, `card.py --kieu` vẫn nhận giá trị cũ;
  3. brief/SOUL/SKILL/IMAGE_RULES không còn in tên cũ.

(So byte với code TRƯỚC khi đổi — PNG carousel, PNG thẻ, HTML/PNG render_edu, brief —
đã chạy một lần ngoài repo lúc làm LOW-248; ở đây giữ phần so được trong một phiên.)

Chạy:  venv/bin/python tests/test_designer_spec_keys.py
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tam import so_tam  # noqa: E402
from test_spec_dre import _anh, _m as _m_dre  # noqa: E402
import role_spec  # noqa: E402
import state_paths  # noqa: E402

ARTICLE = "Nvidia mở kho mô hình Nemotron cho mọi nhà phát triển. Jensen Huang nói đây là bước ngoặt."

# Spec hình dạng THẬT như vai viết trước LOW-248 (khung dre_prepare/ethan_prepare/kite_prepare cũ).
DRE_OLD = {
    "tam_co": "thuong", "nen": "sang",
    "cover": {"anh": "A1", "hook": "Nvidia mở kho mô hình cho mọi người", "category": "MODEL RELEASE",
              "label": "NEMOTRON"},
    "slides": [
        {"anh": "A2", "quote": "Chúng tôi mở kho mô hình", "attrib": "Jensen Huang"},
        {"ghep": ["A7", "A8"], "text": "Hai ảnh ngang ghép dọc cùng tone"},
        {"anh": "A9", "cat_ngang": True, "tam": [0.5, 0.4], "text": "Ảnh người cắt dọc"},
        {"anh": "A10", "nhan_vat": "Jensen Huang", "quote": "Đây là bước ngoặt", "attrib": "via Reuters"},
        {"anh": "A3", "text": "Cái cần theo dõi tiếp theo"},
    ],
}
DRE_NEW = {
    "tier": "regular", "background_tone": "light",
    "cover": {"image": "A1", "hook": "Nvidia mở kho mô hình cho mọi người", "category": "MODEL RELEASE",
              "label": "NEMOTRON"},
    "slides": [
        {"image": "A2", "quote": "Chúng tôi mở kho mô hình", "attrib": "Jensen Huang"},
        {"stack": ["A7", "A8"], "text": "Hai ảnh ngang ghép dọc cùng tone"},
        {"image": "A9", "landscape_crop": True, "crop_center": [0.5, 0.4], "text": "Ảnh người cắt dọc"},
        {"image": "A10", "subject": "Jensen Huang", "quote": "Đây là bước ngoặt", "attrib": "via Reuters"},
        {"image": "A3", "text": "Cái cần theo dõi tiếp theo"},
    ],
}
# LOW-343: Ethan chi con full_bleed — cap cu/moi doi ten khoa van phai ra cung dau vao the.
ETHAN_OLD = {"anh": "N1", "anh2": "N2", "kieu": "tran", "nhan_vat": "Jensen Huang",
             "title": "Nvidia mở kho mô hình Nemotron", "kicker": "MODEL RELEASE"}
ETHAN_NEW = {"image": "N1", "image2": "N2", "card_style": "full_bleed", "subject": "Jensen Huang",
             "title": "Nvidia mở kho mô hình Nemotron", "kicker": "MODEL RELEASE"}


def _kite(old: bool) -> dict:
    hi, subj = ("nhan", "nhan_vat") if old else ("highlight", "subject")
    return {"theme": "ink", "hero": "grid", "section": "RESEARCH", "folio": "NEMOTRON", "slides": [
        {"kind": "cover", "eyebrow": "MODEL", "title": "Nemotron mở kho", "image": "B1",
         "caption": "Bảng trong bài · via AA", "standfirst": "Nvidia mở mô hình cho mọi nhà phát triển."},
        {"kind": "bars", "eyebrow": "SỐ LIỆU", "title": "Chi phí giảm ba lần", "accent": "ba lần",
         "bars": [{"label": "Trước", "value": 2.75, "text": "2,75 USD"},
                  {"label": "Sau boost", "value": "0,9", "text": "0,90 USD", hi: True}],
         "caption": "Số trong bài · via Nvidia", "standfirst": "Tuỳ chọn."},
        {"kind": "figure", "eyebrow": "SỐ LIỆU", "title": "Ảnh người trong bài", "image": "H2", subj: "Marc Benioff",
         "caption": "Ảnh · via Salesforce", "standfirst": "Một câu."},
    ] + [{"kind": "statement", "eyebrow": "Ý", "title": f"Ý {i}", "standfirst": "Câu.",
          "cards": [{"num": "01", "text": "a"}, {"num": "02", "text": "b"}]} for i in range(4, 7)]}


def _photo(path, w, h, seed):
    """Ảnh giả kiểu ẢNH CHỤP (nhiều màu) — không bị cổng đọc thành chart."""
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(seed)
    lo = rng.integers(0, 255, (6, 5, 3), dtype=np.uint8)
    base = np.asarray(Image.fromarray(lo).resize((w, h), Image.Resampling.BICUBIC), dtype=np.int16)
    noise = rng.integers(-25, 25, (h, w, 3), dtype=np.int16)
    Image.fromarray(np.clip(base + noise, 0, 255).astype(np.uint8)).save(path)


def _dre_manifest(wd):
    anh = [_anh(wd, f"A{i}", 1000, 1250) for i in range(1, 7)]
    anh += [_anh(wd, "A7", 1500, 1000), _anh(wd, "A8", 1500, 1000), _anh(wd, "A9", 1400, 900),
            _anh(wd, "A10", 1000, 1250, faces=1, description="Jensen Huang phát biểu")]
    for i, a in enumerate(anh):
        _photo(a["original_path"], a["w"], a["h"], i)
    return _m_dre(wd, anh, article_text=ARTICLE, min_images=6, stackable_pairs=[["A7", "A8"]])


def _walk_keys(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(x, list):
        for v in x:
            yield from _walk_keys(v)


OLD_KEYS = {"anh", "anh2", "ghep", "cat_ngang", "tam", "nhan_vat", "tam_co", "nen", "kieu", "nhan"}


# ---------------------------------------------------------------- role_spec
def test_normalisers_turn_old_real_specs_into_new_specs_exactly():
    assert role_spec.dre_spec(DRE_OLD) == DRE_NEW
    assert json.dumps(role_spec.dre_spec(DRE_OLD)) == json.dumps(DRE_NEW), "thu tu khoa phai giu nguyen"
    assert role_spec.ethan_spec(ETHAN_OLD) == ETHAN_NEW
    assert json.dumps(role_spec.kite_spec(_kite(True))) == json.dumps(_kite(False))
    # spec moi di qua van nguyen (idempotent), va khong con khoa cu nao
    for f, new in ((role_spec.dre_spec, DRE_NEW), (role_spec.ethan_spec, ETHAN_NEW), (role_spec.kite_spec, _kite(False))):
        assert f(new) == new
        assert not OLD_KEYS & set(_walk_keys(f(new)))


def test_legacy_maps_match_the_name_table():
    """Bảng docs/tu_dien_ten/designer_spec_keys_v2.json và role_spec là MỘT ánh xạ."""
    t = json.loads((ROOT / "docs" / "tu_dien_ten" / "designer_spec_keys_v2.json").read_text(encoding="utf-8"))

    def plain(d):
        return {k: v for k, v in d.items() if not k.startswith("_")}
    assert plain(t["dre_spec"]) == role_spec.DRE_LEGACY_KEYS
    assert plain(t["dre_spec.cover|slides[]"]) == role_spec.DRE_LEGACY_ITEM_KEYS
    assert {k: v for k, v in t["dre_spec.values"]["tier"].items() if k != v} == role_spec.TIER_LEGACY_VALUES
    assert t["dre_spec.values"]["background_tone"] == role_spec.BACKGROUND_TONE_LEGACY_VALUES
    assert plain(t["ethan_spec"]) == role_spec.ETHAN_LEGACY_KEYS
    assert {k: v for k, v in t["ethan_spec.values"]["card_style"].items() if k != v} == role_spec.CARD_STYLE_LEGACY_VALUES
    assert plain(t["kite_spec.slides[]"]) == role_spec.KITE_LEGACY_SLIDE_KEYS
    assert t["kite_spec.slides[].bars[]"] == role_spec.KITE_LEGACY_BAR_KEYS
    assert set(t["dre_spec.values"]["tier"].values()) == set(role_spec.TIERS)
    assert set(t["ethan_spec.values"]["card_style"].values()) == set(role_spec.CARD_STYLES)


def test_old_values_map_and_unknown_values_pass_through():
    assert role_spec.dre_spec({"tam_co": "flagship", "nen": "toi"}) == {"tier": "flagship", "background_tone": "dark"}
    assert role_spec.dre_spec({"nen": " SANG "})["background_tone"] == "light"
    assert role_spec.dre_spec({"nen": "cau vong"})["background_tone"] == "cau vong"   # cong chan van bao
    assert role_spec.ethan_spec({"kieu": "tran"})["card_style"] == "full_bleed"
    assert role_spec.ethan_spec({"kieu": "banner"})["card_style"] == "banner"
    assert role_spec.background_tone("toi") == "dark" and role_spec.background_tone("light") == "light"
    assert role_spec.card_style_value("tran") == "full_bleed" and role_spec.card_style_value("quote") == "quote"


def test_new_key_wins_when_both_present():
    d = role_spec.dre_spec({"nen": "toi", "background_tone": "light",
                            "cover": {"anh": "A9", "image": "A1"}, "slides": [{"ghep": ["A1", "A2"], "stack": ["A3", "A4"]}]})
    assert d == {"background_tone": "light", "cover": {"image": "A1"}, "slides": [{"stack": ["A3", "A4"]}]}
    assert role_spec.ethan_spec({"kieu": "tran", "card_style": "quote"}) == {"card_style": "quote"}
    k = role_spec.kite_spec({"slides": [{"bars": [{"nhan": True, "highlight": False}]}]})
    assert k["slides"][0]["bars"][0] == {"highlight": False}


def test_normalisers_do_not_mutate_input_and_tolerate_junk():
    old = json.loads(json.dumps(DRE_OLD))
    role_spec.dre_spec(old)
    assert old == DRE_OLD
    assert role_spec.dre_spec([1]) == [1] and role_spec.kite_spec({"slides": ["x", None]}) == {"slides": ["x", None]}


# ---------------------------------------------------------------- old spec == new spec
def test_dre_old_and_new_spec_give_same_carousel_spec():
    import carousel
    import dre_submit
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        m = _dre_manifest(wd)
        a = dre_submit.resolve_spec(role_spec.dre_spec(DRE_OLD), m, wd)
        b = dre_submit.resolve_spec(DRE_NEW, m, wd)
    assert json.dumps(a, ensure_ascii=False) == json.dumps(b, ensure_ascii=False)
    ra, loi, _canh, dung = b
    assert loi == [], loi
    assert ra["tier"] == "regular" and ra["background_tone"] == "light"
    assert ra["background_tone"] in carousel.BACKGROUND
    assert ra["slides"][3]["subject"] == "Jensen Huang"
    assert len(ra["slides"][1]["images"]) == 2
    assert ra["slides"][2]["image"].endswith("A9" + state_paths.LANDSCAPE_SUFFIX)
    assert not OLD_KEYS & set(_walk_keys(ra)), "carousel.spec.json chi mang ten moi"
    assert [n for n, _ in dung][:3] == ["bìa", "slide 2", "slide 3"]


def test_dre_errors_name_new_keys():
    import dre_submit
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        m = _dre_manifest(wd)
        bad = json.loads(json.dumps(DRE_NEW))
        bad["background_tone"] = "cau vong"
        bad["slides"][0] = {"image": "A7", "text": "ngang"}
        bad["slides"][4] = {"text": "khong anh"}
        _ra, loi, _c, _d = dre_submit.resolve_spec(bad, m, wd)
    txt = "\n".join(loi)
    assert '"background_tone": "cau vong" không hợp lệ — chọn dark | light' in txt, txt
    assert '"stack": ["A7"' in txt and '"landscape_crop": true' in txt, txt
    assert 'thiếu "image": "A?" hoặc "stack"' in txt, txt
    assert not re.search(r'"(anh|ghep|cat_ngang|nen|nhan_vat)"', txt), txt


def test_ethan_old_and_new_spec_give_same_card_inputs():
    import ethan_submit
    from test_spec_ethan import _m
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "N1", 1600, 1000), _anh(wd, "N2", 1600, 1000, faces=1, description="Jensen Huang")]
        m = _m(wd, anh, article_text=ARTICLE)
        for old, new in ((ETHAN_OLD, ETHAN_NEW),
                         ({"anh": "N1", "kieu": "tran", "title": "Nvidia mở kho mô hình Nemotron cho mọi người"},
                          {"image": "N1", "card_style": "full_bleed", "title": "Nvidia mở kho mô hình Nemotron cho mọi người"})):
            a = ethan_submit.resolve_spec(role_spec.ethan_spec(old), m, wd)
            b = ethan_submit.resolve_spec(new, m, wd)
            assert json.dumps(a, ensure_ascii=False) == json.dumps(b, ensure_ascii=False)
            assert b[1] == [], b[1]
            assert set(b[0]) == {"card_style", "image", "image2", "cluttered"}
        assert b[0]["card_style"] == "full_bleed"
        _kq, loi, _c = ethan_submit.resolve_spec({"image": "N1", "card_style": "tran"}, m, wd)
    assert not any("không phải kiểu của Ethan" in x for x in loi), loi   # "tran" = full_bleed cu
    assert any('kiểu full_bleed: thiếu "title"' in x for x in loi), loi


def test_kite_old_and_new_spec_give_same_render_input_and_html():
    import kite_submit
    import render_edu
    from test_spec_kite import _hinh, _khong_soi_mat, _m
    with tempfile.TemporaryDirectory() as t, so_tam(t), _khong_soi_mat():
        wd = Path(t)
        hinh = [_hinh(wd, ma="B1", w=1600, h=1100), _hinh(wd, ma="H2", w=1600, h=1100, kind="photo", faces=1)]
        for i, h in enumerate(hinh):
            _photo(h["original_path"], h["w"], h["h"], 90 + i)
        m = _m(wd, hinh)
        a = kite_submit.resolve_spec(role_spec.kite_spec(_kite(True)), m, wd)
        b = kite_submit.resolve_spec(_kite(False), m, wd)
    assert json.dumps(a, ensure_ascii=False) == json.dumps(b, ensure_ascii=False)
    ra, loi, _c = b
    assert loi == [], loi
    assert not OLD_KEYS & set(_walk_keys(ra)), "render_edu.spec.json chi mang ten moi"
    html = render_edu.s_bars(ra["slides"][1], dict(render_edu.THEMES["ink"], hero="grid"))
    assert html.count('class="bar-fill highlight"') == 1 and html.count('class="bar-fill"') == 1, html
    # cot DUOC khai highlight la cot thu hai, khong phai cot mac dinh dau tien
    assert html.index('class="bar-fill"') < html.index('class="bar-fill highlight"')
    assert ".bar-fill.highlight{" in render_edu.base_css(dict(render_edu.THEMES["ink"], hero="grid"))


def test_approve_post_redo_reads_old_and_new_dre_spec_alike():
    import approve_post
    for n in range(1, 7):
        assert approve_post._code_of_slide(role_spec.dre_spec(DRE_OLD), n) == approve_post._code_of_slide(DRE_NEW, n)
    assert approve_post._code_of_slide(DRE_NEW, 1) == ["A1"]
    assert approve_post._code_of_slide(DRE_NEW, 3) == ["A7", "A8"]


# ---------------------------------------------------------------- CLI giu gia tri cu
def _run(args):
    return subprocess.run([sys.executable, "-X", "utf8"] + args, cwd=str(ROOT), capture_output=True, text=True,
                          timeout=120)


def test_carousel_cli_nen_accepts_old_and_new_values():
    with tempfile.TemporaryDirectory() as t:
        sp = Path(t) / "s.json"
        sp.write_text("{}", encoding="utf-8")
        for v in ("dark", "light", "toi", "sang"):
            r = _run(["carousel.py", "--spec", str(sp), "--out", str(Path(t) / "x.png"), "--nen", v])
            assert r.returncode == 1 and "Thieu cover.image" in r.stderr, (v, r.returncode, r.stderr[-300:])
        r = _run(["carousel.py", "--spec", str(sp), "--out", str(Path(t) / "x.png"), "--nen", "mo"])
        assert r.returncode == 2, r.stderr
    import carousel
    assert tuple(carousel.BACKGROUND) == role_spec.BACKGROUND_TONES
    assert all(set(v) == {"bg", "fg", "muted"} for v in carousel.BACKGROUND.values())


def test_card_kieu_accepts_old_and_new_values():
    import card
    for v in ("quote", "full_bleed", "tran"):
        r = _run(["card.py", "--image", "/khong/co.png", "--title", "Câu thử", "--out", "/tmp/x.png", "--kieu", v])
        assert r.returncode != 2 and "invalid choice" not in r.stderr, (v, r.stderr[-300:])
    r = _run(["card.py", "--image", "/khong/co.png", "--title", "Câu thử", "--out", "/tmp/x.png", "--kieu", "banner"])
    assert r.returncode == 2 and "invalid choice" in r.stderr
    try:
        card.build("/khong/co.png", "Câu thử", "/tmp/x.png", kieu="banner")
        raise AssertionError("kieu la phai dung")
    except SystemExit as e:
        assert "quote hoac full_bleed" in str(e)


# ---------------------------------------------------------------- prompt chi in ten moi
def test_prompts_and_error_texts_print_only_new_spec_names():
    code_files = ("dre_prepare.py", "dre_submit.py", "ethan_prepare.py", "ethan_submit.py", "kite_prepare.py",
                  "kite_submit.py", "carousel.py", "card.py", "render_edu.py", "approve_post.py", "submit_common.py",
                  "image_brand.py", "image_rules_dre.py", "image_rules_ethan.py", "image_rules_kite.py",
                  "prepare/vision.py", "prepare/manifest.py", "prepare/fallback_rounds.py", "manifest_values.py",
                  "task_bodies.py")
    quoted = re.compile(r'\\?"(anh|anh2|ghep|cat_ngang|tam|nhan_vat|tam_co|nen|kieu|thuong|tran|toi|sang)\\?"\s*[:\]]'
                        r'|\\?"nhan\\?"\s*:|\bcat_ngang: true|kieu tran\b|"(tran|toi|sang)"\)')
    bad = []
    for f in code_files:
        for i, line in enumerate((ROOT / f).read_text(encoding="utf-8").splitlines(), 1):
            if quoted.search(line):
                bad.append(f"{f}:{i}: {line.strip()[:120]}")
    docs = ("hermes/profiles/shared/dre.SOUL.md", "hermes/profiles/shared/ethan.SOUL.md",
            "hermes/profiles/shared/kite.SOUL.md", "hermes/skills/carousel/SKILL.md",
            "hermes/skills/carousel-edu/SKILL.md", "hermes/skills/hero-image/SKILL.md",
            "IMAGE_RULES_DRE.md", "IMAGE_RULES_ETHAN.md", "IMAGE_RULES_KITE.md", "STYLE_TEXT_SPEC.md", "README.md")
    ticked = re.compile(r'`"?(anh|anh2|ghep|cat_ngang|nhan_vat|tam_co|nen|tran|toi|sang)"?[`:]|--kieu tran')
    for f in docs:
        for i, line in enumerate((ROOT / f).read_text(encoding="utf-8").splitlines(), 1):
            if ticked.search(line):
                bad.append(f"{f}:{i}: {line.strip()[:120]}")
    assert not bad, "con ten spec cu trong prompt/tai lieu:\n  " + "\n  ".join(bad)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
