#!/usr/bin/env python3
"""LOW-434 (30/09/2026): `MODEL_DESCRIPTION` / `NOT_MODEL_DESCRIPTION` chua byte backspace
0x08 THAT thay cho `\\b` (go `\\b` trong chuoi thuong chu khong phai raw string) nen tu
"LLM" va "firm" khong bao gio khop: mo ta Wikidata chi ghi "LLM" khong duoc coi la model,
con "venture capital firm" khong bi loai nhu du dinh.

Chay:  venv/bin/python tests/test_low434_backspace_regex.py
"""
import subprocess
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_brand as th                                     # noqa: E402


def test_llm_word_matches_model_description():
    assert th.MODEL_DESCRIPTION.search("LLM")
    assert th.MODEL_DESCRIPTION.search("family of LLMs by Meta")
    # `\b` la ranh gioi tu that: chuoi con trong tu khac khong khop
    assert not th.MODEL_DESCRIPTION.search("Illmatic album")


def test_firm_word_is_excluded_from_model_description():
    assert th.NOT_MODEL_DESCRIPTION.search("venture capital firm")
    assert not th.NOT_MODEL_DESCRIPTION.search("confirmed language model")


def test_wikidata_model_logo_uses_llm_and_firm_words():
    """Duong chay that (:949): mo ta chi noi "LLM" thi nhan logo; mo ta "AI firm" bi loai."""
    def entity(desc):
        return {"descriptions": {"en": {"value": desc}},
                "claims": {th.P_LOGO: [{"mainsnak": {"datavalue": {"value": "Logo.svg"}}}]}}

    def ask_api(url, **kw):
        if kw.get("action") == "wbsearchentities":
            return {"search": [{"id": "Q1"}, {"id": "Q2"}]}
        return {"entities": {"Q1": entity("investment firm LLM fund"), "Q2": entity("open LLM by Acme")}}

    with mock.patch.object(th, "_ask_api", side_effect=ask_api):
        assert th._wikidata_model_logo("Acme") == "Logo.svg"   # Q1 bi loai (firm), Q2 nhan (LLM)


def test_no_raw_backspace_byte_in_python_sources():
    """Chan loai loi nay quay lai (song song voi luat ruff PLE2510 trong ruff.toml)."""
    files = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    bad = [f for f in files if b"\x08" in (ROOT / f).read_bytes()]
    assert not bad, f"byte 0x08 that trong: {bad} (dung \\b trong raw string)"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
