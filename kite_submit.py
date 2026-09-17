#!/usr/bin/env python3
"""kite_submit.py — NOP carousel.edu cua Kite: kiem spec, dung bang render_edu.py,
gui album, ban giao, ghi da_dung. Vai chi viet spec.json (khung do
kite_prepare.py in ra).

Kiem TRUOC khi render (render_edu cung co cong chan, nhung bao som thi vai sua
mot vong): so slide 6..10, slide 1 la cover, kind hop le, truong bat buoc tung
kind, ma hinh that -> tep (chi hinh la chart >= 800px), caption khi co image,
theme/hero hop le va (lam lai) phai khac lan truoc, do dai chu vuot muc thi
canh bao.

Khoa spec English tu LOW-248 (role_spec.py); spec cu doc qua role_spec.kite_spec.

Dung:
    venv/bin/python kite_submit.py <draft_id>
    venv/bin/python kite_submit.py <draft_id> --khong-gui --out /tmp/k/k.png   # thu
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                    # noqa: E402
import env_load                                              # noqa: E402
import kite_prepare as kb                                   # noqa: E402
import image_rules_kite                                       # noqa: E402
import submit_common as nc                                       # noqa: E402
import state_paths                                            # noqa: E402
import render_edu                                            # noqa: E402
import role_spec                                             # noqa: E402

DRAFTS = cb.DRAFTS
# MOT bang duy nhat, o renderer (doi 06/09/2026 dot 2). Ban chep o day truoc
# kia thieu vai truong ma builder that su doc cung (`callout` cua loop,
# `standfirst` cua figure/bars, cac khoa long trong cards/steps/bars), va no chi
# chay khi di qua nop — goi thang render_edu.py thi khong co cong nao.
REQUIRED = {k: v["fields"] for k, v in render_edu.REQUIRED_KIND.items()}
LIMIT = {"title": 70, "standfirst": 240, "callout": 130, "eyebrow": 32}
# LOW-45 (Ong Chu 12/09/2026): "bài có 8 slide thì tối thiểu phải có 3 hình
# thật" — 1 ảnh thật KHÁC NHAU cho mỗi 3 slide, làm tròn LÊN (8 -> 3, 6 -> 2,
# 10 -> 4). Chi ap dung khi vong tim đủ nguồn (xem `resolve_spec`).
SLIDE_NEW_IMAGE_REAL = 3
# Chi bat dang DAN NGUON ro rang ("theo nguồn", "nguồn:") — KHONG bat blunt
# nhu caption/readmore ben duoi, vi standfirst la van xuoi tu do (dung o ca 5
# kind) va co the hop le chua "nguồn" theo nghia thuong ("nguồn cung", "nguồn
# lực") — blunt substring o day se bat nham y het loi 08/09/2026 da sua cho
# title/eyebrow (Samsung/TSMC, Wafer).
_RE_NGUON_QUY = re.compile(r"(theo\s+nguồn\b|\bnguồn\s*[:：])", re.IGNORECASE)


def _check_figure_slide(i: int, sl: dict, s2: dict, hinh: dict, m: dict,
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

            s2["image"] = hinh[img]["original_path"]

            # KHONG DUNG LAI ANH DA DUNG (Ong Chu 06/09/2026). Dre va Ethan

            # co cong nay tu dau; Kite thi khong doc lan khong ghi, nen mot

            # bang benchmark Dre dung hom qua van len bo cua Kite hom nay.

            l, _ = image_rules_kite.check_not_reused(f"slide {i} ({img})", hinh[img]["original_path"],

                                         m.get("draft_id", ""), m.get("link", ""))

            loi += l

            # IMAGE_RULES.md:12 tuyen bo Kite "phai theo" luat anh, nhung bang

            # cong chan §9 khong co cot Kite va chuoi kite_* khong goi cong

            # nao ngoai check_not_reused — mot khoang cach im lang giua tai lieu

            # va ma (audit 06/09/2026). Bon cong duoi day khong dinh gi toi

            # bo cuc nen ap duoc nguyen xi cho khung cua Kite:

            nhan = f"slide {i} ({img})"

            l, c = image_rules_kite.check_duplicate(nhan, hinh[img]["original_path"], da_thay)

            loi += l

            canh += c

            try:

                from PIL import Image as _Im

                with _Im.open(hinh[img]["original_path"]) as _im:

                    l, c = image_rules_kite.check_blank_image(nhan, _im)

                    loi += l

                    canh += c

                    l, c = image_rules_kite.check_resolution(nhan, _im.width, _im.height)

                    loi += l

                    canh += c

            except OSError as e:

                loi.append(f"{nhan}: khong mo duoc anh ({type(e).__name__})")

            # Mat nguoi (LOW-186, 16/09/2026): Kite gio CO truong `subject`

            # trong slide, giong Dre/Ethan — khai duoc thi chi CANH BAO (nguoi

            # duyet tu soi dung sai), khong khai duoc thi CHAN cung nhu hai vai

            # kia. `kite_prepare.figure_real` khong con loai anh mat vo danh tu

            # buoc chuan bi nen ung vien nay phai doi hoi giong het Dre/Ethan.

            l, c = image_rules_kite.check_unnamed_face(nhan, hinh[img]["original_path"], sl.get("subject"))

            loi += l

            canh += c

            if not sl.get("caption"):

                loi.append(f"slide {i}: có image thì phải có caption \"… · via <ai>\"")

            # ANH KHAI NIEM duoc dung o ca bia lan slide than (IMAGE_RULES
            # §1.2c noi long LOW-58, Ong Chu 15/09/2026: "anh nao cung dung
            # duoc, khong phai cau ne"). Truoc day chan cung o `figure` than;
            # gio chi CANH BAO de nguoi duyet biet day la anh minh hoa chu
            # de chu khong phai anh chup dung su kien.

            kn = hinh[img].get("concept") or {}

            if kn and i > 1:

                canh.append(f"slide {i}: 🧭 {img} là ẢNH KHÁI NIỆM ({kn.get('keyword')}) — "

                           "minh hoạ chủ đề, không phải ảnh chụp đúng sự kiện của tin.")


def _resolve_slide(i: int, sl: dict, hinh: dict, m: dict, da_thay: dict,
                loi: list, canh: list):
    """Mot slide cua vai -> mot slide cua render_edu, hoac None khi kind la.
    Tach khoi resolve_spec 07/09/2026: than vong lap dai 95 dong."""
    k = sl.get("kind")

    if k not in REQUIRED:

        loi.append(f"slide {i}: kind \"{k}\" không hợp lệ (cover/statement/steps/loop/figure/bars/cta)")

        return None

    thieu = [f for f in REQUIRED[k] if not sl.get(f)]

    if thieu:

        loi.append(f"slide {i} ({k}): thiếu {', '.join(thieu)}")

    # Khoa LONG (cards[].num, steps[].desc, bars[].label...) — renderer doc

    # cung nen thieu la KeyError sau khi da mo Chromium.

    # kiem_truong([sl]) chi thay MOT slide nen luon danh so "slide 1"; ban

    # truoc 07/09/2026 tim "slide {i}" de doi -> khong bao gio khop, moi loi

    # khoa long deu bao "slide 1" du o slide nao (test_spec_kite bat duoc).

    loi += [d.replace(f"slide 1 [{k}]", f"slide {i} ({k})")

            for d in render_edu.check_field([sl])

            if "[" in d and "thieu" in d and "]:" in d and

            not any(f"thieu '{f}'" in d for f in REQUIRED[k])]

    s2 = dict(sl)

    _check_figure_slide(i, sl, s2, hinh, m, da_thay, loi, canh)

    for f, gh in LIMIT.items():

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

                render_edu._value(b.get("value"))

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
    # `standfirst` khac caption/readmore.text o cho no la van xuoi tu do, nen
    # dung mau hep hon (_RE_NGUON_QUY) thay vi blunt substring nhu tren.
    sf = sl.get("standfirst")
    if isinstance(sf, str) and _RE_NGUON_QUY.search(sf):
        loi.append(f"slide {i}: dẫn nguồn ghi 'via', không ghi 'nguồn'")
    return s2


def resolve_spec(spec: dict, m: dict, wd) -> tuple:
    loi, canh = [], []
    slides = spec.get("slides") or []
    if not (6 <= len(slides) <= 10):
        loi.append(f"có {len(slides)} slide — cần 6..10")
    if slides and slides[0].get("kind") != "cover":
        loi.append("slide 1 phải là kind \"cover\"")
    hinh = {a["id"]: a for a in kb.figure_real(m)}
    da_thay = {}                    # hash anh -> nhan slide, TRONG BO nay (check_duplicate)
    # brand trong spec render la CHU in o masthead/folio (render_edu chi dung no
    # lam chu) -> phai la handle hien thi (dcgr -> dcgr.tech), khong phai slug.
    # d24ddfc da sua byline/follow, con masthead van in "dcgr" (05/09/2026).
    ra = {"brand": kb.handle_channel(m["brand"]), "section": spec.get("section") or "RESEARCH",
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
        s2 = _resolve_slide(i, sl, hinh, m, da_thay, loi, canh)
        if s2 is None:
            continue
        ra["slides"].append(s2)

    # Brief noi "CO n hinh that lien quan -> BAT BUOC dung it nhat mot"
    # (kite_prepare.py), nhung truoc 06/09/2026 khong cong nao kiem: vai bo qua
    # ca bang benchmark that roi ve vector, dung cai loi Ong Chu da bat 05/09
    # ("dung anh that khi engine tim duoc").
    # CHI ep khi anh DA DUOC NHIN (relevant is True). Vision tat/thieu
    # OPENAI_API_KEY thi moi anh co relevant=None, hinh_that van nhan het —
    # ep luc do la day quang cao / widget gia co phieu len slide, dung loai rac
    # ma vision sinh ra de loai (do 06/09/2026). Chua nhin thi goi y, khong ep.
    da_nhin = [ma for ma, a in hinh.items() if a.get("relevant") is True]
    co_anh = [sl for sl in slides if sl.get("image")]
    # BIA LUON PHAI LA ANH THAT — khong co ngoai le (Ong Chu 10/09/2026: *"khong
    # chap nhan viec dung vector o hero slide, thoi dai nay khong co anh gi ma
    # khong the tim duoc"*). Ban 10/09 sang chi chan khi CO ung vien, nen ba ca
    # van ra bia vector: 0 anh, vision tat, va tin chuyen sang chi con mot tam
    # (than gianh mat). Nay ca ba deu chan — im lang ve vector la giau mot that
    # bai cua vong tim anh duoi mot bo slide trong nhu that.
    #
    # Chan cung KHONG lam vai treo: `nc.count_round_error` dem ba vong loi Y HET
    # nhau roi bao vai `kanban_block` va day len Ong Chu — dung duong danh cho
    # "cong dang doi mot thu khong the co (thieu anh...)".
    hero = kb.figure_hero(m)
    if not (slides and slides[0].get("image")):
        chua = [ma for ma, a in hinh.items() if a.get("relevant") is None]
        if hero:
            loi.append(f"bìa đang vẽ hero vector trong khi có hình thật dùng được ({hero['id']}) — "
                       f"đặt `\"image\": \"{hero['id']}\"` + `\"caption\"` vào slide 1 (cover). "
                       "Hình thật nói nhiều hơn một sơ đồ tự vẽ; bìa có ảnh thì cả bộ không vẽ hero art.")
        elif chua:
            # Co anh nhung CHUA AI NHIN: khong duoc ep len bia (day quang cao/
            # banner len bia), ma cung khong duoc ve vector. Day la hong khau
            # van hanh, khong phai lua chon bo cuc — noi thang thu can bat.
            loi.append(f"bìa không có ảnh, mà {len(chua)} hình ({', '.join(chua)}) thì vision CHƯA "
                       "NHÌN (router tắt/thiếu OPENAI_API_KEY) nên chưa được phép lên bìa. Bìa "
                       "KHÔNG được vẽ hero vector. Bật vision rồi chạy lại "
                       f"`kite_prepare.py {m.get('draft_id', '<id>')} --lam-moi`.")
        else:
            # 0 anh SAU KHI `kite_prepare.ensure_has_cover` da tu chay lai vong
            # tim — nen day khong con la "vai luoi", ma la vong tim that su ve
            # trang. Ong Chu 10/09/2026: "Dre tim duoc anh dung... ko co ly gi
            # ma ko tim duoc anh de bao hong" — nen dong dau tien phai la MOT
            # LAN NUA, va chi khi lan do cung trang moi den luot bao len.
            loi.append("bìa không có ảnh thật và vòng tìm ảnh về trắng — bìa KHÔNG được vẽ hero "
                       f"vector. `kite_prepare.py {m.get('draft_id', '<id>')}` đã tự tìm lại một "
                       "lượt (ảnh thương hiệu §1.2d + ảnh khái niệm §1.2c, cùng máy móc Dre dùng). "
                       f"Chạy tay thêm một lượt: `kite_prepare.py {m.get('draft_id', '<id>')} "
                       "--lam-moi`. Vẫn trắng thì `kanban_block` kèm nguyên văn dòng này — engine "
                       "về trắng cho một tin có thật là việc của Ông Chủ, không phải của vai.")
    if da_nhin and not co_anh:
        loi.append(f"có {len(da_nhin)} hình thật dùng được ({', '.join(da_nhin)}) mà không slide nào dùng — "
                   "BẮT BUỘC dùng ít nhất một: `figure` cho chart/bảng, hoặc image ở bìa. "
                   "Vẽ vector hết trong khi có hình thật là bỏ phí bằng chứng của bài.")
    # SO ANH THAT toi thieu theo SO SLIDE (LOW-45, Ong Chu 12/09/2026: "bài có 8
    # slide thì tối thiểu phải có 3 hình thật") — khac han cong "it nhat mot" o
    # tren: cong do chi doi KHONG VE VECTOR HET khi co anh, cong nay doi DIEN
    # RONG hon cho bo nhieu slide, tranh ca dcgr Moonshot 12/09: engine tim ra 6
    # anh that (A1..A6) ma bo 8 slide chi dung DUNG MOT anh, lap lai o ca bia
    # lan than. Dem theo MA KHAC NHAU tren slide (khong theo so slide co anh) vi
    # dung lai cung mot ma o hai slide da bi `check_duplicate` (§8) chan rieng.
    # CHI chan cung khi NGUON DU (du_nhin >= muc can) — thieu nguon that thi chi
    # canh bao, khong bay ra thu Kite khong the co.
    so_slide_moi_anh = len(slides)
    can_toi_thieu = -(-so_slide_moi_anh // SLIDE_NEW_IMAGE_REAL)     # ceil khong import math
    ma_da_len_slide = {sl.get("image") for sl in slides if sl.get("image")}
    if len(ma_da_len_slide) < can_toi_thieu:
        thong_diep = (f"{so_slide_moi_anh} slide cần tối thiểu {can_toi_thieu} ảnh thật KHÁC NHAU "
                     f"(1 ảnh thật / {SLIDE_NEW_IMAGE_REAL} slide, Ông Chủ 12/09/2026) — hiện chỉ "
                     f"{len(ma_da_len_slide)} mã lên slide ({', '.join(sorted(ma_da_len_slide)) or 'không có'}).")
        if len(da_nhin) >= can_toi_thieu:
            loi.append(thong_diep + f" Vòng tìm đã có {len(da_nhin)} ảnh thật dùng được "
                       f"({', '.join(da_nhin)}) — dùng thêm ảnh KHÁC nhau cho các slide `figure`, "
                       "đừng lặp một tấm ở nhiều slide.")
        else:
            canh.append(thong_diep + f" Vòng tìm chỉ ra {len(da_nhin)} ảnh dùng được — không đủ "
                       "nguồn nên không chặn cứng, nhưng nên tìm thêm nếu còn thời gian.")
    # TIN CHUYEN TU DRE/ETHAN vi thieu anh: sieu chat hon mot bac (Ong Chu
    # 09/09/2026: "sau khi tim duoc hinh tot ma van ko du de lam va pass qua cho
    # Kite thi Kite cung phai dung nhung hinh do trong body"). Cong "it nhat
    # mot" o tren van cho phep dat DUY NHAT mot tam len bia roi ve vector ca
    # than — dung cai bi che. O day doi DU MA va doi co hinh ngoai bia.
    ep = kb.figure_right_use(m)
    if ep:
        # Chay DOC LAP voi cong tren (khong `elif`): bo khong dung tam nao thi
        # vai can biet CA "thieu ma nao" ngay vong nay, khong phai sua hai vong.
        tu_vai = kb.transfer_from_role(m)
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
    # CO Y tinh lai tu `hinh` (= kb.hinh_that(m), da loc >= 800px va bo mat
    # nguoi khong ro ai), KHONG doc thang m["not_yet_seen"]: khoa do trong manifest
    # tinh tren TOAN BO m["images"] chua loc (prepare/manifest.py), nen se ke ca
    # anh nho <800px ma Kite khong bao gio dung duoc — doc thang no vao day se
    # bao "vision chưa nhìn" cho mot anh khong the thanh candidate, dung loai
    # canh bao gia da bi bat 08/09/2026 (b403ca4) o cong "nguon/via" ben tren.
    # `da_nhin` cung tinh cung cach tu `hinh` (khong co khoa manifest tuong
    # duong) nen hai tap phai chung mot vu tru moi so sanh dung.
    chua_nhin = [ma for ma, a in hinh.items() if a.get("relevant") is None]
    if chua_nhin and not da_nhin:
        canh.append(f"vision chưa nhìn {', '.join(chua_nhin)} (router tắt/thiếu khoá) — "
                    "hình thật CHƯA được kiểm nội dung, chỉ dùng khi bạn tự tin nó đúng bài")
    # CHI quet cac truong CHU HIEN THI tren slide — truoc day doc het sl.values()
    # nen an ca "image" (ma anh noi bo nhu "A13") vao chu, bao nham so 13 la bia
    # (Ong Chu 15/09/2026). "kind" cung la truong dieu khien, khong hien thi.
    chu = " ".join(str(sl.get(k) or "") for sl in slides
                   for k in ("eyebrow", "title", "standfirst", "callout", "caption"))
    canh.extend(nc.check_numbers_on_card(chu, m, wd))
    return ra, loi, canh


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop carousel.edu cua Kite (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--spec")
    ap.add_argument("--khong-gui", action="store_true")
    ap.add_argument("--bo-qua-dau", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    import role
    role.set_active_role("kite")

    meta, brand, wd, m, spec, spec_path, da_dung = nc.load_draft_context(a.draft_id, a.spec, "kite_prepare.py", "kite_submit.py")
    spec = role_spec.kite_spec(spec)         # LOW-248: spec viet truoc deploy con ten cu
    spec_r, loi, canh = resolve_spec(spec, m, wd)
    hook = (spec.get("slides") or [{}])[0].get("title", "")
    if da_dung:
        if (spec.get("theme"), spec.get("hero")) == (da_dung.get("theme"), da_dung.get("hero")):
            loi.append("LÀM LẠI: theme và hero trùng lần trước — đổi ít nhất một")
        if nc.normalize(hook) == nc.normalize(da_dung.get("hook")):
            loi.append("LÀM LẠI: hook bìa giống lần trước — viết khác")
    for c in canh:
        print(f"[CANH BAO] {c}")
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return nc.count_round_error(wd, loi,
                               f"venv/bin/python kite_submit.py {a.draft_id}")

    out = Path(a.out or meta.get("image") or str(DRAFTS / f"{a.draft_id}.png"))
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    for p in env_load.album_secondary(stem.name, stem.parent):
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
        print(f"\nSua {spec_path} theo bao loi roi chay lai: venv/bin/python kite_submit.py {a.draft_id}")
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
    bg_path = state_paths.handoff_file(wd if a.khong_gui else DRAFTS, a.draft_id)
    bg_path.write_text(bg, encoding="utf-8")

    mid = None
    if a.khong_gui:
        print(f"[thu] khong gui Telegram (--khong-gui). {n} slide o {out.parent}")
    else:
        mid = nc.send_album("kite", files, f"Carousel edu {n} slide: {hook}", a.draft_id, wd, da_dung,
                           {"theme": theme, "hero": hero, "hook": hook,
                            # ma hinh THAT da dat len slide — de bai sau (ke ca
                            # cua Dre/Ethan) khong dung lai (06/09/2026).
                            "image_ids": [sl.get("image") for sl in (spec.get("slides") or [])
                                     if sl.get("image")]})
    # Bang den (kanban swarm): ban giao co cau truc cua Kite len the goc + dong
    # "[metadata]" de Kite dan vao kanban_complete -> Miles thay trong
    # "Parent task results". Best-effort.
    md = {"slide": n, "hook": hook, "theme": theme, "hero": hero, "image_ids": hinh,
          "file_path": str(out), "handoff_path": str(bg_path), "message_id": mid, "role": "kite"}
    if not a.khong_gui:
        nc.write_blackboard(a.draft_id, "images", md, "kite")
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
