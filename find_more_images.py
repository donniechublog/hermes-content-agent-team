#!/usr/bin/env python3
"""find_more_images.py — VAI LAM ANH TU DI TIM THEM ANH khi ban chuan bi thieu.

Vi sao co tep nay (Ong Chu 12/09/2026, tin TSMC t_a8ffd2f6): kien truc 3 lop
04/09 (engine chuan bi -> vai viet mot tep -> script nop) cat luon quyen TIM
anh cua vai — "designer ma khong duoc phep di tim anh, ai nghi ra cai luat
thieu nang nay?". Cai dat la TAI/CROP/NHIN (co hoc, ton luot), khong phai TIM
(can mat va phan doan — dung viec cua designer). Engine chi biet mot danh sach
nguon co dinh; kho mong thi no co MOT vong tim rong, het vong la dung ca bai,
Ong Chu phai go tay.

Nay giu phan dung, bo phan pha hoai:
  - engine van chuan bi nhu cu, cong chan van cua script;
  - THIEU thi vai goi lenh nay voi TU KHOA TIENG ANH (hoac URL trang/anh vai
    biet). Script di hoi Bing News + Wikimedia Commons, mo trang bang browser,
    tai, nhin (vision), do, cat san — y het engine — roi noi vao xong.json va
    in ra anh moi. Vai chon, may van xu ly.
  - moi lan chay ghi lai tu khoa da thu (tim_them.json), de khong lap lai huong cu;
  - van thieu sau nhieu huong tu khoa khac nhau da hop ly thi kanban_block, cau
    block PHAI ke tu khoa da thu (LOW-174, 15/09/2026: bo tran cung "toi da 3
    luot" — dem theo draft_id vinh vien khien mot bai tung bi block se KHONG
    BAO GIO thu lai duoc, ke ca khi huong tiep can da doi, vd sau khi sua engine
    vision LOW-164 thi tu khoa cu van bi tu choi chay lai).

Dung:
    venv/bin/python find_more_images.py <draft_id> --tu-khoa "TSMC fab Arizona" [--tu-khoa ...]
    venv/bin/python find_more_images.py <draft_id> --url https://... [--url ...]
Sau do chay lai <vai>_prepare.py <draft_id> de doc brief moi (xong.json da cap nhat).
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                              # noqa: E402
import image_prepare as cb                                    # noqa: E402
import article_sources                                             # noqa: E402
import schema                                                # noqa: E402
import role as vai_mod                                        # noqa: E402
from browser_session import BrowserSession                       # noqa: E402
from prepare import decision_log                              # noqa: E402
from prepare.browser import browser_pass                    # noqa: E402
from prepare.common import _write_json, _domain                  # noqa: E402
from prepare.manifest import contact_sheet, compute_derived             # noqa: E402
from prepare.vision import _seen_image                          # noqa: E402
from prepare.download_filter import download_and_filter                      # noqa: E402

COUNT_REPORT_NEW_TURN = 4         # bao moi hoi Bing moi luot
COUNT_COMMONS_NEW_TURN = 6
MAX_IMAGE_EXTRA = 12        # tran anh moi noi vao mot luot (8 -> 12 khi co them nguon web, 12/09)
_ANH_EXT = re.compile(r"\.(jpe?g|png|webp)(\?.*)?$", re.I)


def read_count_turn(wd: Path) -> dict:
    p = wd / "tim_them.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {"luot": 0, "da_thu": []}


def check_keyword(tu_khoa: list) -> list:
    """Tu khoa phai la TIENG ANH (luat 05/09/2026: khong nem tieu de Viet vao Bing/
    Commons — 0 ket qua) va khong rong. Tra danh sach loi (rong = hop le)."""
    loi = []
    for tk in tu_khoa:
        if not tk.strip():
            loi.append("tu khoa rong")
        elif article_sources.has_vietnamese(tk):
            loi.append(f"'{tk}': tu khoa phai TIENG ANH (Bing/Commons khong hieu tieng Viet)")
        elif len(tk.split()) > 6:
            loi.append(f"'{tk}': qua dai (> 6 tu) — Bing chi tra ket qua cho truy van ngan")
    return loi


def candidate_commons(tu_khoa: str, so: int = COUNT_COMMONS_NEW_TURN) -> list:
    """Commons theo tu khoa cua VAI: loc long hon `anh_commons` (khong doi nguyen
    cum trong ten tep) vi vai da chon tu khoa co chu y — dung bo loc cua anh
    khai niem (>= 2 tu dac trung). Tra [] khi hong (da in ly do)."""
    import scan_common
    import image_concept
    pages = scan_common.ask_commons(tu_khoa, so=14, loai_logo=False)
    if pages is None:
        print(f"[tim them] Commons '{tu_khoa}': API hong -> bo qua nguon nay", file=sys.stderr)
        return []
    ra = image_concept.filter_commons(pages, tu_khoa, so=so)
    for c in ra:
        c.pop("khai_niem", None)       # vai tim co chu y, khong phai anh khai niem chung chung
        c["tu"] = "commons"
        c["diem"] = 35
        c["anh"], c["rong"], c["cao"] = try_small_commons(c["anh"], c["rong"], c["cao"])
    return ra


OPENVERSE = "https://api.openverse.org/v1/images/"
LICENSE_OK = ("by", "by-sa", "cc0", "pdm")     # dung duoc, chi can ghi nguon
SHORT_SIDE_OPENVERSE = 700


_COMMONS_GOC = re.compile(r"^(https://upload\.wikimedia\.org/wikipedia/commons)/([0-9a-f])/([0-9a-f]{2})/([^/?]+)$")
THUMB_COMMONS = 2000        # ban thu nho Commons: goc 8000px la 15-30 MB, qua tran tai 14 MB


def try_small_commons(url: str, w: int, h: int) -> tuple:
    """URL goc tren upload.wikimedia.org -> URL thumb THUMB_COMMONS px (va kich
    thuoc moi). Lan thu dau 12/09/2026: 8/8 anh TSMC tu Openverse bi bo vi
    "qua 14 MB" — toan anh 8000x5500. Khong phai Commons thi tra nguyen."""
    m = _COMMONS_GOC.match(url or "")
    if not m or w <= THUMB_COMMONS:
        return url, w, h
    goc, a, ab, ten = m.groups()
    return (f"{goc}/thumb/{a}/{ab}/{ten}/{THUMB_COMMONS}px-{ten}",
            THUMB_COMMONS, int(h * THUMB_COMMONS / w))


def filter_openverse(kq: dict, tu_khoa: str, so: int) -> list:
    """Bien ket qua Openverse thanh ung vien cho `download_and_filter`. Tach rieng de test
    khong can mang. Chi giay phep CC dung duoc, chi anh du lon, JPEG/PNG."""
    ra = []
    for r in (kq or {}).get("results") or []:
        url = r.get("url") or ""
        w, h = int(r.get("width") or 0), int(r.get("height") or 0)
        if (r.get("license") or "").lower() not in LICENSE_OK:
            continue
        if min(w, h) < SHORT_SIDE_OPENVERSE or not _ANH_EXT.search(url.split("?")[0]):
            continue
        url, w, h = try_small_commons(url, w, h)
        ra.append({"anh": url, "alt": (r.get("title") or "")[:120], "og": False, "tu": "openverse",
                   "trang": r.get("foreign_landing_url") or url, "rong": w, "cao": h, "diem": 40,
                   "giay_phep": r.get("license"), "tac_gia": r.get("creator") or "",
                   "nguon_openverse": r.get("source") or "", "tu_khoa": tu_khoa})
    ra.sort(key=lambda c: -(c["rong"] * c["cao"]))
    return ra[:so]


def candidate_openverse(tu_khoa: str, so: int = 8) -> list:
    """Anh CC theo tu khoa qua Openverse (gom Wikimedia, Flickr CC...). Day la
    nguon TIM ANH that su cho designer: Bing News chi ra bao cung tin, Commons
    doi ten tep khop chu — hai cai do khong phai "tim anh theo y minh".
    Tra [] khi hong (da in ly do)."""
    import httpx
    try:
        r = httpx.get(OPENVERSE, params={"q": tu_khoa, "page_size": 20}, timeout=25,
                      headers={"User-Agent": "content-team/1.0 (tim_anh_them)"})
        if r.status_code != 200:
            print(f"[tim them] Openverse '{tu_khoa}': HTTP {r.status_code}", file=sys.stderr)
            return []
        return filter_openverse(r.json(), tu_khoa, so)
    except Exception as e:                                   # noqa: BLE001
        print(f"[tim them] Openverse '{tu_khoa}' hong: {type(e).__name__}: {e}", file=sys.stderr)
        return []


def candidate_from_url(urls: list, wd: Path, phien=None) -> list:
    """URL vai dua: la ANH (duoi jpg/png/webp) thi tai thang; la TRANG thi mo
    browser boc anh lon nhu engine."""
    anh, trang = [], []
    for u in urls:
        if _ANH_EXT.search(u.split("#")[0]):
            anh.append({"anh": u, "alt": "", "og": False, "tu": "vai", "trang": u,
                        "rong": 0, "cao": 0, "diem": 60})
        else:
            trang.append({"url": u, "loai": "báo"})
    if trang:
        bp = browser_pass(trang, wd, tim_them=False, phien=phien)
        print(f"[tim them] browser boc {len(bp['cands'])} ung vien tu {len(trang)} trang vai dua",
              file=sys.stderr)
        anh += bp["cands"]
    return anh


def candidate_keyword(tu_khoa: str, wd: Path, mien_co: set, phien=None) -> list:
    """Mot tu khoa -> bao cung tin (Bing News, mo browser) + Commons + Openverse + og:image bao ve thuc the."""
    cands = []
    # TIM ANH WEB (Bing/Yandex qua Chromium) — cai gan nhat voi "go Google Images".
    import find_image_web
    cands += find_image_web.find_image_web(tu_khoa, so=16, phien=phien)
    bao = article_sources.other_outlets_bing(tu_khoa, so=COUNT_REPORT_NEW_TURN, bo_mien=tuple(x for x in mien_co if x))
    print(f"[tim them] Bing '{tu_khoa}': {len(bao)} bao"
          + (": " + ", ".join(_domain(t["url"]) for t in bao) if bao else ""), file=sys.stderr)
    if bao:
        bp = browser_pass([{"url": t["url"], "loai": "báo"} for t in bao], wd, tim_them=False, phien=phien)
        print(f"[tim them] browser boc {len(bp['cands'])} ung vien tu {len(bao)} bao", file=sys.stderr)
        cands += bp["cands"]
    cm = candidate_commons(tu_khoa)
    print(f"[tim them] Commons '{tu_khoa}': {len(cm)} ung vien", file=sys.stderr)
    cands += cm
    ov = candidate_openverse(tu_khoa)
    print(f"[tim them] Openverse '{tu_khoa}': {len(ov)} ung vien", file=sys.stderr)
    cands += ov
    # Anh BAO CHI ve thuc the (og:image cua bai gan day) — cach nguoi tim bang
    # tay (Ong Chu 12/09/2026, 7 link TSMC). Khong doi "cung tin".
    import press_entity_images
    bt = press_entity_images.press_entity_images([tu_khoa], bo_mien=tuple(x for x in mien_co if x))
    cands += bt
    return cands


def say_image_new(m: dict, bo_sung: list, wd: Path, tieu_de: str) -> list:
    """Danh ma A<n> tiep theo, don ve goc/, phan loai + vision. Tra danh sach anh MOI."""
    anh = m["anh"]
    n0 = len(anh)
    moi = []
    for i, a in enumerate(bo_sung, start=n0 + 1):
        if len(moi) >= MAX_IMAGE_EXTRA:
            break
        a["ma"] = f"A{i}"
        dich = wd / "goc" / f"{a['ma']}.png"
        Path(a["goc"]).replace(dich)
        a["goc"] = str(dich)
        a["tim_them"] = True
        moi.append(a)
    if not moi:
        return []
    nguon = {"tieu_de_en": m.get("tieu_de_en") or tieu_de}
    moi, _, _ = _seen_image(moi, nguon, tieu_de, wd)
    anh.extend(moi)
    return moi


def fresh_manifest(m: dict) -> dict:
    """Tinh lai cac gia tri dan xuat sau khi bo anh doi (cung cong thuc voi engine)."""
    dx = compute_derived(m["anh"], m.get("vai_anh", ""), so_xh=int(m.get("so_xep_hang") or 0))
    for k in ("so_mien", "cap_ghep", "goi_y_bia", "so_dung_duoc", "chua_nhin"):
        m[k] = dx[k]
    thieu = cb._description_missing_image(m)
    if thieu:
        m["thieu_anh"] = thieu
    else:
        m.pop("thieu_anh", None)
    return m


def in_result(m: dict, moi: list, so_luot: dict, vai_anh: str) -> None:
    print(f"\n== TIM THEM luot {so_luot['luot']}: +{len(moi)} anh moi ==")
    for a in moi:
        if a.get("lien_quan") is False:
            print(f"- {a['ma']}: ❌ KHÔNG LIÊN QUAN — {a.get('mo_ta') or ''} (nguồn: {a.get('mien') or a.get('tu')})")
            continue
        print(f"- {a['ma']}: {a.get('w')}x{a.get('h')} {'NGANG ' if a.get('ngang') else ''}"
              f"| dùng: {'; '.join(a.get('dung') or []) or 'không'} | nguồn: {a.get('mien') or a.get('tu')}"
              + (f" | ảnh là: {a['mo_ta'][:110]}" if a.get("mo_ta") else ""))
    so, tt = int(m.get("so_dung_duoc", 0)), int(m.get("toi_thieu", 5))
    print(f"Slide dựng được: {so} / tối thiểu {tt}"
          + (" — ĐỦ." if so >= tt else f" — còn thiếu {tt - so}."))
    print(f"Chạy lại: cd {ROOT} && venv/bin/python {vai_anh}_prepare.py {m['draft_id']}  (brief mới, bảng ảnh mới)")
    if so < tt:
        print(f"Đã thử {so_luot['luot']} lượt (từ khoá: {'; '.join(so_luot['da_thu']) or '—'}). "
              "Đổi từ khoá khác hẳn (hãng, sản phẩm, nhà máy, sự kiện, người trong bài) rồi chạy lại, "
              "hoặc nếu đã thử đủ nhiều hướng khác nhau mà vẫn thiếu thì kanban_block — ly do ghi ro "
              "cac tu khoa da thu.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Vai lam anh tu tim them anh khi ban chuan bi thieu")
    ap.add_argument("draft_id")
    ap.add_argument("--tu-khoa", action="append", default=[], help="tu khoa TIENG ANH, lap lai duoc")
    ap.add_argument("--url", action="append", default=[], help="URL trang bao hoac URL anh, lap lai duoc")
    ap.add_argument("--khong-browser", action="store_true")
    a = ap.parse_args()
    if not a.tu_khoa and not a.url:
        sys.exit("[LOI] can it nhat mot --tu-khoa \"...\" (tieng Anh) hoac --url ...")
    loi = check_keyword(a.tu_khoa)
    if loi:
        sys.exit("[LOI] " + "; ".join(loi))

    state = env_load.state_dir()
    wd = cb.workdir(state, a.draft_id)
    xong, khoa = wd / "xong.json", wd / "dang_chay.pid"
    if not xong.exists():
        sys.exit(f"[LOI] chua co ban chuan bi ({xong}) — chay <vai>_prepare.py {a.draft_id} truoc")
    so_luot = read_count_turn(wd)
    cb._handle_lock(khoa, 120, a.draft_id)
    khoa.write_text(str(os.getpid()))
    try:
        m = schema.read_manifest(xong)
        if m is None:
            sys.exit(f"[LOI] khong doc duoc {xong}")
        tieu_de = m.get("tieu_de_en") or m.get("title") or a.draft_id
        vai_anh = vai_mod.canonical_slug(m.get("vai_anh") or "") or vai_mod.DEFAULT_IMAGE
        vai_mod.set_active_role(vai_anh)
        so_luot["luot"] += 1
        so_luot["da_thu"] += a.tu_khoa + a.url
        _write_json(wd / "tim_them.json", so_luot)

        mien_co = {a_.get("mien") for a_ in m["anh"]}
        wd2 = wd / f"them_{so_luot['luot']}"
        wd2.mkdir(parents=True, exist_ok=True)
        cands = []
        t0 = time.time()
        with BrowserSession() as phien:
            ph = None if a.khong_browser else phien
            for tk in a.tu_khoa:
                cands += candidate_keyword(tk, wd2, mien_co, phien=ph)
            if a.url:
                cands += candidate_from_url(a.url, wd2, phien=ph)
        da = {x.get("url") for x in m["anh"]}
        n_truoc = len(cands)
        cands = [c for c in cands if c.get("anh") and c["anh"] not in da]
        if n_truoc != len(cands):
            print(f"[tim them] bo {n_truoc - len(cands)} ung vien trung URL da co", file=sys.stderr)
        cands.sort(key=lambda c: -c.get("diem", 0))
        bo_sung = download_and_filter(cands, wd2) if cands else []
        print(f"[tim them] tai + loc: {len(bo_sung)} anh giu lai / {len(cands)} ung vien "
              f"({time.time() - t0:.0f}s)", file=sys.stderr)
        moi = say_image_new(m, bo_sung, wd, tieu_de)
        m.setdefault("dropped", []).extend(decision_log.collect(wd2, since=t0))   # LOW-225
        fresh_manifest(m)
        contact_sheet(m["anh"], wd / "bang_anh.png")
        _write_json(xong, m)
        in_result(m, moi, so_luot, vai_anh)
    finally:
        khoa.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
