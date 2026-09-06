#!/usr/bin/env python3
"""brief_chung.py — khung chung cua brief bon vai doc `xong.json`.

Vi sao (audit dot 1, 06/09/2026): `dre_chuan_bi`, `ethan_chuan_bi`,
`kite_chuan_bi`, `miles_chuan_bi` deu mo brief bang cung mot khung — dong tieu
de, dong Brand/draft, Link goc, "Tieu de bai goc", khoi LAM LAI, khoi "## Tu
lieu" — chep ~30 dong bon lan. Chung da bat dau lech: cho ghi "Tom tat (Finn)",
cho ghi "Tom tat (Finn/Vera)"; cho cat 15 cau co so, cho cat 25; ba trong bon co
dong "(Khong boc duoc chu tu nguon...)" con mot cai thi khong — nen dung ca do
vai lai khong duoc nhac la thieu tu lieu.

Tep nay giu PHAN KHUNG. Phan RIENG cua tung vai (luat slide, bang ma anh, cach
viet hook) van nam trong `*_chuan_bi.py` cua vai do — do moi la thu vai can doc
ky, va gom chung lai chi lam mot ham day tham so.
"""


def dau(m: dict, ten_vai: str, dong_2: str, nhan_link: str = "Link gốc") -> list:
    """Bon dong mo dau: tieu de, dong tom tat cau hinh, link, tieu de goc.

    `dong_2` la phan RIENG cua vai (so slide toi thieu, kieu the mac dinh...) —
    truyen vao nguyen van vi moi vai mot khac.
    """
    L = [f"# {ten_vai} — ĐÃ CHUẨN BỊ XONG: {m['title']}", dong_2,
         f"{nhan_link}: {m['link']}" + (f" | via: {m['via']}" if m.get("via") else "")]
    if m.get("tieu_de_en"):
        L.append(f"Tiêu đề bài gốc: {m['tieu_de_en']}")
    return L


def khoi_lam_lai(da_dung: dict | None, mo_ta: str) -> list:
    """Khoi canh bao LAM LAI. `mo_ta` la cau noi ro lan nay phai doi CAI GI —
    khac nhau tung vai (bia+hook, anh+hook, theme+hero)."""
    if not da_dung:
        return []
    return ["", f"⚠️ LÀM LẠI — lần trước ({da_dung.get('luc', '?')}): {mo_ta}"]


def khoi_tu_lieu(m: dict, tieu_de: str = "## Tư liệu", nhan: str = "Finn",
                 n_cau: int = 25, n_doan: int = 1500,
                 dong_thieu: str = "(Không bóc được chữ từ nguồn — viết từ tóm tắt, "
                                   "KHÔNG bịa số.)") -> list:
    """Khoi "## Tu lieu": tom tat, nguon, cau co so, doan dau.

    LUON co `dong_thieu` khi khong boc duoc gi. Truoc 06/09/2026 brief cua Ethan
    thieu dong do, nen tren bai boc hong vai khong duoc nhac la dang viet chay —
    dung loai im lang ma ca bo cong chan sinh ra de chan.
    """
    L = ["", tieu_de]
    if m.get("summary"):
        L.append(f"Tóm tắt ({nhan}): {m['summary']}")
    if m.get("source_note"):
        L.append(f"Nguồn ({nhan}): {m['source_note']}")
    tl = m.get("tu_lieu", {}) or {}
    cs = tl.get("cau_co_so") or []
    if cs:
        L.append(f"Câu có số liệu ({len(cs)} câu, bóc từ bài):")
        for i, c in enumerate(cs[:n_cau], 1):
            L.append(f"  {i}. {c}")
    if tl.get("doan_dau"):
        L.append(f"Đoạn đầu bài gốc: {tl['doan_dau'][:n_doan]}")
    if not cs and not tl.get("doan_dau"):
        L.append(dong_thieu)
    return L


def duoi(lenh: str, cam: list = ()) -> list:
    """Doan ket: mot lenh duy nhat, va danh sach thu KHONG duoc lam."""
    L = ["", "## Rồi chạy đúng MỘT lệnh", lenh]
    if cam:
        L.append("")
        L += [f"KHÔNG {c}" for c in cam]
    return L
