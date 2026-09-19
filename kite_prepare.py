#!/usr/bin/env python3
"""kite_prepare.py — BRIEF cho Kite (carousel.edu, render_edu.py).

Kite dung art vector goc, KHONG anh that — tru bieu do/bang co that trong bai
(kind `figure`, hoac bia co `image`). Phan co hoc (nguon, chu bai, chup bang/
figure, tu lieu) nam o image_prepare.py dung chung; tep nay in brief theo cach
nhin cua Kite: tu lieu de dien dat lai paper, danh sach HINH THAT la chart
(>= 800px) dung duoc cho `figure`, theme/hero goi y (khong trung bo gan day),
va khung spec 7 kind voi gioi han do dai tung truong (do theo co chu trong
render_edu.py de khong tran).

Do 04/09/2026 truoc khi doi: moi task Kite 32 tool call — ls 18, skill_view 13,
read_file 19, vision_analyze 13 (doc skill + reference + mo tung slide ra xem).

Dung:
    venv/bin/python kite_prepare.py <draft_id>
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                    # noqa: E402
import role as vai_mod                                        # noqa: E402
import route_missing_images                                       # noqa: E402
import manifest_values                                       # noqa: E402
import state_paths                                                # noqa: E402


def handle_channel(brand: str) -> str:
    """Handle hien thi cua brand KHONG co "@" (slide cuoi tu ghep): dcgr ->
    dcgr.tech (Ong Chu 05/09/2026: slide cuoi in 'Theo doi @dcgr' vi dung thang
    slug). Mot ban o env_load.handle_channel (ADF-r2-9) — truoc day ban nay khong
    doi 'blog' -> 'donniechublog' nhu bob_submit."""
    import env_load
    return env_load.handle_channel(brand, co_a_cong=False)


FIG_EMPTY_MIN = 800
# Tran hinh BAT BUOC: bo chi duoc 6..10 slide, tru bia va cta con 8. Ep het khi
# engine tim duoc 9 tam la hai cong da nhau, vai khong co duong nao nop duoc.
MAX_FORCE_FIGURE = 6


def transfer_from_role(m: dict) -> str:
    """Tên vai đã CHUYỂN tin này sang Kite vì thiếu ảnh thật ("Dre"/"Ethan"), hoặc "".

    Mọi đường vào Kite đều là đường THIẾU ẢNH: `approve_post` chỉ gắn nút "Gửi Kite"
    ở hai chỗ báo thiếu ảnh, và `route_missing_images.after_prepare` tự chuyển khi 0
    ảnh. Cả hai đều đi qua `create_task_kite`, nơi ghi `transferred_from` vào img.json —
    manifest.json thì KHÔNG có (nút của Ông Chủ bấm sau khi engine đã ghi xong).
    """
    im = cb._read_json(cb.DRAFTS / (str(m.get("draft_id", "")) + ".img.json"), {}) or {}
    tu = im.get("transferred_from") or ""
    if tu:
        return vai_mod.display_name(tu)      # ban dang ky: role.py (audit A4)
    return "vai ảnh" if (m.get("kite_task_id") or im.get("kite_task_id")) else ""


def figure_real(m: dict) -> list:
    """Hinh THAT Kite duoc dung: chart/bang VA anh chup, dieu kien: engine da nhin
    va khong danh dau KHONG LIEN QUAN, >= 800px. Ong Chu 05/09/2026: "Dre tim
    duoc 1-2 anh chat luong thi Kite cung nen dua vao slide, chu khong chi text
    & card don dieu". Truoc do chi lay chart -> anh chup bi bo, con chart khong
    lien quan (Fear&Greed) van lot.

    KHONG con loai cung anh "KHONG RO AI" o day (LOW-186, 16/09/2026): Dre/Ethan
    khong loai o buoc chuan bi nay, chi chan luc NOP neu khong khai duoc
    `subject` (`check_unnamed_face`) — Kite truoc day loai thang tu day nen
    ca khi vai da xac minh duoc ten that (vd doc dung bai goc), anh van khong
    bao gio toi duoc buoc nop de khai ten. Ghi chu "KHONG RO AI" van con trong
    `notes` de brief/vai biet ma nao can khai `subject` truoc khi dung.

    Loai them anh co `uses` rong/falsy (LOW-189, 16/09/2026): image_concept.
    label_concept() gan `uses = []` cho anh khai niem dang chart/co mat nguoi
    ma KHONG dong thoi dat relevant = False, nen truoc ban va nay anh da bi
    chinh engine danh dau "khong co cho nao dung duoc" van lot qua day va bi
    dem la hinh that dung duoc, khien cong SLIDE_NEW_IMAGE_REAL doi vai dung
    anh sai chu de."""
    ra = []
    for a in m["images"]:
        if a["w"] < FIG_EMPTY_MIN or a.get("relevant") is False:
            continue
        if "uses" in a and not a.get("uses"):
            continue
        ra.append(a)
    return ra


def figure_open_mark(ht: list) -> dict | None:
    """Hinh MO DAU cua paper trong danh sach hinh that (Figure 1, hoac hinh paper
    dau tien boc duoc), hoac None. Do la tam dung lam hero cua bia."""
    paper = [a for a in ht if a.get("paper_figure")]
    return paper[0] if paper else None


def figure_hero(m: dict) -> dict | None:
    """Tam duoc chon lam HERO cua bia, hoac None khi bia ve vector.

    Ong Chu 10/09/2026: *"kite van dung vector lam hero, chua su dung anh"*. Ban
    truoc (08/09) chi chi dinh hero khi anh co `paper_figure`, tuc **chi bai
    arxiv**: moi tin con lai — anh chup, tru so, co nuoc, bieu do — brief noi
    "bia `image` HOAC `figure`" (tuy chon) va cong chi doi "dung it nhat mot anh
    o dau do", nen dat het vao `figure` than roi ve hero vector la HOP LE.

    Thu tu theo IMAGE_RULES: hinh paper (§1.4 "Figure 1 la hero") -> anh rieng cua
    tin -> anh thuong hieu (§1.2d) -> anh khai niem (§1.2c) -> khoi tit chup trang
    nguon (nac cuoi cung, xem `capability_block_headline`); ba loai sau xep sau
    moi anh rieng cua tin, dung nhu tai lieu ghi.

    Chi anh DA DUOC NHIN, tru hinh paper (boc thang tu PDF nen khong the la
    quang cao): vision tat thi moi anh co `relevant=None`, ep luc do la day
    banner len bia — cung bai hoc voi `figure_right_use`.

    MOT nguon cho ca brief lan cong chan (`kite_submit`).
    """
    ut = [a for a in figure_real(m)
          if a.get("relevant") is True or a.get("paper_figure")]
    if not ut:
        return None
    # LOW-254 (18/09/2026): "khoi tit chup trang nguon" (`capture_kind ==
    # "headline"`) la NAC CUOI CUNG theo chinh ghi chu cua no ("chi lam bia khi
    # khong con anh nao khac", `prepare/fallback_rounds.py`) — tach rieng khoi
    # `rieng` de no KHONG duoc xep ngang hang voi anh rieng that su cua tin, va
    # nam sau ca anh khai niem trong `xep`.
    is_headline_capture = lambda a: a.get("capture_kind") == "headline"   # noqa: E731
    rieng = [a for a in ut
             if not (a.get("concept") or a.get("brand_match") or is_headline_capture(a))]
    xep = ([a for a in rieng if a.get("paper_figure")] + rieng
           + [a for a in ut if a.get("brand_match")]
           + [a for a in ut if a.get("concept")]
           + [a for a in ut if is_headline_capture(a)])
    # Tin CHUYEN sang Kite vi thieu anh: `kite_submit` doi hinh that nam o slide
    # THAN (Ong Chu 09/09), ma cung mot anh khong len duoc hai slide
    # (`image_rules.check_duplicate`). Tam nao bi than giu doc quyen thi LUI xuong ung
    # vien ke tiep, de ca hai tam deu duoc dung: anh khai niem khong nam trong
    # `_force_raw` (§1.2c cam no o than) nen no nhan bia khi anh rieng bi than giu.
    ep = _force_raw(m)
    # LOW-254: nhung "lui xuong ung vien ke tiep" o tren KHONG duoc dung toi
    # khoi tit chup trang nguon khi con anh khac trong `xep` — bug that: bo Cohere
    # x Aleph Alpha chi co dung 2 anh (A1 anh ghep logo hai hang, A8 khoi tit chup
    # tu prnewswire.com, roi/cluttered), `_force_raw` giu doc quyen A1 o than nen
    # vong lui cu tuot xuong A8 lam hero — dung nguoc chinh cai thu tu no tu ghi
    # ("chi lam bia khi khong con anh nao khac"). Chi cho khoi tit len hero khi
    # no la ung vien DUY NHAT trong `xep` (khong con anh nao khac de chon).
    has_other_candidate = any(not is_headline_capture(a) for a in xep)
    for chon in xep:
        if is_headline_capture(chon) and has_other_candidate:
            continue
        if not ep or [ma for ma in ep if ma != chon["id"]]:
            return chon
    # Chi con DUNG MOT tam (hoac vong tren khong con ai ngoai khoi tit de lui
    # xuong, LOW-254): BIA THANG (Ong Chu 10/09/2026: *"khong chap nhan viec
    # dung vector o hero slide"*). Ban truoc tra None o day — than thang va bia
    # ve vector. Vong doi cua §1.2e ("phai co hinh o BODY") sinh ra tu ca NHIEU
    # tam ma Kite chi dung mot; con mot tam thi no VAN duoc dung, chi la dung o
    # bia. `figure_right_use` tru tam nay ra nen than khong doi no nua.
    return xep[0]


def _hero_what_is(h: dict) -> tuple:
    """(tam nay LA GI, caption goi y) cho dong ⭐ HERO."""
    if h.get("paper_figure"):
        return (f"{h['paper_figure']} — hình mở đầu của chính paper, tấm nói nhiều nhất về bài",
                f"{h['paper_figure']} trong paper · via <ai>")
    if h.get("capture_source"):
        # LOW-22: `classify` doc anh chup trang la loai "chart" — khong co nhanh
        # nay thi brief goi no la "bieu do/bang cua bai", vai chu thich sai.
        return (f"khối lead (ảnh chính + tít) chụp từ chính trang {h.get('domain', 'nguồn')} "
                "ở khung điện thoại — Ông Chủ 12/09/2026: cắt lấy khối lead rồi làm bìa",
                f"Ảnh chụp từ {h.get('domain', 'trang nguồn')} · via {h.get('domain', '<ai>')}")
    if h.get("concept"):
        tk = h["concept"].get("keyword", "")
        return (f"ảnh khái niệm ({tk}) — minh hoạ chủ đề, không phải ảnh chụp đúng sự kiện",
                f"{tk} · via Wikimedia Commons")
    if h.get("brand_match"):
        return (f"ảnh thương hiệu của {h['brand_match'].get('company')} (xem nhãn ở trên để "
                "chú thích đúng loại: cơ sở · chân dung · bảng xếp hạng · thẻ logo)",
                "<chú thích đúng loại tấm> · via <ai>")
    return ("biểu đồ/bảng của bài" if h["kind"] == "chart" else "ảnh chụp của bài",
            "<chú thích ngắn> · via <ai>")


def line_hero(m: dict) -> list:
    """Dong chi cho Kite dat tam nao len bia, hoac [] khi bia ve vector."""
    h = figure_hero(m)
    if not h:
        return []
    la_gi, cap = _hero_what_is(h)
    return ["", f"⭐ HERO: {h['id']} là {la_gi}. Đặt `\"image\": \"{h['id']}\"` vào SLIDE 1 "
                f"(cover) kèm `\"caption\": \"{cap}\"`; lúc đó bìa lấy chính hình đó làm hero, "
                "KHÔNG vẽ hero art — `kite_submit.py` chặn bìa vector khi có hình thật dùng được. "
                "Chỉ bỏ qua khi hình sai bài (xem contact_sheet.png) — lúc đó nói rõ một câu vì sao. "
                "Hình còn lại để cho `figure`."]


def _force_raw(m: dict) -> list:
    """Mã hình thật bị ép vào bộ khi tin chuyển sang Kite — CHƯA trừ tấm lên bìa.

    Tách khỏi `figure_right_use` 10/09/2026 để cắt vòng gọi: `figure_hero` cần biết
    tấm nào bị thân giữ, mà `figure_right_use` lại cần biết tấm nào đã lên bìa.
    """
    if not transfer_from_role(m):
        return []
    # `capture_source` (LOW-22) di cung duong voi khai niem: no la BIA, khong ep
    # xuong than — mot man hinh trang bao dat o `figure` la lap lai tit cua bai.
    return [a["id"] for a in figure_real(m)
            if a.get("relevant") is True and not a.get("concept")
            and not a.get("capture_source")][:MAX_FORCE_FIGURE]


def figure_right_use(m: dict) -> list:
    """Mã hình BẮT BUỘC vào SLIDE THÂN, khi tin được CHUYỂN sang Kite vì thiếu ảnh.

    Ông Chủ 09/09/2026: *"sau khi tìm được hình tốt mà vẫn ko đủ để làm và pass
    qua cho Kite thì Kite cũng phải dùng những hình đó trong body"*. Rỗng khi
    tin không phải hàng chuyển sang, hoặc chưa ai nhìn ảnh (vision tắt thì ép là
    đẩy quảng cáo/widget lên slide — xem chú thích cùng loại ở kite_submit).

    KHÔNG ép **ảnh khái niệm** vào đây (dù §1.2c từ LOW-58, 15/09/2026 đã cho
    phép nó vào slide thân — đây chỉ là THỨ TỰ ƯU TIÊN, không phải luật cấm):
    ảnh khái niệm hợp làm bìa hơn, nên để nó ưu tiên `figure_hero`; vai vẫn có
    thể tự đặt nó vào `figure` thân nếu muốn, cổng không chặn nữa.
    Ảnh thương hiệu thì Ở LẠI: §1.2d cho nó vào thân (ảnh thật của chính hãng
    trong tin).

    **Trừ tấm đã lên bìa** (`figure_hero`): cùng một ảnh không lên được hai slide
    (`image_rules.check_duplicate` §8), nên để nó trong danh sách này là đòi một thứ bất
    khả. Hệ quả: tin chỉ có ĐÚNG MỘT tấm thì danh sách rỗng — tấm đó lên bìa và
    thân không đòi gì nữa (§1.2f, Ông Chủ 10/09/2026: không chấp nhận hero
    vector). Đòi của §1.2e sinh ra từ ca NHIỀU tấm mà Kite chỉ dùng một.

    MỘT nguồn cho cả brief lẫn cổng chặn: hai bản đếm khác nhau là brief bảo
    dùng 3 mã còn cổng đòi 4.
    """
    h = figure_hero(m)
    return [ma for ma in _force_raw(m) if not (h and ma == h["id"])]


def ensure_has_cover(draft_id: str, m: dict, wd, khong_browser: bool, cho: int,
                   da_lam_moi: bool = False) -> tuple:
    """Kite KHÔNG được thừa kế một bộ ảnh không đủ cho nhu cầu của chính Kite.

    Ông Chủ 10/09/2026: *"Dre tìm được ảnh đúng, nên kỹ năng tìm ảnh đó dùng
    được. ko có lý gì mà ko tìm được ảnh để báo hỏng"*.

    Đo hôm đó, cả chuỗi: (1) `image_prepare.run` trả thẳng `manifest.json` cũ khi tệp
    đã có (`if xong.exists() and not lam_moi`), (2) task body giao cho Kite chạy
    `kite_prepare.py <id>` — KHÔNG có `--lam-moi`. Nên khi tin được chuyển sang
    Kite vì thiếu ảnh, Kite **đọc lại đúng kết quả đã thất bại của vai cũ** và
    vòng tìm ảnh KHÔNG BAO GIỜ chạy lần nữa. Kỹ năng tìm ảnh có sẵn, chỉ là
    không ai gọi nó cho Kite.

    Hai vai dừng ở hai ngưỡng khác nhau: vai cũ cần đủ ~5 ảnh cho carousel và
    bỏ cuộc khi thiếu; Kite chỉ cần **một tấm lên bìa** (§1.2f) — rẻ hơn nhiều.
    Nên "vai cũ không đủ" không hề có nghĩa "Kite không đủ", và bắt Kite chịu
    chung kết luận là sai từ gốc.

    Chạy lại ĐÚNG MỘT lần (`da_lam_moi` chặn đệ quy), và chỉ khi thật sự chưa có
    tấm nào lên bìa được. Trả `(m, wd)`.
    """
    if da_lam_moi or figure_hero(m) is not None:
        return m, wd
    print("[kite] khong co tam nao len bia duoc -> CHAY LAI vong tim anh "
          "(anh thuong hieu + anh khai niem), khong thua ke ket qua cua vai cu.",
          file=sys.stderr)
    m2, wd2, _ = cb.run(draft_id, True, khong_browser, cho,
                         sau_chuan_bi=route_missing_images.after_prepare)
    h = figure_hero(m2)
    print(f"[kite] sau khi tim lai: {'bia = ' + h['id'] if h else 'VAN CHUA co tam nao len bia duoc'}",
          file=sys.stderr)
    return m2, wd2


def call_y_tone(title: str) -> tuple:
    """(theme, hero, gan_day) — chon cai chua dung gan day, xoay theo tieu de."""
    import render_edu
    gan = render_edu._theme_near_bottom(4)
    try:
        theme, hero = render_edu.pick_theme_auto({"folio": title}, False)
    except SystemExit:
        theme, hero = "orbit", "orbit"
    return theme, hero, gan


def write_brief(m: dict, da_dung: dict | None) -> str:
    theme, hero, gan = call_y_tone(m["title"])
    # Khung in sẵn MỘT `figure` cho mỗi mã bắt buộc, để vai khỏi phải tự suy ra
    # "à, ba hình thì ba slide". `figure_right_use` đã trừ tấm lên bìa, nên khung
    # không bao giờ in cùng một mã ở cả cover lẫn `figure` (`check_duplicate` chặn).
    hero_anh = figure_hero(m)
    ep_khung = figure_right_use(m)
    import brief_common
    L = brief_common.mark(
        m, "KITE",
        f"Brand: {m['brand']} | draft: {m['draft_id']} | 6..10 slide, slide 1 là cover | "
        "art vector gốc, KHÔNG ảnh thật trừ hình thật liệt kê dưới")
    L += brief_common.block_redo(
        da_dung, f"theme={da_dung.get('theme')} hero={da_dung.get('hero')}, hook "
                 f"“{da_dung.get('hook', '')}”. Lần này BẮT BUỘC đổi theme hoặc hero, "
                 "và đổi hook/cách chia slide." if da_dung else "")
    L += brief_common.block_material(
        m, tieu_de="## Tư liệu (diễn đạt lại cho tường minh, KHÔNG bịa số, KHÔNG bịa quote)",
        n_cau=25, n_doan=1500,
        dong_thieu="(Không bóc được chữ từ nguồn — chỉ dùng tóm tắt, KHÔNG bịa.)")
    L += ["", "## Hình thật dùng được cho `figure` / bìa `image` (đã nhìn, ≥ 800px)"]
    ht = figure_real(m)
    if not ht:
        L.append("Không có hình thật nào liên quan — dùng art vector cho cả bộ (bình thường với paper trắng).")
    else:
        nhin = [a for a in ht if a.get("relevant") is True]
        tu_vai, ep = transfer_from_role(m), figure_right_use(m)
        if ep:
            # Ong Chu 09/09/2026: "sau khi tim duoc hinh tot ma van ko du de lam
            # va pass qua cho Kite thi Kite cung phai dung nhung hinh do trong
            # body". Truoc do brief chi doi "it nhat mot", ma mot tam thi Kite
            # de len bia roi ve vector ca body — dung cai Ong Chu che. `ep` da
            # tru tam len bia, nen o day ke ca hai phia cho vai khoi tuong bia
            # khong tinh.
            tong = len(ep) + (1 if hero_anh else 0)
            L.append(f"🔁 TIN NÀY CHUYỂN TỪ {tu_vai} SANG KITE VÌ THIẾU ẢNH THẬT — nhưng "
                     f"{tong} tấm engine tìm được KHÔNG BỊ BỎ ĐI. Luật cho bộ này:")
            if hero_anh:
                L.append(f"- **{hero_anh['id']} lên BÌA** (slide 1) — xem ⭐ dưới.")
            L.append(f"- **Cả {len(ep)} mã còn lại ({', '.join(ep)}) phải xuất hiện** trong spec — "
                     "thiếu tấm nào `kite_submit.py` chặn, kèm tên mã.")
            L.append("- **Phải có hình ở BODY**, không chỉ ở bìa: mỗi tấm một slide `figure` "
                     "(`\"image\": \"<mã>\"` + `\"caption\": \"… · via <ai>\"`). Đặt hết lên bìa "
                     "rồi vẽ vector cả thân là đúng cái lỗi khiến tin phải chuyển sang đây.")
            L.append("- Vector chỉ để lấp phần CÒN THIẾU (steps/loop/bars/statement), không thay "
                     "cho bằng chứng thật đã có.")
        elif nhin:
            L.append(f"CÓ {len(nhin)} hình thật ĐÃ NHÌN và liên quan → BẮT BUỘC dùng ít nhất một: "
                     "`figure` cho chart/bảng, bìa `image` hoặc `figure` cho ảnh chụp"
                     + (" — và một tấm phải lên BÌA làm hero, xem ⭐ dưới. "
                        if hero_anh else ". ")
                     + "Bộ toàn text & card khi có ảnh thật là thiếu.")
        else:
            # Vision tat/thieu khoa -> moi anh relevant=None. Khong duoc ep.
            L.append(f"Có {len(ht)} hình đủ khổ nhưng ⚠️ CHƯA AI NHÌN (vision không chạy) — chưa biết "
                     "chúng có đúng bài không. Dùng thì tự kiểm bằng contact_sheet.png, không bắt buộc.")
    for a in ht:
        kieu = ("BIỂU ĐỒ/BẢNG" if a["kind"] == "chart" else "ẢNH CHỤP") + \
               ("" if a.get("relevant") is True else " ⚠️CHƯA NHÌN")
        th = a.get("brand_match") or {}
        # Anh THUONG HIEU: noi ro no LA GI, vi caption phai khac nhau han. Mot the
        # logo bi chu thich "anh tru so" la sai su that (09/09/2026).
        nhan_th = {"photo": f"🏢 ảnh cơ sở của {th.get('company')} (KHÔNG phải ảnh của sự việc)",
                   "person": f"👤 chân dung {th.get('person_role', 'lãnh đạo')} {th.get('company')}: "
                            f"{th.get('person')} — caption phải nêu đúng tên này, và chỉ dùng khi "
                            "bài có nhắc người đó",
                   "logo": f"🔖 THẺ LOGO {th.get('company')} (logo chính thức trên nền trơn) — hợp làm "
                           "bìa, đừng chú thích như ảnh chụp",
                   "ranking": f"📊 bảng {th.get('site')} · {th.get('board')} có {th.get('company')} — "
                               "KHÔNG phải bảng của tin này, caption ghi rõ nguồn + tên bảng",
                   }.get(th.get("kind"), "")
        # Anh KHAI NIEM: no la anh chup that nen di qua moi cong ky thuat; tu
        # LOW-58 (15/09/2026) duoc dung o ca bia lan than, uu tien bia hon.
        kn = a.get("concept") or {}
        nhan_kn = (f"🧭 ẢNH KHÁI NIỆM ({kn.get('keyword')}) — minh hoạ chủ đề, KHÔNG phải "
                   "ảnh của tin: ưu tiên dùng ở bìa (slide 1), vẫn dùng được ở slide thân "
                   "nếu cần; caption 'via Wikimedia Commons'") if kn else ""
        L.append(f"- {a['id']}: {kieu} {a['w']}x{a['h']} ({a['ratio']}) | nguồn: {a['domain'] or manifest_values.source_label(a['source'])}"
                 + (f" | {a['paper_figure']} của chính paper" if a.get("paper_figure") else "")
                 + (f" | {nhan_kn}" if nhan_kn else "")
                 + (f" | {nhan_th}" if nhan_th else "")
                 + (f" | ảnh là: {a['description'][:90]}" if a.get("description") else (f" | alt: {a['alt'][:70]}" if a.get("alt") else ""))
                 + (" | có mặt người: khai \"subject\": \"<tên>\" vào slide dùng mã này (nếu xác minh "
                    "được qua chính bài/nguồn) rồi ghi đúng tên đó trong caption — không xác minh được "
                    "thì đổi mã khác, đừng đoán tên" if a.get("faces") else ""))
    L += line_hero(m)
    import story_type
    L += story_type.line_brief(m)
    rac = [a["id"] for a in m["images"] if a.get("relevant") is False]
    if rac:
        L.append(f"Không dùng (engine đánh dấu không liên quan): {', '.join(rac)}")
    L.append(f"Nhìn tất cả trong MỘT tấm: {m['workdir']}/{state_paths.CONTACT_SHEET_FILE} (chỉ khi cần).")
    L += ["", "## Tone cho bộ này (mỗi bộ một tone, không trùng bộ gần đây)",
          f"Gợi ý: theme={theme}, hero={hero}. Gần đây đã dùng: {gan or 'chưa có'}.",
          "theme: orbit (agent/hệ thống) | ember (hiệu năng/cảnh báo) | moss (dữ liệu mở/tăng trưởng) | "
          "ink (benchmark/học thuật) | rose (sinh ảnh/sáng tạo). hero: orbit (phân việc) | grid (bảng số) | "
          "wave (xu hướng) | rings (độ chính xác) | graph (quan hệ)."]
    L += ["", f"## Viết spec vào: {m['workdir']}/spec.json  (6..10 slide; mỗi slide MỘT ý; tiếng Việt có dấu)"]
    khung = {
        "theme": theme, "hero": hero,
        "section": "<CHUYÊN MỤC ≤ 24 ký tự, vd RESEARCH · ARXIV>",
        "folio": "<TÊN NGẮN CỦA BÀI ≤ 24 ký tự>",
        "slides": [
            {"kind": "cover", "eyebrow": "<CHUYÊN MỤC · DEEP DIVE, ≤ 28>", "title": "<hook ≤ 60 ký tự>",
             "accent": "<cụm trong title cần nhấn>", "standfirst": "<1 câu ≤ 200 ký tự>",
             "byline": [handle_channel(m["brand"]), "Phân tích", "5 phút đọc"],
             "image": (hero_anh["id"] if hero_anh else "<mã hình thật A? nếu bìa dùng ảnh, hoặc bỏ>"),  # noqa: E501
             "caption": (_hero_what_is(hero_anh)[1] if hero_anh
                         else "<'… · via <ai>' bắt buộc khi có image>")},
            {"kind": "statement", "eyebrow": "BỐI CẢNH", "title": "<≤ 60>", "accent": "<cụm nhấn>",
             "standfirst": "<≤ 220>", "cards": [{"num": "01", "text": "<≤ 90>"}, {"num": "02", "text": "<≤ 90>"}]},
            {"kind": "steps", "eyebrow": "CÁCH VẬN HÀNH", "title": "<≤ 60>",
             "steps": [{"title": "<≤ 30>", "desc": "<≤ 80>"}, {"title": "…", "desc": "…"}, {"title": "…", "desc": "…"}]},
            *[{"kind": "figure", "eyebrow": "SỐ LIỆU", "title": "<≤ 60, tối đa 2 dòng>",
               "accent": "<cụm>", "image": ma, "caption": "<… · via <ai>>",
               "standfirst": "<≤ 200>"} for ma in (ep_khung or ["<mã hình thật A?>"])],
            {"kind": "bars", "eyebrow": "SỐ LIỆU", "title": "<≤ 60>", "accent": "<cụm>",
             "bars": [{"label": "<≤ 28>", "value": "<số THẬT trong bài, viết dạng số>", "text": "<cách ghi, vd 2,75 USD>"},
                      {"label": "<≤ 28>", "value": "<số>", "text": "<…>", "highlight": True}],
             "caption": "<Số trong bài · via <ai>>", "standfirst": "<≤ 160, tuỳ chọn>"},
            {"kind": "loop", "eyebrow": "CƠ CHẾ", "title": "<≤ 60>", "accent": "<cụm>",
             "chips": ["<≤ 3 từ>", "<≤ 3 từ>", "<≤ 3 từ>"], "standfirst": "<≤ 220>", "callout": "<≤ 110>"},
            {"kind": "cta", "eyebrow": "ÁP DỤNG", "title": "<≤ 60>", "checks": ["<≤ 70>", "<≤ 70>", "<≤ 70>"],
             "readmore": {"label": "ĐỌC THÊM", "text": "<“Tên bài” - tác giả/nơi đăng, ≤ 90>"},
             "follow": f"Theo dõi @{handle_channel(m['brand'])}"},
        ],
    }
    L.append(json.dumps(khung, ensure_ascii=False, indent=1))
    L.append("Nhịp feature: bìa hook → bối cảnh/vấn đề → cách vận hành (steps) → số liệu (figure nếu có hình thật, "
             "không thì bars từ 2..6 số THẬT trong bài, không có số thì bỏ) → cơ chế/hệ quả (loop) → áp dụng + CTA. "
             "Ý nào hình nói nhanh hơn chữ thì dùng hình (steps/loop/bars), chữ thuần là đường cuối. Bỏ `figure` "
             "nếu không có hình thật; thêm `statement` khi cần đủ 6. Dẫn nguồn ghi 'via', không ghi 'nguồn'. Cấm logo hãng, số bịa, "
             "quote bịa, ảnh AI. Không em-dash. Ảnh CHỤP ở bìa/figure: CHỦ THỂ (mặt người, sản phẩm) phải nằm "
             "TRÊN khối chữ — chữ càng nhiều khối chữ càng cao, cổng chặn đo bằng Chromium; không dùng ảnh gần "
             "như trống (logo nhỏ trên nền trơn).")
    L += ["", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python kite_submit.py {m['draft_id']}",
          "Script tự kiểm spec, dựng bằng render_edu.py (Chromium), gửi album lên topic kèm nút duyệt, ghi bàn "
          "giao cho Miles. Báo [LOI] thì sửa đúng chỗ đó trong spec.json rồi chạy lại. KHÔNG mở từng slide ra "
          "xem, KHÔNG chạy render_edu.py/send_telegram.py tay, KHÔNG sinh agent con, KHÔNG gửi lại."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief carousel.edu cho Kite")
    ap.add_argument("draft_id")
    ap.add_argument("--lam-moi", action="store_true")
    ap.add_argument("--im", action="store_true")
    ap.add_argument("--khong-browser", action="store_true")
    ap.add_argument("--cho", type=int, default=300)
    a = ap.parse_args()
    m, wd, _ = cb.run(a.draft_id, a.lam_moi, a.khong_browser, a.cho,
                       sau_chuan_bi=route_missing_images.after_prepare)
    # Bia BAT BUOC co anh that (§1.2f) — thieu thi tim lai, dung bao hong.
    m, wd = ensure_has_cover(a.draft_id, m, wd, a.khong_browser, a.cho, a.lam_moi)
    brief = write_brief(m, cb._read_json(wd / state_paths.PREVIOUS_SUBMISSION_FILE))
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
