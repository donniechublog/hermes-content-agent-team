#!/usr/bin/env python3
"""ethan_nop.py — NOP hero card cua Ethan: mot lenh lam het phan co hoc sau khi
vai da viet spec.json (khung do ethan_chuan_bi.py in ra).

  1. Doi ma anh -> tep goc (card.py tu fit kho 4:5); `anh2` -> --image2 (ghep
     doc, card kiem tone); `nhan_vat` -> --nhan-vat.
  2. Chan som loi hay mac: ma anh sai, chart/anh ngang >1.6 ma khong co anh2,
     mat nguoi khong khai, lam lai ma giu anh/hook cu.
  3. Chay card.py (moi cong chan chu/anh nam o do), gui anh len topic `designer`
     kem nut Duyet, ghi ban giao cho Miles, ghi da_dung.json.

Dung:
    venv/bin/python ethan_nop.py <draft_id>
    venv/bin/python ethan_nop.py <draft_id> --khong-gui --out /tmp/x.png   # thu
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402
import ethan_chuan_bi as eb                                  # noqa: E402
import nop_chung as nc                                       # noqa: E402

DRAFTS = cb.DRAFTS


def giai_spec(spec: dict, m: dict, wd) -> tuple:
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
    # TIN XEP HANG (Ong Chu 06/09/2026): anh chinh PHAI la anh xep hang (ma XH).
    # CHI chan khi engine THUC SU co anh xep hang (xem ghi chu cung viec o
    # dre_nop.py): khong co ma XH ma van chan thi vai khong bao gio nop duoc.
    if m.get("tin_xep_hang") and m.get("xep_hang") and not a.get("xep_hang"):
        loi.append(f"TIN XẾP HẠNG mà \"anh\" = {ma} không phải bảng xếp hạng. Dùng \"anh\": \"XH\" — "
                   + cb.cau_xep_hang(m) + ".")
    # Anh xep hang la chu the: khong bat ghep chi vi no la chart; chi bat khi qua ngang.
    can_ghep = (a["loai"] == "chart" and not a.get("xep_hang")) or a["ti_le"] > eb.TI_LE_HERO_MAX
    if can_ghep and not ma2:
        cap = eb.cap_ghep_hero(m)
        loi.append(f"{ma} là {'CHART' if a['loai'] == 'chart' else 'ảnh NGANG ' + str(a['ti_le'])} — "
                   f"card.py chặn một mình. Thêm \"anh2\" cùng tone (cặp gợi ý: {cap or 'không có'}) "
                   "hoặc chọn ảnh khác")
    if ma2:
        b = anh[ma2]
        rc = 1 / (1 / a["ti_le"] + 1 / b["ti_le"])
        if rc > eb.TI_LE_HERO_MAX:
            loi.append(f"ghép {ma}+{ma2} vẫn quá ngang ({rc:.2f} > {eb.TI_LE_HERO_MAX}) — chọn cặp khác")
        if b["ti_le"] < 1.2 or a["ti_le"] < 1.2:
            loi.append(f"ghép dọc chỉ dành cho hai ảnh NGANG (≥1.2); {ma}={a['ti_le']}, {ma2}={b['ti_le']}")
    # ẢNH KHÔNG LIÊN QUAN BÀI (Ông Chủ bắt lỗi 06/09/2026). `anh_chuan_bi.py` đã
    # cho MỌI ảnh ứng viên đi qua vision và đóng cờ `lien_quan`; `dre_nop.py` đọc
    # cờ đó và từ chối, `ethan_nop.py` thì không đọc — nên Ethan chọn được ảnh
    # bảng tỉ số giải golf cho tin GPT-6, rồi bảng câu cá trên băng cho tin xếp
    # hạng trí tuệ. Cả hai đều "leaderboard", và đó đúng là cách nó chọn: bắt
    # chữ, không nhìn nội dung. Không cổng nào nói gì.
    rac = [x for x in (ma, ma2) if x and anh[x].get("lien_quan") is False]
    if rac:
        loi.append(f"{', '.join(rac)} bị vision đánh dấu KHÔNG LIÊN QUAN bài "
                   f"({'; '.join((anh[x].get('mo_ta') or '?')[:60] for x in rac)}) — "
                   "không dùng. Tin xếp hạng/benchmark thì ẢNH ĐÚNG chính là bảng "
                   "xếp hạng của nguồn: engine đã chụp sẵn (mã loại chart), ghép "
                   "dọc với một ảnh ngang cùng tone qua \"anh2\". Đừng đi tìm ảnh "
                   "khác chỉ vì chart bị chặn khi đi một mình.")

    # Mat nguoi: dung CHUNG cong chan voi Dre (nop_chung.kiem_nhan_vat, 06/09/2026).
    # Truoc do Ethan chi hoi "co khai ten chua" nen mot ten CEO bia dat van qua —
    # Dre thi doi chieu ten voi chu bai va voi mo ta cua vision.
    loi.extend(nc.kiem_nhan_vat(anh, [ma, ma2], spec.get("nhan_vat"),
                                nc.chu_bai_cua(m, wd), ""))
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
    # KHONG DUNG LAI ANH DA DUNG (lien phien, dHash) — Ong Chu 06/09/2026.
    import luat_anh
    for x in (ma, ma2):
        if x:
            l, _ = luat_anh.kiem_da_dung(x, anh[x]["goc"], m.get("draft_id", ""))
            loi += l
    # Hook/attrib con nguyen tieng Anh, va so tren the khong co trong tu lieu:
    # hai cong nay Dre da co tu 06/09/2026, Ethan dung chung o nop_chung.
    hook_hay_title = str(spec.get("hook") or spec.get("title") or "")
    loi.extend(nc.kiem_quote_dich(hook_hay_title, "hook"))
    canh = nc.kiem_so_tren_anh(hook_hay_title + " " + str(spec.get("attrib") or ""), m, wd)
    if loi:
        return None, loi, canh
    return {"kieu": kieu, "anh": a, "anh2": anh[ma2] if ma2 else None}, [], canh


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop hero card cua Ethan (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--spec")
    ap.add_argument("--khong-gui", action="store_true")
    ap.add_argument("--bo-qua-dau", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    meta, brand, wd, m, spec, spec_path, da_dung = nc.nap(a.draft_id, a.spec, "ethan_chuan_bi.py", "ethan_nop.py")
    kq, loi, canh = giai_spec(spec, m, wd)
    for c in canh:
        print(f"[CANH BAO] {c}")
    loi = nc.kiem_lam_lai(da_dung, "ảnh", spec.get("anh"), spec.get("hook") or spec.get("title")) + loi
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        print(f"\nSua {spec_path} roi chay lai: venv/bin/python ethan_nop.py {a.draft_id}")
        return 1

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
              f"roi chay lai: venv/bin/python ethan_nop.py {a.draft_id}")
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
        mid = nc.gui_album("designer", [out], f"Thẻ {kq['kieu']}: {hook}", a.draft_id, wd, da_dung,
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
