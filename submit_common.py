#!/usr/bin/env python3
"""submit_common.py — phan dung chung cua cac script NOP (dre_submit, ethan_submit, kite_submit,
miles_submit): nap meta/workdir/manifest.json/spec.json, chuan hoa chuoi, kiem "lam
lai", gui album kem nut duyet + ghi previous_submission.json, ghi bang den.

Truoc 05/09/2026 moi doan nay chep 3–4 ban giong het nhau o tung nop; sua mot
ban thi ban kia troi (audit 05/09). Tep nay KHONG chua logic rieng cua vai nao.
"""
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                    # noqa: E402
import env_load                                              # noqa: E402
import schema                                                # noqa: E402
import state_paths                                           # noqa: E402
import role as _vai                                           # noqa: E402


def normalize(t) -> str:
    """Chuoi de so 'giong het': gop khoang trang, ha chu thuong."""
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def load_draft_context(draft_id: str, spec_arg, ten_brief: str, ten_nop: str) -> tuple:
    """(meta, brand, wd, m, spec, spec_path, da_dung) cho mot draft. Thieu gi thi
    dung han voi cau chi dan cho vai (sys.exit) — nop la CLI, vai doc stdout."""
    meta = cb.load_meta(draft_id)               # dat CT_BRAND theo brand cua draft
    brand = cb._brand_of(meta)
    wd = cb.workdir(env_load.state_dir(), draft_id)
    m = schema.read_manifest(wd / state_paths.MANIFEST_FILE)   # bu khoa dan xuat cho ban cu (C-r2-5)
    if not m:
        sys.exit(f"Chua chuan bi. Chay truoc: venv/bin/python {ten_brief} {draft_id}")
    spec_path = Path(spec_arg) if spec_arg else wd / "spec.json"
    if not spec_path.exists():
        sys.exit(f"Chua co spec: {spec_path} — viet theo khung trong {wd / 'brief.md'} roi chay lai "
                 f"venv/bin/python {ten_nop} {draft_id}.")
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] spec.json khong phai JSON hop le: {type(e).__name__}: {e}")
    return meta, brand, wd, m, spec, spec_path, cb._read_json(wd / state_paths.PREVIOUS_SUBMISSION_FILE)


# ---- ai viet bai nay, va lenh cua nguoi do (LOW-13, 10/09/2026) -------------
# Tu khi co hai nguoi viet, "miles_submit.py" khong con la cau tra loi dung cho moi
# bai. Ba thu duoi day tung go cung ten Miles: ten script in trong brief, ten
# tep brief, va `author` ghi len bang den. Go cung thi task cua Jika bao Jika
# chay lenh cua Miles, va ban giao cua Jika len bang den mang ten Miles — khong
# cho nao bao loi, chi doc ra sai.

def writer_for_article(draft_id: str, brand: str = "") -> str:
    """SLUG nguoi viet da chot cho bai nay.

    Nguon su that la sidecar `<draft_id>.writer.json` — approve_pick chot
    nguoi viet NGAY luc chon tin (luc do con biet vai quet), con luc nop thi
    vai quet da khong con trong tam tay. Sidecar cu (ghi truoc LOW-13) khong co
    khoa `writer_role`, hoac ghi mot slug la -> hoi lai ban dang ky theo brand."""
    d = cb._read_json(cb.DRAFTS / f"{draft_id}.writer.json", {}) or {}
    slug = str(d.get("writer_role") or "")
    if slug in _vai.ROLE:
        return slug
    return _vai.writer_for(None, brand)


def writer_persona_name(slug: str) -> str:
    """Slug vai viet -> chu dung trong TEN SCRIPT va `author` bang den ("miles",
    "jika"). Lay tu ban dang ky chu khong chep bang thu hai: cac cap script deu
    dat theo ten nhan vat (miles_submit, dre_submit, kite_submit...), nen ten persona
    viet thuong CHINH LA tien to script."""
    return _vai.display_name(slug).lower()


def count_of_redo(draft_id: str) -> int:
    """So lan Ong Chu da bam "Lam lai" cho bai nay (drafts/<id>.img.json)."""
    d = cb._read_json(cb.DRAFTS / f"{draft_id}.img.json", {}) or {}
    return int(d.get("remakes", 0) or 0)


def check_redo_reused(da_dung, nhan_anh: str, anh_moi, hook_moi, khoa_anh: str = "image",
                 draft_id: str = "", anh_bat_buoc: bool = False) -> list:
    """Lam lai ma van giu anh/hook cua lan truoc -> loi. `khoa_anh` la khoa trong
    previous_submission.json ("cover_image" voi carousel, "image" voi hero; LOW-242 —
    `anh_moi` van lay tu spec cua vai, chi khoa trong tep nop truoc doi ten).

    CHI ap khi Ong Chu THAT SU bam "Lam lai" (sua 06/09/2026 dot 2). Truoc day
    dieu kien la "co previous_submission.json", ma tep do duoc ghi o MOI lan gui va
    approve_post khong bao gio xoa — nen moi lan chay lai vi bat ky ly do gi (task
    kanban retry, vai chay lai sau mot [CANH BAO]) deu bi bao "Ong Chu bam lam
    lai nghia la bia chua dat, doi bia khac". Vai doi bia that, roi `send_album`
    gui BO THU HAI voi mot nut Duyet thu hai; md5 30 phut cua send_telegram chi
    chan duoc truong hop tep y het.

    Moc so sanh la `remakes` trong img.json — chinh con so approve_post tang moi
    lan bam nut.

    `anh_bat_buoc`: anh/bia hien tai la LUA CHON DUY NHAT hop le theo mot cong
    khac (vd needs_ranking_image voi tin chi co dung mot anh xep hang — xem
    only_ranking_choice, LOW-146). Cong nay tung khoa cung voi cong do: tin xep
    hang bat bia PHAI la anh xep hang, con day cam dung lai anh cua lan truoc —
    chi co MOT anh xep hang va no da la bia lan truoc thi khong con duong nop
    hop le. Khi bat_buoc, bo qua rieng phan sanh anh, van giu cong hook (vai
    van phai doi cach dien dat, chi khong bi ep doi anh khong the doi).
    """
    if not da_dung:
        return []
    if draft_id and count_of_redo(draft_id) <= int(da_dung.get("remakes", -1)):
        return []                    # chay lai, KHONG phai Ong Chu bam lam lai
    loi = []
    cu = da_dung.get(khoa_anh)
    if anh_moi and cu and anh_moi == cu and not anh_bat_buoc:
        loi.append(f"LÀM LẠI: {nhan_anh} vẫn là {cu} như lần trước — Ông Chủ bấm làm lại "
                   f"nghĩa là {nhan_anh} chưa đạt, đổi {nhan_anh} khác")
    if normalize(hook_moi) == normalize(da_dung.get("hook")):
        loi.append("LÀM LẠI: hook giống hệt lần trước — viết hook khác")
    return loi


# So lan nop HONG voi CUNG mot bo loi truoc khi coi la tac (xem count_round_error).
MAX_ROUND = 3


def count_round_error(wd, loi: list, lenh: str, toi_da: int = MAX_ROUND) -> int:
    """Dem so lan nop hong LIEN TIEP voi cung mot bo loi. Tra ve ma thoat.

    "Toi da 2 lan sua [LOI]" truoc 06/09/2026 chi la CHU trong task body —
    khong mot dong code nao dem. Ghep voi cong phi tat dinh (vision relevant
    doi ket qua giua hai lan chay) va cong tung bat kha thi, vai co the lap toi
    khi het ngan sach tool call cua Hermes ma khong ai thay gi ngoai mot task
    treo.

    Dem theo CHU KY loi chu khong theo so lan chay: bo loi doi nghia la vai da
    sua duoc mot thu, cho no di tiep. Ba lan y het nhau moi la tac that. Moc cu
    hon 6 gio coi nhu cua task khac.
    """
    import hashlib
    import json as _j
    import time as _t
    p = Path(wd) / state_paths.SUBMIT_COUNT_FILE
    ky = hashlib.md5("\n".join(sorted(str(x) for x in loi)).encode()).hexdigest()
    cu = {}
    try:
        cu = _j.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if cu.get("error_signature") != ky or _t.time() - cu.get("updated_at", 0) > 6 * 3600:
        cu = {"error_signature": ky, "repeat_count": 0}
    lan = int(cu.get("repeat_count", 0)) + 1
    try:
        p.write_text(_j.dumps({"error_signature": ky, "repeat_count": lan, "updated_at": int(_t.time()),
                               "last_errors": [str(x)[:200] for x in loi[:5]]},
                              ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    if lan < toi_da:
        print(f"\nSua roi chay lai DUNG lenh: {lenh}"
              + (f"   (lan {lan}/{toi_da})" if lan > 1 else ""))
        return 1
    print(f"\n[DUNG] Da {lan} lan nop voi Y HET bo loi tren — dung sua nua.")
    print("  Goi kanban_block va ghi nguyen van dong [LOI] dau tien lam ly do. "
          "Cong nay co the dang doi mot thu khong the co (thieu anh, thieu tu "
          "lieu, nguon hong) — do la viec cua Ong Chu, khong phai cua vai.")
    return 2


def article_text_for(m: dict, wd: Path) -> str:
    """Chu bai + tu lieu gom ve mot chuoi chu thuong, de doi chieu ten nguoi hay
    so lieu vai khai co that su nam trong bai khong."""
    tl = m.get("material") or {}
    s = ((m.get("article_text") or "") + " " + (tl.get("lead_paragraph") or "")
         + " " + " ".join(tl.get("number_sentences") or [])).lower()
    try:
        s += " " + (wd / state_paths.MATERIAL_FILE).read_text(encoding="utf-8").lower()
    except OSError:
        pass
    return s


def _strip_diacritics(t: str) -> str:
    """Bo dau tieng Viet, ha chu thuong (cung phep nhu teaser_assemble._drop_mark)."""
    t = t.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", t)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def _words(t: str) -> list:
    """Chuoi -> danh sach TU da bo dau, moi ky tu khong phai chu/so la ranh gioi."""
    return [w for w in re.split(r"[^0-9a-z]+", _strip_diacritics(t)) if w]


def _name_in_article(nv: str, chu_bai: str) -> bool:
    """Ten nguoi vai khai co thuc su nam trong chu bai khong.

    Truoc 06/09/2026 phep so la `ho not in chu_bai` voi `ho = nv.split(",")[0]`
    — tach hau to CHI bang dau phay, va so CHUOI CON chu khong so TU. Hai huong
    hong cung luc:

      - CHAN OAN: "Sam Altman (CEO OpenAI)" hay "Jensen Huang - Nvidia" giu
        nguyen ca hau to, tat nhien khong nam trong chu bai; du phong "hai tu
        cuoi" thi ra ["(ceo", "openai)"] — con dinh dau ngoac nen cung truot.
        Ten tieng Viet co dau ("Pham Nhat Vuong") khong khop bai goc viet khong
        dau. Vai doc "Bo anh nay" roi bo dung tam anh dung.
      - LOT BUA: `w in chu_bai` la khop chuoi con, nen "Jensen Huang - Nvidia"
        LOT chi vi bai tinh co co dau gach en o cho khac. Cung mot khai bao,
        chan hay lot phu thuoc vao mot ky tu vo can trong bai.

    Gio: bo dau ca hai ben, cat hau to o MOI dau ngan cach (, ( ) - - | /), roi
    so theo TU nguyen ven.
    """
    dau_tien = re.split(r"[,(\[|/]|\s[-–—]\s", nv)[0]
    ten = _words(dau_tien)
    if not ten:
        return True                      # khong con gi de doi chieu -> khong chan
    bai = _words(chu_bai)
    # LIEN NHAU (LOW-285): truoc day so tung tu rieng le, nen "Lovable Sutro" (hai ten
    # hang cach xa nhau trong bai) lot nhu mot ten nguoi.
    if _contains_run(bai, ten):
        return True
    # Ten dai (co ten dem): chap nhan hai tu cuoi — "Nguyen Van A" khop "Van A".
    return len(ten) > 2 and _contains_run(bai, ten[-2:])


def _contains_run(words: list, run: list) -> bool:
    """`run` co nam LIEN NHAU (dung thu tu) trong `words` khong."""
    n = len(run)
    return any(words[i:i + n] == run for i in range(len(words) - n + 1))


def _brand_words(anh: dict) -> set:
    """Cac tu cua TEN HANG/THUC THE trong bo anh (brand_match.company, entity.name) —
    de nhan ra `subject` khai ten hang thay cho ten nguoi (LOW-285)."""
    ra = set()
    for a in (anh or {}).values():
        for ten in ((a.get("brand_match") or {}).get("company"), (a.get("entity") or {}).get("name")):
            ra.update(_words(ten or ""))
    return ra


def _not_person_subject(nv: str, anh: dict, ma_co: list) -> bool:
    """`subject` (phan truoc dau ngan cach dau tien, nhu _name_in_article) KHONG phai ten
    nguoi: mot chu, hoac chua ten hang trong tin — tru khi khop DUNG ten nguoi ma chinh
    tam anh mang theo (brand_match.person, ten in tren anh, alt that): "Michael Dell"
    cua hang Dell van qua."""
    ten = _words(re.split(r"[,(\[|/]|\s[-–—]\s", nv)[0])
    if not ten:
        return False
    bang_chung = set()
    for ma in ma_co:
        a = anh.get(ma) or {}
        for t in _vai.person_names_of(a) + [(a.get("brand_match") or {}).get("person") or ""]:
            if t:
                bang_chung.add(tuple(_words(t)))
    if tuple(ten) in bang_chung:
        return False
    return len(ten) < 2 or any(w in _brand_words(anh) for w in ten)


def check_subject_named(anh: dict, ma_ds, nhan_vat, chu_bai: str, nhan: str) -> list:
    """Cong chan MAT NGUOI dung chung Dre/Ethan.

    Truoc 06/09/2026 chi dre_submit co day du ba lop nay; ethan_submit chi kiem "co
    khai ten hay chua", nen mot cai ten CEO bia dat van qua cong cho the hero
    (su co bia Broadcom 05/09: anh quan chuc G20, khai "Hock Tan"). Gom mot cho
    de hai vai khong con lech."""
    co = [ma for ma in ma_ds if ma and anh.get(ma, {}).get("faces")]
    nv = str(nhan_vat or "").strip()
    loi = []
    if co and not nv:
        loi.append(f"{nhan}{', '.join(co)} có mặt người mà không khai \"subject\": "
                   "\"<tên người trong bài>\" — khai tên nếu đúng là nhân vật, "
                   "không thì đổi ảnh khác")
        return loi
    if not co or not nv:
        return loi
    if _not_person_subject(nv, anh, co):
        loi.append(f"{nhan}subject \"{nv}\" không phải TÊN NGƯỜI (tên hãng/tổ chức, hoặc chỉ "
                   "một chữ) — khai đúng họ tên người trong ảnh có trong bài; không biết là ai "
                   "thì đổi ảnh khác, đừng khai tên hãng cho qua cổng (LOW-285)")
        return loi
    if chu_bai and not _name_in_article(nv, chu_bai):
        loi.append(f"{nhan}subject \"{nv}\" không xuất hiện trong chữ bài — "
                   "khai tên người KHÔNG có trong bài là bịa. Bỏ ảnh này. "
                   "(Nếu tên đúng thì bỏ phần chức danh: khai \"Sam Altman\", "
                   "không khai \"Sam Altman (CEO OpenAI)\".)")
    # VISION MO TA: chi chan cac cum HEP. Truoc 06/09/2026 bo tu khoa co ca tu
    # tran "logo", ma cong nay chi no khi anh CO MAT NGUOI va vai DA khai ten —
    # tuc no nham dung vao anh chan dung/su kien, loai anh the hero can nhat.
    # Anh hop le nhat cua loai do la "CEO dung tren san khau, phia sau la logo
    # hang": vision tra dung LIEN_QUAN=co (chinh prompt o image_prepare day rang
    # logo-tren-toa-nha / su kien cua chinh cong ty trong bai LA lien quan), roi
    # cong nay van chan vi mo ta co chuoi con "logo". Anh khong lien quan da co
    # cong rieng (`relevant is False` o dre_submit/ethan_submit), nen o day chi giu
    # nhung cum thuc su noi len "day la logo cua TO BAO, khong phai cua bai".
    for ma in co:
        mo_ta = (anh.get(ma, {}).get("description") or "").lower()
        if mo_ta and any(k in mo_ta for k in ("không liên quan", "g20",
                                              "logo báo", "logo của tờ",
                                              "logo hãng tin", "watermark")):
            loi.append(f"{nhan}{ma} — vision mô tả: \"{anh[ma]['description'][:80]}\" — "
                       "không phải nhân vật bài này")
    return loi


def check_numbers_on_card(chu: str, m: dict, wd: Path) -> list:
    """Canh bao (khong chan) cac con so vai viet len ANH ma tu lieu khong co.

    Cung mot phep doi chieu caption_check dung cho caption cua Miles, nhung
    truoc 06/09/2026 khong vai lam anh nao goi — so bia tren slide di thang len
    Telegram. Chi CANH BAO vi doi don vi (2,5 ti / 2.5B) la chuyen binh thuong."""
    import caption_check
    la = caption_check.count_is(chu, article_text_for(m, wd))
    if not la:
        return []
    return [f"số trên slide KHÔNG thấy trong tư liệu: {', '.join(la[:8])} — "
            "kiểm lại nguồn, số không có trong tư liệu là bịa (trừ khi đổi đơn vị)"]


# Tu chuc nang tieng Anh: cau tieng Anh THAT gan nhu luon co vai tu trong day,
# con mot nhan toan ten rieng + so ("Claude Opus 4.5 vs GPT-5.2: 82,5 MMLU")
# thi khong co tu nao. Day la thu phan biet "chua dich" voi "ten san pham".
_TU_ANH = {
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "from", "with", "by",
    "is", "are", "was", "were", "be", "been", "has", "have", "had", "will",
    "would", "can", "could", "should", "that", "this", "these", "those", "it",
    "its", "we", "they", "our", "their", "you", "your", "he", "she", "his",
    "her", "but", "not", "than", "then", "when", "while", "which", "who",
    "what", "how", "why", "says", "said", "about", "into", "over", "after",
    "before", "now", "most", "more", "all", "any", "some", "much", "many",
}


def needs_ranking_image(m: dict, a: dict) -> bool:
    """TIN XEP HANG ma anh chinh/bia KHONG phai bang xep hang -> phai doi.

    CHI khi engine THUC SU CHUP duoc bang (`ranking.is_capture(kind)` — LOW-21:
    ban cu so voi chuoi "chup" ma xep_hang chua bao gio phat ra). Truoc
    06/09/2026 chieu cong nay chan ca khi m["ranking"] la None — bao vai dung
    ma "XH" trong khi ma do khong ton tai, nen vai sua kieu gi cung sai va khong
    bao gio nop duoc. Ba duong dan toi canh do: --khong-browser, extract_model()
    rong (tin xep hang KHONG neu ten model), hoac find_and_capture nem. The DU PHONG
    (kind="card") cung khong ep: no la anh engine tu dung, chua he doc bang that.
    Dre va Ethan tung moi ben mot ban cua dieu kien nay (07/09/2026 gom lai)."""
    import ranking
    return bool(m.get("is_ranking_story")
                and ranking.is_capture((m.get("ranking") or {}).get("kind"))
                and not a.get("ranking"))


def only_ranking_choice(m: dict) -> str | None:
    """Ma anh xep hang DUY NHAT cua bai, neu needs_ranking_image dang ep dung no —
    None neu bai khong phai tin xep hang, engine chua chup duoc bang, hoac co tu
    hai anh xep hang tro len (con duong khac de chon).

    Dung de goi check_redo_reused(anh_bat_buoc=...) (LOW-146): khi CHI CO MOT anh
    xep hang, needs_ranking_image bat bia/anh phai la no, con check_redo_reused
    cam dung lai anh cua lan truoc — neu anh do da la lua chon lan truoc, hai cong
    khoa nhau, bo khong con duong nop hop le du sua gi khac."""
    if not m.get("is_ranking_story"):
        return None
    import ranking
    if not ranking.is_capture((m.get("ranking") or {}).get("kind")):
        return None
    ma_xh = [a["id"] for a in (m.get("images") or []) if a.get("ranking")]
    return ma_xh[0] if len(ma_xh) == 1 else None


def irrelevant_images(anh: dict, ma_ds) -> tuple:
    """Cac ma bi vision danh dau KHONG LIEN QUAN bai, kem mo ta cua chung.

    Tra ve (rac, mo_ta). Ong Chu bat loi 06/09/2026: Dre doc co nay, Ethan thi
    khong — nen Ethan chon bang ti so giai golf cho tin GPT-6 ("leaderboard",
    bat chu khong nhin noi dung). Moi vai tu viet cau bao, dieu kien thi chung."""
    rac = [ma for ma in ma_ds if ma and anh[ma].get("relevant") is False]
    return rac, "; ".join((anh[x].get("description") or "?")[:60] for x in rac)


def check_not_reused_across_runs(anh: dict, cap, m: dict) -> list:
    """KHONG DUNG LAI ANH DA DUNG (lien phien, dHash) — Ong Chu 06/09/2026.
    `cap`: [(nhan, ma)]. Ba vai lam anh deu goi check_not_reused theo cung mot
    cach (module luat rieng cua m["image_role"], LOW-182); gom de khong ai bo
    `link` (khoa theo TIN)."""
    rules = _vai.rules_module(m.get("image_role", ""))
    loi = []
    for nhan, ma in cap:
        l, _ = rules.check_not_reused(nhan, anh[ma]["original_path"], m.get("draft_id", ""),
                                     m.get("link", ""))
        loi += l
    return loi


def _clean_photo(a: dict, slug: str = "") -> bool:
    """Anh chup SACH: vision da noi ro "khong roi", lien quan, anh chup (khong chart),
    khong mat nguoi (mat nguoi con phu thuoc ten co trong bai), KHONG bi cong anh trong
    chan (LOW-288). Chua xet ty le."""
    if not a.get("uses") or a.get("relevant") is False or a.get("cluttered") is not False:
        return False
    if _vai.blocked_empty(a, slug):
        return False
    return a.get("kind") == "photo" and not a.get("ranking") and not a.get("faces")


def _clean_use_alone(a: dict, slug: str = "") -> bool:
    """Anh SACH dung mot minh duoc cho mot slide/the, khong can vai khai them gi:
    `_clean_photo`, ngang thi phai cat doc duoc (vision landscape_crop_ok + du cao).
    Thieu dieu kien nao cung khong tinh — cong check_image_fall chi duoc bat vai doi
    anh khi THAT SU co cho doi, khong de ket."""
    if not _clean_photo(a, slug):
        return False
    if a.get("landscape"):
        return (int(a.get("h") or 0) >= schema.HEIGHT_MIN_CROP_LANDSCAPE
                and a.get("landscape_crop_ok") is True)
    return True


def check_image_fall(anh: dict, dung: dict, m: dict) -> list:
    """ANH ROI chi dung khi HET anh sach (LOW-47, Ong Chu 13/09/2026: "khong uu
    tien su dung tat ca nhung anh nhin roi"). `dung`: {ma: nhan slide}.

    Khong cam han: tin it anh thi anh roi van la anh that cua tin, va carousel/
    card tu dat nen chu dac khi buoc dung. Chi chan khi con anh sach CHUA dung
    va CHUA len bai khac (check_not_reused) — de vai doi duoc that, khong ket."""
    # Roi ma DU TU KHOA chinh cua tin (vision TU_KHOA) thi mien — Ong Chu 13/09
    # chon chinh mot do hoa roi nhu vay lam hero.
    cluttered = [(nhan, ma) for ma, nhan in dung.items()
           if ma and (anh.get(ma) or {}).get("cluttered") and not (anh.get(ma) or {}).get("has_keywords")]
    if not cluttered:
        return []
    rules = _vai.rules_module(m.get("image_role", ""))
    sach = []
    for ma, a in anh.items():
        if ma in dung or not _clean_use_alone(a, m.get("image_role", "")):
            continue
        l, _ = rules.check_not_reused(ma, a["original_path"], m.get("draft_id", ""), m.get("link", ""))
        if not l:
            sach.append(ma)
    if not sach:
        return []
    return [f"{nhan}: {ma} là ảnh RỐI (chữ in sẵn/đồ hoạ nhồi/cắt ghép) mà vẫn còn ảnh sạch "
            f"chưa dùng: {', '.join(sach[:6])} — đổi sang ảnh sạch, ảnh rối chỉ dùng khi hết ảnh sạch"
            for nhan, ma in cluttered]


def check_empty_image(a: dict | None, nhan: str, limit: float) -> list:
    """Anh ma phan lon la nen tron (logo/bieu tuong nho tren nen trang) -> loi, o MOI
    designer (LOW-273, Ong Chu 19/09/2026: "ko chap nhan nhung hinh nhu the nay o moi
    designer"). `limit` = nguong rieng cua vai (image_rules_<vai>.EMPTY_SHARE_MAX).
    Vision chua do (khoa `empty_share` thieu) thi khong chan."""
    import subject_fit
    if not a or not subject_fit.too_empty(a.get("empty_share"), limit):
        return []
    return [f"{nhan}: {a.get('id')} gần như TRỐNG ({float(a['empty_share']):.0%} khung là nền trơn, "
            "chủ thể quá nhỏ) — cần ảnh có chủ thể chính lấp khung 4:5, không dùng logo nhỏ trên nền trơn"]


def subject_crop_window(a: dict, text_share: float, faces=None):
    """Khung cat 4:5 dat CHU THE CHINH tron trong khung va nam TREN vung chu, hoac None.
    Nguoi: hop dau tu `faces` (hop mat do bang code); khong co thi hop cua vision.
    Thieu kich thuoc/hop -> None (khong khang dinh vua)."""
    import subject_fit
    box = subject_fit.head_box(faces) if faces else a.get("subject_box")
    return subject_fit.crop_window(int(a.get("w") or 0), int(a.get("h") or 0), box, text_share)


def _fits_frame_with_subject(a: dict, rules) -> bool:
    """Anh ma CHU THE CHINH dat vua trong khung 4:5, tren vung chu slide than (LOW-273,
    Ong Chu 19/09/2026: "ko phai la tim hinh co ty le 4:5, ma la tim hinh co main
    character dat vua trong 4:5"; roi "ko can phai co tim anh doc, cang ko tim anh
    vuong. Mien la chu the hien thi duoc trong mot ratio crop 4:5 la duoc"). Ty le anh
    KHONG tinh: anh ngang chu the gon la vua (dre_submit tu cat quanh chu the, khong can
    vision noi "khong co chu"); anh 4:5 ma la logo nho tren nen trang thi KHONG. Dieu kien
    sach/lien quan/anh chup/khong mat nguoi nhu `_clean_photo`; anh ngang con phai du cao
    de cat khong nhoe. Thieu hop chu the (manifest cu) -> khong tinh."""
    if not _clean_photo(a):
        return False
    if a.get("landscape") and int(a.get("h") or 0) < schema.HEIGHT_MIN_CROP_LANDSCAPE:
        return False
    if a.get("empty_share") is None or not a.get("subject_box"):
        return False
    if float(a["empty_share"]) >= getattr(rules, "EMPTY_SHARE_MAX", 0.6):
        return False
    return subject_crop_window(a, getattr(rules, "TEXT_SHARE_BODY", 0.3)) is not None


def check_stack_last_resort(anh: dict, dung_anh: list, dung: dict, m: dict) -> list:
    """GHEP DOC chi khi HET anh co chu the dat vua khung 4:5 (LOW-273, Ong Chu
    19/09/2026: "uu tien tim hinh dat vua 4:5 ratio ma co chu the truoc, neu ko thi
    chuyen qua ghep" — roi lam ro cung ngay: tieu chi la CHU THE vua khung, khong
    phai ty le anh; xem `_fits_frame_with_subject`). `dung_anh`: [(nhan slide, [ma...])] (Context.dung_anh);
    `dung`: {ma: nhan slide}.

    Vi sao: ghep doc dat hai anh sat nhau — mot duong noi ngang giua khung, va nen
    chu che gan het anh duoi khi cau quote dai (cong LOW-215). Mot anh co chu the
    vua khung thi khong phai noi, khong bi che.

    Chi chan khi con anh vua khung CHUA dung va CHUA len bai khac
    (check_not_reused) — de vai doi duoc that, khong ket. Chi Dre goi ham nay."""
    ghep = [(nhan, mas) for nhan, mas in dung_anh if len(mas) >= 2]
    if not ghep:
        return []
    rules = _vai.rules_module(m.get("image_role", ""))
    vua = []
    for ma, a in anh.items():
        if ma in dung or not _fits_frame_with_subject(a, rules):
            continue
        l, _ = rules.check_not_reused(ma, a["original_path"], m.get("draft_id", ""), m.get("link", ""))
        if not l:
            vua.append(ma)
    if not vua:
        return []
    return [f"{nhan}: ghép {'+'.join(mas)} nhưng còn ảnh có CHỦ THỂ đặt vừa khung 4:5 chưa dùng: "
            f"{', '.join(vua[:6])} — dùng MỘT ảnh đó (\"image\": \"{vua[0]}\"; ảnh ngang thì thêm "
            "\"landscape_crop\": true, script tự cắt quanh chủ thể), ghép dọc chỉ khi hết"
            for nhan, mas in ghep]


def check_quote_translated(chu: str | None, nhan: str) -> list:
    """Quote/hook CON NGUYEN TIENG ANH -> loi. Luat "quote phai DICH sang tieng
    Viet" tu truoc chi nam trong SOUL/brief, khong cong nao kiem (06/09/2026).

    Do bang HAI dieu kien, khong phai mot: (1) khong co dau tieng Viet, VA
    (2) co >= 2 tu chuc nang tieng Anh. Ban dau chi do dieu kien (1) — sai:
    no chan ca nhan hop le toan ten rieng va so ("Claude Opus 4.5 vs GPT-5.2:
    82,5 vs 79,1 MMLU", "GPT-5 Codex Max: 2,75 USD / 1M token"), 5/6 hook thu
    that bi chan oan (do 06/09/2026). card.find_face_mark CO Y khong bao tieng
    Anh vi dung ly do do; cong nay khong duoc di nguoc quyet dinh ay.

    Tieng Viet GO MAT DAU khong phai viec cua ham nay — card.find_face_mark lo,
    va no bao dung ten loi."""
    t = (chu or "").strip()
    if len(t) < 25:
        return []
    import caption_check
    import vietnamese
    if caption_check.billion_odd_mark(t) >= 0.02:
        return []
    tu = re.findall(r"[A-Za-z']+", t.lower())
    anh_tu = {w for w in tu if w in _TU_ANH}
    if len(anh_tu) < 2:
        return []
    # TIENG VIET GO MAT DAU khong phai viec cua ham nay (dung y docstring tren): de cong
    # mat dau bao, no bao DUNG ten loi. LOW-289 (20/09/2026): cau Dre viet khong dau
    # "…cong nghe that su van hanh the nao" co "the"/"that" trong _TU_ANH nen bi bao
    # "con nguyen tieng Anh"; Dre viet lai quote hai lan roi block, trong khi viec phai
    # lam la go lai CO DAU. Do tren cau that: tieng Viet mat dau co 11-13 dau hieu Viet
    # va 0-2 tu chuc nang Anh; cau tieng Anh nguoc lai (1-2 va 5-8) — nen dem CA HAI,
    # khong dung mot dieu kien. Cum quen thuoc ("cong nghe", "cap nhat") la du chac.
    viet_tu = {w for w in tu if w in vietnamese.NEGATIVE_FACE_MARK}
    cum_viet = any(" " in x for x in vietnamese.find_face_mark(t))
    if cum_viet or (len(viet_tu) >= 3 and len(viet_tu) > len(anh_tu)):
        return []
    return [f"{nhan}: \"{t[:60]}…\" trông như còn nguyên tiếng Anh — phải DỊCH sang "
            "tiếng Việt (giữ nguyên tên riêng, thuật ngữ)"]


_CUM_DAN_THUA = ("đọc bài", "xem bài", "đọc thêm", "xem thêm", "nguồn:", "link:")
# Domain that ke ca khong http(s):// van bi Facebook/Instagram/Telegram quet
# thanh lien ket va giam hien thi bai dang — bat theo dang "tu.tld" bat ke hoa
# thuong, khong bat nham so thap phan ("16,35" khong co chu cai truoc dau cham).
_DOMAIN = re.compile(
    r"\b[a-zA-Z][a-zA-Z0-9-]*\.(?:com|net|org|vn|io|co|xyz|info|news|me|ai)\b",
    re.IGNORECASE)


def check_same_photo(anh: dict, dung_anh: list) -> list:
    """Hai MA khac nhau ma la CUNG MOT buc anh chup (tai tu hai nguon, cat khac nhau) len
    hai slide — hoac cung mot slide ghep (LOW-284, album Lovable: dien thoai o slide 5
    va 6, trang chu o slide 2 va 6). `dung_anh`: [(nhan slide, [ma...])]. Chi xet anh
    CHUP (chart/bang xep hang cung khuon van khop nhieu diem) — xem same_photo.py."""
    import same_photo
    dung = []                                   # [(nhan, ma)] theo thu tu slide, khong lap ma
    for nhan, ds in dung_anh:
        for ma in ds:
            a = anh.get(ma) or {}
            if ma and a.get("original_path") and a.get("kind") != "chart" and not a.get("ranking") \
                    and all(ma != x for _, x in dung):
                dung.append((nhan, ma))
    loi = []
    for i in range(len(dung)):
        for j in range(i + 1, len(dung)):
            (n1, m1), (n2, m2) = dung[i], dung[j]
            if same_photo.is_same_photo(anh[m1]["original_path"], anh[m2]["original_path"]):
                noi = n1 if n1 == n2 else f"{n1} và {n2}"
                loi.append(f"{noi}: {m1} và {m2} là CÙNG MỘT bức ảnh tải từ hai nguồn "
                           f"({anh[m1].get('domain') or '?'}, {anh[m2].get('domain') or '?'}) — "
                           "đổi một trong hai sang ảnh khác, mỗi slide một ảnh riêng (LOW-284)")
    return loi


def check_no_repeat_image_redo(anh: dict, dung_anh: list, m: dict, drafts_dir) -> list:
    """LAM LAI mot slide cu the nhung ban moi van la CUNG MOT anh cu, chi doi
    ten ma (Ong Chu 13/09/2026, Anthropic/Nvidia IPO: bam Lam lai chi ro slide
    6 hai lan lien, ca hai lan spec moi deu chon lai dung anh cu). Dong "DUNG
    lap lai anh cu" trong task chi la loi mem — cong nay la loi cung: so theo
    dHash (khong theo ma anh) cac anh GOC dang dung o tung slide voi danh sach
    dHash da bi che ghi trong drafts/<id>.img.json (approve_post._write_forbid_image_redo
    ghi luc bam nut Lam lai). Chi chan DUNG slide bi Ong Chu neu ten — cac slide
    khac trong ban lam lai duoc giu nguyen anh cu binh thuong."""
    draft_id = m.get("draft_id")
    if not draft_id:
        return []
    ip = Path(drafts_dir) / f"{draft_id}.img.json"
    if not ip.exists():
        return []
    try:
        im = json.loads(ip.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    cam = im.get("forbidden_slide_images") or {}
    if not cam:
        return []
    rules = _vai.rules_module(m.get("image_role", ""))
    from PIL import Image
    loi = []
    for nhan, ma_list in dung_anh:
        mo = re.search(r"slide (\d+)", nhan)
        so = "1" if nhan == "bìa" else (mo.group(1) if mo else None)
        ds = cam.get(so) if so else None
        if not ds:
            continue
        for ma in ma_list:
            fp = anh.get(ma, {}).get("original_path")
            if not fp:
                continue
            try:
                h = rules.dhash(Image.open(fp).convert("RGB"))
            except (OSError, ValueError):
                continue
            if any(rules.is_near_duplicate(h, int(c, 16)) for c in ds):
                loi.append(f"{nhan}: {ma} vẫn là ảnh đã bị Ông Chủ từ chối lúc làm lại trước "
                           "— chọn ảnh THẬT SỰ khác (khác nguồn, khác góc), không chỉ đổi mã")
                break
    return loi


def check_guide_source_compact(chu: str | None, nhan: str) -> list:
    """Dan nguon KHONG duoc co "đọc bài"/"xem bài"... (Ong Chu 13/09/2026: thua,
    carousel da co dau doc bai chinh la cai slide) va KHONG duoc co ten mien
    dang "tenbao.com" — nen tang (FB/IG/Telegram) quet chu do la lien ket va
    giam hien thi ca bai. Dan nguon chi can "via <ten bao>" hoac ten nguoi noi,
    khong can dong tu "doc/xem" va khong can duoi ten mien."""
    t = (chu or "").strip()
    if not t:
        return []
    loi = []
    thap = t.lower()
    cum = next((c for c in _CUM_DAN_THUA if c in thap), None)
    if cum:
        loi.append(f"{nhan}: \"{t[:60]}\" có cụm \"{cum}\" — thừa, bỏ đi, dẫn nguồn "
                   "chỉ cần \"via <tên báo>\" hoặc tên người nói")
    mien = _DOMAIN.search(t)
    if mien:
        loi.append(f"{nhan}: \"{t[:60]}\" có tên miền \"{mien.group(0)}\" — nền tảng quét "
                   "thành liên kết, giảm hiển thị cả bài. Bỏ đuôi miền, chỉ giữ tên báo "
                   "(vd \"via BusinessTimes\" thay vì \"via businesstimes.com\")")
    return loi


def check_rank_matches_image(chu: str, a: dict, nhan: str = "hook") -> list:
    """THU HANG vai viet len the phai TRUNG hang engine KHOANH trong anh (LOW-24).

    Ca 12/09/2026: hook "claude-opus-4-7-high leo lên #3 bảng văn bản Arena" in
    len anh khoanh hang #26 (bang khac). Brief co ghi "#26 / WebDev / Code Arena"
    nhung chi la chu dan; `needs_ranking_image` EP dung anh XH ma khong hoi hang.
    Day la cong: so trong chu phai la so trong anh, khong thi khong nop duoc.

    Chi xet khi anh la BANG CHUP THAT (is_capture) va co `rank`; the du phong (kind
    "card") in hang tu tieu de nen khong doi chieu. Chu khong noi hang -> khong
    chan (khong bat vai phai nhac hang). `extract_rank` hieu "dẫn đầu" = 1 va bo
    "top 10" kieu kich co danh sach — cung bo doc voi engine, khong doc rieng."""
    import ranking
    xh = (a or {}).get("ranking") or {}
    if not xh.get("rank") or not ranking.is_capture(xh.get("kind")):
        return []
    hang_chu = ranking.extract_rank(chu or "", xh.get("model") or "")
    if hang_chu is None or int(hang_chu) == int(xh["rank"]):
        return []
    return [f"{nhan}: viết #{hang_chu} nhưng ảnh {a.get('id', 'XH')} khoanh hàng "
            f"#{xh['rank']} trên {xh.get('site')} ({xh.get('board')}) — số trên thẻ phải "
            f"là số trong ảnh: sửa thành #{xh['rank']} (và nói đúng bảng đó), hoặc đổi ảnh"]


MINUTES_ALBUM_FIT_LEN = 10


def _recently_posted(vai: str, files, phut: int = MINUTES_ALBUM_FIT_LEN) -> bool:
    """Bo anh NAY co vua len Telegram trong `phut` phut qua khong.

    So theo TEN TEP + moc thoi gian, khong phai theo chuoi con cua draft_id
    (sua 06/09/2026 dot 2). Ban cu quet 400 dong cuoi cua MOI tep .jsonl va hoi
    `if draft_id in dong` — hai sai lam trong mot dong:

      1. KHONG co moc thoi gian. Bam "Lam lai": album lan 1 tu hom qua da co
         dong trong so; lan 2 `post()` nem GuiLoi NGAY (429, thieu tep) — nhanh
         cuu o duoi thay dong CU, ghi da_dung voi bo anh CHUA gui, roi in
         "ĐỪNG chạy lại". Album moi khong bao gio len, va anh bi khoa 14 ngay.
      2. So chuoi con: draft `gpt-5-...` khop moi dong cua `gpt-5-codex-...`.

    Doc ca hai truong `files` (co tu 05/09) va chuoi tho cho dong cu.
    """
    import json as _j
    import time as _t
    try:
        d = env_load.state_dir() / "telegram_sent"
        p = d / f"{vai}.jsonl"
        if not p.exists() or not files:
            return False
        ten = sorted(Path(f).name for f in files)
        moc = _t.time() - phut * 60
        for dong in reversed(p.read_text(encoding="utf-8").splitlines()[-200:]):
            try:
                r = _j.loads(dong)
            except ValueError:
                continue
            if (r.get("ts") or 0) < moc:
                break                      # cac dong con lai con cu hon nua
            if sorted(Path(f).name for f in (r.get("files") or [])) == ten:
                return True
    except OSError:
        pass
    return False


def send_album(vai: str, files, mo_ta: str, draft_id: str, wd: Path, da_dung, ghi: dict):
    """Gui anh/album len topic cua `vai` kem nut duyet, roi ghi previous_submission.json
    (`ghi` = cac truong rieng cua vai: cover_image/image_ids/image/hook/theme...). Tra ve message_id."""
    import send_telegram
    xong = schema.read_manifest(wd / state_paths.MANIFEST_FILE) or {}

    def _ghi_so(mid=None):
        """Ghi previous_submission.json + so anh da dung. Goi NGAY KHI album da len topic, ke
        ca khi buoc gui nut Duyet loi ngay sau do: anh da nam tren Telegram thi
        so PHAI co dong tuong ung, khong thi bai sau dung lai dung tam vua dang —
        chinh thu luat nay sinh ra de chan (do 06/09/2026)."""
        cb._write_json(wd / state_paths.PREVIOUS_SUBMISSION_FILE, {**ghi, "submitted_at": time.strftime("%H:%M %d/%m"),
                                           "submission_count": int((da_dung or {}).get("submission_count", 0)) + 1,
                                           # Moc de phan biet "Ong Chu bam Lam lai"
                                           # voi "vai chay lai" — xem check_redo_reused.
                                           "remakes": count_of_redo(draft_id),
                                           "message_id": mid})
        # Gom ma tu MOI khoa co the chua ma anh, khong doan theo hinh dang mot
        # khoa: Ethan de anh ghep thu hai o "image2", Dre/Kite de list o "image_ids".
        rules = _vai.rules_module(vai)
        goc = {a["id"]: a["original_path"] for a in xong.get("images", [])}
        ma_ds = []
        for k in ("image_ids", "image", "image2", "cover_image"):
            v = ghi.get(k)
            ma_ds += list(v) if isinstance(v, (list, tuple)) else [v]
        for ma in dict.fromkeys(x for x in ma_ds if x):
            if goc.get(ma):
                rules.record_used(goc[ma], draft_id, vai, xong.get("link", ""))

    # Nop THANH CONG thi xoa bo dem vong loi. `count_round_error` chi reset khi BO
    # LOI doi hoac qua 6 gio, con duong thanh cong truoc 06/09/2026 khong dung
    # vao tep submit_count.json — nen mot bai hong 2 lan vi "can >= 2 quote", sua
    # xong, gui duoc, roi mot gio sau Ong Chu bam Lam lai va vai lai quen quote
    # la repeat_count=3 NGAY LUOT DAU: [DUNG] va bao goi kanban_block.
    (wd / state_paths.SUBMIT_COUNT_FILE).unlink(missing_ok=True)
    try:
        res = send_telegram.post(vai, [str(f) for f in files], mo_ta[:1000], duyet=draft_id)
    except send_telegram.SendError as e:
        # Album co the DA len roi ma rieng buoc gui nut Duyet moi hong (429 flood
        # control chang han). Truoc 06/09/2026 nhanh nay thoat ngay, so trong ron
        # trong khi anh da nam tren topic.
        if _recently_posted(vai, files):
            _ghi_so()
            sys.exit(f"[LOI] album ĐÃ lên topic nhưng gửi nút Duyệt lỗi: {e}\n"
                     "Ảnh đã ghi vào sổ. Đợi 1–2 phút rồi chạy lại ĐÚNG lệnh nộp: script "
                     "chỉ gửi BÙ nút, không gửi trùng album (LOW-134). Vẫn lỗi thì "
                     "kanban_block, ghi rõ: THIẾU NÚT DUYỆT — Ông Chủ reply vào album "
                     "\"gửi cho <tên người viết>\" để duyệt.")
        sys.exit(f"[LOI] {e}")
    r = res.get("result")
    mid = (r[-1] if isinstance(r, list) else r or {}).get("message_id")
    if res.get("duplicate"):
        if res.get("button_state") == "resent":
            print(f"[xong] album đã lên từ lần trước; vừa gửi BÙ nút Duyệt "
                  f"(message_id={res.get('button_message_id')}).")
        elif res.get("button_state") != "sent":
            # Dong so cu (truoc LOW-134) khong biet lan truoc nut co len khong.
            # Khong duoc de vai in "da gui kem nut duyet" trong khi co the khong co nut nao.
            print("[CANH BAO] album trùng bản đã gửi trong 30 phút nên KHÔNG gửi lại, "
                  "và không rõ lần trước có nút Duyệt không. Xem lại topic: thiếu nút thì "
                  "báo Ông Chủ reply vào album \"gửi cho <tên người viết>\".")
    _ghi_so(mid)
    return mid


def write_blackboard(draft_id: str, key: str, value, author: str) -> None:
    """Ghi ban giao co cau truc len the goc (kanban swarm). Best-effort: hong thi
    in mot dong canh bao, khong lam hong bai."""
    import blackboard
    ok, loi = blackboard.write_background(draft_id, key, value, author)
    if not ok:
        print(f"[CANH BAO] bang den: {loi}")
