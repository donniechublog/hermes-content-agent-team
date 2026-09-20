#!/usr/bin/env python3
"""HỢP ĐỒNG DỮ LIỆU — một chỗ khai báo cho các tệp JSON đi giữa các bước.

Vi sao (audit_content_team F2): bon hop dong duoi day deu la dict TU DO, khong
khai o dau. Hau qua do duoc:

  - `so_dung_duoc` thieu khoa thi BA noi doan ba kieu: dre_prepare dem lai bang
    mot cong thuc KHAC cong thuc cua nguoi ghi, con approve_post va image_prepare coi
    la 0 ("khong co anh nao") — hai ket luan nguoc nhau tu cung mot tep.
  - `dre_submit.py` vao nhanh bang `m.get("toi_thieu", 5)` roi trong than lai doc
    `m["toi_thieu"]` tho: thieu khoa la KeyError NGAY TRONG CONG CHAN.
  - `write_meta` ghi DE ca dict 8 khoa, ma `blackboard` ghi `root_task` vao cung
    tep o mot tien trinh khac. Hom nay khong mat chi vi THU TU goi may man.

Tep nay KHONG kiem tra luc chay (khong validate). No lam ba viec:
  1. Khai bao khoa bang TypedDict — doi ten khoa thi co MOT cho de sua va de doc.
  2. Giu CONG THUC DAN XUAT dung mot ban (`count_image_use_ok`), de nguoi ghi va
     nguoi doc khong bao gio tinh ra hai so khac nhau.
  3. `read_manifest()` — mot cho doc manifest, tu choi ban cu co bao ro.

CHU Y — "manifest.json" KHONG phai mot hop dong. Do la ten tep dung lai o nhieu cho
voi hinh dang KHAC HAN: engine ghi manifest o
`state/<brand>/prepare/<id>/manifest.json`, con `itachi_prepare.py` ghi
`{"khoa", "slides"}` va `ada_prepare.py` ghi bao cao gom, deu ten `manifest.json`
nhung o workdir khac. Chi manifest cua engine moi theo `Manifest` duoi day.
"""
import json
from pathlib import Path
from typing import Any, TypedDict

# Tang phien ban khi doi Y NGHIA mot khoa (khong phai khi them khoa tuy chon).
# Ban 0 = moi manifest ghi truoc 09/09/2026, khong co truong `phien_ban`.
# Ban 2 (LOW-227, 17/09/2026) = khoa English; bang cu -> moi o
# docs/tu_dien_ten/manifest_keys_v2.json. Migration mot lan da chay va da go (LOW-229).
# Ban 3 (LOW-230, 17/09/2026) = GIA TRI liet ke English (source, kind, uses…); bang o
# docs/tu_dien_ten/manifest_values_v3.json, nhan tieng Viet in qua manifest_values.
VERSION_MANIFEST = 3


class Manifest(TypedDict, total=False):
    """`state/<brand>/prepare/<draft_id>/manifest.json` — engine ghi, moi vai doc.

    Nguoi ghi: `prepare.manifest.build_manifest` (26 khoa goc), roi
    `image_prepare.run` them `missing_images`, `route_missing_images.after_prepare` them
    `kite_task_id`/`kite_asked`/`kite_unavailable` — CA BA con trong khoa cua engine, nen
    nguoi doc luon thay ban da chot. Rieng `approve_post._button_lower_ready` ghi de
    `min_images` + them `min_lowered_at` SAU DO, luc Ong Chu bam nut.

    `total=False` vi ban cu thieu khoa moi; cot BAT BUOC ghi trong chu thich.
    """
    version: int                   # 2 tu LOW-227; ban 0/1 (khoa Viet) nang qua read_manifest

    # --- BAT BUOC: co noi doc tho `m[k]`, thieu la no ---
    draft_id: str
    brand: str
    title: str
    link: str
    workdir: str                   # duong dan TUYET DOI toi thu muc lam viec
    images: list                   # [Image]
    # So ANH THAT toi thieu de VAI DUOC GIAO dung duoc bo nay (`role.min_images`).
    # Voi Dre con la so SLIDE toi thieu — moi slide mot anh rieng nen hai con so
    # trung nhau, va `dre_submit`/`dre_prepare` doc khoa nay theo nghia "slide".
    # Voi Ethan thi KHONG trung (1 anh, 1 the): truoc 10/09/2026 cho nay luon la
    # so cua carousel nen bai cua Ethan bi bao thieu anh oan.
    min_images: int
    flagship: bool

    # --- Tuy chon: moi noi doc deu co mac dinh ---
    via: str
    category: str
    summary: str
    source_note: str
    title_en: str
    material: dict                 # {number_sentences, lead_paragraph, source_count, source}
    article_text: str              # CAT con 20000 ky tu luc ghi
    dropped: list                  # LOW-225: ung vien bi bo o pha tai (stage/rule/evidence/thumb)
    domains: list
    stackable_pairs: list
    two_company_pairs: list    # M&A: cap [id_A, id_B] anh cua HAI hang (story_type.py, 12/09/2026)
    image_order_by_story_type: list  # loai tin -> vat duoc phep, de brief noi vi sao co logo/co/bieu do gia
    cover_suggestions: list        # id anh goi y lam bia, XH dung dau neu co
    not_yet_seen: list             # id anh vision chua nhin duoc
    usable_count: int              # xem `count_image_use_ok` — CHUM khai niem tinh la MOT
    base_min_images: int           # san tuyet doi CUA VAI DO, `ha san` khong xuong duoi day
    image_role: str                # SLUG vai duoc giao bo anh nay ("" o manifest cu)
    is_ranking_story: bool
    ranking: dict | None           # BANG DAU TIEN; None khi khong chup duoc
    ranking_count: int             # so bang chup duoc; 0 khi khong co
    created_at: int
    source_path: str
    route_error: str               # route_missing_images: gui tin hoi that bai

    # --- Co dinh tuyen, chi co khi bai THIEU anh (route_missing_images ghi) ---
    missing_images: dict           # {"count": int, "min_images": int}
    kite_task_id: str              # task id Kite, khi engine tu chuyen
    kite_asked: bool               # da hoi Ong Chu bang nut
    kite_unavailable: bool         # brand chua co Kite, khong hua chuyen
    min_lowered_at: int            # luc Ong Chu bam "lam voi N anh"


class Image(TypedDict, total=False):
    """MOT muc trong `Manifest.images` (va `image` trong state/golden/v0/samples.jsonl).

    Khong co TypedDict nay truoc LOW-227 — khoa anh chi ton tai rai rac trong
    prepare/vision.py va cac vong tim anh. Khai o day de doi ten co MOT cho doi chieu."""
    id: str                        # "A1", "A2"... — ma anh trong MOT draft
    original_path: str             # duong dan TUYET DOI tep goc da tai
    ready_path: str | None         # tep da xu ly san (cat/phong); None khi chua xu ly
    url: str
    alt: str
    source: str                    # vong tim ra tam nay: press_entity | other_outlet | concept | article | brand | …
    page_url: str
    domain: str
    og: bool
    chart_hint: bool
    w: int
    h: int
    ratio: float
    kind: str                      # "photo" | "chart"
    short_side: int
    landscape: bool
    uses: list                     # MA slot (cover, body_chart…); cau Viet: manifest_values.USE_LABELS
    notes: list
    chart_stats: str
    faces: int
    bottom_brightness: int
    bottom_left_brightness: int
    score: int
    score_reason: str
    description: str
    relevant: bool | None          # None = vision chua nhin
    landscape_crop_ok: bool | None
    has_keywords: bool | None
    cluttered: bool | None
    cluttered_legacy: bool | None  # khoa `roi` cu (LOW-47), KHONG code nao doc — giu du lieu
    subject_box: list | None       # LOW-273: [x0,y0,x1,y1] 0..1 hop bao CHU THE CHINH (vision); None = khong co
    subject_kind: str | None       # person | product | building | logo | screen | chart | other
    empty_share: float | None      # 0..1 phan tam anh la nen tron (subject_fit.EMPTY_SHARE_MAX)
    printed_name: str | None       # LOW-279: ten nguoi IN tren anh (lower-third/bang ten), vision chep lai
    people: list                   # LOW-293: ten nguoi tam anh mang theo, tin xac nhan duoc
    decisions: list                # LOW-225 prepare.decision_log: [{stage, outcome, rule, evidence}]
    vision_raw: dict               # LOW-225: {model, question, answer} cua lan hoi vision
    from_find_more: bool
    commons: bool
    concept: dict                  # {keyword, reason}
    brand_match: dict              # {company, key, kind, keyword, person, person_role, board, background_tone, ticker}
    entity: dict                   # {name, article_name, source}
    ranking: dict                  # cung hinh voi Manifest.ranking + file_path
    image_url: str                 # URL ung vien truoc khi tai
    capture_source: bool
    capture_kind: str
    page_title: str
    background_color: str
    padding_color: str
    unpadded_path: str             # ban truoc khi dem padding_color (ti le tu nhien) — chi
                                    # co khi padding_color duoc set; renderer full-bleed nhu
                                    # render_edu.py (Kite) phai dung tep nay thay vi original_path
                                    # (LOW-262), carousel.py (Dre) van dung original_path nhu cu
    paper_figure: str
    fallback: bool
    html_tag: str


class Meta(TypedDict, total=False):
    """`drafts/<draft_id>.meta.json` — sinh luc Ong Chu chon tin.

    HAI TIEN TRINH ghi: `approve_pick.write_meta` (8 khoa dau, ghi DE ca dict)
    va `blackboard._write_meta` (chi `root_task`, chay bang python cua hermes).
    Vi write_meta ghi de chu khong merge, thu tu goi la thu duy nhat giu cho
    `root_task` khong bi xoa — xem `merge_meta`.
    """
    source_url: str                # BAT BUOC (draft_write thoat neu rong)
    title: str                     # BAT BUOC
    category: str                  # BAT BUOC
    brand: str                     # quyet dinh CT_BRAND cua ca tien trinh
    image: str
    via: str
    score: int | float | None      # None khi Nova/Vera quet (khong cham diem)
    score_reason: str
    root_task: str                 # the goc bang den; chi brand bat bang den


class SidecarImage(TypedDict, total=False):
    """`drafts/<draft_id>.img.json` — de LAM LAI task anh duoc."""
    image_role: str                # SLUG vai (ban cu con ghi ten persona)
    carousel: bool
    title: str
    body: str                      # nguyen body task, de dung lai khi lam lai
    remakes: int
    link: str
    summary: str
    source_note: str
    via: str
    last_task: str
    kite_task_id: str              # approve_post ghi khi Ong Chu bam "Gui Kite"
    transferred_from: str
    transfer_reason: str           # approve_post.create_task_kite (ADF-r2-5: tung ghi ma chua khai)
    redo_reasons: list             # [{attempt, slide, reason}]
    forbidden_slide_images: dict


class SidecarWrite(TypedDict, total=False):
    """`drafts/<draft_id>.writer.json` — task viet CHI sinh khi Ong Chu bam "Duyet anh".

    approve_pick.create_pair ghi 6 khoa dau; approve_post cap nhat `created`
    (True khi da tao task, "rejected" khi bo han) va `writer_task`. Khong co
    TypedDict nay truoc audit lượt 2 (ADF-r2-5) — `created` nhan ba kieu ma khong
    ai khai, test_schema chi gac Manifest va Meta."""
    writer_role: str               # SLUG vai viet (writer)
    title: str
    body: str                      # body task viet, dung san
    created: bool | str            # False -> True (da tao) | "rejected"
    root_task: str                 # the goc bang den
    dre_task: str                  # task vai anh — cha cua task viet
    dre_task_before_kite: str      # dre_task truoc khi chuyen Kite (approve_post, bang den)
    writer_task: str               # id task viet, khi da tao


class LineImageUsed(TypedDict):
    """MOT DONG trong `state/<brand>/used_images.jsonl` (noi them, khong sua).

    Khoa theo TIN chu khong theo draft: cung mot tin giao cho hai vai ra hai
    draft_id nhung dung chung bo anh engine tai ve."""
    dhash: str
    draft_id: str
    role: str                      # vai tao album (LOW-242, truoc: `vai`)
    story_key: str                 # khoa on dinh cua tin, xem image_provenance.story_key (truoc: `tin`)
    file_name: str                 # ten tep anh goc (truoc: `ten`)
    md5: str
    used_at: int                   # epoch giay, de xet cua so 14 ngay (truoc: `luc`)


# ---------------------------------------------------------------- dan xuat
# Anh NGANG thap hon nguong nay khong cat doc 4:5 duoc (con ~80% chieu cao roi
# phong len 1080 se nhoe) — chi con duong "ghep" voi mot anh ngang khac. MOT ban
# cho ca nguoi dem (count_image_use_ok) lan cong chan (dre_submit): truoc 12/09/2026
# dre_submit go cung 700 con nguoi dem thi khong biet, nen A5 900x600 cua tin TSMC
# duoc dem la mot slide trong khi khong ai dung no mot minh duoc.
HEIGHT_MIN_CROP_LANDSCAPE = 700


def _only_stack_ok(a: dict) -> bool:
    """Tam nay CHI dung duoc qua "ghep" — khong dung MOT MINH duoc, vi mot
    trong hai ly do:
      1. qua thap de cat doc (`h < HEIGHT_MIN_CROP_LANDSCAPE`), hoac
      2. la anh chup NGANG co chu/logo/so lieu de len (`landscape_crop_ok is False`
         — vision xac nhan, xem prepare.vision.classify) nen image_rules cam crop.
    Su co 12/09/2026 lan hai (t_a8ffd2f6): Dre chay that, 4/5 anh ngang cao
    >=700 la bien hieu/logo CO CHU (khong phai chart — chart da co duong rieng
    "than, dan full be ngang"), nhung cong thuc cu chi nhin chieu cao nen dem
    ca bon la "dung mot minh duoc" — thua 2 slide so voi that te. `landscape_crop_ok`
    la None voi manifest CU (chua nhin lai) hoac khi vision khong tra loi duoc
    cau hoi — coi nhu CHUA XAC NHAN, an toan hon la dem lam dung mot minh."""
    if not a.get("landscape"):
        return False
    if 0 < int(a.get("h") or 0) < HEIGHT_MIN_CROP_LANDSCAPE:
        return True
    if a.get("kind") == "chart":
        return False           # chart ngang dung MOT MINH qua "than, dan full be ngang"
    return a.get("landscape_crop_ok") is not True


def _count_stackable_pairs_real(ds: list, vai_anh: str) -> int:
    """So cap ROI NHAU lon nhat trong `ds` ma moi cap ghep doc ra dung khung
    (`stack_fit_frame` cua module luat rieng `vai_anh`, LOW-182 — theo `ti_le`
    da do, khong mo tep anh).

    Vai la/khong biet -> module cua vai anh mac dinh, CUNG mot quy uoc voi
    `role.min_images`/`can_be_hero`/`search_target_for` (khong nem — nguoi goi
    o do la `role.has_enough_material`, va da co canh bao rieng o
    `image_prepare.prepare_article` khi sidecar mat `vai_anh`).

    Phai la ghep cap TOI UU, khong phai tham lam: bon tam C-A-B-D ma chi A-C,
    A-B, B-D ghep duoc thi nhat A-B truoc ra 1 cap, dung ra 2 (A-C, B-D). So tam
    chi-ghep cua mot bai chi vai tam den chuc tam — duyet tap con co nho la du."""
    from functools import lru_cache

    import role
    v = role.ROLE.get(vai_anh) or role.ROLE[role.DEFAULT_IMAGE]
    rules = role.rules_module(v.slug)
    n = len(ds)
    ke = [[j for j in range(n) if j != i and rules.stack_fit_frame(ds[i].get("ratio"),
                                                                     ds[j].get("ratio"))]
          for i in range(n)]

    @lru_cache(maxsize=None)
    def _tot(con: int) -> int:
        if not con:
            return 0
        i = (con & -con).bit_length() - 1
        bo_i = con & ~(1 << i)
        ra = _tot(bo_i)                                  # tam i dung le, khong vao cap nao
        for j in ke[i]:
            if bo_i >> j & 1:
                ra = max(ra, 1 + _tot(bo_i & ~(1 << j)))
        return ra

    return _tot((1 << n) - 1)


def count_image_use_ok(anh: list, vai_anh: str) -> int:
    """So SLIDE dung duoc tu bo anh, de xet du/thieu — MOT ban duy nhat cua cong thuc.

    Dem theo cai vai DUNG DUOC, khong phai so tam tai ve:
      - chum anh KHAI NIEM chi lam bia nen ca chum dem la MOT ("5" o day la co
        Nhat, khong phai 5 slide);
      - anh ngang QUA THAP (`_only_stack_ok`) khong dung mot minh duoc, hai tam
        nhu the moi ghep thanh MOT slide — mot tam le dem la 0.
    Su co 12/09/2026 (tin TSMC, t_a8ffd2f6): engine dem "5 dung duoc / toi thieu
    5" roi NGUNG TIM (bo qua vong chup trang nguon + anh khai niem) trong khi
    A5 900x600 chi ghep duoc ma khong co cap, tuc chi dung duoc 4 slide. Dre
    block, Ong Chu phai go tay. Truoc khi gom ve day, `dre_prepare` doan lai
    bang `len([a for a in images if a["uses"]])` — mot so KHAC — con `approve_post`
    va `image_prepare` coi thieu khoa la 0. Ba cach doan cho ba ket luan.

    LOW-46 (13/09/2026, tin TSMC lan ba, t_2d546375): cong thuc noi "du 6" ma
    Dre chi dung duoc 4 va phai block. Hai cho dem lac quan hon cong chan that:
      - `len(chi_ghep) // 2` coi BAT KY hai tam chi-ghep nao cung la mot cap —
        A5+A10 (deu 3:2) ghep ra 0.75, ngoai dai 4:5..1:1, dre_submit chan. Nay dem
        so cap roi nhau LON NHAT ma `stack_fit_frame` (module luat rieng cua
        `vai_anh`, LOW-182) cho qua;
      - tam co mat nguoi khong ro ai (A3) van duoc dem, trong khi
        `submit_common.check_subject_named` chan no. Nay bo qua qua `role.face_no_clear_ai`,
        cung dieu kien voi `role.can_be_hero`."""
    import role
    dung_duoc = [a for a in (anh or []) if a.get("uses") and a.get("relevant") is not False
                 and not role.face_no_clear_ai(a) and not role.blocked_empty(a, vai_anh)]
    # LOW-288 (20/09/2026): tam bi cong ANH TRONG chan (LOW-273) khong duoc dem —
    # truoc day bo dem bao "5/6" trong khi mot trong 5 tam la logo nen tron bi chan.
    khai_niem = [a for a in dung_duoc if a.get("concept")]
    rieng = [a for a in dung_duoc if not a.get("concept")]
    chi_ghep = [a for a in rieng if _only_stack_ok(a)]
    return (len(rieng) - len(chi_ghep)) + _count_stackable_pairs_real(chi_ghep, vai_anh) + min(1, len(khai_niem))


def read_manifest(nguon) -> dict | None:
    """Doc manifest cua engine. None neu khong doc duoc hoac khong phai ban hien hanh.

    `nguon` la duong dan toi manifest.json, hoac chinh dict da doc san.

    Chi nhan `version >= VERSION_MANIFEST`. Nhanh nang ban 0/1 (khoa Viet) da go o
    LOW-229 sau khi ca 185 manifest may chu duoc migrate (LOW-227, 17/09/2026) — mot
    tep ban cu xuat hien lai (khoi phuc tu *.v1.bak, may khac) bi TU CHOI co bao ro,
    khong duoc doc im lang ra toan khoa rong."""
    if isinstance(nguon, dict):
        m = dict(nguon)
    else:
        p = Path(nguon)
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"[schema] khong doc duoc manifest {p}: {type(e).__name__}: {e!r}")
            return None
        if not isinstance(m, dict):
            print(f"[schema] manifest {p} khong phai dict")
            return None

    # N-r2-7: version "2" (chuoi) hay None (tep sua tay/tool khac) tung nem
    # TypeError o phep `<` — ham hua "None neu khong doc duoc" ma lai crash.
    try:
        pv = int(m.get("version") or 0)
    except (TypeError, ValueError):
        pv = 0
    if pv < VERSION_MANIFEST:
        ten = "(dict)" if isinstance(nguon, dict) else nguon
        print(f"[schema] manifest {ten} la ban {pv}, can ban {VERSION_MANIFEST} (khoa English, LOW-227) — khong doc")
        return None
    m["version"] = pv
    return m


def merge_meta(cu: dict | None, moi: dict) -> dict:
    """Tron ban meta MOI vao ban CU thay vi ghi de.

    `write_meta` chay hai lan cho mot bai (luc chon tin, roi luc giai xong link
    Google News), con `blackboard` ghi `root_task` vao CUNG tep tu mot tien trinh
    khac. Ghi de ca dict nghia la ai ghi sau xoa cua ai ghi truoc — hom nay chua
    mat chi vi thu tu goi tinh co dung. Tron thi khong phu thuoc thu tu nua.

    Khoa co trong `moi` thang, ke ca khi gia tri rong: do la y cua nguoi ghi."""
    ra = dict(cu or {})
    ra.update(moi)
    return ra


def _kind(td) -> dict[str, Any]:
    """Khoa -> kieu da khai, dung cho test doi chieu khai bao voi thuc te."""
    return dict(getattr(td, "__annotations__", {}))
