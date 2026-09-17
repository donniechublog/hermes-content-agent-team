#!/usr/bin/env python3
"""Bản ghi quyết định cho MỌI ứng viên ảnh (LOW-225, Ông Chủ chốt 17/09/2026).

Giữ hai điều, cả hai đều phải đúng cùng lúc:
  1. KHÔNG ĐỔI HÀNH VI: cùng bộ ứng viên, bật hay tắt bản ghi thì `download_and_filter`
     và `classify` ra y hệt nhau (trừ khoá mới `decisions`/`vision_raw`).
  2. Mọi chỗ bỏ ảnh đều để lại dấu: pha tải ghi `dropped/dropped.jsonl` + ảnh thu
     nhỏ (kể cả năm chỗ trước đây bỏ IM LẶNG: quá nhỏ, cỡ ảnh AI, logo/đồ hoạ, vượt
     trần, không ra byte); vision ghi câu hỏi/câu trả lời thô, vision nói gì, và nhánh
     regex nào đã lật kết quả.

Chạy:  venv/bin/python tests/test_decision_log.py
"""
import io
import json
import os
import random
import sys
import tempfile
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from prepare import decision_log, download_filter, vision                 # noqa: E402


def _quiet(fn):
    old, sys.stderr = sys.stderr, io.StringIO()
    try:
        return fn()
    finally:
        sys.stderr = old


def _photo(w=900, h=700, seed=0) -> Image.Image:
    """Ảnh chụp GIẢ có vân ngẫu nhiên, TẤT ĐỊNH theo seed (hai lượt bật/tắt bản ghi
    phải nhìn đúng một ảnh): không phẳng, không phải chart/logo."""
    return Image.frombytes("RGB", (w, h), random.Random(seed).randbytes(w * h * 3))


def _save(im: Image.Image, path: Path) -> str:
    im.save(path)
    return str(path)


def _png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _blocky_photo(w=900, h=700) -> Image.Image:
    """Ảnh có mảng khối lớn + vân nhẹ: dHash ổn định khi thu nhỏ (nhiễu thuần thì
    không — bản thu nhỏ của nó không được nhận là trùng)."""
    from PIL import ImageChops, ImageDraw
    im = Image.new("RGB", (w, h), (30, 60, 90))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w // 3, h], fill=(200, 40, 40))
    d.ellipse([w // 2, h // 5, w - 40, h - 60], fill=(240, 220, 60))
    d.rectangle([w // 3, h // 2, w // 2 + 80, h], fill=(20, 160, 90))
    return ImageChops.add(im, _photo(w, h, seed=4).point(lambda v: v // 6))


def _candidates(src: Path) -> tuple:
    """Một ứng viên cho mỗi nhánh bỏ ảnh của pha tải + một ảnh tốt."""
    good = _blocky_photo()
    remote = {"https://img.phemex.com/banner.png": _png_bytes(_photo(1000, 800, seed=3)),
              "https://bad.example/missing.png": None}
    cands = [
        {"tep": _save(good, src / "good.png"), "image_url": str(src / "good.png"), "source": "browser",
         "page_url": "https://news.example/a", "score": 50},
        {"tep": _save(good.resize((820, 638)), src / "dup.png"), "image_url": str(src / "dup.png"),
         "source": "browser", "page_url": "https://news.example/a", "score": 49},
        {"tep": _save(_photo(120, 90, seed=1), src / "tiny.png"), "image_url": str(src / "tiny.png"),
         "source": "browser", "page_url": "https://news.example/a", "score": 48},
        {"tep": _save(_photo(seed=2), src / "placeholder.png"), "image_url": str(src / "placeholder.png"),
         "source": "browser", "page_url": "https://news.example/a", "score": 47},
        {"tep": _save(Image.new("RGB", (900, 700), (255, 255, 255)), src / "white.png"),
         "image_url": str(src / "white.png"), "source": "browser", "page_url": "https://news.example/a", "score": 46},
        {"image_url": "https://img.phemex.com/banner.png", "page_url": "https://siliconangle.com/a",
         "source": "browser", "score": 45},
        {"image_url": "https://bad.example/missing.png", "page_url": "https://news.example/a",
         "source": "browser", "score": 44},
    ]
    return cands, remote


def _run_download(cands, remote, wd: Path, log_on: bool):
    patches = [mock.patch.object(download_filter, "_download_bytes", side_effect=lambda u: remote.get(u))]
    if not log_on:
        patches += [mock.patch.object(decision_log, "note", lambda *a, **k: None),
                    mock.patch.object(decision_log, "drop_candidate", lambda *a, **k: None)]
    for p in patches:
        p.start()
    try:
        return _quiet(lambda: download_filter.download_and_filter([dict(c) for c in cands], wd))
    finally:
        for p in reversed(patches):
            p.stop()


def _strip(images: list) -> list:
    return [{k: v for k, v in a.items() if k not in ("decisions", "original_path")} for a in images]


def _dropped(wd: Path) -> list:
    return decision_log.collect(wd)


# ------------------------------------------------ 1. pha tải: không đổi hành vi
def test_download_output_identical_with_and_without_log():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "src").mkdir()
        cands, remote = _candidates(tmp / "src")
        on = _run_download(cands, remote, tmp / "on", log_on=True)
        off = _run_download(cands, remote, tmp / "off", log_on=False)
        assert _strip(on) == _strip(off), "bật bản ghi làm đổi kết quả pha tải"
        assert len(on) == 1 and on[0]["decisions"][0]["stage"] == "download"
        assert not (tmp / "off" / decision_log.DROPPED_DIR).exists()


# ------------------------------------------------ 2. pha tải: mọi nhánh bỏ đều có dấu
def test_every_download_drop_branch_is_recorded_with_thumbnail():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "src").mkdir()
        cands, remote = _candidates(tmp / "src")
        _run_download(cands, remote, tmp / "wd", log_on=True)
        rows = _dropped(tmp / "wd")
        stages = {r["stage"] for r in rows}
        for stage in ("near_duplicate", "too_small", "junk_url", "blank", "third_party_host", "acquire_error"):
            assert stage in stages, f"thiếu bản ghi {stage}: {sorted(stages)}"
        for r in rows:
            if r["stage"] != "acquire_error":
                assert r["thumb"] and Path(r["thumb"]).is_file(), r
                assert max(Image.open(r["thumb"]).size) <= decision_log.THUMB_MAX
        host = next(r for r in rows if r["stage"] == "third_party_host")
        assert "phemex.com" in host["evidence"] and host["url"].endswith("banner.png")


def test_over_limit_truncation_was_silent_now_recorded():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cands = [{"tep": _save(_photo(seed=10 + i), tmp / f"p{i}.png"), "image_url": str(tmp / f"p{i}.png"),
                  "source": "browser", "page_url": "https://news.example/a", "score": 50 - i} for i in range(4)]
        with mock.patch.object(download_filter, "MAX_IMAGE", 2):
            ra = _quiet(lambda: download_filter.download_and_filter(cands, tmp / "wd"))
        assert len(ra) == 2
        over = [r for r in _dropped(tmp / "wd") if r["stage"] == "over_limit"]
        assert len(over) == 2, over


# ------------------------------------------------ 3. vision: câu thô + nhánh lật
class _Res:
    def __init__(self, content: bytes):
        self._c = content

    def read(self):
        return self._c


def _vision_says(txt: str):
    body = json.dumps({"choices": [{"message": {"content": txt}}]}).encode()
    return mock.patch.object(vision, "_call_router", return_value=_Res(body))


def _classify(tmp: Path, answer: str, log_on: bool) -> dict:
    p = tmp / f"img_{int(log_on)}.png"
    _photo(1080, 1350, seed=5).save(p)
    a = {"id": "A1", "original_path": str(p), "url": "https://x/a.png", "source": "browser", "alt": ""}
    patches = [_vision_says(answer), mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"})]
    if not log_on:
        patches.append(mock.patch.object(decision_log, "note", lambda *a, **k: None))
    for q in patches:
        q.start()
    try:
        return _quiet(lambda: vision.classify(a, wd=tmp, tieu_de="Broadcom mo nha may moi"))
    finally:
        for q in reversed(patches):
            q.stop()


ANSWER_FLIPPED = ("MO_TA: tru so van phong Broadcom voi logo tren toa nha.\n"
                  "LIEN_QUAN: khong\nCLUTTERED: khong\nTU_KHOA: co")


def test_vision_records_raw_answer_and_which_regex_flipped_it():
    with tempfile.TemporaryDirectory() as tmp:
        a = _classify(Path(tmp), ANSWER_FLIPPED, log_on=True)
        assert a["relevant"] is True, "nhánh override hiện có phải vẫn lật như cũ"
        stages = [(d["stage"], d["outcome"], d["rule"]) for d in a["decisions"]]
        assert ("vision", "drop", "LIEN_QUAN") in stages, stages
        assert ("vision_override", "keep", "keyword_context_flip_true") in stages, stages
        raw = a["vision_raw"]
        assert "LIEN_QUAN: khong" in raw["answer"] and "Broadcom" in raw["question"] and raw["model"]


def test_classify_output_identical_with_and_without_log():
    with tempfile.TemporaryDirectory() as tmp:
        on = _classify(Path(tmp), ANSWER_FLIPPED, log_on=True)
        off = _classify(Path(tmp), ANSWER_FLIPPED, log_on=False)
        keys = ("uses", "relevant", "notes", "description", "cluttered", "has_keywords", "landscape_crop_ok")
        assert {k: on.get(k) for k in keys} == {k: off.get(k) for k in keys}


def test_relevance_drop_is_recorded():
    with tempfile.TemporaryDirectory() as tmp:
        a = _classify(Path(tmp), "MO_TA: xe canh sat tren pho.\nLIEN_QUAN: khong\nCLUTTERED: khong\nTU_KHOA: khong",
                      log_on=True)
        assert a["relevant"] is False and a["uses"] == []
        assert any(d["stage"] == "relevance" and d["rule"] == "vision_not_relevant" for d in a["decisions"])


def test_vision_unavailable_is_flagged_not_silent():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        p = tmp / "a.png"
        _photo(1080, 1350).save(p)
        a = {"id": "A1", "original_path": str(p), "url": "https://x/a.png", "source": "browser"}
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with mock.patch.dict("os.environ", env, clear=True), \
             mock.patch.object(vision.env_load, "load", lambda *x, **k: None):
            a = _quiet(lambda: vision.classify(a, wd=tmp, tieu_de="T"))
        assert a["relevant"] is None
        assert any(d["rule"] == "vision_unavailable" for d in a["decisions"])


# ------------------------------------------------ 4. gom vào manifest
def test_collect_only_rows_of_this_run():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp)
        decision_log.drop_candidate(wd / "commons", {"image_url": "old"}, "blank")
        import time
        mid = time.time()
        time.sleep(0.01)
        decision_log.drop_candidate(wd / "them_1", {"image_url": "new"}, "junk_url")
        rows = decision_log.collect(wd, since=mid)
        assert [r["url"] for r in rows] == ["new"]
        assert len(decision_log.collect(wd)) == 2


def test_manifest_carries_dropped():
    from prepare.manifest import build_manifest
    rows = [{"stage": "third_party_host", "url": "u"}]
    m = build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {}, Path("/tmp"),
                       [], [], False, {}, {}, False, 6, vai_anh="dre", dropped=rows)
    assert m["dropped"] == rows
    m2 = build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {}, Path("/tmp"),
                        [], [], False, {}, {}, False, 6, vai_anh="dre")
    assert m2["dropped"] == []


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
