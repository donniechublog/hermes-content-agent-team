#!/usr/bin/env python3
"""LOW-337 (Ông Chủ 23/09/2026): đặt bài cho một tin ĐÃ có bản chưa lên channel thì phải nói ra.

Chiều 23/09, tin "GPT-6 Sol and Luna" ra HAI album: draft `…-dre-…` được chuyển sang
Kite (đường chuyển vai dùng lại draft cũ) và draft `…-kite-…` đặt mới lúc 15:31. Không
cổng nào kêu: `_draft_id` CỐ Ý cho một tin đi nhiều vai, còn cổng chặn giao trùng chỉ so
cùng vai + cùng brand trong cùng một bản tin. Dấu "đã lên channel" lại tính theo draft,
nên duyệt cả hai là tin lên channel hai lần.

Ông Chủ chốt: CẢNH BÁO lúc đặt bài, không chặn.

Mỗi phần có ví dụ PHẢI KÊU đi kèm PHẢI IM:
  1. `live_drafts_same_link`: cùng link + cùng brand + chưa lên channel → kêu; khác brand,
     đã lên channel, hoặc draft cũ quá hạn → im.
  2. dòng trả lời của `/dat` (approve_command) có câu cảnh báo, và vẫn đặt bài.

Chạy:  venv/bin/python tests/test_low337_same_link_warning.py
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import approve_pick as ap  # noqa: E402

LINK = "https://openai.com/index/introducing-gpt-6-sol-and-luna/"


def _draft(d: Path, ma: str, link=LINK, vai="dre", brand="donniechublog",
           len_channel=False, tuoi_ngay=0):
    (d / (ma + ".img.json")).write_text(json.dumps({"link": link, "image_role": vai}),
                                        encoding="utf-8")
    (d / (ma + ".meta.json")).write_text(json.dumps({"brand": brand, "source_url": link}),
                                         encoding="utf-8")
    (d / (ma + ".json")).write_text(json.dumps({"channel_album_mid": 42} if len_channel else {}),
                                    encoding="utf-8")
    if tuoi_ngay:
        cu = time.time() - tuoi_ngay * 86400
        os.utime(d / (ma + ".img.json"), (cu, cu))


def _soi(tmp, link=LINK, brand="donniechublog"):
    with mock.patch.object(ap, "DRAFTS", Path(tmp)):
        return ap.live_drafts_same_link(link, brand)


# ---------------------------------------------------------------- 1. tìm bản còn sống
def test_same_link_same_brand_is_reported():
    with tempfile.TemporaryDirectory() as t:
        _draft(Path(t), "gpt-6-sol-and-luna-dre-donniechublog")
        assert _soi(t) == [("gpt-6-sol-and-luna-dre-donniechublog", "dre")], _soi(t)


def test_link_with_tracking_query_still_matches():
    with tempfile.TemporaryDirectory() as t:
        _draft(Path(t), "d1", link=LINK + "?utm_source=x")
        assert len(_soi(t, link=LINK.rstrip("/"))) == 1, _soi(t)


def test_other_story_is_quiet():
    with tempfile.TemporaryDirectory() as t:
        _draft(Path(t), "d1", link="https://openai.com/index/gpt-6-astra/")
        assert _soi(t) == [], _soi(t)


def test_other_brand_is_quiet():
    """Cùng tin chạy cho blog và dcgr là hai kênh khác nhau — không phải trùng."""
    with tempfile.TemporaryDirectory() as t:
        _draft(Path(t), "d1", brand="dcgr")
        assert _soi(t) == [], _soi(t)


def test_already_on_channel_is_quiet():
    """Bản cũ ĐÃ lên channel thì chuyện đã xong, đặt bản mới là cố ý."""
    with tempfile.TemporaryDirectory() as t:
        _draft(Path(t), "d1", len_channel=True)
        assert _soi(t) == [], _soi(t)


def test_old_draft_is_quiet():
    with tempfile.TemporaryDirectory() as t:
        _draft(Path(t), "d1", tuoi_ngay=ap.LIVE_DRAFT_DAYS + 1)
        assert _soi(t) == [], _soi(t)


def test_broken_draft_file_does_not_kill_the_pick():
    """Một tệp hỏng không được làm chết cả lệnh đặt bài — cảnh báo là lớp thêm."""
    with tempfile.TemporaryDirectory() as t:
        (Path(t) / "hong.img.json").write_text("{khong phai json", encoding="utf-8")
        _draft(Path(t), "d1")
        assert _soi(t) == [("d1", "dre")], _soi(t)


def test_link_key_normalises():
    assert ap._link_key("https://WWW.Openai.com/a/?b=1#c") == "openai.com/a"
    assert ap._link_key("http://openai.com/a") == ap._link_key("https://openai.com/a/")
    assert ap._link_key("") == ""


# ---------------------------------------------------------------- 2. dòng trả lời
def test_manual_pick_warns_and_still_creates():
    import approve_command as ac
    with tempfile.TemporaryDirectory() as t:
        _draft(Path(t), "gpt-6-sol-and-luna-dre-donniechublog")
        with mock.patch.object(ap, "DRAFTS", Path(t)):
            trung = ap.live_drafts_same_link(LINK, "donniechublog")
        dong = "✅ <b>GPT-6</b>\nKite dựng ảnh (donniechublog) — task t_1"
        ds = ", ".join(f"{ma} ({ac.NAME_ROLE_IMAGE.get(v, v)})" for ma, v in trung[:3])
        dong += (f"\n⚠️ Tin này đã có {len(trung)} bản chưa lên channel: {ds}"
                 " — vẫn đặt thêm, nhưng duyệt cả hai là tin lên hai lần")
        assert "đã có 1 bản chưa lên channel" in dong and "Dre" in dong, dong
        assert "task t_1" in dong, dong                   # VAN dat bai, khong chan


def test_both_pick_paths_call_the_gate():
    """Hai đường đặt bài (báo cáo researcher và `/dat` tay) đều phải soi."""
    for f in ("approve_pick.py", "approve_command.py"):
        than = (ROOT / f).read_text(encoding="utf-8")
        assert "live_drafts_same_link(" in than, f


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
