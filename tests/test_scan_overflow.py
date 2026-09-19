#!/usr/bin/env python3
"""LOW-283 (19/09/2026): Vera quet ra hon 15 headline thi phan du sang blog.

Ong Chu chot CHIA THEO THU TU Vera nop: dcgr giu moi muc BAT BUOC + cac tin
dau cho du 15, phan con lai thanh mot bao cao danh so rieng o topic "vera" ben
blog. Tu buoc chon tro di khong doi gi — blog chon bang manifest cua chinh no.

Cac cong o day, moi cong la mot cach tach nay co the hong ma khong ai thay:
  - split_overflow: muc bat buoc lot sang blog -> hom sau bi gieo lai, bao "vai bo sot".
  - manifest_write: manifest phan du phai nam trong state cua BLOG, danh so lai 1..n.
  - overflow_target: blog chua co topic thi KHONG tach (deploy truoc tao topic).
  - env_for_brand: tien trinh con gui sang blog khong duoc mang token/group dcgr.
  - profile_missing: chat trong topic Vera ben blog khong goi `hermes -p vera`.

Chay:  venv/bin/python tests/test_scan_overflow.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import env_load                                               # noqa: E402
import chat_router                                            # noqa: E402
import manifest_write as mg                                   # noqa: E402
import scan_submit                                            # noqa: E402
from tam import bat_buoc_tam                                  # noqa: E402


def _items(n):
    return [{"title": f"Tin {i}", "link": f"https://a.vn/{i}", "summary_vi": ""} for i in range(1, n + 1)]


def _with_env(values: dict, fn):
    old = {k: os.environ.get(k) for k in values}
    try:
        for k, v in values.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return fn()
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ------------------------------------------------------------ split_overflow
def test_split_overflow_keeps_first_items_up_to_cap_in_order():
    with tempfile.TemporaryDirectory() as t, bat_buoc_tam(t, vera={}):
        keep, over = mg.split_overflow(_items(18), 15, "vera")
    assert [x["title"] for x in keep] == [f"Tin {i}" for i in range(1, 16)]
    assert [x["title"] for x in over] == ["Tin 16", "Tin 17", "Tin 18"]


def test_split_overflow_no_split_at_or_below_cap():
    with tempfile.TemporaryDirectory() as t, bat_buoc_tam(t, vera={}):
        for n in (1, 14, 15):
            keep, over = mg.split_overflow(_items(n), 15, "vera")
            assert len(keep) == n and over == [], n
        keep, over = mg.split_overflow(_items(20), 0, "vera")
        assert len(keep) == 20 and over == [], "cap 0 = tat"


def test_split_overflow_required_item_past_cap_stays_in_scan_brand():
    """Muc bat buoc dung thu 18 van o dcgr, va chiem mot cho trong 15."""
    items = _items(20)
    with tempfile.TemporaryDirectory() as t, bat_buoc_tam(
            t, vera={"k": {"name": "Nvidia: Tin 18", "link": "https://a.vn/18"}}):
        keep, over = mg.split_overflow(items, 15, "vera")
    titles = [x["title"] for x in keep]
    assert "Tin 18" in titles and len(keep) == 15, titles
    assert titles[-1] == "Tin 18" and "Tin 15" not in titles, "thu tu goc phai giu"
    assert "Tin 18" not in [x["title"] for x in over]


def test_split_overflow_auto_added_item_never_overflows():
    items = _items(17) + [{"title": "Bo sot", "link": "https://a.vn/x", "auto_added": True}]
    with tempfile.TemporaryDirectory() as t, bat_buoc_tam(t, vera={}):
        keep, over = mg.split_overflow(items, 15, "vera")
    assert keep[-1]["title"] == "Bo sot" and len(keep) == 15
    assert len(over) == 3


# ------------------------------------------------------------ manifest_write end-to-end
def test_manifest_write_puts_overflow_in_target_brand_state_numbered_from_1():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        ds = t / "list.json"
        ds.write_text(json.dumps([{"title": f"Tin số {i}", "link": f"https://a.vn/{i}",
                                   "summary_vi": "Một mệnh đề ngắn"} for i in range(1, 19)],
                                 ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, CT_BRAND="dcgr", CT_STATE_DIR=str(t / "state"))
        r = subprocess.run(
            [sys.executable, str(ROOT / "manifest_write.py"), "--vai", "vera", "--in", str(ds),
             "--bao-cao", str(t / "report.txt"), "--overflow-after", "15", "--overflow-brand", "blog",
             "--overflow-report", str(t / "overflow_report.txt")],
            cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr[-800:]
        main = list((t / "state" / "dcgr").glob("vera_candidates_*.json"))
        over = list((t / "state" / "blog").glob("vera_candidates_*.json"))
        assert len(main) == 1 and len(over) == 1, (main, over)
        a = json.loads(main[0].read_text(encoding="utf-8"))["items"]
        b = json.loads(over[0].read_text(encoding="utf-8"))["items"]
        assert [x["index"] for x in a] == list(range(1, 16))
        assert [x["index"] for x in b] == [1, 2, 3], "phan du danh so lai tu 1"
        assert [x["title"] for x in b] == ["Tin số 16", "Tin số 17", "Tin số 18"]
        assert scan_submit.overflow_manifest_path(r.stdout) == over[0]
        assert scan_submit._count_items(t / "report.txt") == 15, "dong phu khong duoc dem thanh tin"
        assert scan_submit._count_items(t / "overflow_report.txt") == 3
        assert "blog" in (t / "report.txt").read_text(encoding="utf-8")


def test_manifest_write_without_overflow_flags_unchanged():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        ds = t / "list.json"
        ds.write_text(json.dumps([{"title": f"Tin số {i}", "link": f"https://a.vn/{i}"}
                                  for i in range(1, 19)], ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, CT_BRAND="dcgr", CT_STATE_DIR=str(t / "state"))
        r = subprocess.run([sys.executable, str(ROOT / "manifest_write.py"), "--vai", "vera", "--in", str(ds)],
                           cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr[-800:]
        a = json.loads(next((t / "state" / "dcgr").glob("vera_candidates_*.json")).read_text(encoding="utf-8"))
        assert len(a["items"]) == 18
        assert not (t / "state" / "blog").exists()
        assert scan_submit.overflow_manifest_path(r.stdout) is None


# ------------------------------------------------------------ scan_submit gate
def test_overflow_target_needs_topic_in_target_brand():
    with tempfile.TemporaryDirectory() as t:
        topics = Path(t) / "topics.blog.json"
        old = env_load.topics_path
        env_load.topics_path = lambda brand=None: topics if brand == "blog" else old(brand)
        try:
            topics.write_text(json.dumps({"finn": 10}), encoding="utf-8")
            assert _with_env({"CT_BRAND": "dcgr"}, lambda: scan_submit.overflow_target("vera")) is None, \
                "blog chua co topic vera -> khong tach"
            topics.write_text(json.dumps({"finn": 10, "vera": 99}), encoding="utf-8")
            assert _with_env({"CT_BRAND": "dcgr"}, lambda: scan_submit.overflow_target("vera")) == ("blog", 15)
            assert _with_env({"CT_BRAND": "blog"}, lambda: scan_submit.overflow_target("vera")) is None, \
                "khong bao gio chuyen sang chinh container dang chay"
            assert _with_env({"CT_BRAND": "dcgr"}, lambda: scan_submit.overflow_target("nova")) is None
        finally:
            env_load.topics_path = old


# ------------------------------------------------------------ env_load
def test_state_dir_and_topics_path_accept_other_brand():
    with tempfile.TemporaryDirectory() as t:
        def run():
            assert env_load.state_dir("blog") == Path(t) / "blog"
            assert env_load.state_dir() == Path(t) / "dcgr"
            assert env_load.topics_path("blog").name == "topics.blog.json"
            assert env_load.topics_path().name == "topics.dcgr.json"
        _with_env({"CT_BRAND": "dcgr", "CT_STATE_DIR": t}, run)


def test_env_for_brand_drops_parent_brand_secrets_and_telegram_vars():
    """Tien trinh dcgr da nap token/group cua dcgr; `load` dung setdefault nen
    con chay CT_BRAND=blog van gui bang bot dcgr neu khong bo."""
    with tempfile.TemporaryDirectory() as t:
        base = Path(t)
        (base / "secret.dcgr.env").write_text("DCGR_ONLY=1\nTELEGRAM_GROUP_ID=-100dcgr\n", encoding="utf-8")
        (base / "secret.blog.env").write_text("TELEGRAM_GROUP_ID=-100blog\nBLOG_KEY=x\n", encoding="utf-8")
        old = env_load._BASE
        env_load._BASE = base
        try:
            env = _with_env({"CT_BRAND": "dcgr", "DCGR_ONLY": "1", "TELEGRAM_GROUP_ID": "-100dcgr",
                             "TELEGRAM_BOT_TOKEN": "dcgr-token", "BLOG_KEY": "stale", "PATH_KEEP": "y"},
                            lambda: env_load.env_for_brand("blog"))
        finally:
            env_load._BASE = old
    assert env["CT_BRAND"] == "blog"
    assert env["HERMES_HOME"].endswith(".hermes-blog")
    for k in ("DCGR_ONLY", "TELEGRAM_GROUP_ID", "TELEGRAM_BOT_TOKEN", "BLOG_KEY"):
        assert k not in env, k
    assert env.get("PATH_KEEP") == "y", "bien khong thuoc tep secret nao phai giu"


# ------------------------------------------------------------ chat guard
def test_profile_missing_only_when_home_has_profiles_dir():
    with tempfile.TemporaryDirectory() as t:
        home = Path(t)
        assert chat_router.profile_missing("vera", home) is False, "home khong co profiles/ -> giu hanh vi cu"
        (home / "profiles" / "finn").mkdir(parents=True)
        assert chat_router.profile_missing("vera", home) is True
        assert chat_router.profile_missing("finn", home) is False
        assert chat_router.profile_missing(None, home) is False, "profile mac dinh"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
