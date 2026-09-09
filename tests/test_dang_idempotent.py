#!/usr/bin/env python3
"""`publish()` khong duoc dang MOT PHAN NAO len channel hai lan (issue E5).

Su co goc: `_dang_nen` goi `publish()` roi MOI `mark_draft("published")`. Tien
trinh chet giua hai buoc do (systemd Restart=always, thread daemon bi SIGTERM)
thi bai ket o "publishing"; `_cuu_bai_ket_publishing` ha ve "publish_failed" va
moi bam Duyet lai -> `publish()` chay lai tu dau -> bai len channel LAN THU HAI.
Doc gia thay hai bai giong het nhau.

Ban sua 06/09/2026 moi khoa CHAN ALBUM (`channel_album_mid`). Ba chan con lai
van dang lai duoc: anh don (sendPhoto), bai chi co chu, va phan CHU tach rieng
khi caption dai hon 1024. Tep nay giu ca ba chan do.

Chay:  venv/bin/python tests/test_dang_idempotent.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import duyet_bai as db                                        # noqa: E402


class _FakeHttpx:
    """Thay `db.httpx` de dem so lan THAT SU goi sendMediaGroup / sendPhoto."""

    def __init__(self, res):
        self.res = res
        self.goi = []

    def Client(self, *a, **k):                                # noqa: N802
        ngoai = self

        class _C:
            def __enter__(self):
                return self

            def __exit__(self, *e):
                return False

            def post(self, url, **kw):
                ngoai.goi.append(url)

                class _R:
                    def json(_self):
                        return ngoai.res
                return _R()
        return _C()


def _draft(tmp, **truong):
    """Mot draft toi thieu tren dia, tra ve (draft_id, duong dan)."""
    d = {"caption": "xin chao", "status": "publishing"}
    d.update(truong)
    p = Path(tmp) / "d1.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return "d1", p


def _chay(tmp, res_http=None):
    """Goi publish() voi DRAFTS + httpx + _gui_chu gia. Tra (res, httpx, chu)."""
    fake = _FakeHttpx(res_http or {"ok": True, "result": [{"message_id": 111}]})
    chu = []
    cu_drafts, cu_httpx, cu_chu = db.DRAFTS, db.httpx, db._gui_chu
    db.DRAFTS = Path(tmp)
    db.httpx = fake
    db._gui_chu = lambda *a, **k: (chu.append(a) or
                                   {"ok": True, "result": {"message_id": 222}})
    try:
        return db.publish("tok", "@kenh", "d1"), fake, chu
    finally:
        db.DRAFTS, db.httpx, db._gui_chu = cu_drafts, cu_httpx, cu_chu


# ------------------------------------------------- chan CHU (bai chi co chu)
def test_bai_chi_co_chu_ghi_dau_sau_khi_gui():
    """Gui xong phai ghi `channel_chu_mid` vao draft NGAY — do la thu duy nhat
    cho lan bam Duyet ke tiep biet chu da len roi."""
    with tempfile.TemporaryDirectory() as tmp:
        _, p = _draft(tmp)
        res, _, chu = _chay(tmp)
        assert res.get("ok"), res
        assert len(chu) == 1, f"phai gui dung mot lan: {chu}"
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d.get("channel_chu_mid") == 222, f"khong ghi dau: {d}"


def test_bai_chi_co_chu_da_gui_thi_khong_gui_lai():
    """Dung su co E5: draft da co dau -> bam Duyet lai KHONG duoc gui lai."""
    with tempfile.TemporaryDirectory() as tmp:
        _draft(tmp, channel_chu_mid=222)
        res, _, chu = _chay(tmp)
        assert res.get("ok"), res
        assert chu == [], f"da gui roi ma van gui lai: {chu}"


# --------------------------------------------------------- chan ANH DON
def test_anh_don_ghi_dau_sau_khi_gui():
    with tempfile.TemporaryDirectory() as tmp:
        anh = Path(tmp) / "a.png"
        anh.write_bytes(b"PNG")
        _, p = _draft(tmp, image=str(anh))
        res, fake, _ = _chay(tmp, {"ok": True, "result": {"message_id": 333}})
        assert res.get("ok"), res
        assert len(fake.goi) == 1, f"phai goi sendPhoto dung mot lan: {fake.goi}"
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d.get("channel_anh_mid") == 333, f"khong ghi dau: {d}"


def test_anh_don_da_gui_thi_khong_gui_lai():
    """Truoc 09/09/2026 chan nay khong co dau nao: bai anh don len channel hai
    lan moi khi tien trinh chet dung khe giua publish va mark_draft."""
    with tempfile.TemporaryDirectory() as tmp:
        anh = Path(tmp) / "a.png"
        anh.write_bytes(b"PNG")
        _draft(tmp, image=str(anh), channel_anh_mid=333)
        res, fake, _ = _chay(tmp)
        assert res.get("ok"), res
        assert fake.goi == [], f"da gui anh roi ma van goi lai: {fake.goi}"


# ------------------------------------------------------------- chan ALBUM
def test_album_da_gui_thi_khong_gui_lai():
    with tempfile.TemporaryDirectory() as tmp:
        _draft(tmp, images=["http://x/a.png"], channel_album_mid=111)
        res, fake, _ = _chay(tmp)
        assert res.get("ok"), res
        assert fake.goi == [], f"da gui album roi ma van goi lai: {fake.goi}"


# ------------------------- caption dai: album xong, chu hong roi bam lai
def test_caption_dai_bam_lai_chi_gui_phan_con_thieu():
    """Kich ban that: album len channel, buoc gui CHU hong (Telegram 400 vi
    HTML cua LLM) -> publish_failed -> Ong Chu bam Duyet lai. Lan hai chi duoc
    gui phan CHU; album KHONG duoc len lan nua."""
    with tempfile.TemporaryDirectory() as tmp:
        _, p = _draft(tmp, caption="x" * (db.CAPTION_LIMIT + 5),
                      images=["http://x/a.png"], channel_album_mid=111)
        res, fake, chu = _chay(tmp)
        assert res.get("ok"), res
        assert fake.goi == [], f"album da len ma van gui lai: {fake.goi}"
        assert len(chu) == 1, f"phan chu phai duoc gui dung mot lan: {chu}"
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d.get("channel_chu_mid") == 222, f"khong ghi dau chu: {d}"


def test_caption_dai_bam_lai_lan_ba_khong_gui_gi_nua():
    """Sau khi CA HAI chan da co dau thi bam bao nhieu lan cung khong gui gi."""
    with tempfile.TemporaryDirectory() as tmp:
        _draft(tmp, caption="x" * (db.CAPTION_LIMIT + 5),
               images=["http://x/a.png"], channel_album_mid=111,
               channel_chu_mid=222)
        res, fake, chu = _chay(tmp)
        assert res.get("ok"), res
        assert fake.goi == [] and chu == [], f"van gui lai: http={fake.goi} chu={chu}"


if __name__ == "__main__":
    ham = [v for k, v in list(globals().items()) if k.startswith("test_")]
    loi = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"FAIL {h.__name__}: {e}")
    print(f"\n{len(ham) - loi}/{len(ham)} test qua")
    sys.exit(1 if loi else 0)
