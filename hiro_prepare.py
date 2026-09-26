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
import re
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
LOGO_LETTER = "L"                  # ma the logo cua tin: `3L` (LOW-420)
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


def _candidate_urls(item: dict, wide_only: bool = False) -> list:
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
        found = (_find(item, link, wide=True) if wide_only
                 else _find(item, link, wide=False) or _find(item, link, wide=True))
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
    w, ht = img.size
    if min(w, ht) < MIN_SHORT_SIDE:
        return None
    if rules.is_blank_image(img)[0]:
        return None
    # dHash tren anh GOC (chua cat): so sanh giua cac anh va voi anh mac dinh cua trang phai
    # cung mot kieu — hash ban da cat 4:5 lech han ban goc (do 25/09: vong tim lai lay lai
    # dung anh logo TradingView vi so hash ban cat voi hash ban goc).
    h = rules.dhash(img)
    if any(rules.is_near_duplicate(h, s, rules.dhash_threshold_for(img)) for s in seen):
        return None                                           # cung anh o URL khac (do 25/09: 3 ban 1200x686)
    seen.append(h)
    chart = bool(rules.is_chart(img)[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    if chart:
        img.save(out, "PNG")                                  # full be ngang, carousel tu dat
    else:
        _save_crop(img, out, "4:5", cat_ngang=True)
    return {"path": str(out), "w": w, "h": ht, "chart": chart, "dhash": h}


def _company_logo_card(vendor: dict, sub: Path) -> dict | None:
    """The logo HANG (Wikidata P154 -> Commons -> `image_brand.card_logo`), ghi vao `sub` rieng
    cua tin. Khong dung `image_brand.image_wikidata`: ham do con di tim anh cong ty + anh nguoi
    (nhieu luot mang), va ghi the vao MOT duong co dinh cua workdir — bo Hiro nhieu tin, nhieu
    hang thi the sau de the truoc."""
    import httpx
    import image_brand
    name = image_brand.DISPLAY_NAME.get(vendor["key"], (vendor["company"],))[0]
    files = (image_brand.material_wikidata(name) or {}).get("logo") or []
    u = image_brand.commons_urls(files[:1]).get(files[0]) if files else None
    if not u:
        return None
    sub.mkdir(parents=True, exist_ok=True)
    goc = sub / state_paths.LOGO_ORIGINAL_FILE
    goc.write_bytes(httpx.get(u["url"], headers={"User-Agent": env_load.UA_WIKI}, timeout=30,
                              follow_redirects=True).content)
    the, _nen, fill = image_brand.card_logo(goc, sub / state_paths.LOGO_CARD_FILE, env_load.brand_long())
    return {"path": str(the), "label": vendor["company"], "image_url": u["url"], "fill": round(fill, 4)}


# Duoi phap nhan bo khoi chip ten hang: bia mau cua Ong Chu ghi "ANTHROPIC", "OPENAI", "MICROSOFT"
# (26/09/2026); Wikidata tra "Oracle Corporation" -> chip "ORACLE CORPORATION" dai gap doi.
_LEGAL_SUFFIX = re.compile(r"[\s,]+(?:corporation|corp\.?|inc\.?|incorporated|ltd\.?|limited|llc|plc|"
                           r"co\.|company|holdings|group|s\.?a\.?|ag|gmbh|n\.?v\.?)$", re.I)


def short_label(name: str) -> str:
    """'Oracle Corporation' -> 'Oracle', 'Alibaba Group' -> 'Alibaba'. Thuan."""
    ten = (name or "").strip()
    while True:
        moi = _LEGAL_SUFFIX.sub("", ten).strip()
        if moi == ten or not moi:
            return ten
        ten = moi


def logo_for_item(item: dict, folder: Path) -> dict | None:
    """The logo cua CHU THE tin cho slide bia (LOW-420): logo MODEL neu tieu de goi ten mot ho
    model co logo rieng (LOW-337: "khi nhac toi model, chi duoc phep dung logo cua model"), khong
    thi logo HANG CHINH — hang dau tien trong tin (`image_brand.vendors_in_story`). None = khong
    co -> slide bia dung anh that cua tin. Mang; loi thi None, khong hong ca bo.

    CHI hang chinh, KHONG roi sang hang thu hai: do that 26/09/2026 (may chu, bao cao Vera) tin
    "TSMC tinh doi Nvidia chia phan loi nhuan" ra logo NVIDIA vi luot tra Commons cua TSMC hong tam
    thoi — logo hang khac tren tieu de cua TSMC la gan sai chu the. Hong thi thu lai MOT lan."""
    import image_brand
    n = item["index"]
    sub = folder / f"logo_{n}"
    try:
        found = None
        for c in image_brand.model_logo_images(item.get("title", ""), sub, only_table=True):
            found = {"path": c["file_path"], "label": c["brand_match"]["company"],
                     "image_url": c["image_url"], "fill": c["brand_match"].get("logo_fill")}
            break
        if not found:
            chinh = image_brand.vendors_in_story(item.get("title", ""), item.get("summary_vi", ""))[:1]
            for v in chinh * 2:                              # hang chinh, thu lai mot lan
                try:
                    found = _company_logo_card(v, sub)
                except Exception as e:                       # noqa: BLE001 — loi mang tam thoi
                    print(f"[CANH BAO] #{n}: logo {v['company']} loi {type(e).__name__}", file=sys.stderr)
                if found:
                    break
    except Exception as e:                                   # noqa: BLE001 — mot tin hong khong hong ca bo
        print(f"[CANH BAO] #{n}: the logo loi {type(e).__name__}: {e}", file=sys.stderr)
        return None
    if not found:
        return None
    return {"code": f"{n}{LOGO_LETTER}", "path": found["path"], "w": 1200, "h": 1500, "chart": False,
            "kind": "logo", "label": short_label(found["label"]), "fill": found.get("fill"),
            "image_url": found["image_url"], "domain": "commons.wikimedia.org",
            "why": f"thẻ logo {found['label']} (dùng cho slide bìa)"}


def prepare_item(item: dict, folder: Path, wide_only: bool = False, avoid: list = ()) -> list:
    """Toi da MAX_CANDIDATES anh da cat cho mot tin (+ the logo `nL` neu co, LOW-420):
    [{code, path, w, h, chart, domain, why}]. `avoid`: dhash anh KHONG lay (anh mac dinh cua
    trang, xem drop_shared_placeholders)."""
    n = item["index"]
    ra, seen = [], list(avoid)
    for url, page, why in _candidate_urls(item, wide_only):
        if len(ra) >= MAX_CANDIDATES:
            break
        code = f"{n}{LETTERS[len(ra)]}"
        got = _save_candidate(url, folder / f"{code}.png", seen)
        if got:
            ra.append({"code": code, **got, "image_url": url,
                       "domain": urlparse(page or url).netloc.removeprefix("www."), "why": why})
    if not wide_only:
        logo = logo_for_item(item, folder)
        if logo:
            ra.append(logo)
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
    found = {it["index"]: ds for it, ds in zip(job["items"], lists)}
    images, placeholders = drop_shared_placeholders(found)
    # Tin chi co anh mac dinh cua trang (do 25/09: hai tin tradingview) -> tim o bao khac.
    # The logo khong tinh la "anh" o day: tin chi con logo van can anh that cho slide quote.
    for it in job["items"]:
        n = it["index"]
        if found.get(n) and not [a for a in images.get(n) or [] if a.get("kind") != "logo"]:
            images[n] = prepare_item(it, folder, wide_only=True, avoid=placeholders) + \
                [a for a in images.get(n) or [] if a.get("kind") == "logo"]
    contact_sheet(images, wd / state_paths.CONTACT_SHEET_FILE)
    cache.write_text(json.dumps({str(k): v for k, v in images.items()}, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    return job, images, wd


def drop_shared_placeholders(images: dict) -> tuple[dict, list]:
    """Bo anh xuat hien o HAI tin KHAC NHAU trong cung bo — anh mac dinh cua nha bao.
    Tra (anh con lai, dhash cac anh bi bo — de vong tim lai tranh chung).

    Do that 25/09/2026 (bao cao Vera, may chu): tin #9 va #12 deu tu tradingview.com, ca hai
    ra CUNG mot anh og "TradingView News" (logo trang, khong phai anh tin). Mot anh that cua
    mot tin khong bao gio la anh dung cua mot tin khac trong cung ban tin.

    THE LOGO (LOW-420) khong co dhash nen khong bi xet: hai tin cung mot hang (hai tin Microsoft)
    dung chung logo la dung, khong phai anh mac dinh cua trang."""
    rules = role.active_rules()
    hashes = {(n, a["code"]): a["dhash"] for n, ds in images.items() for a in ds if a.get("dhash") is not None}
    shared = {k for k, h in hashes.items()
              for k2, h2 in hashes.items() if k2[0] != k[0] and rules.is_near_duplicate(h, h2)}
    for n, code in sorted(shared):
        print(f"[CANH BAO] #{n}: bo {code} — trung anh cua tin khac (anh mac dinh cua trang)",
              file=sys.stderr)
    return ({n: [a for a in ds if (n, a["code"]) not in shared] for n, ds in images.items()},
            [hashes[k] for k in shared])


def contact_sheet(images: dict, out: Path, thumb=(240, 300)) -> Path | None:
    """MOT tam luoi moi anh ung vien kem ma (3A, 3B...) — vai mo mot tam nay de xem anh co
    dung chu de khong, thay vi mo tung anh (do 25/09: tin Microsoft vung Vinh ra anh mot
    nhom nguoi khong lien quan, tin Surface ra anh can phong trong)."""
    from PIL import Image, ImageDraw
    items = [(a["code"], a["path"]) for n in sorted(images) for a in images[n]]
    if not items:
        return None
    cols = 6
    rows = (len(items) + cols - 1) // cols
    w, h = thumb
    sheet = Image.new("RGB", (cols * w, rows * (h + 34)), (250, 250, 250))
    d = ImageDraw.Draw(sheet)
    for i, (code, path) in enumerate(items):
        x, y = (i % cols) * w, (i // cols) * (h + 34)
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((w - 8, h - 8))
                sheet.paste(im, (x + (w - im.width) // 2, y + 4))
        except OSError:
            continue
        d.text((x + 8, y + h + 6), code, fill=(0, 0, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, "PNG")
    return out


def style_at(position: int) -> str:
    """Kieu slide theo VI TRI trong album (LOW-420, Ong Chu 26/09/2026: "se dat xen ke voi style
    quote"): slide le (1, 3, 5...) la BIA LOGO, slide chan la QUOTE. Theo vi tri, khong theo tin:
    bo tin (skipped) thi cac slide sau doi kieu theo, album van xen ke deu."""
    return "cover" if position % 2 == 1 else "quote"


def logo_label(images: dict, n: int) -> str:
    """Chip ten hang mac dinh cua tin `n` = nhan cua the logo (neu co)."""
    return next((a.get("label") or "" for a in images.get(n) or [] if a.get("kind") == "logo"), "")


def spec_skeleton(job: dict, images: dict) -> dict:
    """Khung spec dien san tu manifest: vai sua chu (tieng Viet, ngan) va doi ma anh neu can.
    Slide bia (le) mac dinh dung the logo, slide quote (chan) mac dinh dung anh that."""
    slides, skipped = [], []
    for it in job["items"]:
        n = it["index"]
        ds = images.get(n) or []
        if not ds:
            skipped.append({"index": n, "reason": "không tìm được ảnh thật"})
            continue
        style = style_at(len(slides) + 1)
        anh = [a for a in ds if a.get("kind") != "logo"]
        logo = [a for a in ds if a.get("kind") == "logo"]
        chon = (logo or anh) if style == "cover" else (anh or logo)
        s = {"index": n, "style": style, "image": chon[0]["code"],
             "title": it.get("title", ""), "summary": it.get("summary_vi", "")}
        if style == "cover":
            s["label"] = logo_label(images, n)
            s["category"] = str(it.get("category") or "BUSINESS").upper()
        slides.append(s)
    return {"background_tone": "dark", "slides": slides, "skipped": skipped}


def wd_sheet(draft_id: str) -> Path:
    return workdir(draft_id) / state_paths.CONTACT_SHEET_FILE


def write_brief(draft_id: str, job: dict, images: dict, spec_path: Path) -> str:
    L = [f"# HIRO — bản tin vắn {len(job['items'])} tin từ {role.display_name(job['scan_role'])}",
         f"Brand: {job['brand']} | draft: {draft_id} | mỗi headline MỘT slide, tối đa 10",
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
            kieu = ("THẺ LOGO (cho slide bìa)" if a.get("kind") == "logo"
                    else "chart/bảng (giữ full bề ngang)" if a["chart"] else "ảnh chụp (đã cắt 4:5)")
            L.append(f"- `{a['code']}` {a['w']}x{a['h']} {kieu} ← {a['domain']}"
                     + (f" — {a['why']}" if a.get("why") else ""))
    L += ["",
          f"## Spec: SỬA tệp {spec_path} (đã điền sẵn từ danh sách, ảnh mặc định = ảnh đầu mỗi tin)",
          "Mỗi phần tử `slides`: `index` (số tin, giữ ĐÚNG thứ tự), `image` (mã ảnh CỦA CHÍNH tin đó), "
          "`title`, `summary`. Tin không dùng được thì chuyển sang `skipped` kèm `reason` — "
          "không bỏ im lặng.",
          "- HAI KIỂU SLIDE XEN KẼ THEO VỊ TRÍ (script tự xếp, không cần khai): slide 1, 3, 5… là "
          "BÌA LOGO — ảnh nên là thẻ logo `nL`, chữ chỉ có `title` (in lớn, không hiện summary) + chip "
          "`category` (FUNDING, POLICY, PRODUCT, MODEL RELEASE, RESEARCH, BUSINESS…) + chip `label` "
          "(tên hãng/model, đã điền sẵn từ logo). Slide 2, 4, 6… là QUOTE — ảnh thật, `title` trong "
          "khung quote, `summary` ngoài khung. Slide bìa: `title` nên là một câu giật (con số, nghịch "
          "lý) vì nó đứng một mình.",
          "- `title`: tiếng Việt có dấu, ngắn gọn (~60–80 ký tự), giữ tên riêng/tên model/con số; "
          "tiêu đề tiếng Anh thì DỊCH.",
          "- `summary`: MỘT–HAI câu ý chính (~100–180 ký tự), không đào sâu (việc đó của bài riêng).",
          "- Không em-dash, không đuôi tên miền. Chữ dài quá khung thì script báo, rút gọn.",
          f"- MỞ MỘT tấm {wd_sheet(draft_id)} (lưới mọi ảnh kèm mã) để xem ảnh mỗi tin có đúng chủ "
          "đề không. Ảnh mặc định sai chủ đề/người lạ/phòng trống/logo trang thì đổi sang mã khác "
          "CỦA CÙNG tin; tin không còn ảnh nào đúng thì chuyển sang `skipped` kèm lý do.",
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
