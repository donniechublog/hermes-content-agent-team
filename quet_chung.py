#!/usr/bin/env python3
"""quet_chung.py — thu cac script QUET va script GHI MANIFEST dung chung.

Vi sao co tep nay (06/09/2026, audit dot 1): cung mot viec duoc viet lai o
nhieu cho, va cac ban da bat dau lech nhau.

  - Chuan hoa URL: `scan_sources._norm_url`, `manifest_build._norm`,
    `bat_buoc.chuan_link` — ba ban CUNG y dinh, khac thu tu `.lower()` va
    `.strip()`. Ba ban chuan hoa khac nhau nghia la "da thay tin nay chua" tra
    loi khac nhau tuy ai hoi.
  - Tai trang: `scan_models._get` va `scan_business._get`, cung chu thich ve
    brotli, khac moi tham so `params`.
  - User-Agent: nam roi o NAM tep.
  - Ghi JSON nguyen tu: ba ban tmp + replace.
  - Ten hien thi cua vai: hai bang.

Tep nay KHONG chua logic quet — chi nhung manh nho ma moi nguoi deu can. Script
quet nao can thu rieng thi cu giu rieng.
"""
import json
import os
import re
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
from datetime import datetime
from pathlib import Path

import httpx

# Mot User-Agent duy nhat cho ca doi: bao nao chan thi chan tat, khong phai do
# xem script nao dang bi chan.
UA = "Mozilla/5.0 (compatible; donniechu-scout/1.0)"

VN = timezone(timedelta(hours=7))

# Ten hien thi cua ba vai di tim tin. Truoc day co hai bang (quet_nop.TEN va
# bao_cao_manifest.TEN_VAI) va chung phai nho sua cung luc.
# `vera` la but danh cu cho role `market` — bao_cao_manifest van nhan ca hai
# de bao cao cu khong ra "None".
TEN_VAI = {"scout": "Finn", "nova": "Nova", "market": "Vera", "vera": "Vera"}


def chuan_link(u: str) -> str:
    r"""URL ve dang so sanh duoc: bo scheme, bo `www.`, bo query/fragment, bo `/`
    cuoi, ha chu thuong.

    Day la phep so "hai link co phai mot bai khong" cua CA day chuyen — sua o
    day la sua cho moi noi, va do la diem cua tep nay.

    HA CHU THUONG TRUOC roi moi boc scheme. Ban cua `scan_sources`/
    `manifest_build` ha chu o CUOI, ma regex `^https?://(www\.)?` phan biet hoa
    thuong — nen "HTTP://WWW.a.io" khong bi boc scheme va thanh mot khoa khac
    han "a.io". Hai ban do coi cung mot bai la hai bai; ban cua `bat_buoc` lam
    dung, va day lay theo no.
    """
    u = re.sub(r"^https?://(www\.)?", "", (u or "").strip().lower())
    return re.sub(r"[?#].*$", "", u).rstrip("/")


def get(url: str, timeout: int = 45, params=None) -> httpx.Response:
    """GET mot trang.

    KHONG xin brotli: may chu cua OpenAI tra ve luong brotli ma bo giai nen cua
    httpx nghen giua chung ("decoder process called with data when
    can_accept_more_data() is False") — feed hong han, khong phai loi encoding.
    Bo 'br' khoi Accept-Encoding thi may chu chuyen sang gzip va doc binh thuong.
    """
    return httpx.get(url, timeout=timeout, follow_redirects=True, params=params,
                     headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})


import env_load                                              # noqa: E402

# Mot ban duy nhat, o env_load (moi script deu da import no).
ghi_json = env_load.ghi_json


def moc_thoi_gian(txt: str) -> float:
    """Chuoi ngay cua RSS/Atom -> epoch. 0 neu khong doc duoc.

    Hai dinh dang deu gap that: RFC 2822 (`Tue, 02 Sep 2026 10:00:00 GMT`) cua
    RSS va ISO 8601 cua Atom.
    """
    for f in (lambda t: parsedate_to_datetime(t).timestamp(),
              lambda t: datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()):
        try:
            return f(txt)
        except Exception:                                    # noqa: BLE001
            continue
    return 0.0

# Tu qua chung, bo khi so "hai tieu de co noi cung mot chuyen khong". Truoc
# 06/09/2026 co hai ban: `nguon_bai.TU_RONG` va mot bo go tay trong
# `anh_bai._tu_dac_trung`, khac nhau dung mot tu ("how") — nen cung mot cap tieu
# de co the "cung tin" voi ham nay va "khac tin" voi ham kia.
TU_RONG = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "or", "with",
           "new", "ai", "model", "is", "its", "as", "at", "by", "from", "how"}


def tu_dac_trung(t: str) -> set:
    """Tu dac trung cua mot tieu de: bo dau cau, bo tu chung, bo tu <= 2 ky tu."""
    return {w for w in re.sub(r"[^\w\s]", " ", (t or "").lower()).split()
            if w not in TU_RONG and len(w) > 2}
