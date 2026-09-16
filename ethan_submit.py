#!/usr/bin/env python3
"""ethan_submit.py — NOP hero card cua Ethan: mot lenh lam het phan co hoc sau khi
vai da viet spec.json (khung do ethan_prepare.py in ra).

  1. Doi ma anh -> tep goc (card.py tu fit kho 4:5); `anh2` -> --image2 (ghep
     doc, card kiem tone); `nhan_vat` -> --nhan-vat.
  2. Chan som loi hay mac: ma anh sai, chart/anh ngang >1.6 ma khong co anh2,
     mat nguoi khong khai, lam lai ma giu anh/hook cu.
  3. Chay card.py (moi cong chan chu/anh nam o do), gui anh len topic `designer`
     kem nut Duyet, ghi ban giao cho Miles, ghi da_dung.json.

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

DRAFTS = cb.DRAFTS


def _check_stack(a: dict, ma: str, ma2, anh: dict, m: dict, loi: list) -> None:
    """Anh di mot minh duoc khong, va ghep voi "anh2" co hop le khong.

    (13/09/2026: bo dieu kien "anh qua ngang phai ghep"/"ghep roi van qua
    ngang" — tuong duong `kiem_anh_thap`, da bo khoi he thong, moi
    vai. Chi con giu: chart la chu the (khong bi keo di ghep NEU la xep hang),
    va ghep doc chi hop khi CA HAI anh deu ngang (rang buoc cau truc cua chinh
    co che ghep, khong phai cam doan ve chat luong/nguon)."""
    can_ghep = a["loai"] == "chart" and not a.get("xep_hang")
    if can_ghep and not ma2:
        cap = eb.stackable_pairs_hero(m)
        loi.append(f"{ma} là CHART — card.py chặn một mình. Thêm \"anh2\" (cặp gợi ý: "
                   f"{cap or 'không có'}) hoặc chọn ảnh khác")
    if ma2:
        b = anh[ma2]
        if b["ti_le"] < 1.2 or a["ti_le"] < 1.2:
            loi.append(f"ghép dọc chỉ dành cho hai ảnh NGANG (≥1.2); {ma}={a['ti_le']}, {ma2}={b['ti_le']}")


def _check_text(spec: dict, kieu: str, loi: list) -> None:
    """Truong chu bat buoc theo kieu the: quote can hook/tagline/attrib, tran
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
            loi.append("kiểu tran: thiếu \"title\" (một câu hoàn chỉnh)")


def resolve_spec(spec: dict, m: dict, wd) -> tuple:
    """Spec cua Ethan (ma anh) -> (ket_qua, loi, canh). Tach 07/09/2026: ba cong
    trung voi Dre (tin xep hang, khong lien quan, anh da dung) sang submit_common,
    phan ghep va phan chu thanh hai ham rieng."""
    anh = {a["ma"]: a for a in m["anh"]}
    loi = []
    kieu = (spec.get("kieu") or "quote").strip().lower()
    if kieu not in ("quote", "tran"):
        loi.append("\"kieu\" phải là \"quote\" (mặc định) hoặc \"tran\"")
    ma, ma2 = spec.get("anh"), spec.get("anh2")
    if not ma or ma not in anh:
        loi.append(f"\"anh\" không tồn tại: {ma} (có: {', '.join(anh) or 'không có ảnh nào'})")
        return None, loi, []
    if ma2 and ma2 not in anh:
        loi.append(f"\"anh2\" không tồn tại: {ma2}")
        ma2 = None
    if ma2 == ma:
        loi.append("\"anh2\" trùng \"anh\"")
        ma2 = None
    a = anh[ma]
    # TIN XEP HANG (Ong Chu 06/09/2026): anh chinh PHAI la anh xep hang (ma XH),
    # nhung CHI khi engine da CHUP duoc bang — xem submit_common.needs_ranking_image.
    if nc.needs_ranking_image(m, a):
        loi.append(f"TIN XẾP HẠNG mà \"anh\" = {ma} không phải bảng xếp hạng. Dùng \"anh\": \"XH\" — "
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
                   "dọc với một ảnh ngang cùng tone qua \"anh2\". Đừng đi tìm ảnh "
                   "khác chỉ vì chart bị chặn khi đi một mình.")

    # Mat nguoi: dung CHUNG cong chan voi Dre (submit_common.check_subject_named, 06/09/2026).
    loi.extend(nc.check_subject_named(anh, [ma, ma2], spec.get("nhan_vat"),
                                nc.article_text_for(m, wd), ""))
    _check_text(spec, kieu, loi)
    loi += nc.check_not_reused_across_runs(anh, [(x, x) for x in (ma, ma2) if x], m)
    loi += nc.check_image_fall(anh, {x: n for x, n in ((ma, "anh"), (ma2, "anh2")) if x}, m)
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
    return {"kieu": kieu, "anh": a, "anh2": anh[ma2] if ma2 else None,
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
    kq, loi, canh = resolve_spec(spec, m, wd)
    for c in canh:
        print(f"[CANH BAO] {c}")
    # LOW-146: cung khoa voi Dre — bai chi co dung mot anh xep hang va bi ep dung
    # no thi khong bao "lam lai ma van giu anh cu" (xem submit_common.only_ranking_choice).
    bat_buoc = spec.get("anh") is not None and spec.get("anh") == nc.only_ranking_choice(m)
    loi = nc.check_redo_reused(da_dung, "ảnh", spec.get("anh"), spec.get("hook") or spec.get("title"),
                          draft_id=a.draft_id, anh_bat_buoc=bat_buoc) + loi
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return nc.count_round_error(wd, loi,
                               f"venv/bin/python ethan_submit.py {a.draft_id}")

    out = Path(a.out or meta.get("image") or str(DRAFTS / f"{a.draft_id}.png"))
    out.parent.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, str(ROOT / "card.py"), "--image", kq["anh"]["goc"],
            "--brand", brand, "--out", str(out), "--kieu", kq["kieu"]]
    if kq["anh2"]:
        args += ["--image2", kq["anh2"]["goc"]]
    if spec.get("nhan_vat"):
        args += ["--nhan-vat", str(spec["nhan_vat"])]
    if a.bo_qua_dau:
        args.append("--bo-qua-dau")
    if kq.get("cluttered"):
        args.append("--cluttered")
    if kq["kieu"] == "quote":
        hook = str(spec["hook"]).strip()
        args += ["--ratio", "4:5", "--title", hook, "--tagline", str(spec["tagline"]).strip().upper(),
                 "--attrib", str(spec["attrib"]).strip()]
    else:
        hook = str(spec["title"]).strip()
        args += ["--title", hook, "--kicker", str(spec.get("kicker") or "").strip().upper()]
    r = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    for dong in (r.stderr or "").splitlines():
        if dong.startswith("[CANH BAO]"):
            print(dong)
    if r.returncode != 0:
        cuoi = [d for d in ((r.stderr or "") + "\n" + (r.stdout or "")).splitlines() if d.strip()]
        for d in cuoi[-8:]:
            print(f"[LOI] {d}")
        print(f"\nSua {spec_path} theo bao loi (thuong la doi anh / them anh2 / khai nhan_vat / sua chu) "
              f"roi chay lai: venv/bin/python ethan_submit.py {a.draft_id}")
        return 1
    if not out.exists():
        sys.exit(f"[LOI] card.py bao xong nhung khong thay {out}")

    anh_dung = [kq["anh"]["ma"]] + ([kq["anh2"]["ma"]] if kq["anh2"] else [])
    nguon = sorted({m_["mien"] or m_["tu"] for m_ in m["anh"] if m_["ma"] in anh_dung})
    bg = "\n".join([f"Nguồn tin: {m['title']}", f"Link gốc: {m['link']}"]
                   + ([f"Via: {m['via']}"] if m.get("via") else [])
                   + ["Nguồn ảnh (ghi vào chú thích bài):"]
                   + [f"- {ma} ← {anh_['mien'] or anh_['tu']} ({anh_.get('trang', '')[:100]})"
                      for ma in anh_dung for anh_ in m["anh"] if anh_["ma"] == ma]
                   + [f"Hook trên thẻ: {hook}", f"Tệp: {out}"])
    bg_path = (wd if a.khong_gui else DRAFTS) / f"{a.draft_id}.ban_giao.md"
    bg_path.write_text(bg, encoding="utf-8")

    mid = None
    if a.khong_gui:
        print(f"[thu] khong gui Telegram (--khong-gui). The o {out}")
    else:
        mid = nc.send_album("ethan", [out], f"Thẻ {kq['kieu']}: {hook}", a.draft_id, wd, da_dung,
                           {"anh": kq["anh"]["ma"], "hook": hook,
                            # anh2 (ghep doc) cung phai bi danh dau da dung —
                            # thieu no thi bai sau dung lai duoc (06/09/2026).
                            "anh2": (kq["anh2"] or {}).get("ma")})
    print(f"[xong] the {kq['kieu']} -> {out}" + (f"; da gui topic designer (message_id={mid}) kem nut duyet"
                                                 if mid else "") + f"; ban giao: {bg_path}")
    print("Ket qua task (dung dong nay de ket thuc task): "
          f"Dựng thẻ {kq['kieu']} “{hook}”, ảnh từ {', '.join(nguon) or 'nguồn bài'}; "
          + ("đã gửi topic kèm nút duyệt, bàn giao nguồn cho Miles tự động." if mid else "chưa gửi (thử)."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
