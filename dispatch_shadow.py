#!/usr/bin/env python3
"""dispatch_shadow.py — CHẠY BÓNG tự chọn tin (LOW-349).

Mỗi ngày chấm cho từng headline mà vai quét (Finn/Qinn/Vera/Nova) research ra:
Ông Chủ có chọn headline này không. KHÔNG chọn gì — chỉ ghi gợi ý rồi đo độ trùng
với lựa chọn thật, theo vai quét và theo loại tin. Loại tin nào trùng đủ cao thì
mới tính chuyện bật tự chọn cho riêng loại đó (ticket sau).

Giao designer nào KHÔNG đo ở đây (Ông Chủ 21/09/2026): đó chỉ là xếp hàng task —
tin benchmark model mặc định Ethan, còn lại luân phiên Dre/Kite — không phải gu.

Ba luật giữ cho số đo là số thật:
  - Gợi ý của một tin chỉ dùng thứ CÓ LÚC QUÉT: loại tin chuẩn
    (`story_type.standard_type`) và bậc điểm. Không đọc `picked` của chính tin đó.
  - Bảng học chỉ lấy từ các lượt quét TRƯỚC tin đó (theo `scanned_at`), nên lần
    chạy đầu chấm lùi được cả lịch sử mà không rò kết quả.
  - Gợi ý đóng băng trong `dispatch_shadow.jsonl` lúc chấm; kết quả thật đọc lại
    từ manifest mỗi lần báo cáo (Ông Chủ chọn muộn vẫn được tính).

Hai chỗ dữ liệu thô dễ đánh lừa:
  - Quét lại trong ngày tạo bản `_tHHMMSS` mới chứa lại chính các tin cũ, và Ông
    Chủ chỉ chọn trên bản mới nhất. Nên gộp theo link: một tin = một lần đếm,
    "được chọn" nếu được chọn ở bất kỳ bản nào.
  - Lượt quét mà cả ngày không chọn tin nào thường là Ông Chủ chưa xem, không
    phải chê cả lượt. Những tin đó không tính là "không chọn".

Đo trên lịch sử thật 21/09/2026 (79 manifest, hai brand): chỉ ĐIỂM của Finn đoán
được (80–89 được chọn 83%, 90+ 94%). Loại tin, nguồn và chữ trong headline không
hơn đoán mò, nên không dùng. Vera/Nova không chấm điểm, nên tin của họ chưa có gợi
ý chọn — báo cáo theo vai quét cho thấy điều đó mỗi ngày.

Không hiện gợi ý trong báo cáo quét: Ông Chủ thấy gợi ý thì dễ chọn theo, số đo
độ trùng sẽ ảo.

Dùng:
    venv/bin/python dispatch_shadow.py            # chấm tin mới + in báo cáo
    venv/bin/python dispatch_shadow.py --send     # ... và gửi topic Ada
"""
import argparse
import collections
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from html import escape as html_escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                              # noqa: E402
import role                                                  # noqa: E402
import scan_common                                           # noqa: E402
import state_paths                                           # noqa: E402
import story_type                                            # noqa: E402

VERSION = 1                       # tăng khi đổi thuật toán — mỗi dòng log ghi bản đã chấm nó
MANIFEST_GLOB = "*_candidates_*.json"                # cùng mẫu với cleanup.py

LEARN_WINDOW_DAYS = 60            # chỉ học 60 ngày gần nhất: gu có thể đổi
# Ô (loại tin, bậc điểm) cần ≥ 10 tin đã quyết mới tin tỉ lệ của ô. Đo trên lịch sử thật
# 21/09/2026: với 5 thì 4/5 may rủi đã qua 70% — dcgr ra 24 gợi ý chọn sai cả 24 (Vera/Nova
# không chấm điểm, mọi tin chung một ô); với 10 thì 0 gợi ý sai, blog chọn đúng 75% -> 84%.
MIN_PICK_SAMPLES = 10
PICK_RATE = 0.7                   # Ông Chủ đã chọn ≥ 70% số tin trong ô -> gợi ý chọn
DECISION_HOURS = 24               # tin chưa chọn sau 24h mới tính là "không chọn"
DECIDED = ("picked", "not_picked")

# Đủ điều kiện bật tự chọn (chỉ BÁO, script này không bật gì): trong READY_WINDOW lần
# gần nhất gợi ý chọn của loại tin, ≥ READY_AGREEMENT là tin Ông Chủ cũng chọn.
READY_WINDOW = 20
READY_MIN_SAMPLES = 10
READY_AGREEMENT = 0.9


def _as_int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return -1


def score_tier(score) -> str:
    """Cùng ranh giới bậc với báo cáo của Ada (`ada_prepare._tier`)."""
    s = _as_int(score)
    if s < 0:
        return "none"
    return "90+" if s >= 90 else "80-89" if s >= 80 else "70-79" if s >= 70 else "<70"


def _parse_time(v):
    try:
        t = datetime.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def load_scans(state: Path) -> list:
    """Mọi manifest quét của brand, cũ -> mới theo `scanned_at`. Không xếp theo mtime:
    approve_pick ghi ngược `picked` vào manifest nên mtime đổi mỗi lần chọn."""
    scans = []
    for p in state.glob(MANIFEST_GLOB):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"[canh bao] bo qua {p.name}: {e}", file=sys.stderr)
            continue
        at = _parse_time(d.get("scanned_at")) or datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
        # manifest cũ còn ghi slug vai cũ ("scout" = Finn, "market" = Vera)
        scan_role = role.canonical_slug(d.get("scan_role") or p.name.split("_")[0])
        scans.append({"manifest": p.name, "scan_role": scan_role, "scanned_at": at,
                      "items": d.get("items") or []})
    return sorted(scans, key=lambda s: (s["scanned_at"], s["manifest"]))


def story_key(item: dict) -> str:
    link = scan_common.standard_link(item.get("link") or "")
    return link or " ".join(str(item.get("title") or "").lower().split())


def gather_stories(scans: list) -> list:
    """Gộp mọi lần một tin xuất hiện thành MỘT tin: đặc trưng lấy từ lần đầu,
    được chọn nếu được chọn ở bất kỳ bản nào."""
    stories = {}
    for s in scans:
        for it in s["items"]:
            k = story_key(it)
            if not k:
                continue
            st = stories.get(k)
            if st is None:
                st = stories[k] = {
                    "key": k, "manifest": s["manifest"], "index": it.get("index"),
                    "scan_role": s["scan_role"], "scanned_at": s["scanned_at"],
                    "title": str(it.get("title") or "")[:90],
                    "category": story_type.standard_type(it.get("category")),
                    "score": it.get("score"), "picked": False}
            if it.get("picked"):
                st["picked"] = True
    return list(stories.values())


def _local_date(t: datetime) -> str:
    """Ngày theo giờ VN — lượt quét 06:00 VN là 23:00 UTC hôm trước."""
    return t.astimezone(scan_common.VN).date().isoformat()


def reviewed_days(stories: list) -> set:
    """{(vai quét, ngày VN)} có ít nhất một tin được chọn, tức Ông Chủ đã xem lượt đó."""
    return {(st["scan_role"], _local_date(st["scanned_at"])) for st in stories if st["picked"]}


def outcome(st: dict, reviewed: set, now: datetime) -> str:
    """picked | not_picked | pending (chưa đủ DECISION_HOURS) | not_reviewed (cả ngày không chọn gì)."""
    if st["picked"]:
        return "picked"
    if now - st["scanned_at"] < timedelta(hours=DECISION_HOURS):
        return "pending"
    if (st["scan_role"], _local_date(st["scanned_at"])) not in reviewed:
        return "not_reviewed"
    return "not_picked"


def learn(stories: list, before: datetime, reviewed: set, now: datetime) -> dict:
    """Tỉ lệ chọn từ các tin quét TRƯỚC `before` (trong LEARN_WINDOW_DAYS) đã có quyết định."""
    since = before - timedelta(days=LEARN_WINDOW_DAYS)
    by_cell = collections.defaultdict(lambda: [0, 0])      # (loại tin, bậc) -> [đã quyết, được chọn]
    by_tier = collections.defaultdict(lambda: [0, 0])
    for st in stories:
        if not since <= st["scanned_at"] < before:
            continue
        o = outcome(st, reviewed, now)
        if o not in DECIDED:
            continue
        tier = score_tier(st["score"])
        for cell in (by_cell[(st["category"], tier)], by_tier[tier]):
            cell[0] += 1
            cell[1] += int(o == "picked")
    return {"by_cell": by_cell, "by_tier": by_tier}


def suggest(st: dict, table: dict) -> dict:
    """Theo ô (loại tin, bậc điểm); ô thiếu mẫu thì theo bậc điểm; vẫn thiếu thì chưa gợi ý."""
    tier = score_tier(st["score"])
    seen, picked = table["by_cell"].get((st["category"], tier), (0, 0))
    basis = "category_tier"
    if seen < MIN_PICK_SAMPLES:
        (seen, picked), basis = table["by_tier"].get(tier, (0, 0)), "tier"
    pick = None if seen < MIN_PICK_SAMPLES else picked / seen >= PICK_RATE
    return {"suggested_pick": pick, "pick_basis": basis if pick is not None else "",
            "pick_rate": round(picked / seen, 2) if seen else None, "pick_samples": seen}


def load_log(path: Path) -> dict:
    """{story key: dòng gợi ý}. Dòng ĐẦU của mỗi tin thắng — gợi ý đã đóng băng."""
    out = {}
    if not path.exists():
        return out
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            d = json.loads(line)
        except ValueError:
            print(f"[canh bao] {path.name}:{n} khong phai JSON, bo qua", file=sys.stderr)
            continue
        if d.get("key"):
            out.setdefault(d["key"], d)
    return out


def score_new(stories: list, logged: dict, reviewed: set, now: datetime) -> list:
    """Chấm các tin chưa có trong log, cũ -> mới; mỗi tin chỉ học từ lượt quét trước nó."""
    tables, new = {}, []
    for st in sorted(stories, key=lambda s: s["scanned_at"]):
        if st["key"] in logged:
            continue
        at = st["scanned_at"]
        if at not in tables:
            tables[at] = learn(stories, at, reviewed, now)
        new.append({"key": st["key"], "manifest": st["manifest"], "index": st["index"],
                    "scan_role": st["scan_role"], "scanned_at": at.isoformat(),
                    "title": st["title"], "category": st["category"], "score": st["score"],
                    **suggest(st, tables[at]), "scored_at": now.isoformat(), "version": VERSION})
    return new


def _tally(rows: list) -> collections.Counter:
    t = collections.Counter()
    for r in rows:
        if r["outcome"] not in DECIDED:
            continue
        yes, s = r["outcome"] == "picked", r["suggested_pick"]
        t["decided"] += 1
        t["picked"] += yes
        if s is None:
            t["no_suggestion"] += 1
            continue
        t["suggested"] += bool(s)
        t["hit"] += bool(s) and yes                # gợi ý chọn và Ông Chủ cũng chọn
        t["picked_scored"] += yes
    return t


def _readiness(rows: list) -> dict:
    """Loại tin này đủ điều kiện bật tự chọn chưa. `rows` xếp cũ -> mới."""
    picks = [r for r in rows if r["outcome"] in DECIDED and r["suggested_pick"]][-READY_WINDOW:]
    ok = sum(r["outcome"] == "picked" for r in picks)
    return {"n": len(picks), "ok": ok,
            "ready": len(picks) >= READY_MIN_SAMPLES and ok >= READY_AGREEMENT * len(picks)}


def _is_miss(r: dict) -> bool:
    """Chỉ lỗi SẼ TỐN CÔNG khi tự chọn: gợi ý chọn một tin Ông Chủ đã bỏ. "Gợi ý bỏ mà
    Ông Chủ chọn" thì rẻ — Ông Chủ vẫn tự chọn được như bây giờ."""
    return r["outcome"] == "not_picked" and r["suggested_pick"] is True


def evaluate(logged: dict, stories: dict, reviewed: set, now: datetime, days: int) -> dict:
    """Ghép gợi ý đã đóng băng với kết quả THẬT hiện tại. Số tổng tính trong `days`
    ngày; độ sẵn sàng tính trên cả log (READY_WINDOW lần gần nhất)."""
    rows = []
    for key, s in logged.items():
        st = stories.get(key)
        if st is None:                               # manifest đã bị cleanup.py xoá
            continue
        rows.append({**s, "outcome": outcome(st, reviewed, now), "at": st["scanned_at"]})
    rows.sort(key=lambda r: r["at"])
    since = now - timedelta(days=days)
    recent = [r for r in rows if r["at"] >= since]
    by_role, by_category = collections.defaultdict(list), collections.defaultdict(list)
    for r in recent:
        by_role[r["scan_role"]].append(r)
    for r in rows:
        by_category[r["category"]].append(r)
    return {"total": _tally(recent),
            "roles": {k: _tally(rs) for k, rs in by_role.items()},
            "categories": {c: {"tally": _tally([r for r in rs if r["at"] >= since]),
                               "ready": _readiness(rs)} for c, rs in by_category.items()},
            "misses": [r for r in recent if _is_miss(r)][-5:][::-1],
            "pending": sum(r["outcome"] == "pending" for r in recent)}


def _ratio(a: int, b: int) -> str:
    return f"{a}/{b} ({round(100 * a / b)}%)" if b else "—"


def _status(r: dict) -> str:
    if r["ready"]:
        return "✅ đủ điều kiện tự chọn"
    if r["n"] < READY_MIN_SAMPLES:
        return f"chưa đủ mẫu ({r['n']}/{READY_MIN_SAMPLES})"
    return f"chưa khớp ({r['ok']}/{r['n']})"


def render(summary: dict, brand: str, days: int) -> str:
    t = summary["total"]
    L = [f"<b>Ada · chạy bóng tự chọn tin</b> ({html_escape(brand, quote=False)}, {days} ngày)",
         "Chưa chọn gì, chỉ so gợi ý với lựa chọn của bạn."]
    if not t["decided"]:
        L.append("Chưa có headline nào đã quyết để so.")
        return "\n".join(L)
    L += ["", f"<b>Tổng:</b> {t['decided']} headline đã quyết, bạn chọn {t['picked']}.",
          f"• Gợi ý chọn đúng {_ratio(t['hit'], t['suggested'])}.",
          f"• Bắt được {_ratio(t['hit'], t['picked_scored'])} headline bạn chọn."]
    if t["no_suggestion"]:
        L.append(f"• {t['no_suggestion']} headline chưa có gợi ý (thiếu dữ liệu).")
    L += ["", "<b>Theo vai quét</b> (bạn chọn · gợi ý chọn đúng · bắt được)"]
    for slug, rt in sorted(summary["roles"].items(), key=lambda kv: -kv[1]["decided"]):
        if rt["decided"]:
            L.append(f"• {html_escape(role.display_name(slug), quote=False)}: {rt['picked']}/{rt['decided']} · "
                     f"{_ratio(rt['hit'], rt['suggested'])} · {_ratio(rt['hit'], rt['picked_scored'])}")
    L += ["", "<b>Theo loại tin</b> (gợi ý chọn đúng · bắt được)"]
    for cat, c in sorted(summary["categories"].items(), key=lambda kv: -kv[1]["tally"]["decided"]):
        ct = c["tally"]
        if ct["decided"]:
            L.append(f"• {html_escape(cat or 'KHÁC', quote=False)}: {_ratio(ct['hit'], ct['suggested'])} · "
                     f"{_ratio(ct['hit'], ct['picked_scored'])} → {_status(c['ready'])}")
    if summary["misses"]:
        L += ["", "<b>Gợi ý chọn mà bạn đã bỏ</b> (gần nhất)"]
        for r in summary["misses"]:
            score = r["score"] if r["score"] is not None else "?"
            L.append(f"• {html_escape(r['title'][:70], quote=False)} "
                     f"({html_escape(r['category'] or 'KHÁC', quote=False)}, {score} điểm, "
                     f"{html_escape(role.display_name(r['scan_role']), quote=False)})")
    if summary["pending"]:
        L += ["", f"{summary['pending']} headline còn chờ bạn chọn, chưa tính."]
    return "\n".join(L)


def run(state: Path, now: datetime, days: int) -> tuple:
    """(số tin chấm mới, tóm tắt). Tách khỏi main để test chạy thẳng trên thư mục tạm."""
    stories = gather_stories(load_scans(state))
    reviewed = reviewed_days(stories)
    path = state / state_paths.DISPATCH_SHADOW_FILE
    logged = load_log(path)
    new = score_new(stories, logged, reviewed, now)
    if new:
        with open(path, "a", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in new)
        for r in new:
            logged[r["key"]] = r
    return len(new), evaluate(logged, {st["key"]: st for st in stories}, reviewed, now, days)


def send(text: str) -> bool:
    r = subprocess.run([sys.executable, str(ROOT / "publish.py"), "--to-env", "TELEGRAM_GROUP_ID",
                        "--thread-name", "ada", "--text", text],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"[LOI] gửi: {(r.stderr or r.stdout)[-300:]}", file=sys.stderr)
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Chạy bóng tự chọn tin: chấm gợi ý, đo độ trùng với Ông Chủ")
    ap.add_argument("--days", type=int, default=30, help="khung ngày của số tổng (mặc định 30)")
    ap.add_argument("--send", action="store_true", help="gửi báo cáo vào topic Ada")
    a = ap.parse_args()
    n, summary = run(env_load.state_dir(), datetime.now(timezone.utc), a.days)
    text = render(summary, env_load.brand_long(), a.days)
    print(f"chấm {n} tin mới\n\n{text}")
    if not a.send:
        return 0
    if not summary["total"]["decided"]:
        print("chưa có headline nào đã quyết, không gửi")
        return 0
    return 0 if send(text) else 1


if __name__ == "__main__":
    sys.exit(main())
