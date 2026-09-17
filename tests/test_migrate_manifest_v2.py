#!/usr/bin/env python3
"""migrate_manifest_v2.py (LOW-227): one-shot rename of on-disk JSON keys to v2.

Guards the four properties the deploy relies on: dry-run writes nothing; a real run
keeps the original bytes as *.v1.bak and writes exactly what `schema.read_manifest`
returns (v0 derived keys included); non-manifest xong.json (Itachi/Ada) and v2
files are untouched; a second run is a no-op."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import schema  # noqa: E402

V1_IMAGE = {"ma": "A1", "goc": "/x/goc/A1.png", "san": "/x/san/A1.png", "tu": "commons", "trang": "https://p",
            "mien": "commons.wikimedia.org", "dung": ["bìa"], "ghi_chu": ["n"], "lien_quan": True,
            "mo_ta": "d", "mat": 0, "ngang": False, "ti_le": 0.8, "loai": "anh", "w": 800, "h": 1000,
            "khai_niem": {"tu_khoa": "server room", "ly_do": "r"}, "roi": True,
            "thuong_hieu": {"hang": "Anthropic", "khoa": "anthropic", "loai": "logo", "nen": "sáng", "ma": "arena-text"},
            "xep_hang": {"tep": "/x/goc/xh.png", "kieu": "bang", "hang": "Anthropic", "dong": 3, "duoc_nhac": True}}


def _manifest(version):
    m = {"draft_id": "d1", "brand": "donniechublog", "title": "t", "link": "l", "workdir": "/x",
         "anh": [dict(V1_IMAGE)], "toi_thieu": 1, "vai_anh": "ethan", "tu_lieu": {"cau_co_so": [], "tu": "browser"},
         "thieu_anh": {"so": 0, "toi_thieu": 1}, "xep_hang": None,
         "dropped": [{"stage": "download", "rule": "r", "url": "u", "trang": "https://p", "tu": "commons"}]}
    if version:
        m.update(phien_ban=version, so_dung_duoc=1, so_xep_hang=0)
    return m


def _layout(tmp: Path) -> dict:
    st, dr = tmp / "state", tmp / "drafts"
    files = {
        "v1": st / "blog" / "chuan_bi" / "d1" / "xong.json",
        "v0": st / "dcgr" / "chuan_bi" / "d0" / "xong.json",
        "itachi": st / "blog" / "chuan_bi" / "gin_03" / "xong.json",
        "img": dr / "d1.img.json",
        "golden": st / "golden" / "v0" / "samples.jsonl",
    }
    for p in files.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    files["v1"].write_text(json.dumps(_manifest(1), ensure_ascii=False), encoding="utf-8")
    files["v0"].write_text(json.dumps(_manifest(0), ensure_ascii=False), encoding="utf-8")
    files["itachi"].write_text(json.dumps({"khoa": "k", "slides": []}), encoding="utf-8")
    files["img"].write_text(json.dumps({"vai_anh": "dre", "carousel": True, "ly_do_lam_lai": [{"lan": 1, "slide": None, "ly_do": "x"}]},
                                       ensure_ascii=False), encoding="utf-8")
    files["golden"].write_text(json.dumps({"id": "blog/d1/A1", "image": V1_IMAGE}, ensure_ascii=False) + "\n", encoding="utf-8")
    return files


def _run(tmp: Path, *extra) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "migrate_manifest_v2.py"), "--state", str(tmp / "state"),
                           "--drafts", str(tmp / "drafts"), *extra], capture_output=True, text=True, cwd=ROOT)


def _snapshot(files: dict) -> dict:
    return {k: p.read_bytes() for k, p in files.items()}


def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _layout(tmp)
        before = _snapshot(files)
        r = _run(tmp, "--dry-run")
        assert r.returncode == 0, r.stderr
        assert _snapshot(files) == before
        assert not list(tmp.rglob("*.v1.bak"))
        assert "manifest  migrate" in r.stdout and "not an engine manifest" in r.stdout, r.stdout


def test_real_run_matches_read_manifest_and_keeps_backup():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _layout(tmp)
        before = _snapshot(files)
        expected_v1 = schema.read_manifest(json.loads(before["v1"]))
        expected_v0 = schema.read_manifest(json.loads(before["v0"]))
        r = _run(tmp)
        assert r.returncode == 0, r.stderr
        v1 = json.loads(files["v1"].read_text(encoding="utf-8"))
        v0 = json.loads(files["v0"].read_text(encoding="utf-8"))
        assert v1 == expected_v1 and v0 == expected_v0
        assert v1["version"] == 2 and "phien_ban" not in v1
        assert "usable_count" in v0 and v0["ranking_count"] == 0, v0
        img = v1["images"][0]
        assert img["id"] == "A1" and img["ready_path"] == "/x/san/A1.png" and img["cluttered"] is True
        assert img["brand_match"] == {"company": "Anthropic", "key": "anthropic", "kind": "logo",
                                      "background_tone": "sáng", "board_id": "arena-text"}
        assert img["ranking"] == {"file_path": "/x/goc/xh.png", "kind": "bang", "company": "Anthropic",
                                  "row": 3, "mentioned": True}
        assert v1["material"] == {"number_sentences": [], "source": "browser"}
        assert v1["missing_images"] == {"count": 0, "min_images": 1}
        assert v1["dropped"] == [{"stage": "download", "rule": "r", "url": "u", "page_url": "https://p",
                                  "source": "commons"}]
        side = json.loads(files["img"].read_text(encoding="utf-8"))
        assert side == {"image_role": "dre", "carousel": True,
                        "redo_reasons": [{"attempt": 1, "slide": None, "reason": "x"}]}
        gold = json.loads(files["golden"].read_text(encoding="utf-8"))
        assert gold["id"] == "blog/d1/A1" and gold["image"]["relevant"] is True
        assert files["itachi"].read_bytes() == before["itachi"]
        for k in ("v1", "v0", "img", "golden"):
            bak = files[k].with_name(files[k].name + ".v1.bak")
            assert bak.read_bytes() == before[k], k
        assert not files["itachi"].with_name("xong.json.v1.bak").exists()


def test_second_run_is_noop():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _layout(tmp)
        assert _run(tmp).returncode == 0
        after_first = _snapshot(files)
        baks = {p: p.read_bytes() for p in tmp.rglob("*.v1.bak")}
        r = _run(tmp)
        assert r.returncode == 0, r.stderr
        assert _snapshot(files) == after_first
        assert {p: p.read_bytes() for p in tmp.rglob("*.v1.bak")} == baks
        assert "already v2" in r.stdout, r.stdout


def test_conflicting_keys_fail_loudly():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _layout(tmp)
        m = _manifest(1)
        m["anh"][0]["id"] = "A9"
        files["v1"].write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        before = files["v1"].read_bytes()
        r = _run(tmp)
        assert r.returncode == 1 and "[LOI]" in r.stderr, (r.returncode, r.stderr)
        assert files["v1"].read_bytes() == before


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
