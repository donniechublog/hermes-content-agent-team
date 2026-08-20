#!/usr/bin/env python3
"""Rap teaser hoan chinh tu ban nhap tho cua Jean — tat dinh, khong LLM.

Jean chi viet tieu de + cac doan van THUAN (khong emoji, khong cau ket).
Script nay tu dong: viet hoa tieu de, gan emoji dung so luong tu emoji_deck
(khong the sai vi doc dung so doan thuc te, khong phai so Jean tu dem), them
cau ket co dinh, cat toi da 2 anh dau.

Vi day la buoc rap cuoi cung, Jean khong con co hoi lam sai bon thu nay nua.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import emoji_deck                                            # noqa: E402

CLOSING = ("Xem bài chi tiết ở còm, nếu không thấy còm vui lòng vào trang "
          "chính để xem trực tiếp.")


def assemble(title: str, paragraphs: list, images: list) -> dict:
    n = len(paragraphs)
    if n == 0:
        raise ValueError("Can it nhat 1 doan van")
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
    a = ap.parse_args()

    data = json.loads(Path(a.infile).read_text(encoding="utf-8"))
    result = assemble(data["title"], data["paragraphs"], data.get("images", []))

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
