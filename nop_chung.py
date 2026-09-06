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


def chuan(t) -> str:
    """Chuoi de so 'giong het': gop khoang trang, ha chu thuong."""
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def nap(draft_id: str, spec_arg, ten_brief: str, ten_nop: str) -> tuple:
    """(meta, brand, wd, m, spec, spec_path, da_dung) cho mot draft. Thieu gi thi
    dung han voi cau chi dan cho vai (sys.exit) — nop la CLI, vai doc stdout."""
    meta = cb.nap_meta(draft_id)               # dat CT_BRAND theo brand cua draft
    brand = cb._brand_cua(meta)
    wd = cb.workdir(env_load.state_dir(), draft_id)
    m = cb._doc_json(wd / "xong.json")
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


def kiem_lam_lai(da_dung, nhan_anh: str, anh_moi, hook_moi, khoa_anh: str = "anh") -> list:
    """Lam lai ma van giu anh/hook cua lan truoc -> loi. `khoa_anh` la khoa trong
    da_dung.json ("bia" voi carousel, "anh" voi hero)."""
    if not da_dung:
        return []
    loi = []
    cu = da_dung.get(khoa_anh)
    if anh_moi and cu and anh_moi == cu:
        loi.append(f"LÀM LẠI: {nhan_anh} vẫn là {cu} như lần trước — Ông Chủ bấm làm lại "
                   f"nghĩa là {nhan_anh} chưa đạt, đổi {nhan_anh} khác")
    if chuan(hook_moi) == chuan(da_dung.get("hook")):
        loi.append("LÀM LẠI: hook giống hệt lần trước — viết hook khác")
    return loi


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


def _album_da_len(draft_id: str) -> bool:
    """Album cua draft nay da duoc Telegram nhan chua — doc nhat ky telegram_sent
    ma gui_telegram ghi NGAY SAU khi album di, truoc buoc gui nut Duyet."""
    try:
        d = env_load.state_dir() / "telegram_sent"
        if not d.exists() or not draft_id:
            return False
        for p in d.glob("*.jsonl"):
            for dong in p.read_text(encoding="utf-8").splitlines()[-400:]:
                if draft_id in dong:
                    return True
    except OSError:
        pass
    return False


def gui_album(vai: str, files, mo_ta: str, draft_id: str, wd: Path, da_dung, ghi: dict):
    """Gui anh/album len topic cua `vai` kem nut duyet, roi ghi da_dung.json
    (`ghi` = cac truong rieng cua vai: bia/anh/hook/theme...). Tra ve message_id."""
    import gui_telegram
    xong = cb._doc_json(wd / "xong.json") or {}

    def _ghi_so(mid=None):
        """Ghi da_dung.json + so anh da dung. Goi NGAY KHI album da len topic, ke
        ca khi buoc gui nut Duyet loi ngay sau do: anh da nam tren Telegram thi
        so PHAI co dong tuong ung, khong thi bai sau dung lai dung tam vua dang —
        chinh thu luat nay sinh ra de chan (do 06/09/2026)."""
        cb._ghi_json(wd / "da_dung.json", {**ghi, "luc": time.strftime("%H:%M %d/%m"),
                                           "lan": int((da_dung or {}).get("lan", 0)) + 1,
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

    try:
        res = gui_telegram.post(vai, [str(f) for f in files], mo_ta[:1000], duyet=draft_id)
    except gui_telegram.GuiLoi as e:
        # Album co the DA len roi ma rieng buoc gui nut Duyet moi hong (429 flood
        # control chang han). Truoc 06/09/2026 nhanh nay thoat ngay, so trong ron
        # trong khi anh da nam tren topic.
        if _album_da_len(draft_id):
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
