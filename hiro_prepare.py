#!/usr/bin/env python3
"""hiro_prepare.py — BRIEF cho Hiro (carousel ban tin van, LOW-404).

Doc danh sach tin `hiro_job.json` (hiro_pick ghi luc Ong Chu reply `Hiro`), tim toi da
`MAX_CANDIDATES` anh that cho MOI tin, cat san, roi in brief + khung spec. Vai chi con
viec: viet tieu de + tom tat tieng Viet cho tung slide va chon ma anh.

Anh moi tin (re nhat co the — N tin mot luc, khong chay engine cua Dre N lan):
  1. `image_url` researcher da gan (Finn gan og:image luc quet), roi
  2. `article_images.find(tieu_de, link, sau_rong=False)`: anh trong CHINH bai, xep hang net.
Anh chup cat 4:5 quanh giua (`download_filter._save_crop`, dong dau crop cho cong doc);
chart/bang/screenshot GIU NGUYEN be ngang — `carousel._body_image` dan full be ngang (luat
"khong cat be ngang chart", crop_ratio). Anh qua nho / trong / loi tai thi bo.

Dung:
    venv/bin/python hiro_prepare.py <draft_id>            # in brief (tim anh neu chua)
    venv/bin/python hiro_prepare.py <draft_id> --lam-moi  # bo cache, tim lai anh
"""
import argparse
import concurrent.futures as cf
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                               # noqa: E402
import role                                                   # noqa: E402
import state_paths                                            # noqa: E402

ROLE = "hiro"
MAX_CANDIDATES = 3                 # anh ung vien moi tin — du de Lam lai co anh khac
MIN_SHORT_SIDE = 400               # duoi nua khung 1080 thi phong len vo han
LETTERS = "ABCDEFGH"


def workdir(draft_id: str) -> Path:
    return state_paths.workdir(env_load.state_dir(), draft_id)


def load_job(draft_id: str) -> dict:
    p = workdir(draft_id) / state_paths.HIRO_JOB_FILE
    if not p.exists():
        sys.exit(f"[LOI] khong co {p} — task Hiro phai tao tu reply `Hiro` vao bao cao researcher.")
    return json.loads(p.read_text(encoding="utf-8"))


def _real_link(link: str) -> str:
    """Link Google News (tin Vera doc RSS) -> URL bai that; khong giai duoc thi giu nguyen.

    Do that 25/09/2026 (bao cao Vera 15 tin, may chu): 4/4 link news.google.com ra 0 anh —
    trang do la trang chuyen huong chay JS. Dung lai bo giai cua article_sources (cung bo
    ma create_pair dung cho Dre)."""
    import article_sources
    try:
        return article_sources.resolve_code_gnews(link) or link
    except Exception:                                        # noqa: BLE001
        return link


def _find(item: dict, link: str, wide: bool) -> list:
    import article_images
    try:
        return article_images.find(item.get("title", ""), link, sau_rong=wide)
    except Exception as e:                                   # noqa: BLE001 — mot tin hong khong hong ca bo
        print(f"[CANH BAO] #{item.get('index')}: tim anh loi {type(e).__name__}: {e}", file=sys.stderr)
        return []


def _candidate_urls(item: dict) -> list:
    """[(url, trang chua anh, ly do)] theo thu tu uu tien, khong trung.

    Trang bai truoc (`sau_rong=False`, re). Trang bai KHONG cho anh nao (do 25/09: stocktwits,
    geekwire, mlex chan bot / render JS) thi moi tim them o bao khac dua cung tin
    (`sau_rong=True`)."""
    ra, thay = [], set()
    if item.get("image_url"):
        ra.append((item["image_url"], item.get("link", ""), "ảnh researcher gắn"))
        thay.add(item["image_url"])
    if item.get("link"):
        link = _real_link(item["link"])
        found = _find(item, link, wide=False) or _find(item, link, wide=True)
        for c in found:
            if c["image_url"] not in thay:
                thay.add(c["image_url"])
                ra.append((c["image_url"], c.get("page_url") or link, c.get("score_reason", "")))
    return ra


def _save_candidate(url: str, out: Path, seen: list) -> dict | None:
    """Tai + cat mot anh ra `out`. None neu khong dung duoc hoac trung anh da giu (`seen`: dhash)."""
    import article_images
    from PIL import Image
    from prepare.download_filter import _save_crop
    rules = role.active_rules()
    try:
        r = article_images._download(url)
        if r.status_code != 200:
            return None
        img = Image.open(io.BytesIO(r.content))
        img.load()
        img = img.convert("RGB")
    except Exception:                                        # noqa: BLE001 — anh hong thi bo, thu anh sau
        return None
    w, h = img.size
    if min(w, h) < MIN_SHORT_SIDE:
        return None
    if rules.is_blank_image(img)[0]:
        return None
    if any(rules.is_near_duplicate(rules.dhash(img), s, rules.dhash_threshold_for(img)) for s in seen):
        return None                                           # cung anh o URL khac (do 25/09: 3 ban 1200x686)
    seen.append(rules.dhash(img))
    chart = bool(rules.is_chart(img)[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    if chart:
        img.save(out, "PNG")                                  # full be ngang, carousel tu dat
    else:
        _save_crop(img, out, "4:5", cat_ngang=True)
    return {"path": str(out), "w": w, "h": h, "chart": chart}


def prepare_item(item: dict, folder: Path) -> list:
    """Toi da MAX_CANDIDATES anh da cat cho mot tin: [{code, path, w, h, chart, domain, why}]."""
    n = item["index"]
    ra, seen = [], []
    for url, page, why in _candidate_urls(item):
        if len(ra) >= MAX_CANDIDATES:
            break
        code = f"{n}{LETTERS[len(ra)]}"
        got = _save_candidate(url, folder / f"{code}.png", seen)
        if got:
            ra.append({"code": code, **got, "image_url": url,
                       "domain": urlparse(page or url).netloc.removeprefix("www."), "why": why})
    return ra


def run(draft_id: str, refresh: bool = False) -> tuple[dict, dict, Path]:
    """(job, {index: [anh]}, workdir). Cache o hiro_images.json tru khi `refresh`."""
    role.set_active_role(ROLE)
    job = load_job(draft_id)
    wd = workdir(draft_id)
    cache = wd / state_paths.HIRO_IMAGES_FILE
    if cache.exists() and not refresh:
        images = {int(k): v for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
        return job, images, wd
    folder = wd / state_paths.HIRO_IMAGES_DIR
    with cf.ThreadPoolExecutor(max_workers=env_load.quantity(4)) as ex:
        lists = list(ex.map(lambda it: prepare_item(it, folder), job["items"]))
    images = {it["index"]: ds for it, ds in zip(job["items"], lists)}
    cache.write_text(json.dumps({str(k): v for k, v in images.items()}, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    return job, images, wd


def spec_skeleton(job: dict, images: dict) -> dict:
    """Khung spec dien san tu manifest: vai sua chu (tieng Viet, ngan) va doi ma anh neu can."""
    slides, skipped = [], []
    for it in job["items"]:
        ds = images.get(it["index"]) or []
        if not ds:
            skipped.append({"index": it["index"], "reason": "không tìm được ảnh thật"})
            continue
        slides.append({"index": it["index"], "image": ds[0]["code"],
                       "title": it.get("title", ""), "summary": it.get("summary_vi", "")})
    return {"background_tone": "dark", "slides": slides, "skipped": skipped}


def write_brief(draft_id: str, job: dict, images: dict, spec_path: Path) -> str:
    L = [f"# HIRO — bản tin vắn {len(job['items'])} tin từ {role.display_name(job['scan_role'])}",
         f"Brand: {job['brand']} | draft: {draft_id} | mỗi headline MỘT slide, không bìa, tối đa 20",
         "",
         "## Tin và ảnh đã tải + cắt sẵn (chỉ dùng MÃ ẢNH, không tải/mở gì thêm)"]
    for it in job["items"]:
        L.append(f"\n### #{it['index']} {it.get('title', '')}")
        if it.get("summary_vi"):
            L.append(f"Tóm tắt researcher: {it['summary_vi']}")
        L.append(f"Link: {it.get('link', '')}")
        ds = images.get(it["index"]) or []
        if not ds:
            L.append("⚠️ KHÔNG có ảnh thật dùng được — để tin này trong `skipped` kèm lý do.")
        for a in ds:
            kieu = "chart/bảng (giữ full bề ngang)" if a["chart"] else "ảnh chụp (đã cắt 4:5)"
            L.append(f"- `{a['code']}` {a['w']}x{a['h']} {kieu} ← {a['domain']}"
                     + (f" — {a['why']}" if a.get("why") else ""))
    L += ["",
          f"## Spec: SỬA tệp {spec_path} (đã điền sẵn từ danh sách, ảnh mặc định = ảnh đầu mỗi tin)",
          "Mỗi phần tử `slides`: `index` (số tin, giữ ĐÚNG thứ tự), `image` (mã ảnh CỦA CHÍNH tin đó), "
          "`title`, `summary`. Tin không dùng được thì chuyển sang `skipped` kèm `reason` — "
          "không bỏ im lặng.",
          "- `title`: tiếng Việt có dấu, ngắn gọn (~60–80 ký tự), giữ tên riêng/tên model/con số; "
          "tiêu đề tiếng Anh thì DỊCH.",
          "- `summary`: MỘT–HAI câu ý chính (~100–180 ký tự), không đào sâu (việc đó của bài riêng).",
          "- Không em-dash, không đuôi tên miền. Chữ dài quá khung thì script báo, rút gọn.",
          "- Đổi ảnh khi ảnh mặc định sai chủ đề/mặt người lạ/logo trống — chọn mã khác CỦA CÙNG tin.",
          "",
          "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python hiro_submit.py {draft_id}",
          "Script dựng slide, chạy cổng chặn, gửi album lên topic kèm nút duyệt. Báo [LOI] thì sửa "
          "đúng chỗ đó trong spec rồi chạy lại. KHÔNG chạy carousel.py/send_telegram.py tay."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief carousel ban tin van cho Hiro")
    ap.add_argument("draft_id")
    ap.add_argument("--lam-moi", action="store_true", help="Bo cache anh, tim lai")
    ap.add_argument("--im", action="store_true", help="Khong in brief")
    a = ap.parse_args()
    job, images, wd = run(a.draft_id, a.lam_moi)
    spec_path = wd / "spec.json"
    if not spec_path.exists() or a.lam_moi:
        spec_path.write_text(json.dumps(spec_skeleton(job, images), ensure_ascii=False, indent=2),
                             encoding="utf-8")
    brief = write_brief(a.draft_id, job, images, spec_path)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
