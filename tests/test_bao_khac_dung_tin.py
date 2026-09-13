#!/usr/bin/env python3
"""LOW-33 (12/09/2026): "bao khac" phai CUNG TIN, va vong chup trang nguon khong
duoc mac dinh moi URL trong `trang` la bai goc.

Ca that: the Ethan "DeepSeek-V4.1-Flash tha trong so" ra anh con vit-robot — anh
hero cua bai "Hugging Face robot duck is already a hit" tren therundown.ai.
`tieu_de_en` = <title> tho "deepseek-ai/DeepSeek-V4.1-Flash · Hugging Face"
(hau to `·` khong bi boc), "Hugging"+"Face" du nguong 2 tu chung, Bing tra bai
vit-robot; `_round_capture_source` lay tam dau tien chup duoc va gan lien_quan=True.
Fail tren code cu (khong co strip_site_suffix/same_story; vong chup khong loc), pass
tren code moi.

Chay:  venv/bin/python tests/test_bao_khac_dung_tin.py
"""
import io
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import article_sources                                             # noqa: E402
import capture_page                                            # noqa: E402
from chuan_bi import fallback_rounds                                 # noqa: E402
from test_nac_chup_nguon import _anh_gia                     # noqa: E402

HF = "deepseek-ai/DeepSeek-V4.1-Flash · Hugging Face"
VIT = "Hugging Face robot duck is already a hit"
THAT = "DeepSeek releases V4.1 Flash, says it outperforms flagship V4 Pro"


def test_boc_hau_to_site_ca_dau_cham_giua():
    assert article_sources.strip_site_suffix(HF) == "deepseek-ai/DeepSeek-V4.1-Flash"
    assert article_sources.strip_site_suffix("Tin X | The Verge") == "Tin X"
    assert article_sources.strip_site_suffix("Tin X » TechCrunch") == "Tin X"
    assert article_sources.strip_site_suffix("Tin X - The Verge") == "Tin X"
    assert article_sources.strip_site_suffix("GPT-5 vs Claude") == "GPT-5 vs Claude"   # gach noi trong ten: giu
    assert article_sources.strip_site_suffix("Claude Opus 4.7 · Anthropic") == "Claude Opus 4.7"


def test_ten_nen_tang_khong_phai_tu_dac_trung():
    assert not (article_sources.story_tokens(HF) & {"hugging", "face"})
    assert {"deepseek", "flash"} <= article_sources.story_tokens(HF)


def test_bai_vit_robot_khong_cung_tin_bai_that_thi_co():
    assert article_sources.same_story(HF, VIT) is False
    assert article_sources.same_story(HF, THAT) is True
    assert article_sources.same_story(HF, "DeepSeek V4.1 Flash vs GLM-5.3 Flash") is True


def test_bao_khac_bing_dung_cung_tin():
    src = (ROOT / "article_sources.py").read_text(encoding="utf-8")
    than = src[src.index("def other_outlets_bing("):src.index("\ndef find(")]
    assert "story_tokens(" in than and "strip_site_suffix(" in than, "other_outlets_bing chua di qua same_story"


def _chay_vong(tieu_de, tit_trang_cua):
    """Stub capture_lead_mobile: bai goc (link) khong chup duoc, bao khac tra tit."""
    goi = []

    def gia(url, ra, phien=None):
        goi.append(url)
        tit = tit_trang_cua.get(url)
        if tit is None:
            return None
        _anh_gia(Path(ra))
        return {"anh": url, "trang": url, "tu": "chup_nguon", "chup_nguon": True,
                "tit_trang": tit, "alt": "khối lead", "ly_do": "khối lead"}
    that = capture_page.capture_lead_mobile
    capture_page.capture_lead_mobile = gia
    err = io.StringIO()
    try:
        with tempfile.TemporaryDirectory() as d, redirect_stderr(err):
            anh, dung_duoc, _ = fallback_rounds._round_capture_source(
                [], "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash",
                [{"url": "https://www.therundown.ai/articles/hugging-face-robot-duck"},
                 {"url": "https://siliconangle.com/deepseek-v4-1-flash"}],
                Path(d), tieu_de=tieu_de)
            return goi, anh, err.getvalue()
    finally:
        capture_page.capture_lead_mobile = that


def test_vong_chup_bo_bao_khac_khong_cung_tin_va_lay_bao_dung():
    goi, anh, log = _chay_vong(HF, {
        "https://www.therundown.ai/articles/hugging-face-robot-duck": VIT,
        "https://siliconangle.com/deepseek-v4-1-flash": THAT,
    })
    assert len(anh) == 1 and anh[0]["mien"] == "siliconangle.com", [a["mien"] for a in anh]
    assert "KHÔNG cùng tin" in log and "therundown.ai" in log, log


def test_vong_chup_khong_co_tieu_de_thi_giu_hanh_vi_cu():
    """Goi cu (khong tieu_de) khong bi doi: van lay tam dau tien — test_nac_chup_nguon giu."""
    goi, anh, _ = _chay_vong("", {
        "https://www.therundown.ai/articles/hugging-face-robot-duck": VIT,
    })
    assert len(anh) == 1 and anh[0]["mien"] == "therundown.ai"


def test_chup_lead_mobile_tra_tit_trang():
    src = (ROOT / "capture_page.py").read_text(encoding="utf-8")
    assert '"tit_trang": tit_trang' in src, "capture_lead_mobile phai tra tit trang de doi chieu"


if __name__ == "__main__":
    ok = 0
    ten = [k for k in list(globals()) if k.startswith("test_")]
    for k in ten:
        try:
            globals()[k]()
            ok += 1
        except AssertionError as e:
            print(f"    FAIL {k}: {e}")
    print(f"{Path(__file__).name:<34} {ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
