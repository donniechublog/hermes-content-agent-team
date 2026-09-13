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
import image_prepare as cb                                    # noqa: E402
import env_load                                              # noqa: E402
import submit_common as nc                                       # noqa: E402
import schema                                                # noqa: E402

DRAFTS = ROOT / "drafts"


class _Boi:
    """Bo dem dung chung khi giai MOT spec: cac hang so cua bai, cong voi ba cai
    tich luy ma tung slide deu ghi vao (`loi`, `da_dung`, `dung_anh`).

    Vi sao la mot doi tuong chu khong phai bien cuc bo cua `giai_spec`: phan
    giai mot slide dai 110 dong va co hai nhanh lon (ghep doc / anh don), nen no
    phai tach ra thanh ham rieng — ma tach ra thi ba cai tich luy do khong con
    la bien dong kin nua. Gom mot cho de khong phai truyen sau tham so lac nhau
    qua tung tang."""

    def __init__(self, m: dict, wd: Path):
        self.m, self.wd = m, wd
        self.anh = {a["ma"]: a for a in m["anh"]}
        self.chu_bai = nc.article_text_for(m, wd)
        self.loi = []
        self.da_dung = {}                # ma anh -> nhan slide da dung no
        self.dung_anh = []               # [(nhan slide, [ma...])]

    def nhan_ma(self, ma: str, nhan: str) -> None:
        """Ghi nhan mot ma da duoc dung o `nhan`, va bao neu no dung hai lan."""
        if ma in self.da_dung:
            self.loi.append(f"{nhan}: {ma} đã dùng ở {self.da_dung[ma]} — mỗi ảnh đúng một slide")
        self.da_dung[ma] = nhan

    def kiem_lien_quan(self, ma_ds, nhan: str) -> None:
        rac, mo_ta = nc.irrelevant_images(self.anh, ma_ds)
        if rac:
            self.loi.append(
                f"{nhan}: {', '.join(rac)} bị đánh dấu KHÔNG LIÊN QUAN bài ({mo_ta}) — "
                "không dùng, chọn mã khác hoặc gộp ý/giảm slide")

    def kiem_mat(self, ma_ds, muc: dict, nhan: str) -> None:
        # Cong chan nam o nop_chung de Ethan dung chung dung mot ban (06/09/2026).
        self.loi.extend(nc.check_subject_named(self.anh, ma_ds, muc.get("nhan_vat"),
                                         self.chu_bai, f"{nhan}: "))


def _giai_ghep(bo: _Boi, ghep, muc: dict, nhan: str) -> dict | None:
    """Nhanh "ghep": hai anh NGANG chong doc thanh mot khung 4:5..1:1."""
    import image_rules
    if not isinstance(ghep, list) or len(ghep) != 2:
        bo.loi.append(f"{nhan}: \"ghep\" phải là đúng 2 mã ảnh, vd [\"A3\", \"A5\"]")
        return None
    sai = [x for x in ghep if x not in bo.anh]
    if sai:
        bo.loi.append(f"{nhan}: mã ảnh không tồn tại: {', '.join(sai)} (có: {', '.join(bo.anh)})")
        return None
    for x in ghep:
        bo.nhan_ma(x, nhan)
    bo.kiem_lien_quan(ghep, nhan)
    ims = [Image.open(bo.anh[x]["goc"]).convert("RGB") for x in ghep]
    rc = 1 / sum(im.height / im.width for im in ims)
    if not (image_rules.TI_LE_45 - image_rules.TOLERANCE_RATIO <= rc
            <= image_rules.TI_LE_11 + image_rules.TOLERANCE_RATIO):
        bo.loi.append(f"{nhan}: ghép {ghep[0]}+{ghep[1]} ra tỉ lệ {rc:.2f}, ngoài dải 4:5..1:1 — "
                      f"chọn cặp khác (cặp gợi ý: {bo.m.get('cap_ghep')})")
    # Cong lech tone (`luat_anh.lech_tone`) da bo khoi he thong (Ong Chu
    # 13/09/2026): bo cam doan ve nguon/chat luong nay, moi vai.
    bo.kiem_mat(ghep, muc, nhan)
    bo.dung_anh.append((nhan, list(ghep)))
    return {"images": [bo.anh[x]["goc"] for x in ghep]}


def _giai_don(bo: _Boi, ma: str, muc: dict, nhan: str, la_bia: bool) -> dict | None:
    """Nhanh mot ma anh: chon ban dung (goc / da cat san / cat ngang) va chan
    cac cach dung sai loai anh."""
    m = bo.m
    if ma not in bo.anh:
        bo.loi.append(f"{nhan}: mã ảnh không tồn tại: {ma} (có: {', '.join(bo.anh)})")
        return None
    bo.nhan_ma(ma, nhan)
    bo.kiem_lien_quan([ma], nhan)
    a, ra = bo.anh[ma], {}
    # Dieu kien "tin xep hang ma bia khong phai bang" dung chung voi Ethan
    # (nop_chung.can_anh_xep_hang — xem lich su hoi quy o do).
    if la_bia and nc.needs_ranking_image(m, a):
        bo.loi.append(f"bìa: TIN XẾP HẠNG mà bìa là {ma}, không phải bảng xếp hạng. "
                      f"Bìa dùng \"anh\": \"XH\" — " + cb.describe_ranking_image(m) + ".")
    if la_bia:
        # So hang trong hook bia phai la so hang engine khoanh (LOW-24, chung voi Ethan).
        bo.loi.extend(nc.check_rank_matches_image(str(muc.get("hook") or ""), a, "bìa"))
    if a["loai"] == "chart" and not a.get("xep_hang"):
        # Do hoa ROI lam bia duoc (LOW-47): carousel hien nguyen be ngang, nen chu
        # dac phu nua duoi — khong con "hook de len mat nua duoi" nua.
        if la_bia and a.get("roi"):
            ra["image"] = a["goc"]
        elif la_bia:
            bo.loi.append(f"bìa: {ma} là CHART/screenshot, hook đè lên là mất nửa dưới — "
                          "bìa dùng ảnh khác (gợi ý: "
                          f"{', '.join(m.get('goi_y_bia') or ['—'])}) hoặc \"ghep\" hai ảnh ngang")
            return None
        else:
            ra["image"] = a["san"] or a["goc"]
            ra["chart"] = True
    elif a.get("xep_hang"):
        # Anh xep hang: bia/slide deu dan NGUYEN VEN full be ngang (nhu chart),
        # va duoc phep lam bia — hook de len nua duoi, bang o nua tren.
        ra["image"] = a["san"] or a["goc"]
        if not la_bia:
            ra["chart"] = True
    elif a["ngang"]:
        if muc.get("cat_ngang") and a["h"] < schema.HEIGHT_MIN_CROP_LANDSCAPE:
            bo.loi.append(f"{nhan}: {ma} chỉ cao {a['h']}px, cắt dọc 4:5 còn ~{int(a['h']*0.8)}px "
                          "rồi phóng lên 1080 sẽ nhoè — chỉ dùng qua \"ghep\" hoặc bỏ")
            return None
        if muc.get("cat_ngang"):
            tam = muc.get("tam") or [0.5, 0.5]
            out = bo.wd / "san" / f"{ma}.ngang.png"
            cb._save_crop(Image.open(a["goc"]).convert("RGB"), out, "4:5",
                         float(tam[0]), float(tam[1]), cat_ngang=True)
            ra["image"] = str(out)
        else:
            bo.loi.append(f"{nhan}: {ma} là ảnh NGANG ({a['ti_le']}). Hai đường: "
                          f"\"ghep\": [\"{ma}\", \"<ảnh ngang cùng tone>\"] "
                          f"(cặp gợi ý: {m.get('cap_ghep') or 'không có'}), hoặc "
                          "\"cat_ngang\": true CHỈ KHI đây là ảnh người/sản phẩm không có chữ")
            return None
    else:
        ra["image"] = a["san"]
    bo.kiem_mat([ma], muc, nhan)
    bo.dung_anh.append((nhan, [ma]))
    return ra


# Cac truong CHU vai viet, di thang sang spec cua carousel.py khong doi.
CHU_GIU = ("nhan_vat", "text", "quote", "attrib", "hook", "category", "label")


def _giai_muc(bo: _Boi, muc: dict, nhan: str, la_bia: bool) -> dict | None:
    """Mot muc cua vai (bia hoac mot slide) -> mot muc cua carousel.py."""
    ghep, ma = muc.get("ghep"), muc.get("anh")
    if ghep:
        ra = _giai_ghep(bo, ghep, muc, nhan)
    elif ma:
        ra = _giai_don(bo, ma, muc, nhan, la_bia)
    else:
        bo.loi.append(f"{nhan}: thiếu \"anh\": \"A?\" hoặc \"ghep\": [\"A?\", \"A?\"]")
        return None
    if ra is None:
        return None
    # Anh roi buoc phai dung: carousel.py dat nen chu dac thay lop mo (LOW-47).
    if any((bo.anh.get(x) or {}).get("roi") for x in (list(ghep) if ghep else [ma])):
        ra["roi"] = True
    for k in CHU_GIU:
        if muc.get(k) is not None:
            ra[k] = muc[k]
    return ra


def giai_spec(spec: dict, m: dict, wd: Path) -> tuple:
    """Dich spec cua vai (ma anh) -> spec cua carousel.py (duong dan). Tra ve
    (spec_carousel, loi, canh, dung_anh) — dung_anh: [(slide_nhan, [ma...])].

    Tach thanh `_Boi` + `_giai_ghep`/`_giai_don`/`_giai_muc` ngay 07/09/2026:
    ban cu la 166 dong voi 36 nhanh trong mot ham, va la cho DUY NHAT kiem spec
    cua Dre truoc khi ve. Phan lon luat trong day la luat Ong Chu dat sau mot su
    co that, ma khong luat nao co test — `test_cong_chan` nhac `bob_nop` 19 lan,
    `dre_nop` mot lan. Nay o `tests/test_spec_dre.py`.
    """
    bo = _Boi(m, wd)
    loi = bo.loi

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
    c = _giai_muc(bo, cover, "bìa", True) if cover else None
    if c is not None:
        if not str(c.get("hook") or "").strip():
            loi.append("bìa: thiếu \"hook\"")
        if not str(c.get("category") or "").strip():
            loi.append("bìa: thiếu \"category\" (MODEL RELEASE / PRODUCT / RESEARCH / FUNDING / "
                       "POLICY / EARNINGS / M&A ...)")
        ra["cover"] = c
    ra["slides"] = []
    for i, s in enumerate(slides, start=2):
        g = _giai_muc(bo, s, f"slide {i}", False)
        if g is None:
            continue
        if not (str(g.get("text") or "").strip() or str(g.get("quote") or "").strip()):
            loi.append(f"slide {i}: cần \"text\" hoặc \"quote\"")
        # Quote con nguyen tieng Anh: cong chan tieng Viet cua card.py chi bat
        # "tieng Viet go mat dau", co y bo qua tieng Anh nen quote chua dich lot
        # thang len Telegram (06/09/2026).
        loi.extend(nc.check_quote_translated(g.get("quote"), f"slide {i}"))
        # Dan nguon gon: khong "doc bai"/"xem bai", khong duoi ten mien — Ong
        # Chu 13/09/2026, nen tang quet ten mien thanh lien ket, giam hien thi.
        loi.extend(nc.check_guide_source_compact(g.get("attrib"), f"slide {i} (attrib)"))
        loi.extend(nc.check_guide_source_compact(g.get("text"), f"slide {i} (text)"))
        ra["slides"].append(g)
    # KHONG DUNG LAI ANH DA DUNG (lien phien, dHash) — Ong Chu 06/09/2026. Dat SAU
    # khi bia + moi slide da giai, luc `da_dung` da co du ma.
    loi += nc.check_not_reused_across_runs(bo.anh, [(f"{n} ({ma})", ma) for ma, n in bo.da_dung.items()], m)
    n = len(slides) + 1
    toi_thieu = m.get("toi_thieu", 5)
    if n < toi_thieu:
        # Doc MOT lan: truoc day vao nhanh bang `.get(..., 5)` roi trong than lai
        # doc `m["toi_thieu"]` tho — thieu khoa va n < 5 la KeyError ngay giua
        # cong chan, khong phai loi noi dung (F2).
        loi.append(f"chỉ {n} slide, tin này cần tối thiểu {toi_thieu} (kể cả bìa) — "
                   "chia thêm tầng: con số, ý nghĩa, đối thủ, cái cần theo dõi")
    so_quote = sum(1 for s in slides if str(s.get("quote") or "").strip())
    if so_quote < 2:
        loi.append(f"chỉ {so_quote} slide quote, cần ≥ 2 — chọn 2 câu đắt nhất làm \"quote\"+\"attrib\"")
    # So tren slide co trong tu lieu khong (chi CANH BAO — doi don vi la thuong).
    chu_slide = " ".join(str(x.get(k) or "") for x in [cover] + list(slides)
                         for k in ("hook", "text", "quote", "label", "attrib"))
    canh = nc.check_numbers_on_card(chu_slide, m, wd)
    # LAM LAI mot slide cu the nhung van ra dung anh cu (Ong Chu 13/09/2026) —
    # dat SAU khi bia + moi slide da giai, luc bo.dung_anh da co du (nhan, ma).
    loi += nc.check_no_repeat_image_redo(bo.anh, bo.dung_anh, m, DRAFTS)
    # Anh roi chi dung khi het anh sach (LOW-47) — sau khi moi slide da giai.
    loi += nc.check_image_fall(bo.anh, bo.da_dung, m)
    return ra, loi, canh, bo.dung_anh


def don_slide_cu(stem: Path) -> None:
    """Xoa <id>_2..10.png va *.ghep.png cua lan truoc: draft_write gom
    thanh album, lan lam lai it slide hon se lot slide cu."""
    for p in list(env_load.album_secondary(stem.name, stem.parent)) + \
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

    meta, brand, wd, m, spec, spec_path, da_dung = nc.load_draft_context(a.draft_id, a.spec, "dre_chuan_bi.py", "dre_nop.py")
    spec_cs, loi, canh, dung_anh = giai_spec(spec, m, wd)
    for c in canh:
        print(f"[CANH BAO] {c}")
    cover = spec.get("cover") or {}
    loi = nc.check_redo_reused(da_dung, "bìa", cover.get("anh") or "+".join(cover.get("ghep") or []),
                          cover.get("hook"), khoa_anh="bia", draft_id=a.draft_id) + loi
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return nc.count_round_error(wd, loi,
                               f"venv/bin/python dre_nop.py {a.draft_id}")

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
        mid = nc.send_album("dre", files, mo_ta, a.draft_id, wd, da_dung,
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
        nc.write_blackboard(a.draft_id, "anh", md, "dre")
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
