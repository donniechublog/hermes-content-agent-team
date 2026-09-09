#!/usr/bin/env python3
"""HỢP ĐỒNG DỮ LIỆU — một chỗ khai báo cho các tệp JSON đi giữa các bước.

Vi sao (audit_content_team F2): bon hop dong duoi day deu la dict TU DO, khong
khai o dau. Hau qua do duoc:

  - `so_dung_duoc` thieu khoa thi BA noi doan ba kieu: dre_chuan_bi dem lai bang
    mot cong thuc KHAC cong thuc cua nguoi ghi, con duyet_bai va anh_chuan_bi coi
    la 0 ("khong co anh nao") — hai ket luan nguoc nhau tu cung mot tep.
  - `dre_nop.py` vao nhanh bang `m.get("toi_thieu", 5)` roi trong than lai doc
    `m["toi_thieu"]` tho: thieu khoa la KeyError NGAY TRONG CONG CHAN.
  - `write_meta` ghi DE ca dict 8 khoa, ma `bang_den` ghi `root_task` vao cung
    tep o mot tien trinh khac. Hom nay khong mat chi vi THU TU goi may man.

Tep nay KHONG kiem tra luc chay (khong validate). No lam ba viec:
  1. Khai bao khoa bang TypedDict — doi ten khoa thi co MOT cho de sua va de doc.
  2. Giu CONG THUC DAN XUAT dung mot ban (`so_anh_dung_duoc`), de nguoi ghi va
     nguoi doc khong bao gio tinh ra hai so khac nhau.
  3. `doc_manifest()` — doc manifest cu, bu cac khoa dan xuat con thieu roi dan
     nhan `phien_ban`, de ban cu va ban moi doc ra nhu nhau.

CHU Y — "xong.json" KHONG phai mot hop dong. Do la ten tep dung lai o nhieu cho
voi hinh dang KHAC HAN: engine ghi manifest o
`state/<brand>/chuan_bi/<id>/xong.json`, con `itachi_chuan_bi.py` ghi
`{"khoa", "slides"}` va `ada_chuan_bi.py` ghi bao cao gom, deu ten `xong.json`
nhung o workdir khac. Chi manifest cua engine moi theo `Manifest` duoi day.
"""
import json
from pathlib import Path
from typing import Any, TypedDict

# Tang phien ban khi doi Y NGHIA mot khoa (khong phai khi them khoa tuy chon).
# Ban 0 = moi manifest ghi truoc 09/09/2026, khong co truong `phien_ban`.
PHIEN_BAN_MANIFEST = 1


class Manifest(TypedDict, total=False):
    """`state/<brand>/chuan_bi/<draft_id>/xong.json` — engine ghi, moi vai doc.

    Nguoi ghi: `chuan_bi.manifest.dung_manifest` (26 khoa goc), roi
    `anh_chuan_bi.chay` them `thieu_anh`, `route_thieu_anh.sau_chuan_bi` them
    `chuyen_kite`/`hoi_kite`/`khong_kite` — CA BA con trong khoa cua engine, nen
    nguoi doc luon thay ban da chot. Rieng `duyet_bai._nut_ha_san` ghi de
    `toi_thieu` + them `ha_san_luc` SAU DO, luc Ong Chu bam nut.

    `total=False` vi ban cu thieu khoa moi; cot BAT BUOC ghi trong chu thich.
    """
    phien_ban: int                 # tu ban 1; thieu = ban 0 (truoc 09/09/2026)

    # --- BAT BUOC: co noi doc tho `m[k]`, thieu la no ---
    draft_id: str
    brand: str
    title: str
    link: str
    workdir: str                   # duong dan TUYET DOI toi thu muc lam viec
    anh: list                      # [{ma, goc, san, dung, ghi_chu, lien_quan, ...}]
    toi_thieu: int                 # so slide toi thieu cua bai nay
    flagship: bool

    # --- Tuy chon: moi noi doc deu co mac dinh ---
    via: str
    category: str
    summary: str
    source_note: str
    tieu_de_en: str
    tu_lieu: dict
    chu_bai: str                   # CAT con 20000 ky tu luc ghi
    so_mien: list
    cap_ghep: list
    goi_y_bia: list                # ma anh goi y lam bia, XH dung dau neu co
    chua_nhin: list                # ma anh vision chua nhin duoc
    so_dung_duoc: int              # xem `so_anh_dung_duoc` — CHUM khai niem tinh la MOT
    toi_thieu_co_ban: int          # san tuyet doi, `ha san` khong xuong duoi day
    tin_xep_hang: bool
    xep_hang: dict | None          # BANG DAU TIEN; None khi khong chup duoc
    so_xep_hang: int               # so bang chup duoc; 0 khi khong co
    tao_luc: int
    nguon_path: str

    # --- Co dinh tuyen, chi co khi bai THIEU anh (route_thieu_anh ghi) ---
    thieu_anh: dict                # {"so": int, "toi_thieu": int}
    chuyen_kite: str               # task id Kite, khi engine tu chuyen
    hoi_kite: bool                 # da hoi Ong Chu bang nut
    khong_kite: bool               # brand chua co Kite, khong hua chuyen
    ha_san_luc: int                # luc Ong Chu bam "lam voi N anh"


class Meta(TypedDict, total=False):
    """`drafts/<draft_id>.meta.json` — sinh luc Ong Chu chon tin.

    HAI TIEN TRINH ghi: `duyet_chon_tin.write_meta` (8 khoa dau, ghi DE ca dict)
    va `bang_den._ghi_meta` (chi `root_task`, chay bang python cua hermes).
    Vi write_meta ghi de chu khong merge, thu tu goi la thu duy nhat giu cho
    `root_task` khong bi xoa — xem `hop_nhat_meta`.
    """
    source_url: str                # BAT BUOC (draft_write thoat neu rong)
    title: str                     # BAT BUOC
    category: str                  # BAT BUOC
    brand: str                     # quyet dinh CT_BRAND cua ca tien trinh
    image: str
    via: str
    score: int | float | None      # None khi Nova/Vera quet (khong cham diem)
    score_reason: str
    root_task: str                 # the goc bang den; chi brand bat bang den


class SidecarAnh(TypedDict, total=False):
    """`drafts/<draft_id>.img.json` — de LAM LAI task anh duoc."""
    vai_anh: str                   # SLUG vai (ban cu con ghi ten persona)
    carousel: bool
    title: str
    body: str                      # nguyen body task, de dung lai khi lam lai
    remakes: int
    link: str
    summary: str
    source_note: str
    via: str
    chuyen_kite: str               # duyet_bai ghi khi Ong Chu bam "Gui Kite"
    chuyen_tu: str


class DongAnhDaDung(TypedDict):
    """MOT DONG trong `state/<brand>/anh_da_dung.jsonl` (noi them, khong sua).

    Khoa theo TIN chu khong theo draft: cung mot tin giao cho hai vai ra hai
    draft_id nhung dung chung bo anh engine tai ve."""
    dhash: str
    draft_id: str
    vai: str
    tin: str                       # khoa on dinh cua tin, xem luat_anh.khoa_tin
    ten: str
    md5: str
    luc: int                       # epoch giay, de xet cua so 14 ngay


# ---------------------------------------------------------------- dan xuat
def so_anh_dung_duoc(anh: list) -> int:
    """So anh DUNG DUOC de xet du/thieu — MOT ban duy nhat cua cong thuc.

    Chum anh KHAI NIEM chi lam bia nen ca chum dem la MOT: "5" o day la co Nhat,
    khong phai 5 slide. Truoc khi gom ve day, `dre_chuan_bi` doan lai bang
    `len([a for a in anh if a["dung"]])` — mot so KHAC — con `duyet_bai` va
    `anh_chuan_bi` coi thieu khoa la 0. Ba cach doan cho ba ket luan."""
    dung_duoc = [a for a in (anh or []) if a.get("dung") and a.get("lien_quan") is not False]
    so_rieng = sum(1 for a in dung_duoc if not a.get("khai_niem"))
    return so_rieng + min(1, len(dung_duoc) - so_rieng)


def doc_manifest(nguon) -> dict | None:
    """Doc manifest cua engine, tu nang ban cu. None neu khong doc duoc.

    `nguon` la duong dan toi xong.json, hoac chinh dict da doc san.

    Nang ban 0 -> 1: ban cu co the thieu cac khoa DAN XUAT. Bu lai bang dung
    cong thuc cua nguoi ghi thay vi de moi nguoi doc tu doan — do la nguyen nhan
    ba noi ra ba so khac nhau. KHONG dung cham cac khoa khac: bu la de doc ban cu
    cho dung, khong phai de sua du lieu."""
    if isinstance(nguon, dict):
        m = dict(nguon)
    else:
        p = Path(nguon)
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"[schema] khong doc duoc manifest {p}: {type(e).__name__}: {e!r}")
            return None
        if not isinstance(m, dict):
            print(f"[schema] manifest {p} khong phai dict")
            return None

    if m.get("phien_ban", 0) < 1:
        if "so_dung_duoc" not in m:
            m["so_dung_duoc"] = so_anh_dung_duoc(m.get("anh") or [])
        # `so_xep_hang` = SO BANG chup duoc. Ban cu chi co `xep_hang` (bang dau
        # tien) nen suy: co bang thi it nhat mot, khong co thi 0. Nguoi doc tung
        # mac dinh 1 ke ca khi khong co bang nao — nguoc han y nghia.
        if "so_xep_hang" not in m:
            m["so_xep_hang"] = 1 if m.get("xep_hang") else 0
        m["phien_ban"] = PHIEN_BAN_MANIFEST
    return m


def hop_nhat_meta(cu: dict | None, moi: dict) -> dict:
    """Tron ban meta MOI vao ban CU thay vi ghi de.

    `write_meta` chay hai lan cho mot bai (luc chon tin, roi luc giai xong link
    Google News), con `bang_den` ghi `root_task` vao CUNG tep tu mot tien trinh
    khac. Ghi de ca dict nghia la ai ghi sau xoa cua ai ghi truoc — hom nay chua
    mat chi vi thu tu goi tinh co dung. Tron thi khong phu thuoc thu tu nua.

    Khoa co trong `moi` thang, ke ca khi gia tri rong: do la y cua nguoi ghi."""
    ra = dict(cu or {})
    ra.update(moi)
    return ra


def _kieu(td) -> dict[str, Any]:
    """Khoa -> kieu da khai, dung cho test doi chieu khai bao voi thuc te."""
    return dict(getattr(td, "__annotations__", {}))
