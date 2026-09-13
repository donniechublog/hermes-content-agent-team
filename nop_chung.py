#!/usr/bin/env python3
"""nop_chung.py — phan dung chung cua cac script NOP (dre_nop, ethan_nop, kite_nop,
miles_nop): nap meta/workdir/xong.json/spec.json, chuan hoa chuoi, kiem "lam
lai", gui album kem nut duyet + ghi da_dung.json, ghi bang den.

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
import anh_chuan_bi as cb                                    # noqa: E402
import env_load                                              # noqa: E402
import schema                                                # noqa: E402
import vai as _vai                                           # noqa: E402


def chuan(t) -> str:
    """Chuoi de so 'giong het': gop khoang trang, ha chu thuong."""
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def nap(draft_id: str, spec_arg, ten_brief: str, ten_nop: str) -> tuple:
    """(meta, brand, wd, m, spec, spec_path, da_dung) cho mot draft. Thieu gi thi
    dung han voi cau chi dan cho vai (sys.exit) — nop la CLI, vai doc stdout."""
    meta = cb.nap_meta(draft_id)               # dat CT_BRAND theo brand cua draft
    brand = cb._brand_cua(meta)
    wd = cb.workdir(env_load.state_dir(), draft_id)
    m = schema.doc_manifest(wd / "xong.json")   # bu khoa dan xuat cho ban cu (C-r2-5)
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
    return meta, brand, wd, m, spec, spec_path, cb._doc_json(wd / "da_dung.json")


# ---- ai viet bai nay, va lenh cua nguoi do (LOW-13, 10/09/2026) -------------
# Tu khi co hai nguoi viet, "miles_nop.py" khong con la cau tra loi dung cho moi
# bai. Ba thu duoi day tung go cung ten Miles: ten script in trong brief, ten
# tep brief, va `author` ghi len bang den. Go cung thi task cua Jika bao Jika
# chay lenh cua Miles, va ban giao cua Jika len bang den mang ten Miles — khong
# cho nao bao loi, chi doc ra sai.

def vai_viet_cua_bai(draft_id: str, brand: str = "") -> str:
    """SLUG nguoi viet da chot cho bai nay.

    Nguon su that la sidecar `<draft_id>.writer.json` — duyet_chon_tin chot
    nguoi viet NGAY luc chon tin (luc do con biet vai quet), con luc nop thi
    vai quet da khong con trong tam tay. Sidecar cu (ghi truoc LOW-13) khong co
    khoa `vai_viet`, hoac ghi mot slug la -> hoi lai ban dang ky theo brand."""
    d = cb._doc_json(cb.DRAFTS / f"{draft_id}.writer.json", {}) or {}
    slug = str(d.get("vai_viet") or "")
    if slug in _vai.VAI:
        return slug
    return _vai.vai_viet_cua(None, brand)


def persona_viet(slug: str) -> str:
    """Slug vai viet -> chu dung trong TEN SCRIPT va `author` bang den ("miles",
    "jika"). Lay tu ban dang ky chu khong chep bang thu hai: cac cap script deu
    dat theo ten nhan vat (miles_nop, dre_nop, kite_nop...), nen ten persona
    viet thuong CHINH LA tien to script."""
    return _vai.ten_hien(slug).lower()


def so_lan_lam_lai(draft_id: str) -> int:
    """So lan Ong Chu da bam "Lam lai" cho bai nay (drafts/<id>.img.json)."""
    d = cb._doc_json(cb.DRAFTS / f"{draft_id}.img.json", {}) or {}
    return int(d.get("remakes", 0) or 0)


def kiem_lam_lai(da_dung, nhan_anh: str, anh_moi, hook_moi, khoa_anh: str = "anh",
                 draft_id: str = "") -> list:
    """Lam lai ma van giu anh/hook cua lan truoc -> loi. `khoa_anh` la khoa trong
    da_dung.json ("bia" voi carousel, "anh" voi hero).

    CHI ap khi Ong Chu THAT SU bam "Lam lai" (sua 06/09/2026 dot 2). Truoc day
    dieu kien la "co da_dung.json", ma tep do duoc ghi o MOI lan gui va
    duyet_bai khong bao gio xoa — nen moi lan chay lai vi bat ky ly do gi (task
    kanban retry, vai chay lai sau mot [CANH BAO]) deu bi bao "Ong Chu bam lam
    lai nghia la bia chua dat, doi bia khac". Vai doi bia that, roi `gui_album`
    gui BO THU HAI voi mot nut Duyet thu hai; md5 30 phut cua gui_telegram chi
    chan duoc truong hop tep y het.

    Moc so sanh la `remakes` trong img.json — chinh con so duyet_bai tang moi
    lan bam nut.
    """
    if not da_dung:
        return []
    if draft_id and so_lan_lam_lai(draft_id) <= int(da_dung.get("remakes", -1)):
        return []                    # chay lai, KHONG phai Ong Chu bam lam lai
    loi = []
    cu = da_dung.get(khoa_anh)
    if anh_moi and cu and anh_moi == cu:
        loi.append(f"LÀM LẠI: {nhan_anh} vẫn là {cu} như lần trước — Ông Chủ bấm làm lại "
                   f"nghĩa là {nhan_anh} chưa đạt, đổi {nhan_anh} khác")
    if chuan(hook_moi) == chuan(da_dung.get("hook")):
        loi.append("LÀM LẠI: hook giống hệt lần trước — viết hook khác")
    return loi


# So lan nop HONG voi CUNG mot bo loi truoc khi coi la tac (xem dem_vong_loi).
TOI_DA_VONG = 3


def dem_vong_loi(wd, loi: list, lenh: str, toi_da: int = TOI_DA_VONG) -> int:
    """Dem so lan nop hong LIEN TIEP voi cung mot bo loi. Tra ve ma thoat.

    "Toi da 2 lan sua [LOI]" truoc 06/09/2026 chi la CHU trong task body —
    khong mot dong code nao dem. Ghep voi cong phi tat dinh (vision lien_quan
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
    p = Path(wd) / "nop_lan.json"
    ky = hashlib.md5("\n".join(sorted(str(x) for x in loi)).encode()).hexdigest()
    cu = {}
    try:
        cu = _j.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if cu.get("ky") != ky or _t.time() - cu.get("luc", 0) > 6 * 3600:
        cu = {"ky": ky, "lan": 0}
    lan = int(cu.get("lan", 0)) + 1
    try:
        p.write_text(_j.dumps({"ky": ky, "lan": lan, "luc": int(_t.time()),
                               "loi_cuoi": [str(x)[:200] for x in loi[:5]]},
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


def chu_bai_cua(m: dict, wd: Path) -> str:
    """Chu bai + tu lieu gom ve mot chuoi chu thuong, de doi chieu ten nguoi hay
    so lieu vai khai co that su nam trong bai khong."""
    tl = m.get("tu_lieu") or {}
    s = ((m.get("chu_bai") or "") + " " + (tl.get("doan_dau") or "")
         + " " + " ".join(tl.get("cau_co_so") or [])).lower()
    try:
        s += " " + (wd / "tu_lieu.md").read_text(encoding="utf-8").lower()
    except OSError:
        pass
    return s


def _khong_dau(t: str) -> str:
    """Bo dau tieng Viet, ha chu thuong (cung phep nhu teaser_assemble._bo_dau)."""
    t = t.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", t)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def _tu(t: str) -> list:
    """Chuoi -> danh sach TU da bo dau, moi ky tu khong phai chu/so la ranh gioi."""
    return [w for w in re.split(r"[^0-9a-z]+", _khong_dau(t)) if w]


def _ten_co_trong_bai(nv: str, chu_bai: str) -> bool:
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
    ten = _tu(dau_tien)
    if not ten:
        return True                      # khong con gi de doi chieu -> khong chan
    bai = set(_tu(chu_bai))
    if all(w in bai for w in ten):
        return True
    # Ten dai (co ten dem): chap nhan hai tu cuoi — "Nguyen Van A" khop "Van A".
    return len(ten) > 2 and all(w in bai for w in ten[-2:])


def kiem_nhan_vat(anh: dict, ma_ds, nhan_vat, chu_bai: str, nhan: str) -> list:
    """Cong chan MAT NGUOI dung chung Dre/Ethan.

    Truoc 06/09/2026 chi dre_nop co day du ba lop nay; ethan_nop chi kiem "co
    khai ten hay chua", nen mot cai ten CEO bia dat van qua cong cho the hero
    (su co bia Broadcom 05/09: anh quan chuc G20, khai "Hock Tan"). Gom mot cho
    de hai vai khong con lech."""
    co = [ma for ma in ma_ds if ma and anh.get(ma, {}).get("mat")]
    nv = str(nhan_vat or "").strip()
    loi = []
    if co and not nv:
        loi.append(f"{nhan}{', '.join(co)} có mặt người mà không khai \"nhan_vat\": "
                   "\"<tên người trong bài>\" — khai tên nếu đúng là nhân vật, "
                   "không thì đổi ảnh khác")
        return loi
    if not co or not nv:
        return loi
    if chu_bai and not _ten_co_trong_bai(nv, chu_bai):
        loi.append(f"{nhan}nhan_vat \"{nv}\" không xuất hiện trong chữ bài — "
                   "khai tên người KHÔNG có trong bài là bịa. Bỏ ảnh này. "
                   "(Nếu tên đúng thì bỏ phần chức danh: khai \"Sam Altman\", "
                   "không khai \"Sam Altman (CEO OpenAI)\".)")
    # VISION MO TA: chi chan cac cum HEP. Truoc 06/09/2026 bo tu khoa co ca tu
    # tran "logo", ma cong nay chi no khi anh CO MAT NGUOI va vai DA khai ten —
    # tuc no nham dung vao anh chan dung/su kien, loai anh the hero can nhat.
    # Anh hop le nhat cua loai do la "CEO dung tren san khau, phia sau la logo
    # hang": vision tra dung LIEN_QUAN=co (chinh prompt o anh_chuan_bi day rang
    # logo-tren-toa-nha / su kien cua chinh cong ty trong bai LA lien quan), roi
    # cong nay van chan vi mo ta co chuoi con "logo". Anh khong lien quan da co
    # cong rieng (`lien_quan is False` o dre_nop/ethan_nop), nen o day chi giu
    # nhung cum thuc su noi len "day la logo cua TO BAO, khong phai cua bai".
    for ma in co:
        mo_ta = (anh.get(ma, {}).get("mo_ta") or "").lower()
        if mo_ta and any(k in mo_ta for k in ("không liên quan", "g20",
                                              "logo báo", "logo của tờ",
                                              "logo hãng tin", "watermark")):
            loi.append(f"{nhan}{ma} — vision mô tả: \"{anh[ma]['mo_ta'][:80]}\" — "
                       "không phải nhân vật bài này")
    return loi


def kiem_so_tren_anh(chu: str, m: dict, wd: Path) -> list:
    """Canh bao (khong chan) cac con so vai viet len ANH ma tu lieu khong co.

    Cung mot phep doi chieu caption_check dung cho caption cua Miles, nhung
    truoc 06/09/2026 khong vai lam anh nao goi — so bia tren slide di thang len
    Telegram. Chi CANH BAO vi doi don vi (2,5 ti / 2.5B) la chuyen binh thuong."""
    import caption_check
    la = caption_check.so_la(chu, chu_bai_cua(m, wd))
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


def can_anh_xep_hang(m: dict, a: dict) -> bool:
    """TIN XEP HANG ma anh chinh/bia KHONG phai bang xep hang -> phai doi.

    CHI khi engine THUC SU CHUP duoc bang (`xep_hang.la_chup(kieu)` — LOW-21:
    ban cu so voi chuoi "chup" ma xep_hang chua bao gio phat ra). Truoc
    06/09/2026 chieu cong nay chan ca khi m["xep_hang"] la None — bao vai dung
    ma "XH" trong khi ma do khong ton tai, nen vai sua kieu gi cung sai va khong
    bao gio nop duoc. Ba duong dan toi canh do: --khong-browser, tach_model()
    rong (tin xep hang KHONG neu ten model), hoac tim_va_chup nem. The DU PHONG
    (kieu="the") cung khong ep: no la anh engine tu dung, chua he doc bang that.
    Dre va Ethan tung moi ben mot ban cua dieu kien nay (07/09/2026 gom lai)."""
    import xep_hang
    return bool(m.get("tin_xep_hang")
                and xep_hang.la_chup((m.get("xep_hang") or {}).get("kieu"))
                and not a.get("xep_hang"))


def anh_khong_lien_quan(anh: dict, ma_ds) -> tuple:
    """Cac ma bi vision danh dau KHONG LIEN QUAN bai, kem mo ta cua chung.

    Tra ve (rac, mo_ta). Ong Chu bat loi 06/09/2026: Dre doc co nay, Ethan thi
    khong — nen Ethan chon bang ti so giai golf cho tin GPT-6 ("leaderboard",
    bat chu khong nhin noi dung). Moi vai tu viet cau bao, dieu kien thi chung."""
    rac = [ma for ma in ma_ds if ma and anh[ma].get("lien_quan") is False]
    return rac, "; ".join((anh[x].get("mo_ta") or "?")[:60] for x in rac)


def kiem_da_dung_nhieu(anh: dict, cap, m: dict) -> list:
    """KHONG DUNG LAI ANH DA DUNG (lien phien, dHash) — Ong Chu 06/09/2026.
    `cap`: [(nhan, ma)]. Ba vai lam anh deu goi luat_anh.kiem_da_dung theo
    cung mot cach; gom de khong ai bo `link` (khoa theo TIN, xem luat_anh)."""
    import luat_anh
    loi = []
    for nhan, ma in cap:
        l, _ = luat_anh.kiem_da_dung(nhan, anh[ma]["goc"], m.get("draft_id", ""),
                                     m.get("link", ""))
        loi += l
    return loi


def _sach_dung_mot_minh(a: dict) -> bool:
    """Anh SACH dung mot minh duoc cho mot slide/the, khong can vai khai them gi:
    vision da noi ro "khong roi", lien quan, anh chup (khong chart), khong mat
    nguoi (mat nguoi con phu thuoc ten co trong bai), khong ngang (anh ngang
    con phai ghep hoac cat doc — chua chac lam duoc). Thieu dieu kien nao cung
    khong tinh — cong kiem_anh_roi chi duoc bat vai doi anh khi THAT SU co cho
    doi, khong duoc de vai ket vong."""
    if not a.get("dung") or a.get("lien_quan") is False or a.get("roi") is not False:
        return False
    return not (a.get("loai") != "anh" or a.get("xep_hang") or a.get("mat") or a.get("ngang"))


def kiem_anh_roi(anh: dict, dung: dict, m: dict) -> list:
    """ANH ROI chi dung khi HET anh sach (LOW-47, Ong Chu 13/09/2026: "khong uu
    tien su dung tat ca nhung anh nhin roi"). `dung`: {ma: nhan slide}.

    Khong cam han: tin it anh thi anh roi van la anh that cua tin, va carousel/
    card tu dat nen chu dac khi buoc dung. Chi chan khi con anh sach CHUA dung
    va CHUA len bai khac (kiem_da_dung) — de vai doi duoc that, khong ket."""
    # Roi ma DU TU KHOA chinh cua tin (vision TU_KHOA) thi mien — Ong Chu 13/09
    # chon chinh mot do hoa roi nhu vay lam hero.
    roi = [(nhan, ma) for ma, nhan in dung.items()
           if ma and (anh.get(ma) or {}).get("roi") and not (anh.get(ma) or {}).get("du_tu_khoa")]
    if not roi:
        return []
    import luat_anh
    sach = []
    for ma, a in anh.items():
        if ma in dung or not _sach_dung_mot_minh(a):
            continue
        l, _ = luat_anh.kiem_da_dung(ma, a["goc"], m.get("draft_id", ""), m.get("link", ""))
        if not l:
            sach.append(ma)
    if not sach:
        return []
    return [f"{nhan}: {ma} là ảnh RỐI (chữ in sẵn/đồ hoạ nhồi/cắt ghép) mà vẫn còn ảnh sạch "
            f"chưa dùng: {', '.join(sach[:6])} — đổi sang ảnh sạch, ảnh rối chỉ dùng khi hết ảnh sạch"
            for nhan, ma in roi]


def kiem_quote_dich(chu: str, nhan: str) -> list:
    """Quote/hook CON NGUYEN TIENG ANH -> loi. Luat "quote phai DICH sang tieng
    Viet" tu truoc chi nam trong SOUL/brief, khong cong nao kiem (06/09/2026).

    Do bang HAI dieu kien, khong phai mot: (1) khong co dau tieng Viet, VA
    (2) co >= 2 tu chuc nang tieng Anh. Ban dau chi do dieu kien (1) — sai:
    no chan ca nhan hop le toan ten rieng va so ("Claude Opus 4.5 vs GPT-5.2:
    82,5 vs 79,1 MMLU", "GPT-5 Codex Max: 2,75 USD / 1M token"), 5/6 hook thu
    that bi chan oan (do 06/09/2026). card.tim_mat_dau CO Y khong bao tieng
    Anh vi dung ly do do; cong nay khong duoc di nguoc quyet dinh ay.

    Tieng Viet GO MAT DAU khong phai viec cua ham nay — card.tim_mat_dau lo,
    va no bao dung ten loi."""
    t = (chu or "").strip()
    if len(t) < 25:
        return []
    import caption_check
    if caption_check.ty_le_dau(t) >= 0.02:
        return []
    tu = re.findall(r"[A-Za-z']+", t.lower())
    if sum(1 for w in tu if w in _TU_ANH) < 2:
        return []
    return [f"{nhan}: \"{t[:60]}…\" trông như còn nguyên tiếng Anh — phải DỊCH sang "
            "tiếng Việt (giữ nguyên tên riêng, thuật ngữ)"]


def kiem_hang_tren_the(chu: str, a: dict, nhan: str = "hook") -> list:
    """THU HANG vai viet len the phai TRUNG hang engine KHOANH trong anh (LOW-24).

    Ca 12/09/2026: hook "claude-opus-4-7-high leo lên #3 bảng văn bản Arena" in
    len anh khoanh hang #26 (bang khac). Brief co ghi "#26 / WebDev / Code Arena"
    nhung chi la chu dan; `can_anh_xep_hang` EP dung anh XH ma khong hoi hang.
    Day la cong: so trong chu phai la so trong anh, khong thi khong nop duoc.

    Chi xet khi anh la BANG CHUP THAT (la_chup) va co `hang`; the du phong (kieu
    "the") in hang tu tieu de nen khong doi chieu. Chu khong noi hang -> khong
    chan (khong bat vai phai nhac hang). `tach_hang` hieu "dẫn đầu" = 1 va bo
    "top 10" kieu kich co danh sach — cung bo doc voi engine, khong doc rieng."""
    import xep_hang
    xh = (a or {}).get("xep_hang") or {}
    if not xh.get("hang") or not xep_hang.la_chup(xh.get("kieu")):
        return []
    hang_chu = xep_hang.tach_hang(chu or "", xh.get("model") or "")
    if hang_chu is None or int(hang_chu) == int(xh["hang"]):
        return []
    return [f"{nhan}: viết #{hang_chu} nhưng ảnh {a.get('ma', 'XH')} khoanh hàng "
            f"#{xh['hang']} trên {xh.get('site')} ({xh.get('bang')}) — số trên thẻ phải "
            f"là số trong ảnh: sửa thành #{xh['hang']} (và nói đúng bảng đó), hoặc đổi ảnh"]


PHUT_ALBUM_VUA_LEN = 10


def _album_da_len(vai: str, files, phut: int = PHUT_ALBUM_VUA_LEN) -> bool:
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


def gui_album(vai: str, files, mo_ta: str, draft_id: str, wd: Path, da_dung, ghi: dict):
    """Gui anh/album len topic cua `vai` kem nut duyet, roi ghi da_dung.json
    (`ghi` = cac truong rieng cua vai: bia/anh/hook/theme...). Tra ve message_id."""
    import gui_telegram
    xong = schema.doc_manifest(wd / "xong.json") or {}

    def _ghi_so(mid=None):
        """Ghi da_dung.json + so anh da dung. Goi NGAY KHI album da len topic, ke
        ca khi buoc gui nut Duyet loi ngay sau do: anh da nam tren Telegram thi
        so PHAI co dong tuong ung, khong thi bai sau dung lai dung tam vua dang —
        chinh thu luat nay sinh ra de chan (do 06/09/2026)."""
        cb._ghi_json(wd / "da_dung.json", {**ghi, "luc": time.strftime("%H:%M %d/%m"),
                                           "lan": int((da_dung or {}).get("lan", 0)) + 1,
                                           # Moc de phan biet "Ong Chu bam Lam lai"
                                           # voi "vai chay lai" — xem kiem_lam_lai.
                                           "remakes": so_lan_lam_lai(draft_id),
                                           "message_id": mid})
        # Gom ma tu MOI khoa co the chua ma anh, khong doan theo hinh dang mot
        # khoa: Ethan de anh ghep thu hai o "anh2", Kite de o "hinh".
        import luat_anh
        goc = {a["ma"]: a["goc"] for a in xong.get("anh", [])}
        ma_ds = []
        for k in ("anh", "anh2", "bia", "hinh"):
            v = ghi.get(k)
            ma_ds += list(v) if isinstance(v, (list, tuple)) else [v]
        for ma in dict.fromkeys(x for x in ma_ds if x):
            if goc.get(ma):
                luat_anh.ghi_da_dung(goc[ma], draft_id, vai, xong.get("link", ""))

    # Nop THANH CONG thi xoa bo dem vong loi. `dem_vong_loi` chi reset khi BO
    # LOI doi hoac qua 6 gio, con duong thanh cong truoc 06/09/2026 khong dung
    # vao tep nop_lan.json — nen mot bai hong 2 lan vi "can >= 2 quote", sua
    # xong, gui duoc, roi mot gio sau Ong Chu bam Lam lai va vai lai quen quote
    # la lan=3 NGAY LUOT DAU: [DUNG] va bao goi kanban_block.
    (wd / "nop_lan.json").unlink(missing_ok=True)
    try:
        res = gui_telegram.post(vai, [str(f) for f in files], mo_ta[:1000], duyet=draft_id)
    except gui_telegram.GuiLoi as e:
        # Album co the DA len roi ma rieng buoc gui nut Duyet moi hong (429 flood
        # control chang han). Truoc 06/09/2026 nhanh nay thoat ngay, so trong ron
        # trong khi anh da nam tren topic.
        if _album_da_len(vai, files):
            _ghi_so()
            sys.exit(f"[LOI] album ĐÃ lên topic nhưng gửi nút Duyệt lỗi: {e}\n"
                     "Ảnh đã ghi vào sổ. ĐỪNG chạy lại (sẽ trùng) — báo Ông Chủ "
                     "duyệt tay bộ vừa lên.")
        sys.exit(f"[LOI] {e}")
    r = res.get("result")
    mid = (r[-1] if isinstance(r, list) else r or {}).get("message_id")
    if res.get("trung"):
        # post() thay md5 trung trong 30 phut nen tra ve SOM, KHONG gui nut Duyet.
        # Khong duoc de vai in "da gui kem nut duyet" trong khi khong co nut nao.
        print("[CANH BAO] album trùng bản đã gửi trong 30 phút nên KHÔNG gửi lại, "
              "và KHÔNG có nút Duyệt mới. Xem lại topic: bộ trước mà thiếu nút thì "
              "báo Ông Chủ duyệt tay.")
    _ghi_so(mid)
    return mid


def ghi_bang_den(draft_id: str, key: str, value, author: str) -> None:
    """Ghi ban giao co cau truc len the goc (kanban swarm). Best-effort: hong thi
    in mot dong canh bao, khong lam hong bai."""
    import bang_den
    ok, loi = bang_den.ghi_nen(draft_id, key, value, author)
    if not ok:
        print(f"[CANH BAO] bang den: {loi}")
