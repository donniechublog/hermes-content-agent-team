#!/usr/bin/env python3
"""kite_nop.py — NOP carousel.edu cua Kite: kiem spec, dung bang render_edu.py,
gui album, ban giao, ghi da_dung. Vai chi viet spec.json (khung do
kite_chuan_bi.py in ra).

Kiem TRUOC khi render (render_edu cung co cong chan, nhung bao som thi vai sua
mot vong): so slide 6..10, slide 1 la cover, kind hop le, truong bat buoc tung
kind, ma hinh that -> tep (chi hinh la chart >= 800px), caption khi co image,
theme/hero hop le va (lam lai) phai khac lan truoc, do dai chu vuot muc thi
canh bao.

Dung:
    venv/bin/python kite_nop.py <draft_id>
    venv/bin/python kite_nop.py <draft_id> --khong-gui --out /tmp/k/k.png   # thu
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402
import env_load                                              # noqa: E402
import kite_chuan_bi as kb                                   # noqa: E402
import luat_anh                                              # noqa: E402
import nop_chung as nc                                       # noqa: E402
import render_edu                                            # noqa: E402

DRAFTS = cb.DRAFTS
# MOT bang duy nhat, o renderer (doi 06/09/2026 dot 2). Ban chep o day truoc
# kia thieu vai truong ma builder that su doc cung (`callout` cua loop,
# `standfirst` cua figure/bars, cac khoa long trong cards/steps/bars), va no chi
# chay khi di qua nop — goi thang render_edu.py thi khong co cong nao.
BAT_BUOC = {k: v["truong"] for k, v in render_edu.BAT_BUOC_KIND.items()}
GIOI_HAN = {"title": 70, "standfirst": 240, "callout": 130, "eyebrow": 32}


def _kiem_hinh_slide(i: int, sl: dict, s2: dict, hinh: dict, m: dict,
                     da_thay: dict, loi: list, canh: list) -> None:
    """Slide co `image`: doi ma -> tep, roi bon cong luat anh (da dung, trung
    trong bo, anh rong, do phan giai) va canh bao mat nguoi. Khong co image thi
    khong lam gi."""
    img = sl.get("image")

    if img:

        if img not in hinh:

            loi.append(f"slide {i}: image \"{img}\" không phải mã hình thật dùng được "

                       f"(có: {', '.join(hinh) or 'không có'}) — bỏ image hoặc đổi mã")

        else:

            s2["image"] = hinh[img]["goc"]

            # KHONG DUNG LAI ANH DA DUNG (Ong Chu 06/09/2026). Dre va Ethan

            # co cong nay tu dau; Kite thi khong doc lan khong ghi, nen mot

            # bang benchmark Dre dung hom qua van len bo cua Kite hom nay.

            l, _ = luat_anh.kiem_da_dung(f"slide {i} ({img})", hinh[img]["goc"],

                                         m.get("draft_id", ""), m.get("link", ""))

            loi += l

            # LUAT_ANH.md:12 tuyen bo Kite "phai theo" luat anh, nhung bang

            # cong chan §9 khong co cot Kite va chuoi kite_* khong goi cong

            # nao ngoai kiem_da_dung — mot khoang cach im lang giua tai lieu

            # va ma (audit 06/09/2026). Bon cong duoi day khong dinh gi toi

            # bo cuc nen ap duoc nguyen xi cho khung cua Kite:

            nhan = f"slide {i} ({img})"

            l, c = luat_anh.kiem_trung(nhan, hinh[img]["goc"], da_thay)

            loi += l

            canh += c

            try:

                from PIL import Image as _Im

                with _Im.open(hinh[img]["goc"]) as _im:

                    l, c = luat_anh.kiem_anh_rong(nhan, _im)

                    loi += l

                    canh += c

                    l, c = luat_anh.kiem_do_phan_giai(nhan, _im.width, _im.height)

                    loi += l

                    canh += c

            except OSError as e:

                loi.append(f"{nhan}: khong mo duoc anh ({type(e).__name__})")

            # Mat nguoi: Kite khong co truong `nhan_vat` trong spec (khac

            # card.py/carousel.py), nen o day chi CANH BAO — chan cung se

            # khoa het anh su kien ma vai khong co cach nao khai.

            l, c = luat_anh.kiem_mat_nguoi(nhan, hinh[img]["goc"])

            canh += [d + " — Kite chưa có trường nhan_vat, tự soi xem "

                     "người trong ảnh có đúng là người trong bài không"

                     for d in l] + c

            if not sl.get("caption"):

                loi.append(f"slide {i}: có image thì phải có caption \"… · via <ai>\"")


def _giai_slide(i: int, sl: dict, hinh: dict, m: dict, da_thay: dict,
                loi: list, canh: list):
    """Mot slide cua vai -> mot slide cua render_edu, hoac None khi kind la.
    Tach khoi giai_spec 07/09/2026: than vong lap dai 95 dong."""
    k = sl.get("kind")

    if k not in BAT_BUOC:

        loi.append(f"slide {i}: kind \"{k}\" không hợp lệ (cover/statement/steps/loop/figure/bars/cta)")

        return None

    thieu = [f for f in BAT_BUOC[k] if not sl.get(f)]

    if thieu:

        loi.append(f"slide {i} ({k}): thiếu {', '.join(thieu)}")

    # Khoa LONG (cards[].num, steps[].desc, bars[].label...) — renderer doc

    # cung nen thieu la KeyError sau khi da mo Chromium.

    # kiem_truong([sl]) chi thay MOT slide nen luon danh so "slide 1"; ban

    # truoc 07/09/2026 tim "slide {i}" de doi -> khong bao gio khop, moi loi

    # khoa long deu bao "slide 1" du o slide nao (test_spec_kite bat duoc).

    loi += [d.replace(f"slide 1 [{k}]", f"slide {i} ({k})")

            for d in render_edu.kiem_truong([sl])

            if "[" in d and "thieu" in d and "]:" in d and

            not any(f"thieu '{f}'" in d for f in BAT_BUOC[k])]

    s2 = dict(sl)

    _kiem_hinh_slide(i, sl, s2, hinh, m, da_thay, loi, canh)

    for f, gh in GIOI_HAN.items():

        v = sl.get(f)

        if isinstance(v, str) and len(v) > gh:

            canh.append(f"slide {i}: {f} dài {len(v)} ký tự (> {gh}) — có thể tràn/nhỏ chữ")

    for c in sl.get("cards", []) or []:

        if len(str(c.get("text", ""))) > 100:

            canh.append(f"slide {i}: card \"{str(c.get('text'))[:30]}…\" dài, rút ≤ 90")

    for st in sl.get("steps", []) or []:

        if len(str(st.get("desc", ""))) > 90:

            canh.append(f"slide {i}: step desc dài, rút ≤ 80")

    for t in sl.get("checks", []) or []:

        if len(str(t)) > 80:

            canh.append(f"slide {i}: check dài, rút ≤ 70")

    if k == "bars":

        bs = sl.get("bars") or []

        if not 2 <= len(bs) <= 6:

            loi.append(f"slide {i}: bars cần 2..6 cột (có {len(bs)})")

        for j, b in enumerate(bs, 1):

            b = b if isinstance(b, dict) else {}

            try:

                render_edu._gia_tri(b.get("value"))

            except (ValueError, TypeError):

                loi.append(f"slide {i}: cột {j} \"value\" phải là số thật trong bài (có {b.get('value')!r})")

            if len(str(b.get("label", ""))) > 28:

                canh.append(f"slide {i}: cột {j} label dài, rút ≤ 28")

    # CHI xet dung cac truong mang trich dan (caption, readmore.text) — quet
    # het sl.values() nhu truoc bat nham nhan/the/tieu de thuong chua chu
    # "nguồn" theo nghia thuong (vd "Nguồn cung", "Khan hiếm nguồn cung")
    # tuong la loi dinh dang trich dan (Ong Chu 08/09/2026, bat 2 lan doc lap
    # trong dot chay lai hom nay: Samsung/TSMC va Wafer).
    trich_dan = [sl.get("caption")]
    rm = sl.get("readmore")
    if isinstance(rm, dict):
        trich_dan.append(rm.get("text"))
    if any(isinstance(v, str) and "nguồn" in v.lower() for v in trich_dan):
        loi.append(f"slide {i}: dẫn nguồn ghi 'via', không ghi 'nguồn'")
    return s2


def giai_spec(spec: dict, m: dict, wd) -> tuple:
    loi, canh = [], []
    slides = spec.get("slides") or []
    if not (6 <= len(slides) <= 10):
        loi.append(f"có {len(slides)} slide — cần 6..10")
    if slides and slides[0].get("kind") != "cover":
        loi.append("slide 1 phải là kind \"cover\"")
    hinh = {a["ma"]: a for a in kb.hinh_that(m)}
    da_thay = {}                    # hash anh -> nhan slide, TRONG BO nay (kiem_trung)
    # brand trong spec render la CHU in o masthead/folio (render_edu chi dung no
    # lam chu) -> phai la handle hien thi (dcgr -> dcgr.tech), khong phai slug.
    # d24ddfc da sua byline/follow, con masthead van in "dcgr" (05/09/2026).
    ra = {"brand": kb.handle_kenh(m["brand"]), "section": spec.get("section") or "RESEARCH",
          "folio": spec.get("folio") or m["title"][:24].upper()}
    theme, hero = spec.get("theme"), spec.get("hero")
    if theme and theme not in render_edu.THEMES:
        loi.append(f"theme \"{theme}\" không có (chọn: {', '.join(render_edu.THEMES)})")
    if hero and hero not in render_edu.HEROES:
        loi.append(f"hero \"{hero}\" không có (chọn: {', '.join(render_edu.HEROES)})")
    if theme:
        ra["theme"] = theme
    if hero:
        ra["hero"] = hero
    ra["slides"] = []
    for i, sl in enumerate(slides, 1):
        s2 = _giai_slide(i, sl, hinh, m, da_thay, loi, canh)
        if s2 is None:
            continue
        ra["slides"].append(s2)

    # Brief noi "CO n hinh that lien quan -> BAT BUOC dung it nhat mot"
    # (kite_chuan_bi.py), nhung truoc 06/09/2026 khong cong nao kiem: vai bo qua
    # ca bang benchmark that roi ve vector, dung cai loi Ong Chu da bat 05/09
    # ("dung anh that khi engine tim duoc").
    # CHI ep khi anh DA DUOC NHIN (lien_quan is True). Vision tat/thieu
    # OPENAI_API_KEY thi moi anh co lien_quan=None, hinh_that van nhan het —
    # ep luc do la day quang cao / widget gia co phieu len slide, dung loai rac
    # ma vision sinh ra de loai (do 06/09/2026). Chua nhin thi goi y, khong ep.
    da_nhin = [ma for ma, a in hinh.items() if a.get("lien_quan") is True]
    co_anh = [sl for sl in slides if sl.get("image")]
    if da_nhin and not co_anh:
        loi.append(f"có {len(da_nhin)} hình thật dùng được ({', '.join(da_nhin)}) mà không slide nào dùng — "
                   "BẮT BUỘC dùng ít nhất một: `figure` cho chart/bảng, hoặc image ở bìa. "
                   "Vẽ vector hết trong khi có hình thật là bỏ phí bằng chứng của bài.")
    # TIN CHUYEN TU DRE/ETHAN vi thieu anh: sieu chat hon mot bac (Ong Chu
    # 09/09/2026: "sau khi tim duoc hinh tot ma van ko du de lam va pass qua cho
    # Kite thi Kite cung phai dung nhung hinh do trong body"). Cong "it nhat
    # mot" o tren van cho phep dat DUY NHAT mot tam len bia roi ve vector ca
    # than — dung cai bi che. O day doi DU MA va doi co hinh ngoai bia.
    ep = kb.hinh_phai_dung(m)
    if ep:
        # Chay DOC LAP voi cong tren (khong `elif`): bo khong dung tam nao thi
        # vai can biet CA "thieu ma nao" ngay vong nay, khong phai sua hai vong.
        tu_vai = kb.chuyen_tu_vai(m)
        dung = {sl.get("image") for sl in slides if sl.get("image")}
        thieu = [ma for ma in ep if ma not in dung]
        if thieu:
            loi.append(f"tin chuyển từ {tu_vai} sang Kite VÌ THIẾU ẢNH, nên cả {len(ep)} hình "
                       f"thật tìm được phải vào bộ — còn thiếu {', '.join(thieu)}. Mỗi tấm một slide "
                       "`figure` (\"image\": \"<mã>\" + caption \"… · via <ai>\").")
        if co_anh and not any(sl.get("image") for sl in slides[1:]):
            loi.append(f"tin chuyển từ {tu_vai} sang Kite vì thiếu ảnh mà hình thật chỉ nằm ở BÌA — "
                       "phải có ít nhất một slide thân dùng hình thật (`figure`). Đặt hết lên bìa rồi "
                       "vẽ vector cả thân là đúng cái lỗi khiến tin phải chuyển sang đây.")

    # So tren slide phai co trong tu lieu (canh bao) — Kite ve so bia la loi nang
    # nhat cua carousel kien thuc, ma truoc 06/09/2026 khong ai doi chieu.
    chua_nhin = [ma for ma, a in hinh.items() if a.get("lien_quan") is None]
    if chua_nhin and not da_nhin:
        canh.append(f"vision chưa nhìn {', '.join(chua_nhin)} (router tắt/thiếu khoá) — "
                    "hình thật CHƯA được kiểm nội dung, chỉ dùng khi bạn tự tin nó đúng bài")
    chu = " ".join(str(v) for sl in slides for v in sl.values() if isinstance(v, str))
    canh.extend(nc.kiem_so_tren_anh(chu, m, wd))
    return ra, loi, canh


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop carousel.edu cua Kite (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--spec")
    ap.add_argument("--khong-gui", action="store_true")
    ap.add_argument("--bo-qua-dau", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    meta, brand, wd, m, spec, spec_path, da_dung = nc.nap(a.draft_id, a.spec, "kite_chuan_bi.py", "kite_nop.py")
    spec_r, loi, canh = giai_spec(spec, m, wd)
    hook = (spec.get("slides") or [{}])[0].get("title", "")
    if da_dung:
        if (spec.get("theme"), spec.get("hero")) == (da_dung.get("theme"), da_dung.get("hero")):
            loi.append("LÀM LẠI: theme và hero trùng lần trước — đổi ít nhất một")
        if nc.chuan(hook) == nc.chuan(da_dung.get("hook")):
            loi.append("LÀM LẠI: hook bìa giống lần trước — viết khác")
    for c in canh:
        print(f"[CANH BAO] {c}")
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return nc.dem_vong_loi(wd, loi,
                               f"venv/bin/python kite_nop.py {a.draft_id}")

    out = Path(a.out or meta.get("image") or str(DRAFTS / f"{a.draft_id}.png"))
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    for p in env_load.album_phu(stem.name, stem.parent):
        p.unlink(missing_ok=True)
    p_spec = wd / "render_edu.spec.json"
    p_spec.write_text(json.dumps(spec_r, ensure_ascii=False, indent=2), encoding="utf-8")
    args = [sys.executable, str(ROOT / "render_edu.py"), "--spec", str(p_spec), "--out", str(out),
            "--brand", brand] + (["--bo-qua-dau"] if a.bo_qua_dau else [])
    r = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        for d in ((r.stderr or "") + "\n" + (r.stdout or "")).splitlines():
            if d.strip().startswith("-") or "CONG CHAN" in d or "CANH BAO" in d or "Error" in d:
                print(f"[LOI] {d.strip()}")
        cuoi = [d for d in (r.stderr or "").strip().splitlines() if d.strip()]
        if cuoi:
            print(f"[LOI] {cuoi[-1]}")
        print(f"\nSua {spec_path} theo bao loi roi chay lai: venv/bin/python kite_nop.py {a.draft_id}")
        return 1
    m_theme = re.search(r"theme=(\w+) hero=(\S+)", r.stdout or "")
    theme, hero = (m_theme.group(1), m_theme.group(2)) if m_theme else (spec.get("theme"), spec.get("hero"))
    n = len(spec_r["slides"])
    files = [out] + [Path(f"{stem}_{i}.png") for i in range(2, n + 1)]
    thieu = [str(f) for f in files if not f.exists()]
    if thieu:
        sys.exit(f"[LOI] render_edu bao xong nhung thieu tep: {thieu}")

    hinh = [s.get("image") for s in spec.get("slides") or [] if s.get("image")]
    bg = "\n".join([f"Nguồn tin: {m['title']}", f"Link gốc: {m['link']}"]
                   + ([f"Via: {m['via']}"] if m.get("via") else [])
                   + [f"Bộ slide: {n} slide art vector gốc, theme {theme}, hero {hero}"]
                   + ([f"Hình thật đã chèn: {', '.join(hinh)} (nguồn: bài gốc)"] if hinh else [])
                   + [f"Hook bìa: {hook}", f"Tệp: {out}"])
    bg_path = (wd if a.khong_gui else DRAFTS) / f"{a.draft_id}.ban_giao.md"
    bg_path.write_text(bg, encoding="utf-8")

    mid = None
    if a.khong_gui:
        print(f"[thu] khong gui Telegram (--khong-gui). {n} slide o {out.parent}")
    else:
        mid = nc.gui_album("carousel-edu", files, f"Carousel edu {n} slide: {hook}", a.draft_id, wd, da_dung,
                           {"theme": theme, "hero": hero, "hook": hook,
                            # ma hinh THAT da dat len slide — de bai sau (ke ca
                            # cua Dre/Ethan) khong dung lai (06/09/2026).
                            "hinh": [sl.get("image") for sl in (spec.get("slides") or [])
                                     if sl.get("image")]})
    # Bang den (kanban swarm): ban giao co cau truc cua Kite len the goc + dong
    # "[metadata]" de Kite dan vao kanban_complete -> Miles thay trong
    # "Parent task results". Best-effort.
    md = {"slide": n, "hook": hook, "theme": theme, "hero": hero, "hinh_that": hinh,
          "tep": str(out), "ban_giao": str(bg_path), "message_id": mid, "vai": "kite"}
    if not a.khong_gui:
        nc.ghi_bang_den(a.draft_id, "anh", md, "kite")
    print("[metadata] " + json.dumps(md, ensure_ascii=False))
    print(f"[xong] {n} slide -> {out}; theme={theme} hero={hero}"
          + (f"; da gui topic carousel-edu (message_id={mid}) kem nut duyet" if mid else "")
          + f"; ban giao: {bg_path}")
    print("Ket qua task (dung dong nay de ket thuc task): "
          f"Dựng {n} slide carousel edu “{hook}” (theme {theme}, hero {hero})"
          + ("; đã gửi topic kèm nút duyệt, bàn giao nguồn cho Miles tự động." if mid else "; chưa gửi (thử)."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
