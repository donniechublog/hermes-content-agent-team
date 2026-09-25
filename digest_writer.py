#!/usr/bin/env python3
"""digest_writer.py — nhanh BAN TIN VAN cua vai viet (Miles/Jika) cho bo Hiro (LOW-405).

Bo Hiro (LOW-401) la MOT carousel N headline. Truoc tep nay, writer coi no la MOT bai ve
tin #1 (`meta.source_url` = link tin #1):
  - `miles_prepare` goi `image_prepare.run` -> CA engine anh chay tren link tin #1 ngay
    trong thu muc cua Hiro: ghi de `contact_sheet.png`, va 0 anh thi hook
    `route_missing_images` chuyen draft sang KITE (sua `.img.json`, Kite ve de len album);
  - tu lieu chi co bai #1, nen `caption_check` bao "so khong co trong tu lieu" cho moi so
    cua tin 2..N; brief day khung "4 y bat buoc" cua MOT tin.

O day: tu lieu = chinh danh sach slide Ong Chu da duyet (tieu de + tom tat tren slide,
tieu de + tom tat cua researcher), brief = mo bai chung + MOI SLIDE MOT DONG theo dung
thu tu, cong nop dem dong liet ke. Khong mang, khong engine: moi thu Hiro da co.
"""
import json
import re
from pathlib import Path

import caption_check
import state_paths

# Dong liet ke: cung khuon caption_check (bullet "• " hoac "1."), cong khoi van xuoi
# (MAX_PROSE_BLOCK) khong tinh chung — N tin thanh N dong van xuoi thi bi chan cung.
LIST_LINE = caption_check.BULLET_LINE
INTRO_BUDGET = 300                        # ky tu cho mo bai + ket


def is_digest(meta: dict) -> bool:
    return bool((meta or {}).get("digest"))


def load_slides(wd: Path) -> list:
    """Slide Ong Chu da duyet, THEO THU TU tren album: [{slide, index, title, summary,
    link, source_title, source_summary}]. Chu tren slide lay tu spec.json (ban Hiro nop),
    tin bi `skipped` khong co mat — khong co slide thi caption khong duoc noi toi."""
    job = json.loads((wd / state_paths.HIRO_JOB_FILE).read_text(encoding="utf-8"))
    spec = json.loads((wd / "spec.json").read_text(encoding="utf-8"))
    items = {it["index"]: it for it in job.get("items", [])}
    ra = []
    for k, s in enumerate(spec.get("slides") or [], start=1):
        it = items.get(s.get("index"), {})
        ra.append({"slide": k, "index": s.get("index"), "title": s.get("title", ""),
                   "summary": s.get("summary", ""), "link": it.get("link", ""),
                   "source_title": it.get("title", ""), "source_summary": it.get("summary_vi", "")})
    return ra


def material_text(slides: list) -> str:
    """Tu lieu cho caption_check: moi slide mot dong co so lieu cua CA tieu de va tom tat,
    de cong "so khong co trong tu lieu" do tren du N tin chu khong chi tin #1."""
    return "\n".join(
        f"- Slide {s['slide']}: {s['title']}. {s['summary']} "
        f"(researcher: {s['source_title']}. {s['source_summary']})".strip()
        for s in slides) + "\n"


def line_budget(n: int) -> int:
    """Ky tu toi da moi dong tin, de ca caption duoi tran cung cua caption_check."""
    return max(60, (caption_check.CEILING_BACKGROUND_LAYER - INTRO_BUDGET) // max(1, n) - 5)


def write_brief(meta: dict, wd: Path, draft_id: str, persona: str, voice: str, root: Path,
                slides: list) -> str:
    n = len(slides)
    L = [f"# {persona.upper()} — BẢN TIN VẮN: {meta.get('title', '')}",
         f"Brand: {meta.get('brand', '')} | draft: {draft_id} | {n} slide đã duyệt (carousel của Hiro)",
         "", f"## Người đọc: {voice}",
         "", "## Các slide Ông Chủ đã duyệt, ĐÚNG THỨ TỰ trên album (tư liệu DUY NHẤT — chỉ viết điều có ở đây)"]
    for s in slides:
        L.append(f"{s['slide']}. {s['title']} — {s['summary']}")
        if s["source_summary"] and s["source_summary"] != s["summary"]:
            L.append(f"   (researcher: {s['source_summary']})")
    L += ["", f"## Viết caption vào: {wd}/caption.txt  (CHỈ caption, HTML Telegram)",
          "Đây là BẢN TIN VẮN, không phải bài về một tin. Khuôn:",
          "  1. Mở bài 1–2 câu chung cho cả bản tin (xu hướng/điểm nổi bật nhất trong các tin), "
          "kết thúc bằng một câu dẫn có dấu hai chấm.",
          f"  2. Đúng {n} dòng liệt kê, MỖI SLIDE MỘT DÒNG, theo ĐÚNG thứ tự slide ở trên, mở bằng "
          "“• ” (emoji đầu dòng tuỳ chọn). Các dòng dính nhau, không chèn dòng trống giữa chúng.",
          f"     Mỗi dòng ≤ {line_budget(n)} ký tự: ý chính + con số quan trọng nhất của tin đó. "
          "Không đào sâu — chi tiết là việc của bài riêng.",
          "  3. Một dòng trống rồi 1 câu kết (câu hỏi cho người đọc hoặc điều cần theo dõi).",
          "Không dòng \"Nguồn:\" (tin đến từ nhiều báo). Không URL/tên miền sống. Chỉ dùng số có trong "
          "danh sách trên; không cộng dồn, không suy ra số mới. Thẻ HTML chỉ <b> <i> <code>. Không em-dash (— –). "
          f"Cấm cụm: {', '.join(caption_check.STAR_EMPTY)}. Tiếng Việt có dấu.",
          *(["GIỌNG JIKA vẫn giữ (script chặn): câu mở đầu và câu kết BẮT ĐẦU bằng một emoji, "
             "không emoji ở câu văn giữa bài (dòng liệt kê được miễn); gọi người đọc \"quý đạo hữu\", "
             "không \"bạn\"; câu hỏi kết đi thẳng vào nội dung."] if persona == "jika" else []),
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {root} && venv/bin/python {persona}_submit.py {draft_id}",
          "Script đếm dòng liệt kê (phải đúng số slide), chạy cổng chặn, ghép draft, đẩy vào hàng duyệt. "
          "CHỈ khi script báo [LOI] mới sửa đúng chỗ đó rồi chạy lại. Thấy [xong] là kết thúc task, "
          "KHÔNG nộp lại."]
    return "\n".join(L)


def prepare(meta: dict, wd: Path, draft_id: str, persona: str, voice: str, root: Path) -> str:
    """Ghi material.md (cho cong nop) + tra brief. KHONG goi engine anh (xem docstring)."""
    slides = load_slides(wd)
    (wd / state_paths.MATERIAL_FILE).write_text(material_text(slides), encoding="utf-8")
    return write_brief(meta, wd, draft_id, persona, voice, root, slides)


def _plain(t: str) -> str:
    return re.sub(r"<[^>]+>", "", t or "").strip()


def check_caption(cap: str, wd: Path) -> list:
    """Loi cua caption ban tin: dem dong liet ke phai DUNG so slide (moi slide mot dong)."""
    try:
        n = len(load_slides(wd))
    except (OSError, ValueError) as e:
        return [f"khong doc duoc danh sach slide cua ban tin ({type(e).__name__}) — bao Ong Chu"]
    got = [ln for ln in cap.splitlines() if LIST_LINE.match(ln)]
    loi = []
    if len(got) != n:
        loi.append(f"ban tin co {n} slide nhung caption co {len(got)} dong liet ke — viet DUNG {n} dong, "
                   "moi slide mot dong mo bang “• ”, theo thu tu slide")
    dai = [k for k, ln in enumerate(got, start=1) if len(_plain(ln)) > line_budget(n) + 40]
    if dai:
        loi.append(f"dong liet ke {', '.join(map(str, dai))} qua dai (tran ~{line_budget(n)} ky tu) — rut gon")
    return loi
