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

# 1024 la gioi han CHU THICH ANH cua Telegram. Vua trong muc do thi ca caption
# di chung mot tin nhan voi anh; vuot qua thi publish() tu tach thanh phan 1
# (<=1024, van gan lam caption that cua anh) + phan 2 (tin nhan rieng, xem
# approve_post._split_caption_html — LOW-157). Vi vay day la MUC TIEU nen tan
# dung, khong con la loi chan nop — vuot chi con CANH BAO (_check_measure_long).
LIMIT = 1024
# Tran cung cho moi nen tang. Ong Chu chot: viet duoi 2.200 o moi noi thi moat
# khong phai can thiep gi, khong can caption rieng theo nen tang. Con so nay la
# gioi han caption cua Instagram va TikTok (theo tri nho, chua xac nhan duoc tu
# tai lieu vi trang cua ho la SPA) — de thap hon that mot chut thi an toan.
# Caption thuong hien trung binh 962 ky tu nen tran nay khong vuong gi.
CEILING_BACKGROUND_LAYER = 2200
BACKGROUND_SET = 700          # duoi muc nay thi nhac: con nhieu cho ma chua dung het
CARD_ALLOW = {"b", "i", "code", "strong", "em", "a"}

TIME_ROOM = ("gây chấn động", "thay đổi mọi thứ", "cuộc cách mạng", "đột phá",
              "kinh hoàng", "không tưởng", "vô địch", "bá đạo", "cực kỳ ấn tượng",
              "thần thánh", "khủng khiếp", "chấn động")

FROM_ANNOUNCEMENT = ("tự công bố", "hãng công bố", "theo công bố", "chưa kiểm chứng",
              "chưa có kiểm chứng", "nội bộ", "tự đo", "theo hãng", "công ty công bố")

# Cum sao rong bi cam (tieu chuan bien tap): noi thang y nghia bang thong tin cu
# the, dung dan bang "dang chu y / dang quan tam" hoac tu dat cau hoi roi tu tra
# loi kieu "y nghia nam o" (LOW-261: Miles/Jika hay mo doan bang cum nay).
STAR_EMPTY = ("đáng chú ý", "đáng quan tâm", "ý nghĩa nằm ở")

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

# Dan nguon/anh bi cam trong CAPTION (LOW-173): image/carousel da ghi nguon va
# anh roi (watermark, chu thich anh), nhac lai bang chu trong caption la dong
# tac thua. Ap dung cho MOI vai writer va MOI brand vi day la cong chung
# (check() duoc goi qua submit_common.py). Khac voi gate tren slide
# (render_edu._DAN_NGUON_SAI, cho phep "via <ai>"), o day KHONG cho nhac
# nguon/anh duoi bat ky hinh thuc nao — "mã nguồn" khong bi bat (loai tru
# giong _DAN_NGUON_SAI).
#
# Nhanh "nguon tin/tu/theo/bai/anh/du lieu/so lieu" PHAI doi hoi dau ":"/"—"/"-"
# ngay sau (LOW-259): tung bat ca cum nay o giua cau, nen "Bon nguon tin noi
# quan doi My..." (van phong bao chi binh thuong, nghia "four sources say") bi
# chan oan giong het "Nguồn tin: Reuters" — mot dong dan nguon that.
_SOURCE_CREDIT_FORBIDDEN = re.compile(
    r"(?<!\bmã\s)\bnguồn\s*(?:tin|từ|theo|bài|ảnh|dữ liệu|số liệu)?\s*[:—-]"  # "Nguồn: X" / "Nguồn tin: X"
    r"|\btheo\s+nguồn\b"
    r"|\bảnh\s*[:—-]"                              # "Ảnh: X"
    r"|\bảnh\s+từ\b",                              # "ảnh từ ..."
    re.I)

# Tieng Viet CO DAU la yeu cau song con cua kenh. Mat dau la loi nang nhat —
# nang hon thieu so — vi bai khong dang duoc. Da gap that: Miles viet ca caption
# 802 ky tu khong mot dau nao sau khi doi sang provider moi, va khong ai phat
# hien cho toi khi doc ky.
MARK = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
          "ùúủũụưừứửữựỳýỷỹỵđ")
# 0.12 CO Y thap hon 0.15 cua model_audition: day la cong chan bai that (caption
# nhieu ten rieng/thuat ngu tieng Anh keo ty le xuong), con audition do van mau
# thuan Viet. Hai nguong khac nhau la chu dich, khong phai lech. DAU/diacritic_ratio
# chi co MOT ban o day; model_audition va cost_squeeze import tu day.
THRESHOLD_MARK = 0.12          # van ban tieng Viet that thuong tren 0.15


def billion_odd_mark(t: str) -> float:
    chu = [c for c in t.lower() if c.isalpha()]
    return sum(1 for c in chu if c in MARK) / len(chu) if chu else 0.0


COUNT = re.compile(r"\d")
PHRASE_COUNT = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|tỷ|triệu|nghìn|token|USD|\$|B\b|M\b|ms\b|GB\b|MiB\b|điểm)?")


def _drop_card(t: str) -> str:
    return re.sub(r"<[^>]+>", " ", t)


def _words(t: str) -> list:
    return re.sub(r"[^\w\s]", " ", _drop_card(t).lower()).split()


def repeat_phrase(t: str, n=6) -> list:
    """Cum n tu xuat hien tu hai lan tro len."""
    tu = _words(t)
    dem = {}
    for i in range(len(tu) - n + 1):
        k = " ".join(tu[i:i + n])
        dem[k] = dem.get(k, 0) + 1
    return [k for k, v in dem.items() if v > 1]


def count_within(t: str) -> list:
    return [m.group(0).strip() for m in PHRASE_COUNT.finditer(_drop_card(t)) if m.group(0).strip()]


def count_is(chu: str, tu_lieu: str) -> list:
    """Cac con so trong `chu` KHONG tim thay trong `tu_lieu`.

    So sanh theo chuoi chu so (bo dau . , cach) vi hai ben viet khac nhau
    (2,5 ti / 2.5B / 2500 trieu). Chi lay so >= 2 chu so. Tach rieng khoi
    `kiem()` tu 06/09/2026 de vai lam ANH (Dre/Ethan/Kite) dung chung — truoc
    do chi caption cua Miles duoc soat so, con so in TREN SLIDE thi khong ai
    doi chieu, du day moi la thu doc gia nhin thay dau tien."""
    if not tu_lieu or not chu:
        return []
    so_tl = {re.sub(r"[.,\s]", "", m) for m in re.findall(r"\d[\d.,]*", tu_lieu)}
    la = []
    for m in re.findall(r"\d[\d.,]*", _drop_card(chu)):
        k = re.sub(r"[.,\s]", "", m)
        if len(k) >= 2 and k not in so_tl and not any(k in x for x in so_tl):
            la.append(m)
    return list(dict.fromkeys(la))


def _check_measure_long(caption: str) -> tuple:
    """Ba nguong do dai: tran nen tang (loi), gioi han chu thich anh (chi
    nhac — LOW-157: publish() tu tach phan 1/phan 2, khong con chan nop),
    muc nen dat (chi nhac)."""
    loi, canh = [], []
    if len(caption) > CEILING_BACKGROUND_LAYER:
        loi.append(f"Dài {len(caption)} ký tự, vượt trần {CEILING_BACKGROUND_LAYER} của "
                   "Instagram và TikTok. Bài sẽ bị cắt hoặc từ chối khi moat đẩy đi.")
    elif len(caption) > LIMIT:
        canh.append(f"Dài {len(caption)} ký tự, vượt giới hạn chú thích ảnh {LIMIT} — "
                    "sẽ tự tách thành phần chú thích ảnh + tin nhắn riêng khi đăng.")
    elif len(caption) < BACKGROUND_SET:
        canh.append(f"{len(caption)} ký tự, còn {LIMIT - len(caption)} ký tự "
                    "chưa dùng trong giới hạn chú thích ảnh. Khai thác thêm số "
                    "liệu hoặc bối cảnh từ tư liệu.")
    return loi, canh


def _check_still_room(caption: str, tran: str) -> tuple:
    """Nhung thu SOUL da cam va tieu chuan bien tap: em-dash, link song, cum sao
    rong, moi cau mot dong, the HTML la, tu thoi phong, lap y. `tran` la
    caption da bo the."""
    loi, canh = [], []
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

    source_credit = _SOURCE_CREDIT_FORBIDDEN.search(tran)
    if source_credit:
        loi.append(f'Có dòng dẫn nguồn/ảnh kiểu "{source_credit.group(0).strip()}" — '
                   'ảnh/carousel đã ghi nguồn rồi, caption không được lặp lại.')

    sao = [p for p in STAR_EMPTY if p in tran.lower()]
    if sao:
        loi.append("Cụm sáo rỗng bị cấm: " + ", ".join(f'"{p}"' for p in sao)
                   + '. Nói thẳng vì sao quan trọng bằng thông tin cụ thể, '
                   'không dùng "đáng chú ý / đáng quan tâm / ý nghĩa nằm ở".')

    # Tieu chuan bien tap: moi cau mot dong. Bat khi mot DONG con chua >=2 cau
    # (dau ket cau + khoang trang + chu hoa) -> chi NHAC, khong chan cung.
    dong_gop = [dg.strip() for dg in caption.splitlines()
                if re.search(r"[.!?…]\s+[A-ZĐÀ-Ỹ]", dg)]
    if dong_gop:
        canh.append("Mỗi câu nên xuống dòng riêng, mỗi đoạn cách một dòng trống "
                    f"(tiêu chuẩn biên tập). Dòng gộp nhiều câu: “{dong_gop[0][:50]}…”")

    the_la = {m.group(1).lower() for m in re.finditer(r"</?([a-zA-Z][\w-]*)", caption)}
    xau = the_la - CARD_ALLOW
    if xau:
        loi.append(f"Thẻ HTML không được phép: {', '.join(sorted(xau))}. "
                   f"Telegram chỉ hiểu {', '.join(sorted(CARD_ALLOW))}.")

    thay_phong = [w for w in TIME_ROOM if w in tran.lower()]
    if thay_phong:
        loi.append(f"Từ thổi phồng: {', '.join(thay_phong)}.")

    lap = repeat_phrase(caption)
    if lap:
        loi.append("Lặp ý — cụm sau xuất hiện hai lần: "
                   + "; ".join(f'"{c}"' for c in lap[:3]))
    return loi, canh


def _check_figures(caption: str, tran: str, tu_lieu: str, tin: dict) -> tuple:
    """So lieu: nguon co so ma caption khong co (loi), so khong co trong tu lieu
    (nhac), co so ma khong ghi tu cong bo (nhac). Ghi them vao `tin`."""
    loi, canh = [], []
    so_cap = count_within(caption)
    tin["number_count"] = len(so_cap)

    if tu_lieu:
        cau_nguon = [l[2:].strip() for l in tu_lieu.splitlines()
                     if l.startswith("- ") and COUNT.search(l)]
        tin["source_number_sentence_count"] = len(cau_nguon)
        if cau_nguon and not so_cap:
            loi.append(f"Nguồn có {len(cau_nguon)} câu mang số liệu nhưng caption "
                       "KHÔNG có con số nào. Cô đọng được, thiếu thì không.")
        elif cau_nguon and len(so_cap) < 2:
            canh.append(f"Nguồn có {len(cau_nguon)} câu mang số liệu, caption mới "
                        f"dùng {len(so_cap)}. Cân nhắc thêm một số nữa.")
    elif not so_cap:
        canh.append("Caption không có con số nào — kiểm lại xem nguồn có số không.")

    # SO KHONG CO TRONG TU LIEU: moi con so (>= 2 chu so) trong caption phai tim
    # thay trong tu lieu, so voi chuoi chu so (bo dau . , cach). Chi NHAC vi hai
    # ben viet so khac nhau (2,5 ti / 2.5B / 2500 trieu) — chan cung se chan oan.
    # Day la diem soat so lieu ma truoc phai nho Ada (LLM) doc lai (05/09/2026).
    if tu_lieu:
        la = count_is(tran, tu_lieu)
        if la:
            canh.append("Số trong caption KHÔNG thấy trong tư liệu: "
                        + ", ".join(la) + " — kiểm lại nguồn, số không có trong "
                        "tư liệu là bịa (trừ khi anh đổi đơn vị).")

    # So benchmark ma khong ghi ro tu cong bo
    if so_cap and not any(k in tran.lower() for k in FROM_ANNOUNCEMENT):
        canh.append("Có số liệu nhưng chưa ghi rõ là hãng tự công bố hay đã kiểm "
                    "chứng độc lập.")
    return loi, canh


def check(caption: str, tu_lieu: str = "") -> tuple:
    """Tra ve (loi, canh_bao, thong_tin). Co loi thi khong duoc luu draft.

    Tach thanh ba nhom 07/09/2026 (do dai / van phong / so lieu) — ban cu la
    103 dong voi 14 cong noi tiep trong mot ham; thu tu ghi vao `loi` va `canh`
    giu nguyen (moi nhom chi ghi vao hai danh sach do theo dung thu tu cu)."""
    loi, canh, tin = [], [], {}
    tran = _drop_card(caption)

    if not caption.strip():
        return (["Caption rỗng."], [], {})

    td = billion_odd_mark(tran)
    tin["diacritic_ratio"] = round(td, 3)
    if td < THRESHOLD_MARK:
        loi.append(f"MAT DAU tieng Viet — ty le dau {td:.2f}, duoi nguong "
                   f"{THRESHOLD_MARK}. Bai khong co dau la khong dang duoc.")

    for l, c in (_check_measure_long(caption), _check_still_room(caption, tran),
                 _check_figures(caption, tran, tu_lieu, tin)):
        loi += l
        canh += c

    cau = [c for c in re.split(r"(?<=[.!?])\s+", tran) if c.strip()]
    tin["sentence_count"] = len(cau)
    tin["char_count"] = len(caption)
    if len(cau) < 3:
        canh.append(f"Chỉ {len(cau)} câu — cấu trúc SOUL cần mở, thân, ý nghĩa.")
    return (loi, canh, tin)


def main():
    ap = argparse.ArgumentParser(description="Kiem caption truoc khi vao hang duyet")
    ap.add_argument("--caption-file", required=True)
    ap.add_argument("--tu-lieu", help="Tep tu lieu do material.py sinh ra")
    a = ap.parse_args()

    cap = Path(a.caption_file).read_text(encoding="utf-8")
    tl = Path(a.tu_lieu).read_text(encoding="utf-8") if a.tu_lieu and Path(a.tu_lieu).exists() else ""
    loi, canh, tin = check(cap, tl)

    print(f"  {tin.get('char_count', 0)} ký tự | {tin.get('sentence_count', 0)} câu | "
          f"{tin.get('number_count', 0)} chỗ có số | dấu {tin.get('diacritic_ratio', 0):.2f}"
          + (f" | nguồn có {tin['source_number_sentence_count']} câu số liệu"
             if "source_number_sentence_count" in tin else ""))
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
