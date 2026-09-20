#!/usr/bin/env python3
"""Ten model dung chung chi khai bao MOT cho — `env_load` (LOW-326, 20/09/2026).

Truoc day `SAME_STORY_MODEL = "ds/deepseek-v4-pro"` nam o HAI tep (article_sources,
scan_business) va `VISION_MODEL` o mot tep khac; doi nha cung cap phai nho sua ba cho, sot mot
cho la mot duong van dinh DeepSeek. Gio moi module chi doc lai hang so tu `env_load`.

Chay:  venv/bin/python tests/test_model_constants.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import env_load                                                 # noqa: E402

MODEL_CONSTANTS = ("VISION_MODEL", "VISION_FALLBACK_MODEL", "SAME_STORY_MODEL")


def test_model_constants_exist_and_look_like_a_router_route():
    for name in MODEL_CONSTANTS:
        value = getattr(env_load, name)
        assert re.fullmatch(r"[a-z]+/[\w.\-]+", value), (name, value)


def test_same_story_model_is_declared_only_in_env_load():
    for f in ("article_sources.py", "scan_business.py"):
        text = (ROOT / f).read_text(encoding="utf-8")
        assert "SAME_STORY_MODEL = env_load.SAME_STORY_MODEL" in text, f
        assert not re.search(r"^SAME_STORY_MODEL\s*=\s*[\"']", text, re.M), \
            f"{f}: khong khai bao lai chuoi model, doc tu env_load"


def test_vision_module_reads_models_from_env_load():
    text = (ROOT / "prepare" / "vision.py").read_text(encoding="utf-8")
    assert "VISION_MODEL = env_load.VISION_MODEL" in text
    assert "VISION_FALLBACK_MODEL = env_load.VISION_FALLBACK_MODEL" in text


if __name__ == "__main__":
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
