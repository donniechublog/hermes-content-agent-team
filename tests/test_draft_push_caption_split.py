#!/usr/bin/env python3
"""LOW-170 — draft_push (anh don, ban nhap len topic writer) cong them tien to
"<b>BẢN NHÁP</b>\\n\\n" SAU khi caption_check da cho qua. Caption dung sat 1024
ky tu (gate cho qua) thi cong tien to vuot CAPTION_LIMIT — Telegram tu choi
"message caption is too long", vai bi block du script bao "dat" (Jika,
15/09/2026, bai Garry Tan). draft_push gio phai tu tach nhu _split_caption_html
(LOW-157) thay vi gui thang caption chua tach lam caption anh.

Chay:  venv/bin/python tests/test_draft_push_caption_split.py
"""
import json
import re
import sys
import tempfile
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_post as db                                         # noqa: E402


class FakeTelegram:
    def __init__(self):
        self.calls = []

    def __call__(self, request):
        method = request.url.path.rsplit("/", 1)[-1]
        request.read()
        self.calls.append((method, request))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    def count(self, method):
        return sum(1 for m, _ in self.calls if m == method)

    def payload(self, method, index=0):
        """Ho so form/json cua lan goi thu `index` cua `method`."""
        gap = [r for m, r in self.calls if m == method]
        req = gap[index]
        ct = req.headers.get("content-type", "")
        if ct.startswith("multipart/form-data"):
            import email
            msg = email.message_from_bytes(
                b"Content-Type: " + ct.encode() + b"\r\n\r\n" + req.content)
            out = {}
            for part in msg.get_payload():
                name = part.get_param("name", header="Content-Disposition")
                if name and not part.get_filename():
                    out[name] = part.get_payload(decode=True).decode()
            return out
        return json.loads(req.content)


def _draft(tmp: Path, caption: str, with_image: bool) -> dict:
    d = {"caption": caption}
    if with_image:
        p = tmp / "anh.png"
        Image.new("RGB", (64, 64), (1, 2, 3)).save(p, "PNG")
        d["image"] = str(p)
    p_draft = tmp / "d1.json"
    p_draft.write_text(json.dumps(d), encoding="utf-8")
    return p_draft


def _push(tmp: Path, fake: FakeTelegram, caption: str, with_image=True):
    real_client = httpx.Client

    def client(*a, **k):
        k.pop("transport", None)
        return real_client(*a, transport=httpx.MockTransport(fake), **k)

    saved_client, saved_drafts = httpx.Client, db.DRAFTS
    httpx.Client = client
    db.DRAFTS = tmp
    try:
        _draft(tmp, caption, with_image)
        return db.draft_push("tok", -100, "d1", thread_id=1280)
    finally:
        httpx.Client = saved_client
        db.DRAFTS = saved_drafts


def test_anh_don_caption_sat_gioi_han_tach_thanh_hai_tin():
    # 1010 ky tu, co dau cham/khoang trang nhu caption that (khong phai chuoi
    # lien tuc khong dau cat) — duoi CAPTION_LIMIT (1024) nhu caption_check
    # tung do, nhung cong tien to "<b>BẢN NHÁP</b>\n\n" thi vuot: dung canh ma
    # Jika dinh phai.
    cau = "Đây là một câu caption thử nghiệm dùng để lấp đầy độ dài. "
    caption = (cau * (1010 // len(cau) + 1))[:1010]
    with tempfile.TemporaryDirectory() as t:
        fake = FakeTelegram()
        res = _push(Path(t), fake, caption)
        assert res.get("ok") is True
        assert fake.count("sendPhoto") == 1
        assert fake.count("sendMessage") == 1

        photo = fake.payload("sendPhoto")
        assert len(photo["caption"]) <= db.CAPTION_LIMIT
        assert "reply_markup" not in photo, "nut duyet phai doi sang tin phan 2"

        text = fake.payload("sendMessage")
        assert text["reply_markup"], "tin phan 2 phai mang nut duyet"
        # Ghep lai (bo khoang trang do cat tai ranh gioi) phai la caption goc —
        # khong mat/lap noi dung khi tach.
        gop = re.sub(r"\s+", "", photo["caption"] + text["text"])
        goc = re.sub(r"\s+", "", "<b>BẢN NHÁP</b>\n\n" + caption)
        assert gop == goc


def test_anh_don_caption_ngan_khong_tach_van_mot_tin():
    caption = "Caption ngắn, không đụng giới hạn."
    with tempfile.TemporaryDirectory() as t:
        fake = FakeTelegram()
        res = _push(Path(t), fake, caption)
        assert res.get("ok") is True
        assert fake.count("sendPhoto") == 1
        assert fake.count("sendMessage") == 0

        photo = fake.payload("sendPhoto")
        assert photo["caption"] == "<b>BẢN NHÁP</b>\n\n" + caption
        assert photo["reply_markup"], "khong tach thi nut duyet phai o ngay tren anh"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    qua = 0
    for t in TESTS:
        t()
        qua += 1
        print(f"  {t.__name__} OK")
    print(f"{qua}/{len(TESTS)} test qua")
