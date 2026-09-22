#!/usr/bin/env python3
"""scan_prepare.py — BRIEF cho ba vai DI TIM TIN (Finn/scout, Nova/nova, Vera/market).

Truoc: cron giao task, vai tu chay script quet, tu `cat`/`read_file` tep JSON
40 muc, tu `grep`, tu `web_search` them, sua tep nop nhieu lan qua `patch`
(do 03-04/09/2026: Finn 21 tool call, Nova 22 va 9 web_search, Vera 14).
Gio: tep nay chay script quet (cache trong ngay), in MOT ban tom tat gon —
tung ung vien mot dong, muc BAT BUOC, khung tep nop — vai chi cham diem / tom
tat / viet y nghia vao MOT tep JSON roi chay scan_submit.py.

Thu muc lam viec: state/<brand>/scan/<vai>_<YYYYMMDD VN>/

Dung:
    venv/bin/python scan_prepare.py --vai finn|nova|vera|qinn [--lam-moi]
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                              # noqa: E402
import required                                              # noqa: E402
import role                                                   # noqa: E402
import scan_common                                            # noqa: E402
import state_paths                                           # noqa: E402

VN = timezone(timedelta(hours=7))
TOPIC = {"finn": "finn", "nova": "nova", "vera": "vera", "qinn": "qinn"}

# Vai chay NHIEU LAN trong ngay: thu muc lam viec phai tach theo luot, khong thi
# luot sau doc lai list.json cua luot truoc va nop nham tin cu (cache quet 3h het
# han nen scan.json thi moi, list.json thi khong — lech nhau im lang).
MANY_ATTEMPT_WITHIN_DATE = {"qinn"}
CACHE_HOURS = 3
# Tran bao cao cua Nova trong brief. Truoc 06/09/2026 la 12.000 va cat CAM
# LANG giua dong: do that o trang thai production (arena song + co moc cu de so
# hang) bao cao ra 13.635 ky tu, tuc LIVEBENCH va OPENROUTER USAGE bi nuot mat
# truoc khi Nova nhin thay — Nova khong biet hai bang do ton tai, chu khong
# phai "doc roi thay khong co gi". Do lai sau khi them 8 bang: 16.800 ky tu.
CEILING_REPORT = 22000


def _crop(bao_cao: str, tran: int = CEILING_REPORT) -> str:
    """Cat bao cao NHUNG noi ro la da cat — im lang thi vai tuong minh da doc het."""
    b = bao_cao.strip()
    if len(b) <= tran:
        return b
    return (b[:tran].rsplit("\n", 1)[0]
            + f"\n\n[!] BAO CAO BI CAT o {tran} ky tu, mat {len(b) - tran} ky tu "
              "cuoi. Cac bang phia duoi KHONG hien ra day — dung ket luan la "
              "'khong co gi'. Bao Ong Chu de nang tran.")


# Khung gio cua MOT luot, tinh tu FRAME_START gio VN. 12 = hai luot/ngay (06:00
# va 18:00 VN, LOW-353). Doi hai so nay la doi CA nhip: phai sua cung luc ba cho —
# hang so nay, cron expr cua job `qinn-scan`, va cong thuc LUOT trong
# hermes/scripts/daily_scan.sh.
FRAME_HOURS = 12
FRAME_START = 6

# LOW-352: Nova/Vera cham hai thanh phan 0-50 (manifest_write.SCORE_PARTS). Noi ro
# diem khong len bao cao: vai biet diem khong phai de "trinh bay" thi cham that hon.
SCORE_NOTE = ("Điểm = score_impact + score_relevance (0–100). Chấm trung thực, dùng hết thang: điểm KHÔNG "
              "lên báo cáo và KHÔNG đổi thứ tự — đội dùng nó để đo xem đoán được Ông Chủ chọn tin nào.")


def turn(gio_vn: int = None) -> int:
    """Luot trong ngay cho vai chay nhieu lan: khung FRAME_HOURS tieng tu FRAME_START gio VN.

    Moc cron nam dau moi khung, vai chay brief o dau khung va nop trong vong vai
    phut -> luon cung mot luot. Khong dung gio tron vi nop luc 17:59 va 18:01 se
    ra hai thu muc khac nhau."""
    h = datetime.now(VN).hour if gio_vn is None else gio_vn
    return ((h - FRAME_START) % 24) // FRAME_HOURS


def workdir(vai: str) -> Path:
    ten = f"{vai}_{datetime.now(VN).strftime('%Y%m%d')}"
    if vai in MANY_ATTEMPT_WITHIN_DATE:
        ten += f"_p{turn()}"
    wd = env_load.state_dir() / state_paths.SCAN_DIR / ten
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def _new(p: Path) -> bool:
    return p.exists() and time.time() - p.stat().st_mtime < CACHE_HOURS * 3600


def _run(args: list, timeout=900) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable] + args, cwd=str(ROOT), capture_output=True,
                          text=True, timeout=timeout)


def _required(vai_bb: str) -> list:
    L = []
    bb = required.read(vai_bb)
    if bb:
        L.append(f"## BẮT BUỘC đưa vào danh sách nộp ({len(bb)}) — thiếu thì script tự thêm và ghi chú "
                 "'vai bỏ sót' lên báo cáo cho Ông Chủ thấy; hãy tự đưa vào và chấm trung thực")
        for v in bb.values():
            link = required.link_call_y(v)
            L.append(f"- [{required.kind_label(v.get('kind', ''))}] {v.get('name', '')[:90]} | {v.get('note', '')[:60]}"
                     + (f" | {link[:100]}" if link else ""))
    else:
        L.append("## BẮT BUỘC: không có mục nào đang chờ")
    return L


def _supplement_required(cs: list) -> int:
    """Muc BAT BUOC mang tu hom truoc ma scan hom nay khong con (loc 72h, chong
    trung) thi them vao cuoi candidates voi diem co hoc 0, de manifest_build
    doi chieu duoc link. 05/09: 4/8 muc "khong tim thay trong candidates",
    Finn mo 18 tool call roi block task."""
    co = {required.chuan_link(c.get("link", "")) for c in cs}
    n = 0
    for v in required.read("finn").values():
        link = v.get("link", "")
        if not link or required.chuan_link(link) in co:
            continue
        m = re.search(r"(\d+)\s*diem", v.get("note", ""))
        try:
            tuoi = (datetime.now(timezone.utc)
                    - datetime.strptime(v.get("added_date", ""), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    ).total_seconds() / 3600
        except ValueError:
            tuoi = 0.0
        cs.append({"source": required.SOURCE_REQUIRED, "title": v.get("name", ""), "link": link, "discussion": "",
                   "points": int(m.group(1)) if m else 0, "comments": 0,
                   "via": required.chuan_link(link).split("/")[0], "posted_by": "",
                   "age_hours": tuoi, "score_recency": 0, "score_spread": 0, "score_partial": 0,
                   "source_median_points": 0, "image_url": None, "required": True})
        n += 1
    return n


# ---- scout (Finn) -----------------------------------------------------------
def submit_command(vai: str) -> str:
    """Dong lenh NOP in trong brief, mang dung slug cua vai (LOW-318, 20/09/2026).

    Truoc day bon brief go cung chuoi: Finn duoc bao chay `--vai scout`, Vera
    `--vai market` — slug CU tu truoc LOW-14. Lenh van chay (argparse giai qua
    `role.canonical_slug`), nhung vai doc brief roi tu nghi minh chay sai vai:
    sang 20/09 Finn neu dung dong nay trong ly do tu chan (LOW-317), tuc mat mot
    vong chan doan chi vi tai lieu goi no bang ten khac."""
    return f"cd {ROOT} && venv/bin/python scan_submit.py --vai {vai}"


def brief_scout(wd: Path, lam_moi: bool, vai: str) -> str:
    cand = wd / "candidates.json"
    if lam_moi or not _new(cand):
        r = _run([str(ROOT / "scan_sources.py"), "--out", str(cand)])
        (wd / "scan.log").write_text((r.stderr or "") + (r.stdout or ""), encoding="utf-8")
        if r.returncode != 0 or not cand.exists():
            sys.exit(f"[LOI] scan_sources.py hong: {(r.stderr or '')[-400:]}")
    d = json.loads(cand.read_text(encoding="utf-8"))
    cs = d.get("candidates", [])
    bo_sung = _supplement_required(cs)
    if bo_sung:
        d["candidates"] = cs
        cand.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    L = [f"# FINN — QUÉT XONG {datetime.now(VN).strftime('%d/%m %H:%M')} VN: {len(cs)} ứng viên "
         f"(đã lọc 72h, chống trùng, chấm sẵn 50/100 điểm cơ học)",
         "Mỗi dòng: #k | điểm cơ học (mới+lan) | nguồn điểm/bình luận | tuổi | tiêu đề | link"]
    if bo_sung:
        L.append(f"({bo_sung} mục BẮT BUỘC mang từ hôm trước không còn trong quét hôm nay đã được thêm "
                 "vào cuối danh sách, nguồn bat_buoc, điểm cơ học 0: vẫn phải nộp, chấm trung thực)")
    for k, c in enumerate(cs, 1):
        L.append(f"#{k} | {c.get('score_partial', 0):2d} (mới {c.get('score_recency', 0)}, lan {c.get('score_spread', 0)})"
                 f" | {required.source_label(c.get('source', ''))} {c.get('points', 0)}p/{c.get('comments', 0)}c | {c.get('age_hours', 0):.0f}h"
                 f" | {c.get('title', '')[:110]} | {c.get('link', '')}")
        if c.get("summary") or c.get("description"):
            L.append(f"     {str(c.get('summary') or c.get('description'))[:200]}")
    L += [""] + _required("finn")
    L += ["", f"## Viết đánh giá vào: {wd}/picks.json — đủ mọi mục BẮT BUỘC + TỐI ĐA 8 tin điểm cao nhất ngoài đó",
          json.dumps([{"k": "<số thứ tự #k trong danh sách (thay cho link, script tự lấy link)>",
                       "category": "<ARXIV | MODEL | LAB | INFRA | TOOL | ENGINEERING | BUSINESS | RESEARCH | SECURITY>",
                       "score_technical": "<0-30: có số liệu đo/mã nguồn/paper thì cao>",
                       "score_relevance": "<0-20: thuộc 5 nhóm (model mới, M&A big tech, arXiv/X/Reddit nổi, use case thật, tin lai); "
                                          "funding round/drama/dự đoán thì trừ nặng>",
                       "score_reason": "<1 câu vì sao điểm này>",
                       "summary_vi": "<MỘT mệnh đề ≤ 15 từ, dữ kiện thuần; chỉ làm ngữ cảnh cho vai viết, KHÔNG lên báo cáo>"}], ensure_ascii=False, indent=1),
          f"Điểm tổng = điểm cơ học (script) + technical + relevance. Không tin nào ≥ {scan_common.SCORE_PASS} "
          "điểm thì chạy bước 3 với --khong-co (script gửi dòng 'hôm nay không có gì' kèm số tin đã quét). "
          f"Tin đã ≥ {scan_common.SCORE_PASS} điểm CƠ HỌC thì --khong-co bị script từ chối.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          submit_command(vai),
          "Script tự ghép manifest (đối chiếu số thứ tự, cộng điểm, đánh số), tự thêm mục bắt buộc còn thiếu, viết báo cáo đánh số, "
          "gửi lên topic. Báo [LOI] thì sửa picks.json rồi chạy lại. KHÔNG cat/grep candidates.json, KHÔNG "
          "web_search, KHÔNG chạy manifest_build/publish tay, KHÔNG tạo task kanban."]
    return "\n".join(L)


# ---- nova ---------------------------------------------------------------------
def brief_nova(wd: Path, lam_moi: bool, vai: str) -> str:
    rep = wd / "scan_models.txt"
    if lam_moi or not _new(rep):
        try:
            r = _run([str(ROOT / "scan_models.py"), "--ngay", "7", "--top", "10",
                       "--khong-bat-buoc"], timeout=1200)
        except subprocess.TimeoutExpired:
            sys.exit("[LOI] scan_models.py qua 20 phut chua xong — bao Ong Chu, "
                     "dung chay lai ngay (nguon nao do dang treo).")
        rep.write_text((r.stdout or "") + "\n[stderr]\n" + (r.stderr or "")[-4000:], encoding="utf-8")
        # KIEM MA THOAT. brief_scout:118 va brief_market deu kiem, rieng day thi
        # khong: scan_models chet giua chung van ghi scan_models.txt gan rong,
        # brief in "Bao cao cua script:" trong, Nova suy ra "khong co gi" va chay
        # `scan_submit --khong-co`. Ong Chu doc "hom nay khong co gi" trong khi that
        # ra 23 bang deu khong duoc doc. Dung loai hong README goi la dang so
        # nhat, va no im lang tuyet doi.
        if r.returncode != 0:
            sys.exit(f"[LOI] scan_models.py hong (ma {r.returncode}): "
                     f"{(r.stderr or '')[-600:]}\n"
                     "  KHONG duoc bao 'hom nay khong co gi' — bao Ong Chu la "
                     "script quet hong.")
    tho = rep.read_text(encoding="utf-8")
    bao_cao = tho.split("\n[stderr]\n")[0]
    # Dua canh bao cua script vao brief. Truoc 06/09/2026 stderr bi vut sach o
    # day, nen moi dong "[openrouter] HONG", "[canh bao] bang 'x' tra rong",
    # "[canh bao] bang_so lech" deu khong bao gio toi mat Nova.
    canh = [d.strip() for d in tho.split("\n[stderr]\n")[-1].splitlines()
            if d.strip() and ("HONG" in d or "[canh bao]" in d or "hong:" in d)]
    mh = {}
    try:
        mh = json.loads((env_load.state_dir() / "model_health.json").read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        pass
    chet = [k for k, v in (mh.get("models") or {}).items() if not v.get("ok")]
    L = [f"# NOVA — QUÉT XONG {datetime.now(VN).strftime('%d/%m %H:%M')} VN (scan_models.py --ngay 7 --top 10)"]
    if canh:
        L += ["", "## ⚠ SCRIPT BÁO SỰ CỐ Ở NGUỒN — báo cáo dưới đây THIẾU, không phải "
              "'hôm nay không có gì'. Nhắc đúng các nguồn này trong summary để Ông Chủ biết:",
              *(f"  {d}" for d in canh[:12])]
    L += ["Báo cáo của script (đọc ở đây, KHÔNG chạy lại, KHÔNG web_search):", "", _crop(bao_cao), ""]
    L.append("Model đội đã đo và đang chết/loại (không đề xuất lại như tin mới): "
             + (", ".join(chet) if chet else "không có") +
             ". Đã loại có lý do: gemini-3.7-flash (cache 0%, đắt 44 lần), kimi-k3 (không tắt suy luận), grok "
             "(cache 0%), nemotron :free (mất dấu). Giá ở bảng coding là NIÊM YẾT, không phải thực đo.")
    L += [""] + _required("nova")
    L += ["", f"## Viết danh sách vào: {wd / state_paths.SCAN_LIST_FILE} — MỘT mục cho MỖI mục bắt buộc (gộp các bảng của cùng model), "
          "tiêu đề phải chứa ĐÚNG tên model như script in",
          json.dumps([{"title": "<Tên model đúng như script in + ý chính, có dấu>",
                       "link": "<bỏ trống với mục BẮT BUỘC (script tự lấy link trang model/bảng); "
                               "chỉ ghi URL thật khi là tin ngoài danh sách>",
                       "summary_vi": "<MỘT mệnh đề ≤ 15 từ: giá vào/ra mỗi triệu token hoặc hạng bảng; chỉ làm ngữ cảnh "
                                     "cho vai viết, KHÔNG lên báo cáo>",
                       "source_note": "<bảng/nguồn + ngày>",
                       "score_impact": "<0-50: vào top 3 bảng lớn (text, WebDev, coding, trí tuệ, ECI, agentic) thì "
                                       "40-50; leo hạng bảng khó bão hoà (HLE, ARC-AGI-2, Terminal-Bench) 30-40; chỉ "
                                       "ra mắt hay đổi giá, bản :free/preview thì dưới 20>",
                       "score_relevance": "<0-50: thay được vai nào của đội, rẻ hay mạnh hơn rõ rệt model đang dùng, "
                                          "frontier Mỹ / top Trung Quốc / hãng ảnh-video dẫn đầu thì cao; thứ đội đã "
                                          "đo và loại thì thấp>",
                       "score_reason": "<1 câu vì sao điểm này>"}], ensure_ascii=False, indent=1),
          SCORE_NOTE,
          "Xếp thứ tự: vào top 3 bảng lớn (text, WebDev, coding, trí tuệ, ECI, agentic) lên đầu; kế đến là leo hạng "
          "ở bảng khó bão hoà (HLE, ARC-AGI-2, Terminal-Bench). Không có gì đáng lên kênh thì "
          "chạy bước 3 với --khong-co.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          submit_command(vai),
          "Script tự ghi manifest đánh số, kiểm mục bắt buộc, viết báo cáo, gửi topic. Báo [LOI] thì sửa list.json "
          "rồi chạy lại. KHÔNG chạy article_sources.py (approve_service làm lúc Ông Chủ chọn), KHÔNG tạo task."]
    return "\n".join(L)


# ---- market (Vera) ------------------------------------------------------------
def brief_market(wd: Path, lam_moi: bool, vai: str) -> str:
    q = wd / state_paths.SCAN_RESULT_FILE
    if lam_moi or not _new(q):
        r = _run([str(ROOT / "scan_business.py"), "--gio", "30", "--out", str(q)])
        (wd / "scan.log").write_text((r.stderr or "") + (r.stdout or ""), encoding="utf-8")
        if r.returncode != 0 or not q.exists():
            sys.exit(f"[LOI] scan_business.py hong: {(r.stderr or '')[-400:]}")
    d = json.loads(q.read_text(encoding="utf-8"))
    tin = d.get("new_stories", [])
    L = [f"# VERA — QUÉT XONG {datetime.now(VN).strftime('%d/%m %H:%M')} VN: {len(tin)} tin trong 30h "
         f"(tổng quét {d.get('scanned_total', '?')}, {d.get('watchlist_count', 0)} tin watchlist)",
         "Mỗi dòng: #k | [W]=watchlist (LUÔN phải đưa) | ngày | số báo: báo | tiêu đề | link"]
    for k, t in enumerate(tin, 1):
        L.append(f"#{k} | {'[W]' if t.get('watchlist') else '   '} | {t.get('date', '')} | "
                 f"{t.get('outlet_count', 1)} báo: {', '.join(t.get('outlets', [])[:3]) or t.get('outlet', '')}"
                 f" | {t.get('title', '')[:110]} | {t.get('link', '')}")
    L += [""] + _required("vera")
    L += ["", f"## Viết danh sách vào: {wd / state_paths.SCAN_LIST_FILE} — tin có HỆ QUẢ (IPO, thâu tóm, hạ tầng, chính sách, lao "
          "động, kiện tụng, cược lớn), kèm mức chắc chắn theo số báo; bỏ giá cổ phiếu trong ngày, PR sản phẩm",
          json.dumps([{"k": "<số thứ tự #k trong danh sách — script tự lấy link và số báo, KHÔNG chép URL>",
                       "title": "<HEADLINE một dòng: chủ thể + việc + con số, tiếng Việt có dấu; đây là thứ DUY NHẤT Ông Chủ đọc>",
                       "summary_vi": "<MỘT mệnh đề ≤ 15 từ vì sao đáng quan tâm; chỉ làm ngữ cảnh cho vai viết, "
                                     "KHÔNG lên báo cáo>",
                       "score_impact": "<0-50: IPO, đổi sở hữu/thâu tóm, tiền lớn vào hạ tầng-chip-điện, chính sách, "
                                       "lao động, phán quyết tiền lệ thì cao, con số càng lớn càng cao; PR sản phẩm, "
                                       "giá cổ phiếu trong ngày, dự đoán thì dưới 15>",
                       "score_relevance": "<0-50: xoay quanh AI hoặc hãng AI lớn, độc giả dcgr cần biết ngay thì cao; "
                                          "chuyện ngoài lề AI thì thấp>",
                       "score_reason": "<1 câu vì sao điểm này>"}], ensure_ascii=False, indent=1),
          SCORE_NOTE,
          "Mọi tin [W] phải có mặt. Không có gì đáng lên kênh thì chạy bước 3 với --khong-co.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          submit_command(vai),
          "Script tự ghi manifest đánh số, tự thêm mục bắt buộc còn thiếu, viết báo cáo, gửi topic. Báo [LOI] thì "
          "sửa list.json rồi chạy lại. KHÔNG chạy article_sources.py, KHÔNG web_search, KHÔNG tạo task."]
    return "\n".join(L)



# ---- qinn (Qinn) -------------------------------------------------------------
def brief_qinn(wd: Path, lam_moi: bool, vai: str) -> str:
    q = wd / state_paths.SCAN_RESULT_FILE
    if lam_moi or not _new(q):
        # Cua so quet trung voi khung mot luot: khong chong lap (tin se trung,
        # tuy `x_seen.json` da chan) va khong ho (tin roi vao khe giua hai luot).
        r = _run([str(ROOT / "scan_x.py"), "--gio", str(FRAME_HOURS), "--out", str(q)])
        (wd / "scan.log").write_text((r.stderr or "") + (r.stdout or ""), encoding="utf-8")
        if r.returncode != 0 or not q.exists():
            sys.exit(f"[LOI] scan_x.py hong: {(r.stderr or '')[-400:]}")
    d = json.loads(q.read_text(encoding="utf-8"))
    tin = d.get("new_stories", [])
    bo = d.get("skipped", {})

    L = []
    # Canh bao tuoi du lieu len TRUOC moi thu khac: "crawler dung" va "hom nay
    # khong co tin dang" nhin giong nhau neu khong noi ra.
    for c in d.get("warnings", []):
        L.append(f"## [!] {c}")
    L.append(
        f"# QINN — QUET XONG {datetime.now(VN).strftime('%d/%m %H:%M')} VN: {len(tin)} tweet "
        f"trong {d.get('window_hours', '?')}h (doc {d.get('scanned_total', '?')} tu DB; "
        f"bo: reply {bo.get('reply', 0)}, qua ngan {bo.get('too_short', 0)}, da thay "
        f"{bo.get('already_seen', 0)})"
    )
    L.append("Xep theo diem CO HOC (tuong tac + link github/arxiv + do dai + thread) — "
             "diem chi de xep thu tu doc, KHONG phai danh gia. Ban moi la bo loc.")
    L.append("Moi muc: #k | [diem] | nguon | @tac gia | loai | so lieu | link, roi text thu vao.")
    for k, t in enumerate(tin, 1):
        sl = t.get("metrics", {}) or {}
        L.append(
            f"\n#{k} | [{t.get('mechanical_score', 0)}] | {t.get('x_source', '')} | {t.get('author', '')} | "
            f"{t.get('tweet_type', '')} | {sl.get('views') or 0} views, {sl.get('likes') or 0} likes | "
            f"{t.get('link', '')}"
        )
        L.append("    " + (t.get("text", "") or "").replace("\n", "\n    ")[:900])
    L += [""] + _required("qinn")
    L += ["", f"## Viet danh sach vao: {wd / state_paths.SCAN_LIST_FILE} — chi tin KY THUAT DUNG DUOC LAU: tool/repo "
          "giai mot viec cu the, ky thuat bao mat, kien truc/he thong, cach lam co the doc lai sau "
          "3 nam. BO: thong bao phat hanh, benchmark/bang xep hang, hype khong co noi dung, tin "
          "ngay, crypto, anh/video khong co phuong phap, tweet chi tom tat tin cua nguoi khac.",
          json.dumps([{"k": "<so thu tu #k — script tu lay link, KHONG chep URL>",
                       "title": "<HEADLINE mot dong tieng Viet co dau: cai gi + lam duoc gi; "
                                "day la thu DUY NHAT Ong Chu doc>",
                       "summary_vi": "<MOT menh de <= 15 tu vi sao dung duoc lau; chi lam ngu canh "
                                     "cho vai viet, KHONG len bao cao>",
                       "category": "<TOOL | SECURITY | ARCH | MODEL — de trong thi TOOL>"}],
                     ensure_ascii=False, indent=1),
          "Tweet cua tac gia GOC hon tweet ke lai. Tin trong `list:` la nguon Ong Chu tu chon — "
          "tin hon home, nhung khong duoc mien tieu chi.",
          "Khong co gi dat nguong thi chay buoc 3 voi --khong-co.",
          "", "## Roi chay dung MOT lenh:",
          submit_command(vai),
          "Script tu ghi manifest danh so, viet bao cao, gui topic. Bao [LOI] thi sua list.json roi "
          "chay lai. KHONG chay article_sources.py, KHONG web_search, KHONG tao task."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief cho vai di tim tin")
    # type= chay TRUOC choices: "--vai scout" (cron cu, tay quen) tu ve "finn".
    ap.add_argument("--vai", required=True, type=role.canonical_slug, choices=list(TOPIC))
    ap.add_argument("--lam-moi", action="store_true", help="Quet lai du cache con moi")
    ap.add_argument("--im", action="store_true")
    a = ap.parse_args()
    wd = workdir(a.vai)
    brief = {"finn": brief_scout, "nova": brief_nova, "vera": brief_market,
             "qinn": brief_qinn}[a.vai](wd, a.lam_moi, a.vai)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
