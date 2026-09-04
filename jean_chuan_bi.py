#!/usr/bin/env python3
"""jean_chuan_bi.py — BRIEF cho Jean (teaser mời đọc bài donniechu.com).

Đầu vào: URL bài (Ông Chủ dán vào chat). Script bóc bài (article_extract), in
tiêu đề, dàn ý, toàn bộ đoạn văn (cắt trần), số ảnh, và luật của teaser_assemble
(độ dài, cấm giọng tường thuật, không URL/emoji/câu kết). Vai chỉ viết tiêu đề
+ các đoạn văn thuần vào spec.json rồi chạy jean_nop.py.

Dùng:
    venv/bin/python jean_chuan_bi.py "https://www.donniechu.com/posts/..."
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                              # noqa: E402
import teaser_assemble                                       # noqa: E402

CHU_TOI_DA = 9000


def slug(url: str) -> str:
    s = re.sub(r"^https?://(www\.)?", "", url.strip()).rstrip("/")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[-60:] or "bai"


def workdir(url: str) -> Path:
    wd = env_load.state_dir() / "chuan_bi" / f"jean_{slug(url)}"
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def boc(url: str, wd: Path, lam_moi: bool) -> dict:
    p = wd / "article.json"
    if p.exists() and not lam_moi:
        return json.loads(p.read_text(encoding="utf-8"))
    r = subprocess.run([sys.executable, str(ROOT / "article_extract.py"), url, "--out", str(p)],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not p.exists():
        sys.exit(f"[LOI] không bóc được bài: {(r.stdout or r.stderr)[-300:]}")
    return json.loads(p.read_text(encoding="utf-8"))


def viet_brief(url: str, d: dict, wd: Path) -> str:
    L = [f"# JEAN — BÀI ĐÃ BÓC: {d.get('title', '')}", f"URL: {url}", f"Ảnh trong bài: {len(d.get('images', []))} "
         "(script tự lấy 2 ảnh đầu, bạn không chọn)", ""]
    if d.get("description"):
        L.append(f"Mô tả: {d['description']}")
    L += ["", "## Dàn ý (phải nhắc ĐỦ các mục lớn này)"]
    for o in d.get("outline", []):
        L.append(f"  {'-' if o.get('level') == 'h2' else '   ·'} {o.get('text', '')}")
    L += ["", "## Toàn bộ đoạn văn gốc"]
    chu = 0
    for p in d.get("paragraphs", []):
        if chu > CHU_TOI_DA:
            L.append("(cắt bớt)")
            break
        L.append(p)
        chu += len(p)
    L += ["", f"## Viết spec vào: {wd}/spec.json",
          json.dumps({"title": "<tiêu đề, hoa hay thường tuỳ, script tự viết hoa>",
                      "paragraphs": ["<đoạn 1, chữ thuần>", "<đoạn 2>", "<…>"]}, ensure_ascii=False, indent=1),
          f"Luật: {teaser_assemble.DAI_MONG_MUON[0]}–{teaser_assemble.DAI_MONG_MUON[1]} từ mong muốn "
          f"(chặn cứng dưới {teaser_assemble.DAI_HONG[0]} hoặc trên {teaser_assemble.DAI_HONG[1]}). Giọng MỜI "
          "đọc, nói thẳng vào nội dung như chuyện của mình; CẤM giọng tường thuật: "
          + ", ".join(f"\"{c}\"" for c in teaser_assemble.CUM_TUONG_THUAT[:10]) + "… (script chặn). "
          "Không bịa ngoài bài, không URL, không emoji, không đánh số, không câu kết (script tự thêm). "
          "Mỗi đoạn là một chuỗi riêng. Tiếng Việt có dấu, không em-dash.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python jean_nop.py \"{url}\"",
          "Script ráp teaser (viết hoa tiêu đề, emoji, câu kết, 2 ảnh), kiểm độ dài và giọng, gửi vào topic "
          "teaser. Báo [LOI] thì sửa đúng đoạn đó trong spec.json rồi chạy lại. KHÔNG chạy article_extract/"
          "teaser_assemble tay, KHÔNG dán lại cả teaser vào câu trả lời: trả lời Ông Chủ đúng một câu."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief teaser cho Jean")
    ap.add_argument("url")
    ap.add_argument("--lam-moi", action="store_true")
    ap.add_argument("--im", action="store_true")
    a = ap.parse_args()
    wd = workdir(a.url)
    d = boc(a.url, wd, a.lam_moi)
    (wd / "url.txt").write_text(a.url, encoding="utf-8")
    brief = viet_brief(a.url, d, wd)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
