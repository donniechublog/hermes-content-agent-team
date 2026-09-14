#!/usr/bin/env python3
"""Soat cron CA HAI brand mot lan moi sang, va nhan neu co gi hong.

VI SAO CAN. Ca 9 job cron deu `deliver: local`, tuc output khong di dau ca —
mot job hong thi bang chung duy nhat la mot tep .md nam trong
`<home>/cron/output/<job>/`, khong ai doc. Tu 06/09/2026 cac script da thoat
KHAC 0 khi hong nen `failure_streak` cua hermes cuoi cung cung dung, nhung
dung ma khong ai nhin thi van bang khong. Job nay la nguoi nhin.

VI SAO KHONG PHAI `deliver: telegram`. Doi `deliver` la doi ca duong ra cua
lan chay THANH CONG: `moat-publish-watch` chay 288 lan/ngay se rot 288 tin vao
channel chung. Hermes co `failure_deliver` (chi gui khi HONG, nhan ca
`telegram:<chat>:<thread>`) — thu do bo tro tot cho job nay, nhung no chi bao
duoc nhung lan chay THAT SU NO. Ba kieu hong nang nhat lai KHONG no lan nao:
ticker chet, job bi pause, job bi tat. Chi co mot lan soat dinh ky moi thay.

CHAY O CA HAI CONTAINER, va moi lan chay soat CA HAI home. Neu chi dat o blog
thi ngay blog chet la khong con ai bao — dung cai lo hong job nay sinh ra de
bit. Hai lan chay khong sinh hai tin: lan sau doc `state/cron_audit.json` thay
cung mot bo van de da bao trong ngay thi im.

Dung:
    venv/bin/python audit_cron.py               # soat, gui neu co van de
    venv/bin/python audit_cron.py --khong-gui   # chi in ra man hinh
    venv/bin/python audit_cron.py --luon-bao    # gui du da bao roi (de thu)
"""
import argparse
import html
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import env_load
import publish

# Nhip ticker cua hermes la 60s (cron/jobs.py TICKER_INTERVAL_SECONDS). Nguong
# "ticker dung" lay DUNG cong thuc cua `hermes cron status`
# (hermes_cli/cron.py: TICKER_INTERVAL_SECONDS * 3 + 20) de hai cho khong bao
# hai ket qua khac nhau ve cung mot home.
TICK_OLD = 60 * 3 + 20

# Job dang le da chay ma `next_run_at` van nam qua khu qua ngan nay = scheduler
# khong no. Rong rai hon nhip ticker vi mot lan restart gateway cung du lam
# lech vai phut, va job nay chi chay ngay mot lan nen khong can nhay cam.
LATE_SECONDS = 15 * 60

# Tep danh dau "hom nay ai da bao gi" — dung chung ca hai brand nen nam o
# `state/` GOC, khong phai `state/<brand>/` (quy uoc trong README, muc State).
MARK = env_load.ROOT / "state" / "cron_audit.json"

ITEM = {"HONG": "🔴", "KET": "🟠", "TAT": "⚪"}


def _epoch(p: Path):
    """Doc mot tep moc thoi gian epoch cua hermes; None neu thieu hoac hong."""
    try:
        return float(p.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _hours(iso: str) -> str:
    """ISO cua hermes -> gio VN doc duoc. Khong doc duoc thi tra nguyen chuoi."""
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return str(iso)
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone().strftime("%H:%M %d/%m")


def _age(giay: float) -> str:
    """Khoang thoi gian -> chuoi ngan tieng Viet."""
    giay = int(giay)
    if giay < 90:
        return f"{giay} giây"
    if giay < 90 * 60:
        return f"{giay // 60} phút"
    if giay < 48 * 3600:
        return f"{giay // 3600} giờ"
    return f"{giay // 86400} ngày"


def format_cron(home: Path) -> list:
    """Moi kho cron cua mot home: kho goc + kho rieng cua tung profile.

    Hermes tach cron THEO PROFILE (cron/jobs.py, issue #4707): mot job tao
    trong profile `coder` nam o `<home>/profiles/coder/cron/jobs.json` chu
    khong phai kho goc. Chi soat kho goc la co the bo sot ca mot nhom job."""
    ra = [(home / "cron", "")]
    ra += sorted((p / "cron", p.name)
                 for p in (home / "profiles").glob("*") if (p / "cron").is_dir())
    return ra


def audit_format(cron_dir: Path, bay_gio: float) -> tuple:
    """Soat MOT kho cron. Tra ve (van_de, so_job_da_soat).

    `van_de`: list dict {muc, ten, ly_do} — `ten` da gom ca profile neu co."""
    van_de, tep = [], cron_dir / "jobs.json"
    if not tep.exists():
        # Kho khong co jobs.json la binh thuong (home chua tung tao job nao).
        return van_de, 0
    try:
        data = json.loads(tep.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        van_de.append({"muc": "HONG", "ten": str(tep),
                       "ly_do": [f"không đọc được jobs.json: {type(e).__name__}"]})
        return van_de, 0

    # Ticker: kiem TRUOC cac job. Ticker dung thi MOI job trong kho deu dong
    # bang, va bao rieng tung job la 9 dong noi cung mot chuyen.
    nhip = _epoch(cron_dir / "ticker_heartbeat")
    thanh = _epoch(cron_dir / "ticker_last_success")
    if nhip is None:
        van_de.append({"muc": "KET", "ten": "ticker",
                       "ly_do": ["không có nhịp nào — gateway chưa từng chạy ở kho này"]})
    elif bay_gio - nhip > TICK_OLD:
        van_de.append({"muc": "KET", "ten": "ticker",
                       "ly_do": [f"nhịp cuối {_age(bay_gio - nhip)} trước "
                                 f"(ngưỡng {TICK_OLD}s) — MỌI job trong kho này đang không nổ"]})
    elif thanh is not None and nhip - thanh > TICK_OLD:
        # Nhip con dap nhung khong tick nao thanh cong: ticker song ma hong.
        van_de.append({"muc": "KET", "ten": "ticker",
                       "ly_do": [f"còn nhịp nhưng lần tick THÀNH CÔNG cuối đã "
                                 f"{_age(bay_gio - thanh)} trước"]})

    jobs = data.get("jobs") or []
    for job in jobs:
        ly_do, muc = [], "TAT"
        ten = job.get("name") or job.get("id") or "?"

        if not job.get("enabled", True):
            ly_do.append("đang TẮT (enabled=false)")
        if (job.get("state") or "") == "paused":
            vi = job.get("paused_reason") or "không ghi lý do"
            ly_do.append(f"đang TẠM DỪNG — {vi}")

        streak = int(job.get("failure_streak") or 0)
        if streak > 0:
            muc = "HONG"
            ly_do.append(f"hỏng {streak} lần liên tiếp")
        trang_thai = job.get("last_status")
        if trang_thai and trang_thai != "ok":
            muc = "HONG"
            ly_do.append(f"lần chạy cuối: {trang_thai}")
        for khoa, nhan in (("last_error", "lỗi"),
                           ("last_delivery_error", "không gửi được kết quả")):
            if job.get(khoa):
                muc = "HONG"
                ly_do.append(f"{nhan}: {str(job[khoa])[:200]}")

        # Job bat nhung scheduler khong no: `next_run_at` nam lai qua khu.
        # Job dang TAT thi next_run_at cu la chuyen binh thuong, khong tinh.
        ke = job.get("next_run_at")
        if job.get("enabled", True) and (job.get("state") or "") != "paused" and ke:
            try:
                t = datetime.fromisoformat(str(ke).replace("Z", "+00:00"))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                tre = bay_gio - t.timestamp()
                if tre > LATE_SECONDS:
                    muc = "KET" if muc == "TAT" else muc
                    ly_do.append(f"lỡ hẹn {_age(tre)} (đáng lẽ chạy lúc {_hours(ke)})")
            except (TypeError, ValueError):
                muc = "HONG"
                ly_do.append(f"next_run_at không đọc được: {ke!r}")

        if ly_do:
            van_de.append({"muc": muc, "ten": ten, "ly_do": ly_do})
    return van_de, len(jobs)


def audit(homes=None, bay_gio=None) -> tuple:
    """Soat moi kho cron cua moi home. Tra ve (van_de, tong_job, thieu_home).

    `van_de` co them khoa `brand`; `thieu_home` la cac brand khong co thu muc
    home — chuyen do khong phai canh bao ma la sai cau hinh cua chinh script."""
    homes = homes if homes is not None else env_load.hermes_homes()
    bay_gio = bay_gio if bay_gio is not None else time.time()
    van_de, tong, thieu = [], 0, []
    for brand, home in sorted(homes.items()):
        if not home.is_dir():
            thieu.append(brand)
            continue
        for cron_dir, profile in format_cron(home):
            v, n = audit_format(cron_dir, bay_gio)
            tong += n
            for m in v:
                m["brand"] = f"{brand}/{profile}" if profile else brand
                van_de.append(m)
    return van_de, tong, thieu


def lock_still_for(van_de) -> list:
    """Chu ky cua mot bo van de — de biet hom nay da bao dung bo nay chua.

    CHI gom brand + ten + muc, KHONG gom ly do: `failure_streak` tang tu 3 len
    4 khong phai tin moi, va neu tinh ca ly do thi mot job hong lien tuc se
    nhan moi lan chay."""
    return sorted(f"{m['brand']}/{m['ten']}/{m['muc']}" for m in van_de)


def read_mark() -> dict:
    try:
        return json.loads(MARK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def use_story(van_de, tong, thieu, ngay: str, so_brand: int) -> str:
    """Tin HTML gui vao topic analyst.

    MOI phan bien doi deu qua `html.escape`: `last_error` la stderr cua script,
    va mot dong stderr co `<` (vi du `<stdin>`, `Traceback ... <module>`) se
    lam Telegram tu choi CA tin voi loi parse HTML — tuc dung hom co loi thi
    canh bao bien mat, dung nhu cai loi da sua o journal_web (06/09/2026)."""
    e = html.escape
    dong = [f"<b>🔧 Soát cron sáng {e(ngay)}</b>", ""]
    for m in sorted(van_de, key=lambda x: (x["muc"] != "HONG", x["brand"], x["ten"])):
        dong.append(f"{ITEM.get(m['muc'], '•')} <b>{e(m['brand'])} / {e(m['ten'])}</b>")
        for l in m["ly_do"]:
            dong.append(f"    {e(l)}")
        dong.append("")
    for b in thieu:
        dong.append(f"🔴 <b>{e(b)}</b> — không thấy thư mục home, script soát sai cấu hình")
        dong.append("")
    hong = sum(1 for m in van_de if m["muc"] == "HONG") + len(thieu)
    khac = len(van_de) + len(thieu) - hong
    dong.append(f"<i>Soát {tong} job ở {so_brand} brand; "
                f"{hong} hỏng, {khac} cần liếc.</i>")
    return "\n".join(dong)


def main() -> int:
    ap = argparse.ArgumentParser(description="Soat cron ca hai brand, bao khi co job hong")
    ap.add_argument("--khong-gui", action="store_true",
                    help="Chi in ra man hinh, khong gui Telegram")
    ap.add_argument("--luon-bao", action="store_true",
                    help="Gui du bo van de nay da duoc bao trong ngay")
    ap.add_argument("--im", action="store_true", help="Khong in ra man hinh")
    a = ap.parse_args()

    homes = env_load.hermes_homes()
    van_de, tong, thieu = audit(homes)
    ngay = datetime.now().strftime("%d/%m")
    khoa = lock_still_for(van_de) + [f"thieu-home/{b}" for b in sorted(thieu)]

    if not a.im:
        for m in van_de:
            print(f"  {m['muc']:5s} {m['brand']}/{m['ten']}: {'; '.join(m['ly_do'])}")
        for b in thieu:
            print(f"  HONG  {b}: khong thay thu muc home (kiem env_load.hermes_homes)")
        print(f"  -- {tong} job, {len(khoa)} van de")

    dau = read_mark()
    hom_nay = datetime.now().strftime("%Y-%m-%d")
    da_bao = dau.get("ngay") == hom_nay and dau.get("van_de") == khoa

    if khoa:
        tin = use_story(van_de, tong, thieu, ngay, len(homes))
    elif dau.get("van_de") and dau.get("ngay") != hom_nay:
        # Het van de sau mot ngay co van de: bao MOT lan roi thoi. Khong co
        # dong nay thi khong bao gio biet cai hong hom qua da het hay chua.
        tin = (f"<b>✅ Cron sạch</b>\n\n{tong} job ở cả hai brand đều bình thường "
               f"— {len(dau['van_de'])} vấn đề của {dau.get('ngay')} đã hết.")
    else:
        tin = ""

    if not tin or (da_bao and not a.luon_bao):
        if not a.im:
            print("khong gui: " + ("khong co van de" if not tin
                                   else f"da bao hom nay boi {dau.get('boi')}"))
        return 0

    if a.khong_gui:
        print(tin)
        return 0

    if not publish.send_topic(tin, "ada"):
        # Co chuyen de noi ma khong noi duoc: phai thoat khac 0, khong thi
        # chinh job canh bao lai la job hong im lang.
        print("[LOI] khong gui duoc canh bao cron", file=sys.stderr)
        return 1

    env_load.write_json(MARK, {"ngay": hom_nay, "van_de": khoa,
                            "boi": env_load._brand() or "don",
                            "luc": datetime.now().isoformat(timespec="seconds")})
    if not a.im:
        print(f"da gui canh bao: {len(khoa)} van de")
    return 0


if __name__ == "__main__":
    sys.exit(main())
