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
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402

DRAFTS = ROOT / "drafts"


def _chuan(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def giai_spec(spec: dict, m: dict, wd: Path) -> tuple:
    """Dich spec cua vai (ma anh) -> spec cua carousel.py (duong dan). Tra ve
    (spec_carousel, loi, dung_anh) — dung_anh: [(slide_nhan, [ma...])]."""
    import luat_anh
    anh = {a["ma"]: a for a in m["anh"]}
    loi, da_dung, dung_anh = [], {}, []

    chu_bai = ((m.get("chu_bai") or "") + " " + (m.get("tu_lieu", {}).get("doan_dau") or "")
               + " " + " ".join(m.get("tu_lieu", {}).get("cau_co_so") or [])).lower()
    try:
        chu_bai += " " + (wd / "tu_lieu.md").read_text(encoding="utf-8").lower()
    except OSError:
        pass

    def _lien_quan(ma_ds, nhan):
        rac = [ma for ma in ma_ds if anh[ma].get("lien_quan") is False]
        if rac:
            loi.append(f"{nhan}: {', '.join(rac)} bị đánh dấu KHÔNG LIÊN QUAN bài "
                       f"({'; '.join((anh[x].get('mo_ta') or '?')[:60] for x in rac)}) — "
                       "không dùng, chọn mã khác hoặc gộp ý/giảm slide")

    def _mat(ma_ds, muc, nhan):
        co = [ma for ma in ma_ds if anh[ma]["mat"]]
        nv = str(muc.get("nhan_vat") or "").strip()
        if co and not nv:
            loi.append(f"{nhan}: {', '.join(co)} có mặt người mà không khai \"nhan_vat\": "
                       "\"<tên người trong bài>\" — khai tên nếu đúng là nhân vật, "
                       "không thì đổi ảnh khác")
        elif co and nv:
            # Ten phai XUAT HIEN trong chu bai — khong thi la dien ten CEO cho qua
            # cong (bia Broadcom 05/09: anh quan chuc G20, khai "Hock Tan").
            ho = nv.split(",")[0].strip().lower()
            if chu_bai and ho and ho not in chu_bai and not all(w in chu_bai for w in ho.split()[-2:]):
                loi.append(f"{nhan}: nhan_vat \"{nv}\" không xuất hiện trong chữ bài — "
                           "khai tên người KHÔNG có trong bài là bịa. Bỏ ảnh này.")
            for ma in co:
                if anh[ma].get("mo_ta") and any(k in anh[ma]["mo_ta"].lower()
                                                for k in ("không liên quan", "g20", "logo")):
                    loi.append(f"{nhan}: {ma} — vision mô tả: \"{anh[ma]['mo_ta'][:80]}\" — "
                               "không phải nhân vật bài này")

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
        ra["slides"].append(g)
    n = len(slides) + 1
    if n < m.get("toi_thieu", 5):
        loi.append(f"chỉ {n} slide, tin này cần tối thiểu {m['toi_thieu']} (kể cả bìa) — "
                   "chia thêm tầng: con số, ý nghĩa, đối thủ, cái cần theo dõi")
    so_quote = sum(1 for s in slides if str(s.get("quote") or "").strip())
    if so_quote < 2:
        loi.append(f"chỉ {so_quote} slide quote, cần ≥ 2 — chọn 2 câu đắt nhất làm \"quote\"+\"attrib\"")
    return ra, loi, dung_anh


def kiem_lam_lai(spec: dict, da_dung: dict | None) -> list:
    if not da_dung:
        return []
    loi = []
    cover = spec.get("cover") or {}
    if cover.get("anh") and cover.get("anh") == da_dung.get("bia"):
        loi.append(f"LÀM LẠI: bìa vẫn là {da_dung['bia']} như lần trước — Ông Chủ bấm làm lại "
                   "nghĩa là bìa chưa đạt, đổi ảnh bìa")
    if _chuan(cover.get("hook")) == _chuan(da_dung.get("hook")):
        loi.append("LÀM LẠI: hook giống hệt lần trước — viết hook khác")
    return loi


def don_slide_cu(stem: Path) -> None:
    """Xoa <id>_2..9.png va *.ghep.png cua lan truoc: draft_write gom
    <id>_[0-9].png thanh album, lan lam lai it slide hon se lot slide cu."""
    for p in list(stem.parent.glob(stem.name + "_[0-9].png")) + \
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


def ghi_bang_den(draft_id: str, key: str, value, author: str = "dre") -> None:
    """Ghi mot muc len bang den cua bai qua bang_den.py (python cua hermes, vi no
    import hermes_cli.kanban_*). Im lang khi loi — chi in mot dong canh bao."""
    hermes_py = Path.home() / "hermes-agent" / "venv" / "bin" / "python"
    try:
        r = subprocess.run([str(hermes_py), str(ROOT / "bang_den.py"), "ghi", draft_id,
                            key, json.dumps(value, ensure_ascii=False), "--author", author],
                           cwd=str(ROOT), capture_output=True, text=True, timeout=60)
        if r.returncode != 0 or "[bang-den] lỗi" in (r.stderr or ""):
            print(f"[CANH BAO] bang den: {(r.stderr or r.stdout).strip()[-200:]}")
    except Exception as e:                                   # noqa: BLE001
        print(f"[CANH BAO] bang den: {type(e).__name__}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop carousel cua Dre (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--spec", help="Tep spec (mac dinh state/<brand>/chuan_bi/<id>/spec.json)")
    ap.add_argument("--khong-gui", action="store_true", help="Chi dung slide, khong gui Telegram")
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="Tat cong tieng Viet (chi khi chu THAT SU la tieng Anh)")
    ap.add_argument("--out", help="Ghi slide ra cho khac (de thu, khong de len drafts/)")
    a = ap.parse_args()

    meta = cb.nap_meta(a.draft_id)
    brand = cb._brand_cua(meta)
    import env_load
    wd = cb.workdir(env_load.state_dir(), a.draft_id)
    m = cb._doc_json(wd / "xong.json")
    if not m:
        sys.exit(f"Chua chuan bi. Chay truoc: venv/bin/python dre_chuan_bi.py {a.draft_id}")
    spec_path = Path(a.spec) if a.spec else wd / "spec.json"
    if not spec_path.exists():
        sys.exit(f"Chua co spec: {spec_path} — viet spec theo khung trong brief "
                 f"({wd / 'brief.md'}) roi chay lai.")
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] spec.json khong phai JSON hop le: {type(e).__name__}: {e}")

    da_dung = cb._doc_json(wd / "da_dung.json")
    spec_cs, loi, dung_anh = giai_spec(spec, m, wd)
    loi = kiem_lam_lai(spec, da_dung) + loi
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
        import gui_telegram
        res = gui_telegram.post("carousel", [str(f) for f in files], mo_ta, duyet=a.draft_id)
        r = res.get("result")
        mid = (r[-1] if isinstance(r, list) else r or {}).get("message_id")
        cb._ghi_json(wd / "da_dung.json", {
            "bia": (spec.get("cover") or {}).get("anh"), "hook": hook,
            "anh": [ma for _, ds in dung_anh for ma in ds],
            "luc": time.strftime("%H:%M %d/%m"), "lan": int((da_dung or {}).get("lan", 0)) + 1,
            "message_id": mid})
    nguon_anh = sorted({m_["mien"] or m_["tu"] for m_ in m["anh"]
                        if m_["ma"] in {ma for _, ds in dung_anh for ma in ds}})
    # Bang den (kanban swarm, 05/09): script ghi ban giao co cau truc len the goc
    # cua bai — code lam, LLM khong phai nho. Cung JSON nay in ra dong
    # "[metadata]" de Dre dan vao kanban_complete(metadata=...) -> Miles/Ada thay
    # trong "Parent task results". Best-effort: bang den hong khong hong bai.
    md = {"slide": n, "hook": hook, "nguon_anh": nguon_anh, "tep": str(out),
          "ban_giao": str(bg_path), "message_id": mid}
    if not a.khong_gui:
        ghi_bang_den(a.draft_id, "anh", md)
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
