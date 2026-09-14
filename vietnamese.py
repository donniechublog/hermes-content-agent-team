#!/usr/bin/env python3
"""vietnamese.py — mấy phép kiểm chữ tiếng Việt dùng chung.

Tách khỏi `card.py` ngày 06/09/2026 (audit đợt 2). Hai hàm dưới đây là cổng
chặn CHỮ, không liên quan gì tới vẽ ảnh, nhưng vì chúng sống trong module vẽ
thẻ nên `manifest_write`, `ada_submit`, `cape_submit`, `itachi_submit` và cả `render_edu`
(renderer HTML) đều phải `import card` — kéo theo PIL và 1.347 dòng dựng ảnh
chỉ để hỏi "chuỗi này có bị gõ mất dấu không". Sửa `card.py` là đụng luôn cả
Nova, Ada, Jean.

`card.py` vẫn re-export hai tên này nên mọi lời gọi cũ giữ nguyên.
"""
import re

# Em-dash bi cam trong moi van ban dang. caption_check chan o bai viet, publish
# doi not truoc khi gui, nhung THE ANH di duong khac nen truot qua. Chan tai day.
MARK_FORBID = {"\u2014": ",", "\u2013": "-", "\u2012": "-", "\u2015": "-"}


def drop_mark_forbid(t: str) -> str:
    if not t:
        return t
    for a, b in MARK_FORBID.items():
        t = t.replace(a, b)
    return re.sub(r"\s+,", ",", re.sub(r"\s{2,}", " ", t)).strip()


# Tieng Viet KHONG DAU tren the la loi nang: the la thu nguoi doc nhin thay dau
# tien, va chu khong dau lam ca kenh trong nhu lam au. Da lot mot lan — nhan
# "CONG CU" in ra tren the that.
#
# Cach nhan biet: tim TU TIENG VIET quen thuoc bi go mat dau. Khong the chi dua
# vao "co dau hay khong", vi tieu de hop le van co the toan tieng Anh
# ("OzBrain", "Audio-to-MIDI"). Nhung neu xuat hien nguyen mot tu tieng Viet
# thieu dau thi chac chan la go sai.
# Am tiet tieng Viet thuong gap, viet KHONG DAU. Danh sach rong vi mot tieu de
# tieng Viet bi go mat dau se dinh nhieu tu cung luc, con tieng Anh thi hau nhu
# khong dinh tu nao.
NEGATIVE_FACE_MARK = {
    # tu chuc nang, xuat hien trong hau het cau tieng Viet
    "va", "cua", "cho", "voi", "khong", "duoc", "nhung", "nguoi", "hon", "tren",
    "duoi", "trong", "ngoai", "moi", "cung", "chung", "cac", "nhieu", "khi",
    "neu", "nen", "phai", "the", "nay", "do", "day", "ra", "vao", "len", "xuong",
    "sau", "truoc", "theo", "bang", "them", "boi", "tu", "den", "roi", "van",
    "chi", "deu", "cang", "rat", "qua", "hay", "hoac", "ma", "la", "co", "khac",
    "o", "an", "vi", "sao", "gi", "ai", "dau", "bao", "moi",
    # dong tu thuong gap
    "lam", "chay", "viet", "doc", "xem", "thay", "biet", "hieu", "dung", "tao",
    "chuyen", "nhan", "gui", "mo", "dong", "tang", "giam", "vuot", "dat", "giu",
    "bo", "them", "sua", "kiem", "tra", "chon", "tim", "ghi", "luu", "tai",
    "phat", "hanh", "cap", "nhat", "ho", "tro", "dua", "lay", "noi", "hoi",
    # danh tu ky thuat va thuong gap
    "cong", "cu", "hinh", "thu", "nghiem", "ha", "tang", "nguon", "kinh",
    "doanh", "nghe", "lieu", "nghien", "tri", "tue", "hoc", "may", "mang",
    "diem", "so", "ty", "trieu", "nghin", "tram", "gia", "phi", "quoc", "te",
    "chinh", "thuc", "ban", "phien", "dau", "cuoi", "giua", "giong", "tuong",
    "bai", "tin", "anh", "chu", "am", "thanh", "khai", "han", "lan", "viec",
    "gioi", "muc", "loai", "dang", "kien", "truc", "he", "thong", "phan",
    "tich", "ket", "qua", "hieu", "suat", "toc", "kha", "nang", "tinh", "nang",
    # tinh tu, so dem
    "manh", "nhanh", "cham", "tot", "xau", "re", "dat", "mien", "moi", "cu",
    "lon", "nho", "cao", "thap", "dai", "ngan", "day", "mong", "sau", "rong",
    "mot", "hai", "ba", "bon", "muoi", "thang", "ngay", "gio", "phut", "nam",
}

# Cum tu chac chan la tieng Viet mat dau — dinh mot cum la du ket luan
PHRASE_FACE_MARK = {
    "cong cu", "mo hinh", "thu nghiem", "ha tang", "ma nguon mo", "ban cap nhat",
    "kinh doanh", "cong nghe", "du lieu", "nghien cuu", "phat hanh", "cap nhat",
    "tri tue", "may hoc", "mien phi", "quoc te", "chinh thuc",
}


def find_face_mark(text: str) -> list:
    """Tra ve dau hieu tieng Viet bi go mat dau trong `text`.

    Hai muc: dinh mot CUM quen thuoc la du, hoac dinh tu HAI am tiet tro len.
    Nguong hai la de tieng Anh khong bi bao nham — tu nhu "the", "do", "so",
    "ra" cung xuat hien trong tieng Anh, nhung hiem khi hai cai cung luc trong
    mot tieu de ngan.
    """
    if not text:
        return []

    # Nhieu am tiet tieng Viet VON khong co dau: "cho", "chung", "cong", "ban".
    # Neu van ban da co dau o dau do thi coi nhu go dung, va nhung tu tren la
    # chinh ta binh thuong chu khong phai loi. Da bao nham "Bo nao dung chung
    # cho moi agent" vi hai tu "cho" va "chung" — trong khi ca cau co dau du.
    # Nen chi soi khi CA VAN BAN khong co lay mot dau nao.
    if re.search(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
                  r"ùúủũụưừứửữựỳýỷỹỵđ]", text, re.I):
        return []

    tu = re.findall(r"[A-Za-zÀ-ỹ]+", text)
    low = [t.lower() for t in tu]

    cum = []
    for i in range(len(low) - 1):
        if f"{low[i]} {low[i+1]}" in PHRASE_FACE_MARK:
            cum.append(f"{tu[i]} {tu[i+1]}")
    if cum:
        return sorted(set(cum))

    don = sorted({tu[i] for i, t in enumerate(low) if t in NEGATIVE_FACE_MARK})
    return don if len(don) >= 2 else []
