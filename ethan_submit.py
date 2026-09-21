#!/usr/bin/env python3
"""ethan_submit.py — NOP hero card cua Ethan: mot lenh lam het phan co hoc sau khi
vai da viet spec.json (khung do ethan_prepare.py in ra).

  1. Doi ma anh -> tep goc (card.py tu fit kho 4:5); `image2` -> --image2 (ghep
     doc, card kiem tone); `subject` -> --nhan-vat; `card_style` -> --kieu.
  2. Chan som loi hay mac: ma anh sai, chart/anh ngang >1.6 ma khong co image2,
     mat nguoi khong khai, lam lai ma giu anh/hook cu.
  3. Chay card.py (moi cong chan chu/anh nam o do), gui anh len topic `designer`
     kem nut Duyet, ghi ban giao cho Miles, ghi previous_submission.json.

Ten khoa/gia tri spec English tu LOW-248 (role_spec.py); spec cu doc qua role_spec.ethan_spec.

Dung:
    venv/bin/python ethan_submit.py <draft_id>
    venv/bin/python ethan_submit.py <draft_id> --khong-gui --out /tmp/x.png   # thu
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                    # noqa: E402
import ethan_prepare as eb                                  # noqa: E402
import submit_common as nc                                       # noqa: E402
import manifest_values                                       # noqa: E402
import state_paths                                            # noqa: E402
import role_spec                                             # noqa: E402

DRAFTS = cb.DRAFTS


def _check_stack(a: dict, ma: str, ma2, anh: dict, m: dict, loi: list) -> None:
    """Anh di mot minh duoc khong, va ghep voi "image2" co hop le khong.

    (13/09/2026: bo dieu kien "anh qua ngang phai ghep"/"ghep roi van qua
    ngang" — tuong duong `kiem_anh_thap`, da bo khoi he thong, moi
    vai. Chi con giu: chart la chu the (khong bi keo di ghep NEU la xep hang),
    va ghep doc chi hop khi CA HAI anh deu ngang (rang buoc cau truc cua chinh
    co che ghep, khong phai cam doan ve chat luong/nguon)."""
    can_ghep = a["kind"] == "chart" and not a.get("ranking")
    if can_ghep and not ma2:
        cap = eb.stackable_pairs_hero(m)
        loi.append(f"{ma} là CHART — card.py chặn một mình. Thêm \"image2\" (cặp gợi ý: "
                   f"{cap or 'không có'}) hoặc chọn ảnh khác")
    if ma2:
        b = anh[ma2]
        if b["ratio"] < 1.2 or a["ratio"] < 1.2:
            loi.append(f"ghép dọc chỉ dành cho hai ảnh NGANG (≥1.2); {ma}={a['ratio']}, {ma2}={b['ratio']}")


def _check_text(spec: dict, kieu: str, loi: list) -> None:
    """Truong chu bat buoc theo kieu the: quote can hook/tagline/attrib, full_bleed
    can mot cau title tron ven."""
    if kieu == "quote":
        if not str(spec.get("hook") or "").strip():
            loi.append("thiếu \"hook\"")
        if not str(spec.get("tagline") or "").strip():
            loi.append("thiếu \"tagline\" (chip category, ví dụ MODEL RELEASE)")
        at = str(spec.get("attrib") or "")
        if not at.strip():
            loi.append("thiếu \"attrib\" ('via <báo>' hoặc 'Phát biểu của <tên>, <hãng>')")
    else:
        if not str(spec.get("title") or "").strip():
            loi.append("kiểu full_bleed: thiếu \"title\" (một câu hoàn chỉnh)")
        # LOW-336: cum tu khoa to mau rieng phai NAM TRONG title — khong thi khong to duoc gi.
        hl = spec.get("highlight") or []
        if not isinstance(hl, list):
            loi.append("\"highlight\" phải là danh sách cụm từ, ví dụ [\"Cactus Compute\", \"Needle3\"]")
        else:
            tit = str(spec.get("title") or "").upper()
            for cum in hl:
                if str(cum).strip().upper() not in tit:
                    loi.append(f"\"highlight\": cụm {cum!r} không có trong title — chép đúng từ trong title")


def _check_subject_above_quote(spec: dict, kieu: str, a: dict, ma: str, ma2, m: dict) -> list:
    """CHU THE CHINH phai nam TREN khung chu cua the `quote` (LOW-273, Ong Chu 19/09/2026:
    "ko chap nhan nhung hinh nhu the nay o moi designer ... main character dat vua trong
    4:5"; slide loi: mat Altman nam duoi khung quote).

    Chi kieu `quote`: khung 4:5 khoa, chu + khung + chip ten kenh DE LEN anh. Kieu
    `full_bleed` (ti le tu do) dat chu DUOI anh nen khong bi. Vi tri khung tinh bang chinh
    ham ve (`card.quote_text_top`), anh dan full be ngang nhu `card._layer_image`.
    Khong ap cho chart/bang xep hang (bang trong anh chuan cua Kite cung chay xuong duoi
    chu) va cap ghep; chua do (manifest cu) thi khong chan."""
    if kieu != "quote" or ma2 or a.get("ranking") or a.get("kind") == "chart":
        return []
    import card
    import image_rules_ethan
    import subject_fit
    faces = image_rules_ethan.face_boxes(a["original_path"]) if a.get("faces") else None
    box = subject_fit.head_box(faces) if faces else a.get("subject_box")
    if not box:
        return []
    text_top, H = card.quote_text_top(str(spec.get("hook") or ""), str(spec.get("attrib") or ""),
                                      None, "4:5", m.get("brand") or "donniechublog")
    w, h = int(a.get("w") or 0), int(a.get("h") or 0)
    band = subject_fit.band_full_width(w, h, box, card.W, H, short_top_share=0)
    if not band:
        return []
    lim = text_top / H + image_rules_ethan.SUBJECT_TEXT_TOLERANCE
    if band[1] <= lim and band[0] >= -image_rules_ethan.SUBJECT_TEXT_TOLERANCE:
        return []
    chu_the = "khuôn mặt" if faces else manifest_values.subject_kind_label(a.get("subject_kind"))
    vi_tri = (f"kéo xuống tới {band[1]:.0%} khung, khung chữ bắt đầu ở {text_top / H:.0%}"
              if band[1] > lim else "bị cắt mất phần trên")
    return [f"{chu_the} của {ma} {vi_tri} — chữ/khung quote sẽ đè lên chủ thể. Đổi "
            "\"card_style\": \"full_bleed\" (chữ nằm DƯỚI ảnh), rút ngắn câu quote, hoặc dùng ảnh "
            "có chủ thể ở nửa trên"]


def resolve_spec(spec: dict, m: dict, wd) -> tuple:
    """Spec cua Ethan (ma anh) -> (ket_qua, loi, canh). Tach 07/09/2026: ba cong
    trung voi Dre (tin xep hang, khong lien quan, anh da dung) sang submit_common,
    phan ghep va phan chu thanh hai ham rieng. `spec` da qua role_spec.ethan_spec
    (ten moi, LOW-248)."""
    anh = {a["id"]: a for a in m["images"]}
    loi = []
    kieu = (spec.get("card_style") or "quote").strip().lower()
    if kieu not in role_spec.CARD_STYLES:
        loi.append("\"card_style\" phải là \"quote\" (mặc định) hoặc \"full_bleed\"")
    ma, ma2 = spec.get("image"), spec.get("image2")
    if not ma or ma not in anh:
        loi.append(f"\"image\" không tồn tại: {ma} (có: {', '.join(anh) or 'không có ảnh nào'})")
        return None, loi, []
    if ma2 and ma2 not in anh:
        loi.append(f"\"image2\" không tồn tại: {ma2}")
        ma2 = None
    if ma2 == ma:
        loi.append("\"image2\" trùng \"image\"")
        ma2 = None
    a = anh[ma]
    # TIN XEP HANG (Ong Chu 06/09/2026): anh chinh PHAI la anh xep hang (ma XH),
    # nhung CHI khi engine da CHUP duoc bang — xem submit_common.needs_ranking_image.
    if nc.needs_ranking_image(m, a):
        loi.append(f"TIN XẾP HẠNG mà \"image\" = {ma} không phải bảng xếp hạng. Dùng \"image\": \"XH\" — "
                   + cb.describe_ranking_image(m) + ".")
    _check_stack(a, ma, ma2, anh, m, loi)
    # ẢNH KHÔNG LIÊN QUAN BÀI (Ông Chủ bắt lỗi 06/09/2026) — điều kiện dùng chung
    # với Dre (submit_common.irrelevant_images), câu báo của Ethan dài hơn vì Ethan
    # hay đi tìm ảnh khác khi chart bị chặn một mình.
    rac, mo_ta = nc.irrelevant_images(anh, (ma, ma2))
    if rac:
        loi.append(f"{', '.join(rac)} bị vision đánh dấu KHÔNG LIÊN QUAN bài ({mo_ta}) — "
                   "không dùng. Tin xếp hạng/benchmark thì ẢNH ĐÚNG chính là bảng "
                   "xếp hạng của nguồn: engine đã chụp sẵn (mã loại chart), ghép "
                   "dọc với một ảnh ngang cùng tone qua \"image2\". Đừng đi tìm ảnh "
                   "khác chỉ vì chart bị chặn khi đi một mình.")

    # Mat nguoi: dung CHUNG cong chan voi Dre (submit_common.check_subject_named, 06/09/2026).
    loi.extend(nc.check_subject_named(anh, [ma, ma2], spec.get("subject"),
                                nc.article_text_for(m, wd), ""))
    _check_text(spec, kieu, loi)
    loi += nc.check_not_reused_across_runs(anh, [(x, x) for x in (ma, ma2) if x], m)
    loi += nc.check_image_fall(anh, {x: n for x, n in ((ma, "image"), (ma2, "image2")) if x}, m)
    # LOW-273: anh trong (logo nho tren nen tron) — "khong chap nhan o moi designer"
    import image_rules_ethan
    for x, n in ((ma, "image"), (ma2, "image2")):
        if x:
            loi += nc.check_empty_image(anh.get(x), n, image_rules_ethan.EMPTY_SHARE_MAX)
    loi += _check_subject_above_quote(spec, kieu, a, ma, ma2, m)
    # Hook/attrib con nguyen tieng Anh, va so tren the khong co trong tu lieu:
    # hai cong nay Dre da co tu 06/09/2026, Ethan dung chung o submit_common.
    hook_hay_title = str(spec.get("hook") or spec.get("title") or "")
    loi.extend(nc.check_quote_translated(hook_hay_title, "hook"))
    # So hang tren the phai la so hang trong anh (LOW-24) — dung chung voi bia Dre.
    loi.extend(nc.check_rank_matches_image(hook_hay_title, a, "hook"))
    # Dan nguon gon: khong "doc bai"/"xem bai", khong duoi ten mien — Ong Chu
    # 13/09/2026, dung chung voi Dre (submit_common.check_guide_source_compact).
    loi.extend(nc.check_guide_source_compact(spec.get("attrib"), "attrib"))
    loi.extend(nc.check_guide_source_compact(hook_hay_title, "hook" if kieu == "quote" else "title"))
    canh = nc.check_numbers_on_card(hook_hay_title + " " + str(spec.get("attrib") or ""), m, wd)
    if loi:
        return None, loi, canh
    return {"card_style": kieu, "image": a, "image2": anh[ma2] if ma2 else None,
            "cluttered": bool(a.get("cluttered") or (ma2 and anh[ma2].get("cluttered")))}, [], canh


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop hero card cua Ethan (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--spec")
    ap.add_argument("--khong-gui", action="store_true")
    ap.add_argument("--bo-qua-dau", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    import role
    role.set_active_role("ethan")

    meta, brand, wd, m, spec, spec_path, da_dung = nc.load_draft_context(a.draft_id, a.spec, "ethan_prepare.py", "ethan_submit.py")
    spec = role_spec.ethan_spec(spec)        # LOW-248: spec viet truoc deploy con ten cu
    kq, loi, canh = resolve_spec(spec, m, wd)
    for c in canh:
        print(f"[CANH BAO] {c}")
    # LOW-146: cung khoa voi Dre — bai chi co dung mot anh xep hang va bi ep dung
    # no thi khong bao "lam lai ma van giu anh cu" (xem submit_common.only_ranking_choice).
    bat_buoc = spec.get("image") is not None and spec.get("image") == nc.only_ranking_choice(m)
    loi = nc.check_redo_reused(da_dung, "ảnh", spec.get("image"), spec.get("hook") or spec.get("title"),
                          draft_id=a.draft_id, anh_bat_buoc=bat_buoc) + loi
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return nc.count_round_error(wd, loi,
                               f"venv/bin/python ethan_submit.py {a.draft_id}")

    out = Path(a.out or meta.get("image") or str(DRAFTS / f"{a.draft_id}.png"))
    out.parent.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, str(ROOT / "card.py"), "--image", kq["image"]["original_path"],
            "--brand", brand, "--out", str(out), "--kieu", kq["card_style"]]
    if kq["image2"]:
        args += ["--image2", kq["image2"]["original_path"]]
    if spec.get("subject"):
        args += ["--nhan-vat", str(spec["subject"])]
    if a.bo_qua_dau:
        args.append("--bo-qua-dau")
    if kq.get("cluttered"):
        args.append("--cluttered")
    if kq["card_style"] == "quote":
        hook = str(spec["hook"]).strip()
        args += ["--ratio", "4:5", "--title", hook, "--tagline", str(spec["tagline"]).strip().upper(),
                 "--attrib", str(spec["attrib"]).strip()]
    else:
        hook = str(spec["title"]).strip()
        args += ["--title", hook, "--kicker", str(spec.get("kicker") or "").strip().upper()]
        for cum in spec.get("highlight") or []:
            args += ["--highlight", str(cum).strip()]
    r = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    for dong in (r.stderr or "").splitlines():
        if dong.startswith("[CANH BAO]"):
            print(dong)
    if r.returncode != 0:
        cuoi = [d for d in ((r.stderr or "") + "\n" + (r.stdout or "")).splitlines() if d.strip()]
        for d in cuoi[-8:]:
            print(f"[LOI] {d}")
        print(f"\nSua {spec_path} theo bao loi (thuong la doi anh / them image2 / khai subject / sua chu) "
              f"roi chay lai: venv/bin/python ethan_submit.py {a.draft_id}")
        return 1
    if not out.exists():
        sys.exit(f"[LOI] card.py bao xong nhung khong thay {out}")

    anh_dung = [kq["image"]["id"]] + ([kq["image2"]["id"]] if kq["image2"] else [])
    nguon = sorted({m_["domain"] or manifest_values.source_label(m_["source"]) for m_ in m["images"] if m_["id"] in anh_dung})
    bg = "\n".join([f"Nguồn tin: {m['title']}", f"Link gốc: {m['link']}"]
                   + ([f"Via: {m['via']}"] if m.get("via") else [])
                   + ["Nguồn ảnh (ghi vào chú thích bài):"]
                   + [f"- {ma} ← {anh_['domain'] or manifest_values.source_label(anh_['source'])} ({anh_.get('page_url', '')[:100]})"
                      for ma in anh_dung for anh_ in m["images"] if anh_["id"] == ma]
                   + [f"Hook trên thẻ: {hook}", f"Tệp: {out}"])
    bg_path = state_paths.handoff_file(wd if a.khong_gui else DRAFTS, a.draft_id)
    bg_path.write_text(bg, encoding="utf-8")

    mid = None
    # Chu hien thi cua kieu the giu nguyen (quote / tran) trong caption + dong ket qua (LOW-248).
    style_label = role_spec.card_style_label(kq["card_style"])
    if a.khong_gui:
        print(f"[thu] khong gui Telegram (--khong-gui). The o {out}")
    else:
        mid = nc.send_album("ethan", [out], f"Thẻ {style_label}: {hook}", a.draft_id, wd, da_dung,
                           {"image": kq["image"]["id"], "hook": hook,
                            # image2 (ghep doc) cung phai bi danh dau da dung —
                            # thieu no thi bai sau dung lai duoc (06/09/2026).
                            "image2": (kq["image2"] or {}).get("id")})
    print(f"[xong] the {style_label} -> {out}" + (f"; da gui topic designer (message_id={mid}) kem nut duyet"
                                                 if mid else "") + f"; ban giao: {bg_path}")
    print("Ket qua task (dung dong nay de ket thuc task): "
          f"Dựng thẻ {style_label} “{hook}”, ảnh từ {', '.join(nguon) or 'nguồn bài'}; "
          + ("đã gửi topic kèm nút duyệt, bàn giao nguồn cho Miles tự động." if mid else "chưa gửi (thử)."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
