#!/usr/bin/env python3
"""dre_submit.py — NOP carousel cua Dre: mot lenh lam het phan co hoc sau khi vai
da viet copy vao spec.json (khung do dre_prepare.py in ra).

Vai chi dien CHU + MA ANH (A1, A2...). Tep nay:
  1. Doi ma anh -> tep da cat san (ready/), hoac anh goc + "chart": true, hoac
     ghep doc hai anh ngang ("stack"), hoac cat be ngang anh nguoi/san pham
     ("landscape_crop") qua crop_ratio co dau vet.
  2. Kiem nhung loi ma vai hay mac TRUOC khi ve (ma anh sai, dung mot anh hai
     lan, chart lam bia, anh ngang khong ghep, mat nguoi khong khai subject,
     lam lai ma giu bia/hook cu) — bao gon, chi dung cho can sua.
  3. Xoa slide cu (lam lai ma it slide hon thi draft_write se gom nham slide
     thua vao album), chay carousel.py (moi cong chan chu/anh/bo cuc nam o do).
  4. Gui album len topic `carousel` kem nut Duyet (send_telegram.post) — chong gui
     trung 30 phut co san ben do.
  5. Ghi ban giao cho Miles (`drafts/<id>.handoff.md`: link that, nguon tung
     anh) — approve_service dan vao task viet khi Ong Chu bam Duyet, vai khong
     phai "nhan Miles".
  6. Ghi previous_submission.json de lan "Lam lai" bat buoc doi bia/hook.

Loi thi in [LOI] + cach sua, thoat 1; vai sua spec.json roi chay lai DUNG lenh.

Ten khoa/gia tri spec English tu LOW-248 (role_spec.py); spec cu doc qua role_spec.dre_spec.

Dung:
    venv/bin/python dre_submit.py <draft_id>                # spec o state/<brand>/prepare/<id>/spec.json
    venv/bin/python dre_submit.py <draft_id> --khong-gui    # thu: dung slide, khong gui Telegram
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
import manifest_values                                       # noqa: E402
import state_paths                                           # noqa: E402
import image_rules_dre                                       # noqa: E402
import role_spec                                             # noqa: E402

DRAFTS = ROOT / "drafts"


class Context:
    """Bo dem dung chung khi giai MOT spec: cac hang so cua bai, cong voi ba cai
    tich luy ma tung slide deu ghi vao (`loi`, `da_dung`, `dung_anh`).

    Vi sao la mot doi tuong chu khong phai bien cuc bo cua `resolve_spec`: phan
    giai mot slide dai 110 dong va co hai nhanh lon (ghep doc / anh don), nen no
    phai tach ra thanh ham rieng — ma tach ra thi ba cai tich luy do khong con
    la bien dong kin nua. Gom mot cho de khong phai truyen sau tham so lac nhau
    qua tung tang."""

    def __init__(self, m: dict, wd: Path):
        self.m, self.wd = m, wd
        self.anh = {a["id"]: a for a in m["images"]}
        self.chu_bai = nc.article_text_for(m, wd)
        self.loi = []
        self.canh = []                   # canh bao: in ra, khong chan
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
        # Cong chan nam o submit_common de Ethan dung chung dung mot ban (06/09/2026).
        # Rieng Dre (LOW-178): ten khai duoc doi chieu voi chu bai VA voi chu
        # thich/nhan nguoi cua chinh tam anh — bai ve Nvidia khong go "Jensen
        # Huang" nhung caption Wikimedia co, thi khong phai bia.
        chu_bai = self.chu_bai
        chung_cu = image_rules_dre.subject_evidence([self.anh.get(x) for x in ma_ds if x])
        if chu_bai and chung_cu:
            chu_bai = chu_bai + " " + chung_cu
        self.loi.extend(nc.check_subject_named(self.anh, ma_ds, muc.get("subject"),
                                         chu_bai, f"{nhan}: "))


def _resolve_stack(bo: Context, ghep, muc: dict, nhan: str) -> dict | None:
    """Nhanh "stack": hai anh NGANG chong doc thanh mot khung STACK_FLOOR..1:1."""
    if not isinstance(ghep, list) or len(ghep) != 2:
        bo.loi.append(f"{nhan}: \"stack\" phải là đúng 2 mã ảnh, vd [\"A3\", \"A5\"]")
        return None
    sai = [x for x in ghep if x not in bo.anh]
    if sai:
        bo.loi.append(f"{nhan}: mã ảnh không tồn tại: {', '.join(sai)} (có: {', '.join(bo.anh)})")
        return None
    for x in ghep:
        bo.nhan_ma(x, nhan)
    bo.kiem_lien_quan(ghep, nhan)
    r1, r2 = (im.width / im.height for im in
              (Image.open(bo.anh[x]["original_path"]) for x in ghep))
    if not image_rules_dre.stack_fit_frame(r1, r2):
        rc = image_rules_dre.ratio_after_stack(r1, r2)
        bo.loi.append(f"{nhan}: ghép {ghep[0]}+{ghep[1]} ra tỉ lệ {rc:.2f}, ngoài dải ghép "
                      f"{image_rules_dre.STACK_FLOOR}..1.0 — "
                      f"chọn cặp khác (cặp gợi ý: {bo.m.get('stackable_pairs')})")
    else:
        # Cao hon 4:5 mot chut la LOI NHO (Ong Chu 12/09/2026): bao de vai biet
        # mep nao bi cat, khong chan (LOW-178).
        nhac = image_rules_dre.stack_crop_note(r1, r2)
        if nhac:
            bo.canh.append(f"{nhan}: {nhac}")
    # Cong lech tone (`tone_mismatch`) da bo khoi he thong (Ong Chu
    # 13/09/2026): bo cam doan ve nguon/chat luong nay, moi vai.
    bo.kiem_mat(ghep, muc, nhan)
    bo.dung_anh.append((nhan, list(ghep)))
    return {"images": [bo.anh[x]["original_path"] for x in ghep]}


def _resolve_single(bo: Context, ma: str, muc: dict, nhan: str, la_bia: bool) -> dict | None:
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
    # (submit_common.needs_ranking_image — xem lich su hoi quy o do).
    if la_bia and nc.needs_ranking_image(m, a):
        bo.loi.append(f"bìa: TIN XẾP HẠNG mà bìa là {ma}, không phải bảng xếp hạng. "
                      f"Bìa dùng \"image\": \"XH\" — " + cb.describe_ranking_image(m) + ".")
    if la_bia:
        # So hang trong hook bia phai la so hang engine khoanh (LOW-24, chung voi Ethan).
        bo.loi.extend(nc.check_rank_matches_image(str(muc.get("hook") or ""), a, "bìa"))
    if a["kind"] == "chart" and not a.get("ranking"):
        # Do hoa ROI lam bia duoc (LOW-47): carousel hien nguyen be ngang, nen chu
        # dac phu nua duoi — khong con "hook de len mat nua duoi" nua.
        if la_bia and a.get("cluttered"):
            ra["image"] = a["original_path"]
        elif la_bia:
            bo.loi.append(f"bìa: {ma} là CHART/screenshot, hook đè lên là mất nửa dưới — "
                          "bìa dùng ảnh khác (gợi ý: "
                          f"{', '.join(m.get('cover_suggestions') or ['—'])}) hoặc \"stack\" hai ảnh ngang")
            return None
        else:
            ra["image"] = a["ready_path"] or a["original_path"]
            ra["chart"] = True
    elif a.get("ranking"):
        # Anh xep hang: bia/slide deu dan NGUYEN VEN full be ngang (nhu chart),
        # va duoc phep lam bia — hook de len nua duoi, bang o nua tren.
        ra["image"] = a["ready_path"] or a["original_path"]
        if not la_bia:
            ra["chart"] = True
    elif a["landscape"]:
        if muc.get("landscape_crop") and a["h"] < schema.HEIGHT_MIN_CROP_LANDSCAPE:
            bo.loi.append(f"{nhan}: {ma} chỉ cao {a['h']}px, cắt dọc 4:5 còn ~{int(a['h']*0.8)}px "
                          "rồi phóng lên 1080 sẽ nhoè — chỉ dùng qua \"stack\" hoặc bỏ")
            return None
        if muc.get("landscape_crop"):
            tam = muc.get("crop_center") or [0.5, 0.5]
            out = bo.wd / state_paths.READY_DIR / f"{ma}{state_paths.LANDSCAPE_SUFFIX}"
            cb._save_crop(Image.open(a["original_path"]).convert("RGB"), out, "4:5",
                         float(tam[0]), float(tam[1]), cat_ngang=True)
            ra["image"] = str(out)
        else:
            bo.loi.append(f"{nhan}: {ma} là ảnh NGANG ({a['ratio']}). Hai đường: "
                          f"\"stack\": [\"{ma}\", \"<ảnh ngang cùng tone>\"] "
                          f"(cặp gợi ý: {m.get('stackable_pairs') or 'không có'}), hoặc "
                          "\"landscape_crop\": true CHỈ KHI đây là ảnh người/sản phẩm không có chữ")
            return None
    else:
        ra["image"] = a["ready_path"]
    bo.kiem_mat([ma], muc, nhan)
    bo.dung_anh.append((nhan, [ma]))
    return ra


# Cac truong CHU vai viet, di thang sang spec cua carousel.py khong doi.
TEXT_KEEP = ("subject", "text", "quote", "attrib", "hook", "category", "label")


def _resolve_item(bo: Context, muc: dict, nhan: str, la_bia: bool) -> dict | None:
    """Mot muc cua vai (bia hoac mot slide) -> mot muc cua carousel.py."""
    ghep, ma = muc.get("stack"), muc.get("image")
    if ghep:
        ra = _resolve_stack(bo, ghep, muc, nhan)
    elif ma:
        ra = _resolve_single(bo, ma, muc, nhan, la_bia)
    else:
        bo.loi.append(f"{nhan}: thiếu \"image\": \"A?\" hoặc \"stack\": [\"A?\", \"A?\"]")
        return None
    if ra is None:
        return None
    # Anh roi buoc phai dung: carousel.py dat nen chu dac thay lop mo (LOW-47).
    if any((bo.anh.get(x) or {}).get("cluttered") for x in (list(ghep) if ghep else [ma])):
        ra["cluttered"] = True
    for k in TEXT_KEEP:
        if muc.get(k) is not None:
            ra[k] = muc[k]
    return ra


def resolve_spec(spec: dict, m: dict, wd: Path) -> tuple:
    """Dich spec cua vai (ma anh) -> spec cua carousel.py (duong dan). Tra ve
    (spec_carousel, loi, canh, dung_anh) — dung_anh: [(slide_nhan, [ma...])].
    `spec` da qua role_spec.dre_spec (ten moi, LOW-248).

    Tach thanh `_Boi` + `_resolve_stack`/`_resolve_single`/`_resolve_item` ngay 07/09/2026:
    ban cu la 166 dong voi 36 nhanh trong mot ham, va la cho DUY NHAT kiem spec
    cua Dre truoc khi ve. Phan lon luat trong day la luat Ong Chu dat sau mot su
    co that, ma khong luat nao co test — `test_cong_chan` nhac `bob_submit` 19 lan,
    `dre_submit` mot lan. Nay o `tests/test_spec_dre.py`.
    """
    bo = Context(m, wd)
    loi = bo.loi

    cover = spec.get("cover") or {}
    slides = spec.get("slides") or []
    if not cover:
        loi.append("thiếu \"cover\"")
    if not slides:
        loi.append("thiếu \"slides\"")
    ra = {"tier": spec.get("tier") or ("flagship" if m.get("flagship") else None)}
    if not ra["tier"]:
        ra.pop("tier")
    nen = str(spec.get("background_tone") or "").strip().lower()
    if nen:
        import carousel
        if nen not in carousel.BACKGROUND:
            loi.append(f"\"background_tone\": \"{nen}\" không hợp lệ — chọn {' | '.join(carousel.BACKGROUND)}")
        else:
            ra["background_tone"] = nen
    c = _resolve_item(bo, cover, "bìa", True) if cover else None
    if c is not None:
        if not str(c.get("hook") or "").strip():
            loi.append("bìa: thiếu \"hook\"")
        if not str(c.get("category") or "").strip():
            loi.append("bìa: thiếu \"category\" (MODEL RELEASE / PRODUCT / RESEARCH / FUNDING / "
                       "POLICY / EARNINGS / M&A ...)")
        ra["cover"] = c
    ra["slides"] = []
    for i, s in enumerate(slides, start=2):
        g = _resolve_item(bo, s, f"slide {i}", False)
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
    toi_thieu = m.get("min_images", 5)
    if n < toi_thieu:
        # Doc MOT lan: truoc day vao nhanh bang `.get(..., 5)` roi trong than lai
        # doc `m["min_images"]` tho — thieu khoa va n < 5 la KeyError ngay giua
        # cong chan, khong phai loi noi dung (F2).
        loi.append(f"chỉ {n} slide, tin này cần tối thiểu {toi_thieu} (kể cả bìa) — "
                   "chia thêm tầng: con số, ý nghĩa, đối thủ, cái cần theo dõi")
    so_quote = sum(1 for s in slides if str(s.get("quote") or "").strip())
    if so_quote < 2:
        loi.append(f"chỉ {so_quote} slide quote, cần ≥ 2 — chọn 2 câu đắt nhất làm \"quote\"+\"attrib\"")
    # So tren slide co trong tu lieu khong (chi CANH BAO — doi don vi la thuong).
    chu_slide = " ".join(str(x.get(k) or "") for x in [cover] + list(slides)
                         for k in ("hook", "text", "quote", "label", "attrib"))
    canh = bo.canh + nc.check_numbers_on_card(chu_slide, m, wd)
    # LAM LAI mot slide cu the nhung van ra dung anh cu (Ong Chu 13/09/2026) —
    # dat SAU khi bia + moi slide da giai, luc bo.dung_anh da co du (nhan, ma).
    loi += nc.check_no_repeat_image_redo(bo.anh, bo.dung_anh, m, DRAFTS)
    # Anh roi chi dung khi het anh sach (LOW-47) — sau khi moi slide da giai.
    loi += nc.check_image_fall(bo.anh, bo.da_dung, m)
    return ra, loi, canh, bo.dung_anh


def single_slide_old(stem: Path) -> None:
    """Xoa <id>_2..10.png va *.ghep.png cua lan truoc: draft_write gom
    thanh album, lan lam lai it slide hon se lot slide cu."""
    for p in list(env_load.album_secondary(stem.name, stem.parent)) + \
            list(stem.parent.glob(stem.name + "*.ghep.png")):
        p.unlink(missing_ok=True)


def use(spec_cs: dict, out: Path, brand: str, wd: Path, bo_qua_dau=False) -> tuple:
    """Chay carousel.py. Tra ve (ok, stdout, stderr)."""
    p = wd / "carousel.spec.json"
    p.write_text(json.dumps(spec_cs, ensure_ascii=False, indent=2), encoding="utf-8")
    args = [sys.executable, str(ROOT / "carousel.py"), "--spec", str(p),
            "--out", str(out), "--brand", brand]
    if bo_qua_dau:
        args.append("--bo-qua-dau")
    r = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    return r.returncode == 0, r.stdout, r.stderr


def handoff(m: dict, spec: dict, dung_anh: list, out: Path) -> str:
    anh = {a["id"]: a for a in m["images"]}
    L = [f"Nguồn tin: {m['title']}", f"Link gốc: {m['link']}"]
    if m.get("via"):
        L.append(f"Via: {m['via']}")
    L.append("Nguồn từng ảnh (ghi vào chú thích bài nếu lấy từ nhiều báo):")
    for nhan, ds in dung_anh:
        for ma in ds:
            a = anh[ma]
            L.append(f"- {nhan}: {ma} ← {a['domain'] or manifest_values.source_label(a['source'])}" +
                     (f" ({a['page_url'][:100]})" if a.get("page_url") else ""))
    L.append(f"Hook bìa: {(spec.get('cover') or {}).get('hook', '')}")
    L.append(f"Slide: {len(spec.get('slides') or []) + 1}, tệp: {out}")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop carousel cua Dre (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--spec", help="Tep spec (mac dinh state/<brand>/prepare/<id>/spec.json)")
    ap.add_argument("--khong-gui", action="store_true", help="Chi dung slide, khong gui Telegram")
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="Tat cong tieng Viet (chi khi chu THAT SU la tieng Anh)")
    ap.add_argument("--out", help="Ghi slide ra cho khac (de thu, khong de len drafts/)")
    a = ap.parse_args()
    import role
    role.set_active_role("dre")

    meta, brand, wd, m, spec, spec_path, da_dung = nc.load_draft_context(a.draft_id, a.spec, "dre_prepare.py", "dre_submit.py")
    spec = role_spec.dre_spec(spec)          # LOW-248: spec viet truoc deploy con ten cu
    spec_cs, loi, canh, dung_anh = resolve_spec(spec, m, wd)
    for c in canh:
        print(f"[CANH BAO] {c}")
    cover = spec.get("cover") or {}
    # LOW-146: khi bai chi co DUNG MOT anh xep hang va needs_ranking_image dang ep
    # bia phai la no, khong bao "lam lai ma van giu bia cu" — khong con anh nao
    # khac de doi (xem submit_common.only_ranking_choice).
    bat_buoc = cover.get("image") is not None and cover.get("image") == nc.only_ranking_choice(m)
    loi = nc.check_redo_reused(da_dung, "bìa", cover.get("image") or "+".join(cover.get("stack") or []),
                          cover.get("hook"), khoa_anh="cover_image", draft_id=a.draft_id,
                          anh_bat_buoc=bat_buoc) + loi
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return nc.count_round_error(wd, loi,
                               f"venv/bin/python dre_submit.py {a.draft_id}")

    out = Path(a.out or meta.get("image") or str(DRAFTS / f"{a.draft_id}.png"))
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    single_slide_old(stem)
    ok, so, se = use(spec_cs, out, brand, wd, a.bo_qua_dau)
    if not ok:
        for dong in (se + "\n" + so).splitlines():
            if dong.startswith("[LOI]") or dong.startswith("[CANH BAO]"):
                print(dong)
        cuoi = [d for d in (se or so).strip().splitlines() if d.strip()]
        if cuoi and not cuoi[-1].startswith("["):
            print(f"[LOI] {cuoi[-1]}")
        print(f"\nSua {spec_path} (chi phan bi bao) roi chay lai: "
              f"venv/bin/python dre_submit.py {a.draft_id}")
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

    bg = handoff(m, spec, dung_anh, out)
    bg_path = state_paths.handoff_file(wd if a.khong_gui else DRAFTS, a.draft_id)
    bg_path.write_text(bg, encoding="utf-8")

    mid = None
    if a.khong_gui:
        print(f"[thu] khong gui Telegram (--khong-gui). {n} slide o {out.parent}")
    else:
        mid = nc.send_album("dre", files, mo_ta, a.draft_id, wd, da_dung,
                           {"cover_image": cover.get("image"), "hook": hook,
                            "image_ids": [ma for _, ds in dung_anh for ma in ds]})
    nguon_anh = sorted({m_["domain"] or manifest_values.source_label(m_["source"]) for m_ in m["images"]
                        if m_["id"] in {ma for _, ds in dung_anh for ma in ds}})
    # Bang den (kanban swarm, 05/09): script ghi ban giao co cau truc len the goc
    # cua bai — code lam, LLM khong phai nho. Cung JSON nay in ra dong
    # "[metadata]" de Dre dan vao kanban_complete(metadata=...) -> Miles thay
    # trong "Parent task results". Best-effort: bang den hong khong hong bai.
    md = {"slide": n, "hook": hook, "image_sources": nguon_anh, "file_path": str(out),
          "handoff_path": str(bg_path), "message_id": mid}
    if not a.khong_gui:
        nc.write_blackboard(a.draft_id, "images", md, "dre")
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
