#!/usr/bin/env python3
"""dre_nop.py — NOP carousel cua Dre: mot lenh lam het phan co hoc sau khi vai
da viet copy vao spec.json (khung do dre_chuan_bi.py in ra).

Vai chi dien CHU + MA ANH (A1, A2...). Tep nay:
  1. Doi ma anh -> tep da cat san (san/), hoac anh goc + "chart": true, hoac
     ghep doc hai anh ngang ("ghep"), hoac cat be ngang anh nguoi/san pham
     ("cat_ngang") qua crop_ti_le co dau vet.
  2. Kiem nhung loi ma vai hay mac TRUOC khi ve (ma anh sai, dung mot anh hai
     lan, chart lam bia, anh ngang khong ghep, mat nguoi khong khai nhan_vat,
     lam lai ma giu bia/hook cu) — bao gon, chi dung cho can sua.
  3. Xoa slide cu (lam lai ma it slide hon thi draft_write se gom nham slide
     thua vao album), chay carousel.py (moi cong chan chu/anh/bo cuc nam o do).
  4. Gui album len topic `carousel` kem nut Duyet (gui_telegram.post) — chong gui
     trung 30 phut co san ben do.
  5. Ghi ban giao cho Miles (`drafts/<id>.ban_giao.md`: link that, nguon tung
     anh) — approve_service dan vao task viet khi Ong Chu bam Duyet, vai khong
     phai "nhan Miles".
  6. Ghi da_dung.json de lan "Lam lai" bat buoc doi bia/hook.

Loi thi in [LOI] + cach sua, thoat 1; vai sua spec.json roi chay lai DUNG lenh.

Dung:
    venv/bin/python dre_nop.py <draft_id>                # spec o state/<brand>/chuan_bi/<id>/spec.json
    venv/bin/python dre_nop.py <draft_id> --khong-gui    # thu: dung slide, khong gui Telegram
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402
import env_load                                              # noqa: E402
import nop_chung as nc                                       # noqa: E402

DRAFTS = ROOT / "drafts"


def giai_spec(spec: dict, m: dict, wd: Path) -> tuple:
    """Dich spec cua vai (ma anh) -> spec cua carousel.py (duong dan). Tra ve
    (spec_carousel, loi, dung_anh) — dung_anh: [(slide_nhan, [ma...])]."""
    import luat_anh
    anh = {a["ma"]: a for a in m["anh"]}
    loi, da_dung, dung_anh = [], {}, []

    chu_bai = nc.chu_bai_cua(m, wd)

    def _lien_quan(ma_ds, nhan):
        rac = [ma for ma in ma_ds if anh[ma].get("lien_quan") is False]
        if rac:
            loi.append(f"{nhan}: {', '.join(rac)} bị đánh dấu KHÔNG LIÊN QUAN bài "
                       f"({'; '.join((anh[x].get('mo_ta') or '?')[:60] for x in rac)}) — "
                       "không dùng, chọn mã khác hoặc gộp ý/giảm slide")

    def _mat(ma_ds, muc, nhan):
        # Cong chan nam o nop_chung de Ethan dung chung dung mot ban (06/09/2026).
        loi.extend(nc.kiem_nhan_vat(anh, ma_ds, muc.get("nhan_vat"), chu_bai, f"{nhan}: "))

    def giai(muc: dict, nhan: str, la_bia: bool) -> dict | None:
        ra = {}
        ghep, ma = muc.get("ghep"), muc.get("anh")
        if ghep:
            if not isinstance(ghep, list) or len(ghep) != 2:
                loi.append(f"{nhan}: \"ghep\" phải là đúng 2 mã ảnh, vd [\"A3\", \"A5\"]")
                return None
            sai = [x for x in ghep if x not in anh]
            if sai:
                loi.append(f"{nhan}: mã ảnh không tồn tại: {', '.join(sai)} (có: {', '.join(anh)})")
                return None
            for x in ghep:
                if x in da_dung:
                    loi.append(f"{nhan}: {x} đã dùng ở {da_dung[x]} — mỗi ảnh đúng một slide")
                da_dung[x] = nhan
            _lien_quan(ghep, nhan)
            ims = [Image.open(anh[x]["goc"]).convert("RGB") for x in ghep]
            rc = 1 / sum(im.height / im.width for im in ims)
            if not (luat_anh.TI_LE_45 - luat_anh.DUNG_SAI_TI_LE <= rc
                    <= luat_anh.TI_LE_11 + luat_anh.DUNG_SAI_TI_LE):
                loi.append(f"{nhan}: ghép {ghep[0]}+{ghep[1]} ra tỉ lệ {rc:.2f}, ngoài dải 4:5..1:1 — "
                           f"chọn cặp khác (cặp gợi ý: {m.get('cap_ghep')})")
            if luat_anh.lech_tone(ims):
                loi.append(f"{nhan}: {ghep[0]} và {ghep[1]} lệch tone, ghép sẽ ra hai vùng — "
                           f"chọn cặp gợi ý: {m.get('cap_ghep')}")
            _mat(ghep, muc, nhan)
            ra["images"] = [anh[x]["goc"] for x in ghep]
            dung_anh.append((nhan, list(ghep)))
        elif ma:
            if ma not in anh:
                loi.append(f"{nhan}: mã ảnh không tồn tại: {ma} (có: {', '.join(anh)})")
                return None
            if ma in da_dung:
                loi.append(f"{nhan}: {ma} đã dùng ở {da_dung[ma]} — mỗi ảnh đúng một slide")
            da_dung[ma] = nhan
            _lien_quan([ma], nhan)
            a = anh[ma]
            if a["loai"] == "chart":
                if la_bia:
                    loi.append(f"bìa: {ma} là CHART/screenshot, hook đè lên là mất nửa dưới — "
                               "bìa dùng ảnh khác (gợi ý: "
                               f"{', '.join(m.get('goi_y_bia') or ['—'])}) hoặc \"ghep\" hai ảnh ngang")
                    return None
                ra["image"] = a["san"] or a["goc"]
                ra["chart"] = True
            elif a["ngang"]:
                if muc.get("cat_ngang") and a["h"] < 700:
                    loi.append(f"{nhan}: {ma} chỉ cao {a['h']}px, cắt dọc 4:5 còn ~{int(a['h']*0.8)}px "
                               "rồi phóng lên 1080 sẽ nhoè — chỉ dùng qua \"ghep\" hoặc bỏ")
                    return None
                if muc.get("cat_ngang"):
                    tam = muc.get("tam") or [0.5, 0.5]
                    out = wd / "san" / f"{ma}.ngang.png"
                    cb._luu_crop(Image.open(a["goc"]).convert("RGB"), out, "4:5",
                                 float(tam[0]), float(tam[1]), cat_ngang=True)
                    ra["image"] = str(out)
                else:
                    loi.append(f"{nhan}: {ma} là ảnh NGANG ({a['ti_le']}). Hai đường: "
                               f"\"ghep\": [\"{ma}\", \"<ảnh ngang cùng tone>\"] "
                               f"(cặp gợi ý: {m.get('cap_ghep') or 'không có'}), hoặc "
                               "\"cat_ngang\": true CHỈ KHI đây là ảnh người/sản phẩm không có chữ")
                    return None
            else:
                ra["image"] = a["san"]
            _mat([ma], muc, nhan)
            dung_anh.append((nhan, [ma]))
        else:
            loi.append(f"{nhan}: thiếu \"anh\": \"A?\" hoặc \"ghep\": [\"A?\", \"A?\"]")
            return None
        for k in ("nhan_vat", "text", "quote", "attrib", "hook", "category", "label"):
            if muc.get(k) is not None:
                ra[k] = muc[k]
        return ra

    cover = spec.get("cover") or {}
    slides = spec.get("slides") or []
    if not cover:
        loi.append("thiếu \"cover\"")
    if not slides:
        loi.append("thiếu \"slides\"")
    ra = {"tam_co": spec.get("tam_co") or ("flagship" if m.get("flagship") else None)}
    if not ra["tam_co"]:
        ra.pop("tam_co")
    nen = str(spec.get("nen") or "").strip().lower()
    if nen:
        import carousel
        if nen not in carousel.NEN:
            loi.append(f"\"nen\": \"{nen}\" không hợp lệ — chọn {' | '.join(carousel.NEN)}")
        else:
            ra["nen"] = nen
    c = giai(cover, "bìa", True) if cover else None
    if c is not None:
        if not str(c.get("hook") or "").strip():
            loi.append("bìa: thiếu \"hook\"")
        if not str(c.get("category") or "").strip():
            loi.append("bìa: thiếu \"category\" (MODEL RELEASE / PRODUCT / RESEARCH / FUNDING / "
                       "POLICY / EARNINGS / M&A ...)")
        ra["cover"] = c
    ra["slides"] = []
    for i, s in enumerate(slides, start=2):
        g = giai(s, f"slide {i}", False)
        if g is None:
            continue
        if not (str(g.get("text") or "").strip() or str(g.get("quote") or "").strip()):
            loi.append(f"slide {i}: cần \"text\" hoặc \"quote\"")
        # Quote con nguyen tieng Anh: cong chan tieng Viet cua card.py chi bat
        # "tieng Viet go mat dau", co y bo qua tieng Anh nen quote chua dich lot
        # thang len Telegram (06/09/2026).
        loi.extend(nc.kiem_quote_dich(g.get("quote"), f"slide {i}"))
        ra["slides"].append(g)
    n = len(slides) + 1
    if n < m.get("toi_thieu", 5):
        loi.append(f"chỉ {n} slide, tin này cần tối thiểu {m['toi_thieu']} (kể cả bìa) — "
                   "chia thêm tầng: con số, ý nghĩa, đối thủ, cái cần theo dõi")
    so_quote = sum(1 for s in slides if str(s.get("quote") or "").strip())
    if so_quote < 2:
        loi.append(f"chỉ {so_quote} slide quote, cần ≥ 2 — chọn 2 câu đắt nhất làm \"quote\"+\"attrib\"")
    # So tren slide co trong tu lieu khong (chi CANH BAO — doi don vi la thuong).
    chu_slide = " ".join(str(x.get(k) or "") for x in [cover] + list(slides)
                         for k in ("hook", "text", "quote", "label", "attrib"))
    canh = nc.kiem_so_tren_anh(chu_slide, m, wd)
    return ra, loi, canh, dung_anh


def don_slide_cu(stem: Path) -> None:
    """Xoa <id>_2..10.png va *.ghep.png cua lan truoc: draft_write gom
    thanh album, lan lam lai it slide hon se lot slide cu."""
    for p in list(env_load.album_phu(stem.name, stem.parent)) + \
            list(stem.parent.glob(stem.name + "*.ghep.png")):
        p.unlink(missing_ok=True)


def dung(spec_cs: dict, out: Path, brand: str, wd: Path, bo_qua_dau=False) -> tuple:
    """Chay carousel.py. Tra ve (ok, stdout, stderr)."""
    p = wd / "carousel.spec.json"
    p.write_text(json.dumps(spec_cs, ensure_ascii=False, indent=2), encoding="utf-8")
    args = [sys.executable, str(ROOT / "carousel.py"), "--spec", str(p),
            "--out", str(out), "--brand", brand]
    if bo_qua_dau:
        args.append("--bo-qua-dau")
    r = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    return r.returncode == 0, r.stdout, r.stderr


def ban_giao(m: dict, spec: dict, dung_anh: list, out: Path) -> str:
    anh = {a["ma"]: a for a in m["anh"]}
    L = [f"Nguồn tin: {m['title']}", f"Link gốc: {m['link']}"]
    if m.get("via"):
        L.append(f"Via: {m['via']}")
    L.append("Nguồn từng ảnh (ghi vào chú thích bài nếu lấy từ nhiều báo):")
    for nhan, ds in dung_anh:
        for ma in ds:
            a = anh[ma]
            L.append(f"- {nhan}: {ma} ← {a['mien'] or a['tu']}" +
                     (f" ({a['trang'][:100]})" if a.get("trang") else ""))
    L.append(f"Hook bìa: {(spec.get('cover') or {}).get('hook', '')}")
    L.append(f"Slide: {len(spec.get('slides') or []) + 1}, tệp: {out}")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop carousel cua Dre (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--spec", help="Tep spec (mac dinh state/<brand>/chuan_bi/<id>/spec.json)")
    ap.add_argument("--khong-gui", action="store_true", help="Chi dung slide, khong gui Telegram")
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="Tat cong tieng Viet (chi khi chu THAT SU la tieng Anh)")
    ap.add_argument("--out", help="Ghi slide ra cho khac (de thu, khong de len drafts/)")
    a = ap.parse_args()

    meta, brand, wd, m, spec, spec_path, da_dung = nc.nap(a.draft_id, a.spec, "dre_chuan_bi.py", "dre_nop.py")
    spec_cs, loi, canh, dung_anh = giai_spec(spec, m, wd)
    for c in canh:
        print(f"[CANH BAO] {c}")
    cover = spec.get("cover") or {}
    loi = nc.kiem_lam_lai(da_dung, "bìa", cover.get("anh"), cover.get("hook"), khoa_anh="bia") + loi
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        print(f"\nSua {spec_path} theo cac dong tren roi chay lai: "
              f"venv/bin/python dre_nop.py {a.draft_id}")
        return 1

    out = Path(a.out or meta.get("image") or str(DRAFTS / f"{a.draft_id}.png"))
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    don_slide_cu(stem)
    ok, so, se = dung(spec_cs, out, brand, wd, a.bo_qua_dau)
    if not ok:
        for dong in (se + "\n" + so).splitlines():
            if dong.startswith("[LOI]") or dong.startswith("[CANH BAO]"):
                print(dong)
        cuoi = [d for d in (se or so).strip().splitlines() if d.strip()]
        if cuoi and not cuoi[-1].startswith("["):
            print(f"[LOI] {cuoi[-1]}")
        print(f"\nSua {spec_path} (chi phan bi bao) roi chay lai: "
              f"venv/bin/python dre_nop.py {a.draft_id}")
        return 1
    for dong in se.splitlines():
        if dong.startswith("[CANH BAO]"):
            print(dong)

    n = len(spec_cs["slides"]) + 1
    files = [out] + [Path(f"{stem}_{i}.png") for i in range(2, n + 1)]
    thieu = [str(f) for f in files if not f.exists()]
    if thieu:
        sys.exit(f"[LOI] carousel.py bao xong nhung thieu tep: {thieu}")
    hook = (spec.get("cover") or {}).get("hook", "")
    mo_ta = f"Carousel {n} slide: {hook}"[:1000]

    bg = ban_giao(m, spec, dung_anh, out)
    bg_path = (wd if a.khong_gui else DRAFTS) / f"{a.draft_id}.ban_giao.md"
    bg_path.write_text(bg, encoding="utf-8")

    mid = None
    if a.khong_gui:
        print(f"[thu] khong gui Telegram (--khong-gui). {n} slide o {out.parent}")
    else:
        mid = nc.gui_album("carousel", files, mo_ta, a.draft_id, wd, da_dung,
                           {"bia": cover.get("anh"), "hook": hook,
                            "anh": [ma for _, ds in dung_anh for ma in ds]})
    nguon_anh = sorted({m_["mien"] or m_["tu"] for m_ in m["anh"]
                        if m_["ma"] in {ma for _, ds in dung_anh for ma in ds}})
    # Bang den (kanban swarm, 05/09): script ghi ban giao co cau truc len the goc
    # cua bai — code lam, LLM khong phai nho. Cung JSON nay in ra dong
    # "[metadata]" de Dre dan vao kanban_complete(metadata=...) -> Miles thay
    # trong "Parent task results". Best-effort: bang den hong khong hong bai.
    md = {"slide": n, "hook": hook, "nguon_anh": nguon_anh, "tep": str(out),
          "ban_giao": str(bg_path), "message_id": mid}
    if not a.khong_gui:
        nc.ghi_bang_den(a.draft_id, "anh", md, "dre")
    print(f"[xong] {n} slide -> {out}" + (f"; da gui topic carousel (message_id={mid}) kem nut duyet"
                                          if mid else "") +
          f"; ban giao cho Miles: {bg_path}")
    print("[metadata] " + json.dumps(md, ensure_ascii=False))
    print("Ket qua task (dung dong nay de ket thuc task): "
          f"Dựng {n} slide carousel “{hook}”, ảnh từ {', '.join(nguon_anh) or 'nguồn bài'}; "
          + ("đã gửi topic kèm nút duyệt, bàn giao nguồn cho Miles tự động." if mid
             else "chưa gửi (thử)."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
