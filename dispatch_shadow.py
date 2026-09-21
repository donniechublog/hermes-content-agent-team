#!/usr/bin/env python3
"""dispatch_shadow.py — CHẠY BÓNG tự giao việc (LOW-349).

Mỗi ngày chấm cho từng tin quét hai gợi ý: có nên chọn không, và giao designer
nào (Ethan / Dre / Kite). KHÔNG giao gì — chỉ ghi gợi ý rồi đo độ trùng với lựa
chọn thật của Ông Chủ, theo từng loại tin. Loại tin nào trùng đủ cao thì mới
tính chuyện bật tự giao cho riêng loại đó (ticket sau).

Ba luật giữ cho số đo là số thật:
  - Gợi ý của một tin chỉ dùng thứ CÓ LÚC QUÉT: loại tin chuẩn
    (`story_type.standard_type`), bậc điểm và vai quét. Không đọc
    `picked`/`assignments` của chính tin đó.
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

Không hiện gợi ý trong báo cáo quét: Ông Chủ thấy "gợi ý: Dre" thì dễ chọn theo,
số đo độ trùng sẽ ảo.

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

# ---- có chọn tin không --------------------------------------------------------
LEARN_WINDOW_DAYS = 60            # chỉ học 60 ngày gần nhất: gu có thể đổi
# Ô (loại tin, bậc điểm) cần ≥ 10 tin đã quyết mới tin tỉ lệ của ô. Đo trên lịch sử thật
# 21/09/2026: với 5 thì 4/5 may rủi đã qua 70% — dcgr ra 24 gợi ý chọn sai cả 24 (Vera/Nova
# không chấm điểm, mọi tin chung một ô); với 10 thì 0 gợi ý sai, blog chọn đúng 75% -> 84%.
MIN_PICK_SAMPLES = 10
PICK_RATE = 0.7                   # Ông Chủ đã chọn ≥ 70% số tin trong ô -> gợi ý chọn
DECISION_HOURS = 24               # tin chưa chọn sau 24h mới tính là "không chọn"
DECIDED = ("picked", "not_picked")

# ---- giao designer nào ---------------------------------------------------------
MIN_DESIGNER_SAMPLES = 3          # (vai quét, loại tin) hoặc loại tin cần ≥ 3 lần giao thật mới theo lịch sử
# Bảng khởi đầu, suy từ khả năng từng vai trong role.py (21/09/2026) — CHƯA phải gu
# của Ông Chủ; lịch sử giao thật đè lên khi đủ MIN_DESIGNER_SAMPLES:
#   Kite   tin kiến thức/giải thích (vẽ vector, chỉ cần 1 ảnh thật cho bìa). BENCHMARK
#          cũng về Kite: ảnh chính là bảng xếp hạng, mà card của Ethan không cho chart
#          đứng một mình (`chart_don=False`).
#   Dre    INFRA: datacenter, nhà máy thường nhiều ảnh (Dre cần ≥ 6 ảnh thật).
#   Ethan  tin xoay quanh một hãng (logo/founder/trụ sở); điểm cao thì lên Dre.
PRIOR_DESIGNER = {"ARXIV": "kite", "TOOL": "kite", "BENCHMARK": "kite", "INFRA": "dre",
                  "MODEL": "ethan", "BUSINESS": "ethan", "M&A": "ethan", "LAB": "ethan",
                  "SECURITY": "ethan"}
UPGRADE_TO_DRE_SCORE = 90

# ---- đủ điều kiện bật tự giao (chỉ BÁO, script này không bật gì) ------------------
READY_WINDOW = 20                 # xét 20 lần gần nhất của loại tin
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
    được chọn nếu được chọn ở bất kỳ bản nào, designer là mọi vai đã được giao."""
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
                    "score": it.get("score"), "picked": False, "designers": set()}
            if it.get("picked"):
                st["picked"] = True
            for a in it.get("assignments") or []:
                if a.get("image_role"):
                    st["designers"].add(role.canonical_slug(a["image_role"]))
    return list(stories.values())


def _local_date(t: datetime) -> str:
    """Ngày theo giờ VN — lượt quét 05:00 VN là 22:00 UTC hôm trước."""
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
    """Bảng học từ các tin quét TRƯỚC `before` (trong LEARN_WINDOW_DAYS) đã có quyết định."""
    since = before - timedelta(days=LEARN_WINDOW_DAYS)
    by_cell = collections.defaultdict(lambda: [0, 0])      # (loại tin, bậc) -> [đã quyết, được chọn]
    by_tier = collections.defaultdict(lambda: [0, 0])
    designers = collections.defaultdict(collections.Counter)            # loại tin -> designer
    designers_by_role = collections.defaultdict(collections.Counter)    # (vai quét, loại tin) -> designer
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
        for d in st["designers"]:
            designers[st["category"]][d] += 1
            designers_by_role[(st["scan_role"], st["category"])][d] += 1
    return {"by_cell": by_cell, "by_tier": by_tier, "designers": designers,
            "designers_by_role": designers_by_role}


def prior_designer(category: str, score, available: set):
    d = PRIOR_DESIGNER.get(category, role.DEFAULT_IMAGE)
    if d == "ethan" and _as_int(score) >= UPGRADE_TO_DRE_SCORE:
        d = "dre"
    if d in available:
        return d
    return role.DEFAULT_IMAGE if role.DEFAULT_IMAGE in available else None


def suggest_designer(category: str, score, table: dict, available: set, scan_role: str = "") -> tuple:
    """(designer, "history" | "prior"). Học theo (vai quét, loại tin) trước, rồi mới
    theo loại tin: cùng là MODEL nhưng tin của Nova (tin tức) hay về Ethan, của Finn
    (kỹ thuật) hay về Dre/Kite. Đo trên lịch sử blog 21/09/2026: tách theo vai quét
    nâng độ trùng designer từ 43% lên 53%. Hoà phiếu thì ưu tiên bảng khởi đầu."""
    prior = prior_designer(category, score, available)
    for counts in (table.get("designers_by_role", {}).get((scan_role, category), {}),
                   table["designers"].get(category, {})):
        counts = {d: n for d, n in counts.items() if d in available}
        if sum(counts.values()) >= MIN_DESIGNER_SAMPLES:
            best = max(counts.values())
            top = sorted(d for d, n in counts.items() if n == best)
            return (prior if prior in top else top[0]), "history"
    return prior, "prior"


def suggest(st: dict, table: dict, available: set) -> dict:
    tier = score_tier(st["score"])
    seen, picked = table["by_cell"].get((st["category"], tier), (0, 0))
    basis = "category_tier"
    if seen < MIN_PICK_SAMPLES:
        (seen, picked), basis = table["by_tier"].get(tier, (0, 0)), "tier"
    pick = None if seen < MIN_PICK_SAMPLES else picked / seen >= PICK_RATE
    designer, designer_basis = suggest_designer(st["category"], st["score"], table, available,
                                                st.get("scan_role", ""))
    return {"suggested_pick": pick, "pick_basis": basis if pick is not None else "",
            "pick_rate": round(picked / seen, 2) if seen else None, "pick_samples": seen,
            "suggested_designer": designer, "designer_basis": designer_basis}


def designers_available() -> set:
    """Designer có profile trong brand này — cùng phép kiểm của
    `approve_dispatch.standard_assignee` (không import nó: kéo theo cả Telegram lẫn
    kanban). Máy không có HERMES_HOME (máy dev, test) thì không lọc."""
    profiles = env_load.hermes_home() / "profiles"
    if not profiles.is_dir():
        return set(role.NAME_ROLE_IMAGE)
    return {d for d in role.NAME_ROLE_IMAGE if (profiles / d).is_dir()}


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


def score_new(stories: list, logged: dict, reviewed: set, available: set, now: datetime) -> list:
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
                    **suggest(st, tables[at], available),
                    "scored_at": now.isoformat(), "version": VERSION})
    return new


def _tally(rows: list) -> collections.Counter:
    """Designer đo ĐỘC LẬP với gợi ý chọn: mọi tin Ông Chủ đã chọn đều có gợi ý designer."""
    t = collections.Counter()
    for r in rows:
        if r["outcome"] not in DECIDED:
            continue
        yes, s = r["outcome"] == "picked", r["suggested_pick"]
        t["decided"] += 1
        t["picked"] += yes
        if yes and r["suggested_designer"] and r["actual_designers"]:
            t["designer_n"] += 1
            t["designer_ok"] += r["suggested_designer"] in r["actual_designers"]
        if s is None:
            t["no_suggestion"] += 1
            continue
        t["suggested"] += bool(s)
        t["hit"] += bool(s) and yes                # gợi ý chọn và Ông Chủ cũng chọn
        t["picked_scored"] += yes
    return t


def _readiness(rows: list) -> dict:
    """Loại tin này đủ điều kiện bật tự giao chưa: trong READY_WINDOW lần gần nhất,
    gợi ý chọn đúng và designer trùng đều ≥ READY_AGREEMENT. `rows` xếp cũ -> mới."""
    decided = [r for r in rows if r["outcome"] in DECIDED]
    picks = [r for r in decided if r["suggested_pick"]][-READY_WINDOW:]
    des = [r for r in decided if r["outcome"] == "picked" and r["suggested_designer"]
           and r["actual_designers"]][-READY_WINDOW:]
    pick_ok = sum(r["outcome"] == "picked" for r in picks)
    designer_ok = sum(r["suggested_designer"] in r["actual_designers"] for r in des)
    enough = len(picks) >= READY_MIN_SAMPLES and len(des) >= READY_MIN_SAMPLES
    ready = (enough and pick_ok >= READY_AGREEMENT * len(picks)
             and designer_ok >= READY_AGREEMENT * len(des))
    return {"ready": ready, "enough": enough, "pick_n": len(picks), "pick_ok": pick_ok,
            "designer_n": len(des), "designer_ok": designer_ok}


def _is_miss(r: dict) -> bool:
    """Chỉ lỗi SẼ TỐN CÔNG khi tự giao: chọn nhầm tin Ông Chủ bỏ, hoặc giao sai designer.
    "Gợi ý bỏ mà Ông Chủ chọn" thì rẻ — Ông Chủ vẫn tự chọn được như bây giờ."""
    if r["outcome"] not in DECIDED:
        return False
    if r["outcome"] == "not_picked":
        return r["suggested_pick"] is True
    return (bool(r["actual_designers"]) and bool(r["suggested_designer"])
            and r["suggested_designer"] not in r["actual_designers"])


def _describe_miss(r: dict) -> str:
    mine = role.display_name(r["suggested_designer"]) if r["suggested_designer"] else "?"
    if r["outcome"] == "not_picked":
        return f"gợi ý chọn → {mine}, bạn bỏ"
    return f"gợi ý {mine}, bạn giao {'/'.join(role.display_name(d) for d in r['actual_designers'])}"


def evaluate(logged: dict, stories: dict, reviewed: set, now: datetime, days: int) -> dict:
    """Ghép gợi ý đã đóng băng với kết quả THẬT hiện tại. Số tổng tính trong `days`
    ngày; độ sẵn sàng tính trên cả log (READY_WINDOW lần gần nhất)."""
    rows = []
    for key, s in logged.items():
        st = stories.get(key)
        if st is None:                               # manifest đã bị cleanup.py xoá
            continue
        rows.append({**s, "outcome": outcome(st, reviewed, now),
                     "actual_designers": sorted(st["designers"]), "at": st["scanned_at"]})
    rows.sort(key=lambda r: r["at"])
    since = now - timedelta(days=days)
    recent = [r for r in rows if r["at"] >= since]
    by_category = collections.defaultdict(list)
    for r in rows:
        by_category[r["category"]].append(r)
    return {"total": _tally(recent),
            "categories": {c: {"tally": _tally([r for r in rs if r["at"] >= since]),
                               "ready": _readiness(rs)} for c, rs in by_category.items()},
            "misses": [r for r in recent if _is_miss(r)][-5:][::-1],
            "pending": sum(r["outcome"] == "pending" for r in recent)}


def _ratio(a: int, b: int) -> str:
    return f"{a}/{b} ({round(100 * a / b)}%)" if b else "—"


def _status(r: dict) -> str:
    if r["ready"]:
        return "✅ đủ điều kiện tự giao"
    lacking = [f"{name} {n}/{READY_MIN_SAMPLES}" for name, n in
               (("gợi ý chọn", r["pick_n"]), ("designer", r["designer_n"])) if n < READY_MIN_SAMPLES]
    if lacking:
        return "chưa đủ mẫu: " + ", ".join(lacking)
    return (f"chưa khớp (chọn đúng {r['pick_ok']}/{r['pick_n']}, "
            f"designer {r['designer_ok']}/{r['designer_n']})")


def render(summary: dict, brand: str, days: int) -> str:
    t = summary["total"]
    L = [f"<b>Ada · chạy bóng tự giao việc</b> ({html_escape(brand, quote=False)}, {days} ngày)",
         "Chưa giao gì, chỉ so gợi ý với lựa chọn của bạn."]
    if not t["decided"]:
        L.append("Chưa có tin nào đã quyết để so.")
        return "\n".join(L)
    L += ["", f"<b>Tổng:</b> {t['decided']} tin đã quyết, bạn chọn {t['picked']}.",
          f"• Gợi ý chọn đúng {_ratio(t['hit'], t['suggested'])}.",
          f"• Bắt được {_ratio(t['hit'], t['picked_scored'])} tin bạn chọn.",
          f"• Designer trùng {_ratio(t['designer_ok'], t['designer_n'])}."]
    if t["no_suggestion"]:
        L.append(f"• {t['no_suggestion']} tin chưa có gợi ý (thiếu dữ liệu).")
    L += ["", "<b>Theo loại tin</b> (chọn đúng · bắt được · designer trùng)"]
    for cat, c in sorted(summary["categories"].items(), key=lambda kv: -kv[1]["tally"]["decided"]):
        ct = c["tally"]
        if not ct["decided"]:
            continue
        L.append(f"• {html_escape(cat or 'KHÁC', quote=False)}: {_ratio(ct['hit'], ct['suggested'])} · "
                 f"{_ratio(ct['hit'], ct['picked_scored'])} · "
                 f"{_ratio(ct['designer_ok'], ct['designer_n'])} → {_status(c['ready'])}")
    if summary["misses"]:
        L += ["", "<b>Gợi ý sai gần nhất</b> (chọn nhầm hoặc sai designer)"]
        for r in summary["misses"]:
            score = r["score"] if r["score"] is not None else "?"
            L.append(f"• {html_escape(r['title'][:60], quote=False)} "
                     f"({html_escape(r['category'] or 'KHÁC', quote=False)}, {score}): {_describe_miss(r)}")
    if summary["pending"]:
        L += ["", f"{summary['pending']} tin còn chờ bạn chọn, chưa tính."]
    return "\n".join(L)


def run(state: Path, now: datetime, available: set, days: int) -> tuple:
    """(số tin chấm mới, tóm tắt). Tách khỏi main để test chạy thẳng trên thư mục tạm."""
    stories = gather_stories(load_scans(state))
    reviewed = reviewed_days(stories)
    path = state / state_paths.DISPATCH_SHADOW_FILE
    logged = load_log(path)
    new = score_new(stories, logged, reviewed, available, now)
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
    ap = argparse.ArgumentParser(description="Chạy bóng tự giao việc: chấm gợi ý, đo độ trùng với Ông Chủ")
    ap.add_argument("--days", type=int, default=30, help="khung ngày của số tổng (mặc định 30)")
    ap.add_argument("--send", action="store_true", help="gửi báo cáo vào topic Ada")
    a = ap.parse_args()
    n, summary = run(env_load.state_dir(), datetime.now(timezone.utc), designers_available(), a.days)
    text = render(summary, env_load.brand_long(), a.days)
    print(f"chấm {n} tin mới\n\n{text}")
    if not a.send:
        return 0
    if not summary["total"]["decided"]:
        print("chưa có tin nào đã quyết, không gửi")
        return 0
    return 0 if send(text) else 1


if __name__ == "__main__":
    sys.exit(main())
