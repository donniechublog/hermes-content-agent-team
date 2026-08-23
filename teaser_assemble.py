#!/usr/bin/env python3
"""Rap teaser hoan chinh tu ban nhap tho cua Jean — tat dinh, khong LLM.

Jean chi viet tieu de + cac doan van THUAN (khong emoji, khong cau ket).
Script nay tu dong: viet hoa tieu de, gan emoji dung so luong tu emoji_deck
(khong the sai vi doc dung so doan thuc te, khong phai so Jean tu dem), them
cau ket co dinh, cat toi da 2 anh dau.

Vi day la buoc rap cuoi cung, Jean khong con co hoi lam sai bon thu nay nua.

Script cung CHAN giong tuong thuat: teaser la loi moi doc, khong phai ban tom
tat ve mot bai bao. Cac model re (deepseek-chat, v4-flash) hay tuot vao giong
"bai viet di sau vao...", "bai cung liet ke...", "tac gia nhan manh..." — nguoi
doc bi day ra ngoai, dung o vi tri nghe ke lai thay vi duoc moi vao. Nhan dien
mot danh sach cum tu co dinh la viec code lam chac hon LLM, nen chan o day.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import emoji_deck                                            # noqa: E402

CLOSING = ("Xem bài chi tiết ở còm, nếu không thấy còm vui lòng vào trang "
          "chính để xem trực tiếp.")

# Cum tu keo nguoi doc ra ngoai bai. Viet KHONG DAU vi ta so khop tren ban da
# bo dau — nho vay "bài viết", "bai viet", "Bài Viết" deu dinh nhu nhau.
# Khoang do dai SOUL yeu cau. Do bang len(p.split()) — dung cach word_count
# van dem, nen con so bao loi va con so bao cao luon khop nhau.
# Do dai KHONG phai thuoc do chat luong. Mot teaser 300 tu dien dat dung va du
# thi tot hon mot bai 700 tu lan man. Nen chia hai muc:
#   - khoang mong muon: ra ngoai chi NHAC o stderr, van chay tiep
#   - nguong hong that: duoi 200 tu thi qua mong de phu het outline, tren 2000 tu
#     thi dang ke lai ca bai chu khong con la loi moi doc — hai cai nay moi chan
# Do bang KY TU chu khong dem tu, vi ky tu moi la thu nen tang rang buoc.
# Ong Chu chot lay gioi han Instagram lam tran chung cho moi noi, chap nhan
# danh doi de mot ban dang duoc khap noi thay vi phai fine-tune tung nen tang.
# Tieng Viet do that la 5,1 ky tu moi tu, nen 800 tu cu ra hon 4.000 ky tu,
# gap doi tran. Ke ca 400 tu cung vuot.
TRAN_NEN_TANG = 2200          # gioi han caption cua Instagram va TikTok
DAI_MONG_MUON = (1500, 2050)  # ky tu, tinh tren TOAN BO caption cuoi cung
DAI_HONG = (700, TRAN_NEN_TANG)

# Van giu chan so tu de bat bai qua mong, nhung khong con la thuoc do chinh
TU_TOI_THIEU = 130

CUM_TUONG_THUAT = [
    "bai viet", "bai bao", "bai nay", "bai cung", "bai con", "bai chi ra",
    "bai nhan manh", "bai de cap", "bai phan tich", "bai liet ke",
    "trong bai", "cua bai", "o bai", "theo bai",
    "tac gia", "nguoi viet",
    "ket bai", "mo bai", "dau bai", "cuoi bai",
    "phan tiep theo", "doan tiep theo",
    "bai viet nay", "noi dung bai",
]


def _bo_dau(text: str) -> str:
    """Bo dau tieng Viet de so khop khong phu thuoc dau va chu hoa."""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def tim_giong_tuong_thuat(title: str, paragraphs: list) -> list:
    """Tra ve [(vi tri, cum tu, trich doan)] cho moi cho dinh giong tuong thuat.

    Chi soi tieu de va cac doan Jean viet — KHONG soi CLOSING, vi cau ket co
    dinh von chua chu "bai" mot cach hop le ("Xem bai chi tiet o com").
    """
    loi = []
    muc = [("tieu de", title)] + [(f"doan {i}", p) for i, p in enumerate(paragraphs, 1)]
    for vi_tri, van in muc:
        phang = _bo_dau(van or "")
        for cum in CUM_TUONG_THUAT:
            for m in re.finditer(r"\b" + re.escape(cum) + r"\b", phang):
                a = max(m.start() - 30, 0)
                loi.append((vi_tri, cum, "..." + (van or "")[a:m.end() + 30] + "..."))
                break        # moi cum bao mot lan cho moi muc, khong lap
    return loi


def assemble(title: str, paragraphs: list, images: list,
             bo_qua_kiem_tra: bool = False) -> dict:
    n = len(paragraphs)
    if n == 0:
        raise ValueError("Can it nhat 1 doan van")
    sotu = sum(len(p.split()) for p in paragraphs)
    # Uoc chieu dai caption cuoi truoc khi ghep, de bao loi som va bao ro
    _emo_tam = ["x"] * n
    _thu = f"{title.upper()}\n\n" + "\n\n".join(
        f"{e} {p}".strip() for e, p in zip(_emo_tam, paragraphs)) + f"\n\n{CLOSING}"
    soky = len(_thu)
    if not bo_qua_kiem_tra:
        if sotu < TU_TOI_THIEU:
            raise ValueError(
                f"Chi {sotu} tu — qua mong de phu het cac muc trong outline.\n"
                "  Doc lai outline va trien khai nhung y con thieu.\n"
                "(Neu that su can giu, chay lai voi --bo-qua-kiem-tra)")
        if soky > TRAN_NEN_TANG:
            thua = soky - TRAN_NEN_TANG
            raise ValueError(
                f"Caption se dai {soky} ky tu, vuot tran {TRAN_NEN_TANG} cua "
                f"Instagram va TikTok — thua {thua}.\n"
                f"  Cat bot khoang {thua} ky tu (~{round(thua / 5.1)} tu). Bo dien "
                "giai va vi du, giu so lieu va y chinh.\n"
                "  Tieng Viet trung binh 5,1 ky tu moi tu.\n"
                "(Neu that su can giu, chay lai voi --bo-qua-kiem-tra)")
        if soky < DAI_HONG[0]:
            raise ValueError(
                f"Caption chi {soky} ky tu — qua ngan cho mot teaser.\n"
                "(Neu that su can giu, chay lai voi --bo-qua-kiem-tra)")
        if not (DAI_MONG_MUON[0] <= soky <= DAI_MONG_MUON[1]):
            print(f"[nhac] caption ~{soky} ky tu ({sotu} tu), ngoai khoang mong "
                  f"muon {DAI_MONG_MUON[0]}-{DAI_MONG_MUON[1]} — khong sao neu "
                  "dien dat dung va du.", file=sys.stderr)
    if not bo_qua_kiem_tra:
        loi = tim_giong_tuong_thuat(title, paragraphs)
        if loi:
            chi_tiet = "\n".join(
                f"  - {vi_tri}: cum \"{cum}\"\n      {trich}" for vi_tri, cum, trich in loi)
            raise ValueError(
                "Giong tuong thuat — teaser phai MOI doc, khong ke lai ve bai:\n"
                + chi_tiet
                + "\n\nViet lai: noi thang vao noi dung, bo chu \"bai viet\"/\"tac gia\".\n"
                  "  KHONG dat:  Bai viet di sau vao con so chi phi...\n"
                  "  DAT      :  Con so chi phi gay bat ngo: 2,75 USD moi task...\n"
                  "(Neu that su can giu, chay lai voi --bo-qua-kiem-tra)")
    emojis = emoji_deck.next_emoji(n)
    body = "\n\n".join(f"{e} {p}".strip() for e, p in zip(emojis, paragraphs))
    caption = f"{title.upper()}\n\n{body}\n\n{CLOSING}"
    return {
        "caption": caption,
        "images": images[:2],
        "word_count": sum(len(p.split()) for p in paragraphs),
        "paragraph_count": n,
        "emoji_used": emojis,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Rap teaser tu ban nhap tho (tieu de + doan van thuan)")
    ap.add_argument("--in", dest="infile", required=True,
                    help="File JSON: {\"title\": str, \"paragraphs\": [str,...], "
                         "\"images\": [url,...]}")
    ap.add_argument("--out", help="Ghi ket qua JSON ra file thay vi in stdout")
    ap.add_argument("--text-only", action="store_true",
                    help="Chi in phan caption (de dan thang vao chat)")
    ap.add_argument("--bo-qua-kiem-tra", action="store_true",
                    help="Bo qua ca hai phep kiem tra do dai va giong (mac dinh: chan)")
    a = ap.parse_args()

    data = json.loads(Path(a.infile).read_text(encoding="utf-8"))
    result = assemble(data["title"], data["paragraphs"], data.get("images", []),
                      bo_qua_kiem_tra=a.bo_qua_kiem_tra)

    if a.text_only:
        print(result["caption"])
        return

    out_json = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(out_json, encoding="utf-8")
        print(a.out)
    else:
        print(out_json)


if __name__ == "__main__":
    main()
