#!/usr/bin/env python3
"""quet_chuan_bi.py — BRIEF cho ba vai DI TIM TIN (Finn/scout, Nova/nova, Vera/market).

Truoc: cron giao task, vai tu chay script quet, tu `cat`/`read_file` tep JSON
40 muc, tu `grep`, tu `web_search` them, sua tep nop nhieu lan qua `patch`
(do 03-04/09/2026: Finn 21 tool call, Nova 22 va 9 web_search, Vera 14).
Gio: tep nay chay script quet (cache trong ngay), in MOT ban tom tat gon —
tung ung vien mot dong, muc BAT BUOC, khung tep nop — vai chi cham diem / tom
tat / viet y nghia vao MOT tep JSON roi chay quet_nop.py.

Thu muc lam viec: state/<brand>/quet/<vai>_<YYYYMMDD VN>/

Dung:
    venv/bin/python quet_chuan_bi.py --vai scout|nova|market [--lam-moi]
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
import bat_buoc                                              # noqa: E402

VN = timezone(timedelta(hours=7))
TOPIC = {"scout": "scout", "nova": "nova", "market": "market"}
CACHE_GIO = 3
# Tran bao cao cua Nova trong brief. Truoc 06/09/2026 la 12.000 va cat CAM
# LANG giua dong: do that o trang thai production (arena song + co moc cu de so
# hang) bao cao ra 13.635 ky tu, tuc LIVEBENCH va OPENROUTER USAGE bi nuot mat
# truoc khi Nova nhin thay — Nova khong biet hai bang do ton tai, chu khong
# phai "doc roi thay khong co gi". Do lai sau khi them 8 bang: 16.800 ky tu.
TRAN_BAO_CAO = 22000


def _cat(bao_cao: str, tran: int = TRAN_BAO_CAO) -> str:
    """Cat bao cao NHUNG noi ro la da cat — im lang thi vai tuong minh da doc het."""
    b = bao_cao.strip()
    if len(b) <= tran:
        return b
    return (b[:tran].rsplit("\n", 1)[0]
            + f"\n\n[!] BAO CAO BI CAT o {tran} ky tu, mat {len(b) - tran} ky tu "
              "cuoi. Cac bang phia duoi KHONG hien ra day — dung ket luan la "
              "'khong co gi'. Bao Ong Chu de nang tran.")


def workdir(vai: str) -> Path:
    wd = env_load.state_dir() / "quet" / f"{vai}_{datetime.now(VN).strftime('%Y%m%d')}"
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def _moi(p: Path) -> bool:
    return p.exists() and time.time() - p.stat().st_mtime < CACHE_GIO * 3600


def _chay(args: list, timeout=900) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable] + args, cwd=str(ROOT), capture_output=True,
                          text=True, timeout=timeout)


def _bat_buoc(vai_bb: str) -> list:
    L = []
    bb = bat_buoc.doc(vai_bb)
    if bb:
        L.append(f"## BẮT BUỘC đưa vào danh sách nộp ({len(bb)}) — thiếu thì script tự thêm và ghi chú "
                 "'vai bỏ sót' lên báo cáo cho Ông Chủ thấy; hãy tự đưa vào và chấm trung thực")
        for v in bb.values():
            link = bat_buoc.link_goi_y(v)
            L.append(f"- [{v.get('loai', '')}] {v.get('ten', '')[:90]} | {v.get('ghi_chu', '')[:60]}"
                     + (f" | {link[:100]}" if link else ""))
    else:
        L.append("## BẮT BUỘC: không có mục nào đang chờ")
    return L


def _bo_sung_bat_buoc(cs: list) -> int:
    """Muc BAT BUOC mang tu hom truoc ma scan hom nay khong con (loc 72h, chong
    trung) thi them vao cuoi candidates voi diem co hoc 0, de manifest_build
    doi chieu duoc link. 05/09: 4/8 muc "khong tim thay trong candidates",
    Finn mo 18 tool call roi block task."""
    co = {bat_buoc.chuan_link(c.get("link", "")) for c in cs}
    n = 0
    for v in bat_buoc.doc("scout").values():
        link = v.get("link", "")
        if not link or bat_buoc.chuan_link(link) in co:
            continue
        m = re.search(r"(\d+)\s*diem", v.get("ghi_chu", ""))
        try:
            tuoi = (datetime.now(timezone.utc)
                    - datetime.strptime(v.get("ngay", ""), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    ).total_seconds() / 3600
        except ValueError:
            tuoi = 0.0
        cs.append({"source": "bat_buoc", "title": v.get("ten", ""), "link": link, "discussion": "",
                   "points": int(m.group(1)) if m else 0, "comments": 0,
                   "via": bat_buoc.chuan_link(link).split("/")[0], "nguoi_dang": "",
                   "age_hours": tuoi, "score_recency": 0, "score_spread": 0, "score_partial": 0,
                   "source_median_points": 0, "image_url": None, "bat_buoc": True})
        n += 1
    return n


# ---- scout (Finn) -----------------------------------------------------------
def brief_scout(wd: Path, lam_moi: bool) -> str:
    cand = wd / "candidates.json"
    if lam_moi or not _moi(cand):
        r = _chay([str(ROOT / "scan_sources.py"), "--out", str(cand)])
        (wd / "scan.log").write_text((r.stderr or "") + (r.stdout or ""), encoding="utf-8")
        if r.returncode != 0 or not cand.exists():
            sys.exit(f"[LOI] scan_sources.py hong: {(r.stderr or '')[-400:]}")
    d = json.loads(cand.read_text(encoding="utf-8"))
    cs = d.get("candidates", [])
    bo_sung = _bo_sung_bat_buoc(cs)
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
                 f" | {c.get('source', '')} {c.get('points', 0)}p/{c.get('comments', 0)}c | {c.get('age_hours', 0):.0f}h"
                 f" | {c.get('title', '')[:110]} | {c.get('link', '')}")
        if c.get("summary") or c.get("description"):
            L.append(f"     {str(c.get('summary') or c.get('description'))[:200]}")
    L += [""] + _bat_buoc("scout")
    L += ["", f"## Viết đánh giá vào: {wd}/picks.json — đủ mọi mục BẮT BUỘC + TỐI ĐA 8 tin điểm cao nhất ngoài đó",
          json.dumps([{"k": "<số thứ tự #k trong danh sách (thay cho link, script tự lấy link)>",
                       "category": "<ARXIV | MODEL | LAB | INFRA | TOOL | ENGINEERING | BUSINESS | RESEARCH | SECURITY>",
                       "score_technical": "<0-30: có số liệu đo/mã nguồn/paper thì cao>",
                       "score_relevance": "<0-20: thuộc 5 nhóm (model mới, M&A big tech, arXiv/X/Reddit nổi, use case thật, tin lai); "
                                          "funding round/drama/dự đoán thì trừ nặng>",
                       "score_reason": "<1 câu vì sao điểm này>",
                       "summary_vi": "<MỘT mệnh đề ≤ 15 từ, dữ kiện thuần; chỉ làm ngữ cảnh cho vai viết, KHÔNG lên báo cáo>"}], ensure_ascii=False, indent=1),
          "Điểm tổng = điểm cơ học (script) + technical + relevance. Không tin nào ≥ 50 điểm thì chạy bước 3 với "
          "--khong-co (script gửi dòng 'hôm nay không có gì' kèm số tin đã quét).",
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python quet_nop.py --vai scout",
          "Script tự ghép manifest (đối chiếu số thứ tự, cộng điểm, đánh số), tự thêm mục bắt buộc còn thiếu, viết báo cáo đánh số, "
          "gửi lên topic. Báo [LOI] thì sửa picks.json rồi chạy lại. KHÔNG cat/grep candidates.json, KHÔNG "
          "web_search, KHÔNG chạy manifest_build/publish tay, KHÔNG tạo task kanban."]
    return "\n".join(L)


# ---- nova ---------------------------------------------------------------------
def brief_nova(wd: Path, lam_moi: bool) -> str:
    rep = wd / "scan_models.txt"
    if lam_moi or not _moi(rep):
        r = _chay([str(ROOT / "scan_models.py"), "--ngay", "7", "--top", "10",
                   "--khong-bat-buoc"], timeout=1200)
        rep.write_text((r.stdout or "") + "\n[stderr]\n" + (r.stderr or "")[-1500:], encoding="utf-8")
    bao_cao = rep.read_text(encoding="utf-8").split("\n[stderr]\n")[0]
    mh = {}
    try:
        mh = json.loads((env_load.state_dir() / "model_health.json").read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        pass
    chet = [k for k, v in (mh.get("models") or {}).items() if not v.get("ok")]
    L = [f"# NOVA — QUÉT XONG {datetime.now(VN).strftime('%d/%m %H:%M')} VN (scan_models.py --ngay 7 --top 10)",
         "Báo cáo của script (đọc ở đây, KHÔNG chạy lại, KHÔNG web_search):", "", _cat(bao_cao), ""]
    L.append("Model đội đã đo và đang chết/loại (không đề xuất lại như tin mới): "
             + (", ".join(chet) if chet else "không có") +
             ". Đã loại có lý do: gemini-3.7-flash (cache 0%, đắt 44 lần), kimi-k3 (không tắt suy luận), grok "
             "(cache 0%), nemotron :free (mất dấu). Giá ở bảng coding là NIÊM YẾT, không phải thực đo.")
    L += [""] + _bat_buoc("nova")
    L += ["", f"## Viết danh sách vào: {wd}/ds.json — MỘT mục cho MỖI mục bắt buộc (gộp các bảng của cùng model), "
          "tiêu đề phải chứa ĐÚNG tên model như script in",
          json.dumps([{"title": "<Tên model đúng như script in + ý chính, có dấu>",
                       "link": "<bỏ trống với mục BẮT BUỘC (script tự lấy link trang model/bảng); "
                               "chỉ ghi URL thật khi là tin ngoài danh sách>",
                       "summary_vi": "<MỘT mệnh đề ≤ 15 từ: giá vào/ra mỗi triệu token hoặc hạng bảng; chỉ làm ngữ cảnh "
                                     "cho vai viết, KHÔNG lên báo cáo>",
                       "source_note": "<bảng/nguồn + ngày>"}], ensure_ascii=False, indent=1),
          "Xếp thứ tự: vào top 3 bảng lớn (text, WebDev, coding, trí tuệ, ECI, agentic) lên đầu; kế đến là leo hạng "
          "ở bảng khó bão hoà (HLE, ARC-AGI-2, Terminal-Bench). Không có gì đáng lên kênh thì "
          "chạy bước 3 với --khong-co.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python quet_nop.py --vai nova",
          "Script tự ghi manifest đánh số, kiểm mục bắt buộc, viết báo cáo, gửi topic. Báo [LOI] thì sửa ds.json "
          "rồi chạy lại. KHÔNG chạy nguon_bai.py (approve_service làm lúc Ông Chủ chọn), KHÔNG tạo task."]
    return "\n".join(L)


# ---- market (Vera) ------------------------------------------------------------
def brief_market(wd: Path, lam_moi: bool) -> str:
    q = wd / "quet.json"
    if lam_moi or not _moi(q):
        r = _chay([str(ROOT / "scan_business.py"), "--gio", "30", "--out", str(q)])
        (wd / "scan.log").write_text((r.stderr or "") + (r.stdout or ""), encoding="utf-8")
        if r.returncode != 0 or not q.exists():
            sys.exit(f"[LOI] scan_business.py hong: {(r.stderr or '')[-400:]}")
    d = json.loads(q.read_text(encoding="utf-8"))
    tin = d.get("tin_moi", [])
    L = [f"# VERA — QUÉT XONG {datetime.now(VN).strftime('%d/%m %H:%M')} VN: {len(tin)} tin trong 30h "
         f"(tổng quét {d.get('tong_quet', '?')}, {d.get('tin_watchlist', 0)} tin watchlist)",
         "Mỗi dòng: #k | [W]=watchlist (LUÔN phải đưa) | ngày | số báo: báo | tiêu đề | link"]
    for k, t in enumerate(tin, 1):
        L.append(f"#{k} | {'[W]' if t.get('watchlist') else '   '} | {t.get('ngay', '')} | "
                 f"{t.get('so_bao', 1)} báo: {', '.join(t.get('cac_bao', [])[:3]) or t.get('toa_soan', '')}"
                 f" | {t.get('tieu_de', '')[:110]} | {t.get('link', '')}")
    L += [""] + _bat_buoc("market")
    L += ["", f"## Viết danh sách vào: {wd}/ds.json — tin có HỆ QUẢ (IPO, thâu tóm, hạ tầng, chính sách, lao "
          "động, kiện tụng, cược lớn), kèm mức chắc chắn theo số báo; bỏ giá cổ phiếu trong ngày, PR sản phẩm",
          json.dumps([{"k": "<số thứ tự #k trong danh sách — script tự lấy link và số báo, KHÔNG chép URL>",
                       "title": "<HEADLINE một dòng: chủ thể + việc + con số, tiếng Việt có dấu; đây là thứ DUY NHẤT Ông Chủ đọc>",
                       "summary_vi": "<MỘT mệnh đề ≤ 15 từ vì sao đáng quan tâm; chỉ làm ngữ cảnh cho vai viết, "
                                     "KHÔNG lên báo cáo>"}], ensure_ascii=False, indent=1),
          "Mọi tin [W] phải có mặt. Không có gì đáng lên kênh thì chạy bước 3 với --khong-co.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python quet_nop.py --vai market",
          "Script tự ghi manifest đánh số, tự thêm mục bắt buộc còn thiếu, viết báo cáo, gửi topic. Báo [LOI] thì "
          "sửa ds.json rồi chạy lại. KHÔNG chạy nguon_bai.py, KHÔNG web_search, KHÔNG tạo task."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief cho vai di tim tin")
    ap.add_argument("--vai", required=True, choices=list(TOPIC))
    ap.add_argument("--lam-moi", action="store_true", help="Quet lai du cache con moi")
    ap.add_argument("--im", action="store_true")
    a = ap.parse_args()
    wd = workdir(a.vai)
    brief = {"scout": brief_scout, "nova": brief_nova, "market": brief_market}[a.vai](wd, a.lam_moi)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
