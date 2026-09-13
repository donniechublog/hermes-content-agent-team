#!/usr/bin/env python3
"""Phan CHUNG cua hai script ghi manifest: `manifest_build` (Finn) va
`manifest_ghi` (Nova/Vera).

Hai script viet CUNG mot dinh dang cho CUNG mot nguoi doc, va cung mot chuoi
viec co hoc: chon muc theo so thu tu `k`, don tom tat cua vai, tu them muc BAT
BUOC bi bo sot, danh so, khong ghi de ban da co trong ngay, chot danh sach bat
buoc, dung bao cao. Truoc 07/09/2026 moi script tu viet lai het, va DA LECH:

  - cong bo em-dash trong `summary_vi` chi co o nhanh Finn. Ly do co no la
    "em-dash lot xuong tan caption" — dieu do dung y het voi caption cua Nova
    va Vera, nhung nhanh kia khong co.
  - `manifest_build.main` co mot chu thich noi ro "cung mot bo kiem nhu
    manifest_ghi", ma bo kiem do da khong con giong.

Cai KHONG gom vao day: cong bao title tieng Viet mat dau. O nhanh Nova/Vera
title do CHINH VAI viet bang tieng Viet; o nhanh Finn title lay tu
candidates.json, tuc tieu de goc cua bao nuoc ngoai — bao "mat dau" cho mot cau
tieng Anh la bao nham moi bai. Khac biet nay la co y, khong phai lech.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common                                           # noqa: E402

TOI_DA_TU_TOM_TAT = 15          # brief cua ca ba vai hua "mot menh de <= 15 tu"
_EM_DASH = re.compile(r"\s*[—–]\s*")


def chon_theo_k(k_tho, danh_sach: list, nhan: str) -> tuple:
    """`k` (so thu tu 1..n trong brief) -> muc trong danh sach nguon.

    Tra ve (muc, loi). `muc` None kem `loi` la mot chuoi khi k ngoai dai.
    Vai chon bang SO chu khong chep URL (tu 05/09/2026): chep sai mot ky tu la
    "khong tim thay", da mat 4/8 muc trong mot lan quet.
    """
    try:
        k = int(k_tho)
    except (TypeError, ValueError):
        k = 0
    if 1 <= k <= len(danh_sach):
        return danh_sach[k - 1], None
    return None, f"{nhan}: k={k_tho} ngoai danh sach 1..{len(danh_sach)}"


def don_tom_tat(tom, nhan: str) -> tuple:
    """Don `summary_vi` cua vai. Tra ve (tom_da_don, [canh bao]).

    Hai phep, dung cho MOI vai di tim tin:
      - em-dash -> dau phay. Headline la thu duy nhat Ong Chu doc tren topic,
        va em-dash o do lot tiep xuong caption bai dang.
      - dai qua 15 tu: chi CANH BAO, khong cat — tin van co gia tri.
    """
    tom = str(tom or "")
    canh = []
    if "—" in tom or "–" in tom:
        tom = _EM_DASH.sub(", ", tom)
        canh.append(f"summary_vi co em-dash -> doi thanh dau phay ({nhan})")
    so_tu = len(tom.split())
    if so_tu > TOI_DA_TU_TOM_TAT:
        # Nhan di kem CA HAI canh bao: ban cu cua nhanh Finn khong ghi bai nao,
        # nen tren mot bao cao 8 tin thi dong canh bao khong chi duoc ai.
        canh.append(f"summary_vi {so_tu} tu (> {TOI_DA_TU_TOM_TAT}), giu nguyen "
                    f"nhung nen rut ({nhan}): {tom[:60]}")
    return tom, canh


def danh_so(items: list) -> list:
    """Gan `index` 1..n theo dung thu tu hien tai cua danh sach."""
    for i, it in enumerate(items, 1):
        it["index"] = i
    return items


def duong_ra_moi(goc: Path) -> Path:
    """Ten khac cho ban ghi LAI trong ngay: `<goc>_tHHMMSS.<duoi>` (gio VN).

    KHONG ghi de ban da co: ghi de la mat co `picked`/`da_giao` ma
    `duyet_chon_tin` ghi nguoc vao chinh tep do, va TE HON la doi nghia so thu
    tu — muc "2" cua ban moi khac muc "2" ma Ong Chu dang nhin, tra loi "2" luc
    do ra dung bai khac.
    """
    # Den GIAY, va van kiem lai: ban cu lay UTC theo PHUT, nen hai lan chay
    # trong cung mot phut ra CUNG mot ten va ban sau DE LEN ban truoc — dung
    # cai ma docstring nay hua la khong lam. Da xay ra that 12/09/2026: ba lan
    # chay quet_nop cua Vera luc 22:01:10 / 22:01:48 / 22:02 (UTC) deu ghi vao
    # `vera_candidates_2026-09-11_t2201.json`, tuc bao cao dau tien gui len
    # topic tro toi mot tep ma noi dung da bi ban thu ba thay mat.
    goi = f"{goc.stem}_t{datetime.now(scan_common.VN).strftime('%H%M%S')}"
    ra = goc.with_name(f"{goi}{goc.suffix}")
    n = 2
    while ra.exists():
        ra = goc.with_name(f"{goi}-{n}{goc.suffix}")
        n += 1
    return ra


def ghi_manifest(out: Path, vai: str, items: list) -> None:
    """Khoa goc giong het nhau cho ca ba vai. Ba vai di tim tin phai ra cung
    mot dinh dang, khong moi noi mot kieu."""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"quet_luc": datetime.now(timezone.utc).isoformat(), "vai": vai,
         "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")


def chot_bat_buoc(vai_bb: str, items: list, bo_qua: bool) -> None:
    """Xoa cac muc BAT BUOC da thuc su vao manifest, va in con lai bao nhieu."""
    if bo_qua:
        return
    import bat_buoc
    da = bat_buoc.xoa(vai_bb, items)
    print(f"da xac nhan {da} muc bat buoc, con lai {len(bat_buoc.doc(vai_bb))}")


def viet_bao_cao(duong_dan, items: list, vai: str, ngay: str = None) -> None:
    """Bao cao do CHINH SCRIPT dung, khong de agent go lai so. Go lai la co hoi
    lech: so trong tin nhan mot dang, so trong manifest mot dang, Ong Chu tra
    loi so lai ra bai khac."""
    if not duong_dan:
        return
    import bao_cao_manifest
    vb = (bao_cao_manifest.dung(items, vai, ngay) if ngay
          else bao_cao_manifest.dung(items, vai))
    Path(duong_dan).write_text(vb, encoding="utf-8")
    print(f"  bao cao -> {duong_dan}", file=sys.stderr)
