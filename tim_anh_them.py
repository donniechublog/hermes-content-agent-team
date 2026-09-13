#!/usr/bin/env python3
"""tim_anh_them.py — VAI LAM ANH TU DI TIM THEM ANH khi ban chuan bi thieu.

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
  - toi da TOI_DA_LUOT luot mot bai, de khong quay lai 60 tool call/task;
  - het luot ma van thieu moi kanban_block, va cau block PHAI ke tu khoa da thu.

Dung:
    venv/bin/python tim_anh_them.py <draft_id> --tu-khoa "TSMC fab Arizona" [--tu-khoa ...]
    venv/bin/python tim_anh_them.py <draft_id> --url https://... [--url ...]
Sau do chay lai <vai>_chuan_bi.py <draft_id> de doc brief moi (xong.json da cap nhat).
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
import anh_chuan_bi as cb                                    # noqa: E402
import nguon_bai                                             # noqa: E402
import schema                                                # noqa: E402
import vai as vai_mod                                        # noqa: E402
from phien_browser import PhienBrowser                       # noqa: E402
from chuan_bi.browser import browser_pass                    # noqa: E402
from chuan_bi.chung import _ghi_json, _mien                  # noqa: E402
from chuan_bi.manifest import bang_anh, dan_xuat             # noqa: E402
from chuan_bi.nhin import _nhin_anh                          # noqa: E402
from chuan_bi.tai_loc import tai_va_loc                      # noqa: E402

TOI_DA_LUOT = 3             # moi bai toi da 3 luot tim them (Ong Chu 12/09/2026)
SO_BAO_MOI_LUOT = 4         # bao moi hoi Bing moi luot
SO_COMMONS_MOI_LUOT = 6
TOI_DA_ANH_THEM = 12        # tran anh moi noi vao mot luot (8 -> 12 khi co them nguon web, 12/09)
_ANH_EXT = re.compile(r"\.(jpe?g|png|webp)(\?.*)?$", re.I)


def doc_so_luot(wd: Path) -> dict:
    p = wd / "tim_them.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {"luot": 0, "da_thu": []}


def kiem_tu_khoa(tu_khoa: list) -> list:
    """Tu khoa phai la TIENG ANH (luat 05/09/2026: khong nem tieu de Viet vao Bing/
    Commons — 0 ket qua) va khong rong. Tra danh sach loi (rong = hop le)."""
    loi = []
    for tk in tu_khoa:
        if not tk.strip():
            loi.append("tu khoa rong")
        elif nguon_bai.co_tieng_viet(tk):
            loi.append(f"'{tk}': tu khoa phai TIENG ANH (Bing/Commons khong hieu tieng Viet)")
        elif len(tk.split()) > 6:
            loi.append(f"'{tk}': qua dai (> 6 tu) — Bing chi tra ket qua cho truy van ngan")
    return loi


def ung_vien_commons(tu_khoa: str, so: int = SO_COMMONS_MOI_LUOT) -> list:
    """Commons theo tu khoa cua VAI: loc long hon `anh_commons` (khong doi nguyen
    cum trong ten tep) vi vai da chon tu khoa co chu y — dung bo loc cua anh
    khai niem (>= 2 tu dac trung). Tra [] khi hong (da in ly do)."""
    import quet_chung
    import anh_khai_niem
    pages = quet_chung.hoi_commons(tu_khoa, so=14, loai_logo=False)
    if pages is None:
        print(f"[tim them] Commons '{tu_khoa}': API hong -> bo qua nguon nay", file=sys.stderr)
        return []
    ra = anh_khai_niem.loc_commons(pages, tu_khoa, so=so)
    for c in ra:
        c.pop("khai_niem", None)       # vai tim co chu y, khong phai anh khai niem chung chung
        c["tu"] = "commons"
        c["diem"] = 35
        c["anh"], c["rong"], c["cao"] = thu_nho_commons(c["anh"], c["rong"], c["cao"])
    return ra


OPENVERSE = "https://api.openverse.org/v1/images/"
GIAY_PHEP_OK = ("by", "by-sa", "cc0", "pdm")     # dung duoc, chi can ghi nguon
CANH_NGAN_OPENVERSE = 700


_COMMONS_GOC = re.compile(r"^(https://upload\.wikimedia\.org/wikipedia/commons)/([0-9a-f])/([0-9a-f]{2})/([^/?]+)$")
THUMB_COMMONS = 2000        # ban thu nho Commons: goc 8000px la 15-30 MB, qua tran tai 14 MB


def thu_nho_commons(url: str, w: int, h: int) -> tuple:
    """URL goc tren upload.wikimedia.org -> URL thumb THUMB_COMMONS px (va kich
    thuoc moi). Lan thu dau 12/09/2026: 8/8 anh TSMC tu Openverse bi bo vi
    "qua 14 MB" — toan anh 8000x5500. Khong phai Commons thi tra nguyen."""
    m = _COMMONS_GOC.match(url or "")
    if not m or w <= THUMB_COMMONS:
        return url, w, h
    goc, a, ab, ten = m.groups()
    return (f"{goc}/thumb/{a}/{ab}/{ten}/{THUMB_COMMONS}px-{ten}",
            THUMB_COMMONS, int(h * THUMB_COMMONS / w))


def loc_openverse(kq: dict, tu_khoa: str, so: int) -> list:
    """Bien ket qua Openverse thanh ung vien cho `tai_va_loc`. Tach rieng de test
    khong can mang. Chi giay phep CC dung duoc, chi anh du lon, JPEG/PNG."""
    ra = []
    for r in (kq or {}).get("results") or []:
        url = r.get("url") or ""
        w, h = int(r.get("width") or 0), int(r.get("height") or 0)
        if (r.get("license") or "").lower() not in GIAY_PHEP_OK:
            continue
        if min(w, h) < CANH_NGAN_OPENVERSE or not _ANH_EXT.search(url.split("?")[0]):
            continue
        url, w, h = thu_nho_commons(url, w, h)
        ra.append({"anh": url, "alt": (r.get("title") or "")[:120], "og": False, "tu": "openverse",
                   "trang": r.get("foreign_landing_url") or url, "rong": w, "cao": h, "diem": 40,
                   "giay_phep": r.get("license"), "tac_gia": r.get("creator") or "",
                   "nguon_openverse": r.get("source") or "", "tu_khoa": tu_khoa})
    ra.sort(key=lambda c: -(c["rong"] * c["cao"]))
    return ra[:so]


def ung_vien_openverse(tu_khoa: str, so: int = 8) -> list:
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
        return loc_openverse(r.json(), tu_khoa, so)
    except Exception as e:                                   # noqa: BLE001
        print(f"[tim them] Openverse '{tu_khoa}' hong: {type(e).__name__}: {e}", file=sys.stderr)
        return []


def ung_vien_tu_url(urls: list, wd: Path, phien=None) -> list:
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


def ung_vien_tu_khoa(tu_khoa: str, wd: Path, mien_co: set, phien=None) -> list:
    """Mot tu khoa -> bao cung tin (Bing News, mo browser) + Commons + Openverse + og:image bao ve thuc the."""
    cands = []
    # TIM ANH WEB (Bing/Yandex qua Chromium) — cai gan nhat voi "go Google Images".
    import tim_anh_web
    cands += tim_anh_web.tim_anh_web(tu_khoa, so=16, phien=phien)
    bao = nguon_bai.bao_khac_bing(tu_khoa, so=SO_BAO_MOI_LUOT, bo_mien=tuple(x for x in mien_co if x))
    print(f"[tim them] Bing '{tu_khoa}': {len(bao)} bao"
          + (": " + ", ".join(_mien(t["url"]) for t in bao) if bao else ""), file=sys.stderr)
    if bao:
        bp = browser_pass([{"url": t["url"], "loai": "báo"} for t in bao], wd, tim_them=False, phien=phien)
        print(f"[tim them] browser boc {len(bp['cands'])} ung vien tu {len(bao)} bao", file=sys.stderr)
        cands += bp["cands"]
    cm = ung_vien_commons(tu_khoa)
    print(f"[tim them] Commons '{tu_khoa}': {len(cm)} ung vien", file=sys.stderr)
    cands += cm
    ov = ung_vien_openverse(tu_khoa)
    print(f"[tim them] Openverse '{tu_khoa}': {len(ov)} ung vien", file=sys.stderr)
    cands += ov
    # Anh BAO CHI ve thuc the (og:image cua bai gan day) — cach nguoi tim bang
    # tay (Ong Chu 12/09/2026, 7 link TSMC). Khong doi "cung tin".
    import anh_bao_thuc_the
    bt = anh_bao_thuc_the.anh_bao_thuc_the([tu_khoa], bo_mien=tuple(x for x in mien_co if x))
    cands += bt
    return cands


def noi_anh_moi(m: dict, bo_sung: list, wd: Path, tieu_de: str) -> list:
    """Danh ma A<n> tiep theo, don ve goc/, phan loai + vision. Tra danh sach anh MOI."""
    anh = m["anh"]
    n0 = len(anh)
    moi = []
    for i, a in enumerate(bo_sung, start=n0 + 1):
        if len(moi) >= TOI_DA_ANH_THEM:
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
    moi, _, _ = _nhin_anh(moi, nguon, tieu_de, wd)
    anh.extend(moi)
    return moi


def lam_moi_manifest(m: dict) -> dict:
    """Tinh lai cac gia tri dan xuat sau khi bo anh doi (cung cong thuc voi engine)."""
    dx = dan_xuat(m["anh"], so_xh=int(m.get("so_xep_hang") or 0))
    for k in ("so_mien", "cap_ghep", "goi_y_bia", "so_dung_duoc", "chua_nhin"):
        m[k] = dx[k]
    thieu = cb._mo_ta_thieu_anh(m)
    if thieu:
        m["thieu_anh"] = thieu
    else:
        m.pop("thieu_anh", None)
    return m


def in_ket_qua(m: dict, moi: list, so_luot: dict, vai_anh: str) -> None:
    print(f"\n== TIM THEM luot {so_luot['luot']}/{TOI_DA_LUOT}: +{len(moi)} anh moi ==")
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
    print(f"Chạy lại: cd {ROOT} && venv/bin/python {vai_anh}_chuan_bi.py {m['draft_id']}  (brief mới, bảng ảnh mới)")
    if so < tt:
        con = TOI_DA_LUOT - so_luot["luot"]
        if con > 0:
            print(f"Còn {con} lượt tìm. Đổi từ khoá khác hẳn (hãng, sản phẩm, nhà máy, sự kiện, người trong bài).")
        else:
            print("HẾT LƯỢT. Nếu vẫn thiếu: kanban_block, ly do ghi ro DA THU tu khoa: "
                  + "; ".join(so_luot["da_thu"]))


def main() -> int:
    ap = argparse.ArgumentParser(description="Vai lam anh tu tim them anh khi ban chuan bi thieu")
    ap.add_argument("draft_id")
    ap.add_argument("--tu-khoa", action="append", default=[], help="tu khoa TIENG ANH, lap lai duoc")
    ap.add_argument("--url", action="append", default=[], help="URL trang bao hoac URL anh, lap lai duoc")
    ap.add_argument("--khong-browser", action="store_true")
    a = ap.parse_args()
    if not a.tu_khoa and not a.url:
        sys.exit("[LOI] can it nhat mot --tu-khoa \"...\" (tieng Anh) hoac --url ...")
    loi = kiem_tu_khoa(a.tu_khoa)
    if loi:
        sys.exit("[LOI] " + "; ".join(loi))

    state = env_load.state_dir()
    wd = cb.workdir(state, a.draft_id)
    xong, khoa = wd / "xong.json", wd / "dang_chay.pid"
    if not xong.exists():
        sys.exit(f"[LOI] chua co ban chuan bi ({xong}) — chay <vai>_chuan_bi.py {a.draft_id} truoc")
    so_luot = doc_so_luot(wd)
    if so_luot["luot"] >= TOI_DA_LUOT:
        sys.exit(f"[DUNG] da het {TOI_DA_LUOT} luot tim them cho bai nay (da thu: "
                 f"{'; '.join(so_luot['da_thu'])}). Van thieu thi kanban_block, ghi ro cac tu khoa da thu.")
    cb._doi_khoa(khoa, 120, a.draft_id)
    khoa.write_text(str(os.getpid()))
    try:
        m = schema.doc_manifest(xong)
        if m is None:
            sys.exit(f"[LOI] khong doc duoc {xong}")
        tieu_de = m.get("tieu_de_en") or m.get("title") or a.draft_id
        vai_anh = vai_mod.slug_that(m.get("vai_anh") or "") or vai_mod.MAC_DINH_ANH
        so_luot["luot"] += 1
        so_luot["da_thu"] += a.tu_khoa + a.url
        _ghi_json(wd / "tim_them.json", so_luot)

        mien_co = {a_.get("mien") for a_ in m["anh"]}
        wd2 = wd / f"them_{so_luot['luot']}"
        wd2.mkdir(parents=True, exist_ok=True)
        cands = []
        t0 = time.time()
        with PhienBrowser() as phien:
            ph = None if a.khong_browser else phien
            for tk in a.tu_khoa:
                cands += ung_vien_tu_khoa(tk, wd2, mien_co, phien=ph)
            if a.url:
                cands += ung_vien_tu_url(a.url, wd2, phien=ph)
        da = {x.get("url") for x in m["anh"]}
        n_truoc = len(cands)
        cands = [c for c in cands if c.get("anh") and c["anh"] not in da]
        if n_truoc != len(cands):
            print(f"[tim them] bo {n_truoc - len(cands)} ung vien trung URL da co", file=sys.stderr)
        cands.sort(key=lambda c: -c.get("diem", 0))
        bo_sung = tai_va_loc(cands, wd2) if cands else []
        print(f"[tim them] tai + loc: {len(bo_sung)} anh giu lai / {len(cands)} ung vien "
              f"({time.time() - t0:.0f}s)", file=sys.stderr)
        moi = noi_anh_moi(m, bo_sung, wd, tieu_de)
        lam_moi_manifest(m)
        bang_anh(m["anh"], wd / "bang_anh.png")
        _ghi_json(xong, m)
        in_ket_qua(m, moi, so_luot, vai_anh)
    finally:
        khoa.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
