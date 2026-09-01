#!/usr/bin/env python3
"""Cong chan caption: bat loi CO HOC truoc khi bai vao hang duyet.

Ong Chu chot: noi dung co the co dong va ngan gon, nhung KHONG duoc phep thieu.

Cai gi kiem bang code thi kiem o day, khong nho LLM tu danh gia minh:

  - RONG SO: nguon co so lieu ma caption khong co con so nao. Da gap that — tin
    DeepSeek vision co bang 11 dong so, caption viet ra 0 con so, vi Miles chi
    duoc doc 3 cau tom tat cua Finn chu khong duoc doc nguon.
  - LAP Y: cung mot cum 6 tu tro len xuat hien hai lan. Da gap: "mo rong nang luc
    multimodality cho dong model nguon mo pho bien" lap o ca doan 2 lan doan 3 —
    trong caption 500 ky tu thi do la phi pham nghiem trong.
  - THOI PHONG, URL, THE HTML LA, QUA DAI: nhung thu SOUL da cam.
  - SO LIEU TU CONG BO ma khong ghi ro la tu cong bo.

Cai gi CAN DOC HIEU thi de Miles lo — script chi bao "nguon co N cau mang so,
caption dung M cau", con chon so nao la viec cua nguoi viet.

Dung:
    venv/bin/python caption_check.py --caption-file /tmp/c.txt --tu-lieu /tmp/tl.md
    venv/bin/python caption_check.py --caption-file /tmp/c.txt          # chi kiem co hoc
"""
import argparse
import re
import sys
from pathlib import Path

# 1024 la gioi han CHU THICH ANH cua Telegram. Vua trong muc do thi anh va chu
# di chung mot tin nhan; vuot qua la Telegram tach lam hai, anh mot noi chu mot
# noi. Nen day vua la tran vua la muc tieu nen tan dung.
GIOI_HAN = 1024
# Tran cung cho moi nen tang. Ong Chu chot: viet duoi 2.200 o moi noi thi moat
# khong phai can thiep gi, khong can caption rieng theo nen tang. Con so nay la
# gioi han caption cua Instagram va TikTok (theo tri nho, chua xac nhan duoc tu
# tai lieu vi trang cua ho la SPA) — de thap hon that mot chut thi an toan.
# Caption thuong hien trung binh 962 ky tu nen tran nay khong vuong gi.
TRAN_NEN_TANG = 2200
NEN_DAT = 700          # duoi muc nay thi nhac: con nhieu cho ma chua dung het
THE_CHO_PHEP = {"b", "i", "code", "strong", "em", "a"}

THOI_PHONG = ("gây chấn động", "thay đổi mọi thứ", "cuộc cách mạng", "đột phá",
              "kinh hoàng", "không tưởng", "vô địch", "bá đạo", "cực kỳ ấn tượng",
              "thần thánh", "khủng khiếp", "chấn động")

TU_CONG_BO = ("tự công bố", "hãng công bố", "theo công bố", "chưa kiểm chứng",
              "chưa có kiểm chứng", "nội bộ", "tự đo", "theo hãng", "công ty công bố")

# Cum sao rong bi cam (tieu chuan bien tap): noi thang y nghia bang thong tin cu
# the, dung dan bang "dang chu y / dang quan tam".
SAO_RONG = ("đáng chú ý", "đáng quan tâm")

# Bat URL/link SONG trong caption. Ngoai http/www con bat DOMAIN TRAN (vd z.ai,
# openai.com) — truoc day lot vi khong co scheme. Chi bat khi dau cham DINH LIEN;
# link da defang kieu "z . ai" (dau cach hai ben dau cham) thi cho qua, dung
# tieu chuan bien tap: link trong noi dung phai viet dau cham thanh " . ".
_TLD = ("ai", "com", "io", "org", "net", "dev", "app", "xyz", "gg", "sh", "co",
        "tech", "cloud", "tv", "gov", "edu", "vn", "me", "so")
_LINK_SONG = re.compile(
    r"https?://|www\.\w"
    r"|(?<![\w.])[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9-]{1,63})*\.(?:" + "|".join(_TLD) + r")\b",
    re.I)

# Tieng Viet CO DAU la yeu cau song con cua kenh. Mat dau la loi nang nhat —
# nang hon thieu so — vi bai khong dang duoc. Da gap that: Miles viet ca caption
# 802 ky tu khong mot dau nao sau khi doi sang provider moi, va khong ai phat
# hien cho toi khi doc ky.
DAU = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
          "ùúủũụưừứửữựỳýỷỹỵđ")
NGUONG_DAU = 0.12          # van ban tieng Viet that thuong tren 0.15


def ty_le_dau(t: str) -> float:
    chu = [c for c in t.lower() if c.isalpha()]
    return sum(1 for c in chu if c in DAU) / len(chu) if chu else 0.0


SO = re.compile(r"\d")
CUM_SO = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|tỷ|triệu|nghìn|token|USD|\$|B\b|M\b|ms\b|GB\b|MiB\b|điểm)?")


def _bo_the(t: str) -> str:
    return re.sub(r"<[^>]+>", " ", t)


def _tu(t: str) -> list:
    return re.sub(r"[^\w\s]", " ", _bo_the(t).lower()).split()


def lap_cum(t: str, n=6) -> list:
    """Cum n tu xuat hien tu hai lan tro len."""
    tu = _tu(t)
    dem = {}
    for i in range(len(tu) - n + 1):
        k = " ".join(tu[i:i + n])
        dem[k] = dem.get(k, 0) + 1
    return [k for k, v in dem.items() if v > 1]


def so_trong(t: str) -> list:
    return [m.group(0).strip() for m in CUM_SO.finditer(_bo_the(t)) if m.group(0).strip()]


def kiem(caption: str, tu_lieu: str = "") -> tuple:
    """Tra ve (loi, canh_bao, thong_tin). Co loi thi khong duoc luu draft."""
    loi, canh, tin = [], [], {}
    tran = _bo_the(caption)

    if not caption.strip():
        return (["Caption rỗng."], [], {})

    td = ty_le_dau(tran)
    tin["ty_le_dau"] = round(td, 3)
    if td < NGUONG_DAU:
        loi.append(f"MAT DAU tieng Viet — ty le dau {td:.2f}, duoi nguong "
                   f"{NGUONG_DAU}. Bai khong co dau la khong dang duoc.")

    if len(caption) > TRAN_NEN_TANG:
        loi.append(f"Dài {len(caption)} ký tự, vượt trần {TRAN_NEN_TANG} của "
                   "Instagram và TikTok. Bài sẽ bị cắt hoặc từ chối khi moat đẩy đi.")
    elif len(caption) > GIOI_HAN:
        loi.append(f"Dài {len(caption)} ký tự, vượt giới hạn {GIOI_HAN}.")
    elif len(caption) < NEN_DAT:
        canh.append(f"{len(caption)} ký tự, còn {GIOI_HAN - len(caption)} ký tự "
                    "chưa dùng trong giới hạn chú thích ảnh. Khai thác thêm số "
                    "liệu hoặc bối cảnh từ tư liệu.")

    # Em-dash: Ong Chu khong dung dau nay trong van ban dang len kenh. Bat o day
    # de nguoi viet sua han, thay vi de publish.py am tham doi giup roi lan sau
    # van viet nhu cu.
    if "—" in caption or "–" in caption:
        loi.append("Có em-dash (— hoặc –). Dùng dấu phẩy, dấu hai chấm, "
                   "hoặc tách thành câu riêng.")

    link_song = _LINK_SONG.search(caption)
    if link_song:
        loi.append(f'Còn URL/link sống trong bài ("{link_song.group(0).strip()}") — '
                   'bỏ ra còm, không đặt trong caption. Nếu buộc phải nhắc tên miền '
                   'thì viết dấu chấm thành " . " (vd z . ai) để không thành link.')

    sao = [p for p in SAO_RONG if p in tran.lower()]
    if sao:
        loi.append("Cụm sáo rỗng bị cấm: " + ", ".join(f'"{p}"' for p in sao)
                   + '. Nói thẳng vì sao quan trọng bằng thông tin cụ thể, '
                   'không dùng "đáng chú ý / đáng quan tâm".')

    # Tieu chuan bien tap: moi cau mot dong. Bat khi mot DONG con chua >=2 cau
    # (dau ket cau + khoang trang + chu hoa) -> chi NHAC, khong chan cung.
    dong_gop = [dg.strip() for dg in caption.splitlines()
                if re.search(r"[.!?…]\s+[A-ZĐÀ-Ỹ]", dg)]
    if dong_gop:
        canh.append("Mỗi câu nên xuống dòng riêng, mỗi đoạn cách một dòng trống "
                    f"(tiêu chuẩn biên tập). Dòng gộp nhiều câu: “{dong_gop[0][:50]}…”")

    the_la = {m.group(1).lower() for m in re.finditer(r"</?([a-zA-Z][\w-]*)", caption)}
    xau = the_la - THE_CHO_PHEP
    if xau:
        loi.append(f"Thẻ HTML không được phép: {', '.join(sorted(xau))}. "
                   f"Telegram chỉ hiểu {', '.join(sorted(THE_CHO_PHEP))}.")

    thay_phong = [w for w in THOI_PHONG if w in tran.lower()]
    if thay_phong:
        loi.append(f"Từ thổi phồng: {', '.join(thay_phong)}.")

    lap = lap_cum(caption)
    if lap:
        loi.append("Lặp ý — cụm sau xuất hiện hai lần: "
                   + "; ".join(f'"{c}"' for c in lap[:3]))

    so_cap = so_trong(caption)
    tin["so_trong_caption"] = len(so_cap)

    if tu_lieu:
        cau_nguon = [l[2:].strip() for l in tu_lieu.splitlines()
                     if l.startswith("- ") and SO.search(l)]
        tin["cau_so_trong_nguon"] = len(cau_nguon)
        if cau_nguon and not so_cap:
            loi.append(f"Nguồn có {len(cau_nguon)} câu mang số liệu nhưng caption "
                       "KHÔNG có con số nào. Cô đọng được, thiếu thì không.")
        elif cau_nguon and len(so_cap) < 2:
            canh.append(f"Nguồn có {len(cau_nguon)} câu mang số liệu, caption mới "
                        f"dùng {len(so_cap)}. Cân nhắc thêm một số nữa.")
    elif not so_cap:
        canh.append("Caption không có con số nào — kiểm lại xem nguồn có số không.")

    # So benchmark ma khong ghi ro tu cong bo
    if so_cap and not any(k in tran.lower() for k in TU_CONG_BO):
        canh.append("Có số liệu nhưng chưa ghi rõ là hãng tự công bố hay đã kiểm "
                    "chứng độc lập.")

    cau = [c for c in re.split(r"(?<=[.!?])\s+", tran) if c.strip()]
    tin["so_cau"] = len(cau)
    tin["do_dai"] = len(caption)
    if len(cau) < 3:
        canh.append(f"Chỉ {len(cau)} câu — cấu trúc SOUL cần mở, thân, ý nghĩa.")
    return (loi, canh, tin)


def main():
    ap = argparse.ArgumentParser(description="Kiem caption truoc khi vao hang duyet")
    ap.add_argument("--caption-file", required=True)
    ap.add_argument("--tu-lieu", help="Tep tu lieu do tu_lieu.py sinh ra")
    a = ap.parse_args()

    cap = Path(a.caption_file).read_text(encoding="utf-8")
    tl = Path(a.tu_lieu).read_text(encoding="utf-8") if a.tu_lieu and Path(a.tu_lieu).exists() else ""
    loi, canh, tin = kiem(cap, tl)

    print(f"  {tin.get('do_dai', 0)} ký tự | {tin.get('so_cau', 0)} câu | "
          f"{tin.get('so_trong_caption', 0)} chỗ có số | dấu {tin.get('ty_le_dau', 0):.2f}"
          + (f" | nguồn có {tin['cau_so_trong_nguon']} câu số liệu"
             if "cau_so_trong_nguon" in tin else ""))
    for c in canh:
        print(f"  [nhắc]  {c}")
    for e in loi:
        print(f"  [LỖI]   {e}")
    if loi:
        print("\nKHONG DAT — sua roi chay lai.")
        return 1
    print("\nDAT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
