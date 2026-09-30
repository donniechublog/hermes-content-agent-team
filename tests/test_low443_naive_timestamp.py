#!/usr/bin/env python3
"""LOW-443 (30/09/2026): chuoi gio KHONG co mui gio (naive) phai duoc hieu la UTC,
khong phai gio may.

Loi cu: `datetime.fromisoformat(t).timestamp()` tren chuoi naive dung mui gio cua
MAY -> may chu gio VN (UTC+7) thay moi tin gia 7 tieng. `parsedate_to_datetime`
cung tra naive khi header ghi `-0000` hoac khong ghi mui gio.

Test ep TZ=Asia/Ho_Chi_Minh ngay trong tep (khong phu thuoc mui gio may chay) de
do ro tren code cu.

Chay:  venv/bin/python tests/test_low443_naive_timestamp.py
"""
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Phai dat TRUOC khi import/goi bat cu thu gi dung mui gio.
os.environ["TZ"] = "Asia/Ho_Chi_Minh"
time.tzset()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scan_common                                            # noqa: E402

# 02/09/2026 10:00:00 UTC
EPOCH = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc).timestamp()

CASES = {
    "rfc2822_gmt": "Wed, 02 Sep 2026 10:00:00 GMT",
    "rfc2822_offset": "Wed, 02 Sep 2026 17:00:00 +0700",
    "rfc2822_minus0000": "Wed, 02 Sep 2026 10:00:00 -0000",     # naive
    "iso_z": "2026-09-02T10:00:00Z",
    "iso_offset": "2026-09-02T17:00:00+07:00",
    "iso_naive": "2026-09-02T10:00:00",                          # naive
}


def test_machine_tz_is_vn():
    # Neu hai dong tren khong co hieu luc thi cac test duoi khong chung minh gi.
    assert time.localtime(EPOCH).tm_gmtoff == 7 * 3600, time.localtime(EPOCH).tm_gmtoff


def test_parse_time_utc_all_formats():
    for ten, txt in CASES.items():
        dt = scan_common.parse_time_utc(txt)
        assert dt is not None, ten
        assert dt.tzinfo is not None, f"{ten}: phai co mui gio"
        assert dt.timestamp() == EPOCH, f"{ten}: {dt.timestamp() - EPOCH:+.0f}s lech"


def test_timestamp_time_all_formats():
    for ten, txt in CASES.items():
        assert scan_common.timestamp_time(txt) == EPOCH, ten


def test_unreadable_gives_none_and_zero():
    for txt in ("", "khong phai ngay", None):
        assert scan_common.parse_time_utc(txt) is None, repr(txt)
        assert scan_common.timestamp_time(txt) == 0.0, repr(txt)


def test_scan_x_out_story_naive_date():
    # 20:00 UTC = 03:00 VN ngay hom sau: naive hieu theo gio may (VN) se ra ngay 02.
    import scan_x
    t = {"timestamp": "2026-09-02T20:00:00", "author": {"handle": "x"}}
    assert scan_x.out_story(t)["date"] == "2026-09-03", scan_x.out_story(t)


def test_article_sources_helper_reads_naive_as_utc():
    import xml.etree.ElementTree as ET
    it = ET.fromstring("<item><pubDate>Wed, 02 Sep 2026 10:00:00 -0000</pubDate></item>")
    assert scan_common.pubdate_epoch(it) == EPOCH


if __name__ == "__main__":
    ok = 0
    ten = [k for k in list(globals()) if k.startswith("test_")]
    for k in ten:
        try:
            globals()[k]()
            ok += 1
        except Exception as e:                                # noqa: BLE001
            print(f"    FAIL {k}: {type(e).__name__}: {e}")
    print(f"{Path(__file__).name:<34} {ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
