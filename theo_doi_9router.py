#!/usr/bin/env python3
"""theo_doi_9router.py — nhật ký 9router theo NGÀY: model, token, chi phí, lật
model, lỗi, khoá API và IP máy gọi. Nguồn sự thật cho Ada khi bàn chi phí.

Vì sao có tệp này (05/09):
  - `usage_audit.py` chỉ in một bảng gộp N giờ rồi quên; không có lịch sử để
    Ada so ngày này với ngày trước, không thấy giờ nào đốt, không thấy chuỗi
    lật model (v4-flash → deepseek-chat) đã âm thầm ăn tiền suốt 2 tuần.
  - 9router KHÔNG ghi IP máy gọi: `usageHistory.meta` luôn `{}`, cột IP không
    có, `custom-server.js` tính `x-9r-real-ip` rồi chỉ dùng cho rate-limit.
    Mà 9router đang bind 0.0.0.0 (LAN 192.168.1.61 + netbird) — ai trong mạng
    cũng gọi được bằng khoá chung. Nên IP phải tự bắt ở tầng socket.

HAI VIỆC, hai lệnh:

  1. `--canh`  : watcher chạy nền (systemd user, xem hermes/systemd/). Mỗi 2s
                 đọc bảng TCP (psutil, không cần root), kết nối MỚI tới cổng
                 20128 → ghi một dòng vào state/9router/ket_noi_<ngày>.jsonl
                 {t, ip, port}. Chỉ IP + thời điểm, không đọc nội dung.
  2. `--ngay`  : chốt nhật ký một ngày VN (mặc định hôm qua): đọc usageHistory
                 CHỈ ĐỌC + ket_noi jsonl → state/9router/nhat_ky/9router_<ngày>
                 .json + .md. Chạy lại bao nhiêu lần cũng ra y hệt (idempotent),
                 nên cả hai brand gọi từ nhat_ky_daily.sh đều được.

Giới hạn thật thà: IP ghi theo KẾT NỐI, không theo request (Hermes dùng httpx
keep-alive, một kết nối chở nhiều request). Muốn tách request theo máy gọi phải
cấp khoá 9router riêng cho từng máy — xem mục "Điểm mù" trong README.

Dùng:
    venv/bin/python theo_doi_9router.py                 # chốt hôm qua, in .md
    venv/bin/python theo_doi_9router.py --ngay 2026-09-04
    venv/bin/python theo_doi_9router.py --ngay 2026-09-04 --gui        # tóm tắt + link → topic analyst
    venv/bin/python theo_doi_9router.py --ngay 2026-09-04 --canh-bao   # chỉ gửi khi có chuyện
    venv/bin/python theo_doi_9router.py --canh          # watcher, chạy mãi
"""
import argparse
import collections
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import publish                                               # noqa: E402

VN = timezone(timedelta(hours=7))
DB = Path(os.environ.get("ROUTER_DB", str(Path.home() / ".9router" / "db" / "data.sqlite")))
CONG = int(os.environ.get("ROUTER_PORT", "20128"))
# 9router dùng CHUNG cho mọi brand → nhật ký nằm ngoài state/<brand>/.
THU_MUC = ROOT / "state" / "9router"
NHAT_KY = THU_MUC / "nhat_ky"
# Hai request cách nhau dưới ngưỡng này mà khác model → coi là một lần lật
# (Hermes fallback ngay giữa lượt, 2 retry cách 2–3s).
GIAY_LAT = 120
# Cặp (chính → dự phòng) là fallback THẬT của Hermes. Các cặp khác đổi model liên
# tiếp phần lớn chỉ là vai chạy song song (designer glm xen writer deepseek) —
# 9router không ghi session nên không tách được, chỉ đếm để tham khảo.
FALLBACK_THAT = {("deepseek-v4-flash", "deepseek-chat")}
LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
# Phiên "rỗng": provider trả ok nhưng gần như không có chữ dù prompt lớn — model
# đốt ngân sách vào suy luận rồi trả về trống (đã đo 3/24 trên deepseek).
RONG_OUT_MAX = 5
RONG_PROMPT_MIN = 1000
# Mọi HERMES_HOME đang chạy (per-brand) → $ theo vai gộp cả hai brand.
HERMES_HOMES = sorted(Path.home().glob(".hermes-*"))
DRAFTS = ROOT / "drafts"
# Link trong tin Telegram → nhat_ky_web.py (netbird IP để điện thoại mở được
# không cần DNS). Đổi bằng biến môi trường NHAT_KY_URL.
WEB_URL = os.environ.get("NHAT_KY_URL", "http://100.87.121.46:9130").rstrip("/")


# ---------------------------------------------------------------- thời gian
def _cua_so_utc(ngay: str) -> tuple[str, str]:
    """Ngày VN → hai mốc ISO 'Z' đúng định dạng 9router lưu (có 'T', 'Z')."""
    d0 = datetime.strptime(ngay, "%Y-%m-%d").replace(tzinfo=VN)
    d1 = d0 + timedelta(days=1)
    f = "%Y-%m-%dT%H:%M:%S.000Z"
    return d0.astimezone(timezone.utc).strftime(f), d1.astimezone(timezone.utc).strftime(f)


def _gio_vn(ts: str) -> int:
    return datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(VN).hour


def _giay(ts: str) -> float:
    return datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()


def _hhmm(ts: str) -> str:
    return datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(VN).strftime("%H:%M:%S")


# ---------------------------------------------------------------- 9router DB
def _ten_bang(con) -> tuple[dict, dict]:
    """apiKey → tên client; connectionId → 'tên (prefix)'. Đọc ngay từ 9router,
    không hardcode: khoá/kết nối đổi trên dashboard là tự theo."""
    khoa, ket_noi = {}, {}
    try:
        for _id, key, name, *_ in con.execute("select id, key, name from apiKeys"):
            khoa[key] = name or key[-8:]
    except sqlite3.Error:
        pass
    try:
        for cid, provider, name, data in con.execute("select id, provider, name, data from providerConnections"):
            try:
                pre = (json.loads(data or "{}").get("providerSpecificData") or {}).get("prefix") or provider
            except Exception:                                # noqa: BLE001
                pre = provider
            ket_noi[cid] = f"{name or provider} ({pre})"
    except sqlite3.Error:
        pass
    return khoa, ket_noi


def doc_ngay(ngay: str) -> dict:
    """Gom usageHistory của một ngày VN thành số liệu. Không LLM, không ghi DB."""
    if not DB.exists():
        return {"ngay": ngay, "loi_doc": f"không thấy CSDL 9router: {DB}"}
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    khoa_ten, kn_ten = _ten_bang(con)
    t0, t1 = _cua_so_utc(ngay)
    rows = con.execute(
        "select timestamp, provider, model, connectionId, apiKey, status, promptTokens, completionTokens, cost, tokens "
        "from usageHistory where timestamp >= ? and timestamp < ? order by timestamp", (t0, t1)).fetchall()

    def moi():
        return {"req": 0, "prompt": 0, "cache": 0, "out": 0, "usd": 0.0, "loi": 0}

    tong = moi()
    theo_model = collections.defaultdict(moi)
    theo_khoa = collections.defaultdict(moi)
    theo_gio = collections.defaultdict(moi)
    loi = collections.Counter()
    top = []
    lat = collections.Counter()
    lat_vi_du = []
    truoc = None                                             # (giây, model)
    rong = collections.Counter()
    rong_vi_du = []
    for ts, provider, model, cid, ak, status, ptok, ctok, cost, tok in rows:
        if (status in (None, "ok")) and (ctok or 0) <= RONG_OUT_MAX and (ptok or 0) >= RONG_PROMPT_MIN:
            rong[model] += 1
            if len(rong_vi_du) < 5:
                rong_vi_du.append(f"{_hhmm(ts)} {model} {ptok:,} prompt → {ctok or 0} out")
        try:
            t = json.loads(tok or "{}")
        except Exception:                                    # noqa: BLE001
            t = {}
        cache = int(t.get("cached_tokens") or 0)
        nhan = f"{model} @ {kn_ten.get(cid, provider or '?')}"
        for a in (tong, theo_model[nhan], theo_khoa[khoa_ten.get(ak, ak or "?")], theo_gio[_gio_vn(ts)]):
            a["req"] += 1
            a["prompt"] += ptok or 0
            a["cache"] += cache
            a["out"] += ctok or 0
            a["usd"] += cost or 0
            if status and status != "ok":
                a["loi"] += 1
        if status and status != "ok":
            loi[f"{model}: {status}"] += 1
        top.append((ptok or 0, _hhmm(ts), model, cache, cost or 0))
        g = _giay(ts)
        if truoc and truoc[1] != model and g - truoc[0] <= GIAY_LAT:
            lat[f"{truoc[1]} → {model}"] += 1
            if len(lat_vi_du) < 6:
                lat_vi_du.append(f"{_hhmm(ts)} {truoc[1]} → {model} (+{g - truoc[0]:.0f}s)")
        truoc = (g, model)

    def pct(a):
        return round(a["cache"] / a["prompt"] * 100, 1) if a["prompt"] else 0.0

    def gon(d):
        return {k: {**v, "usd": round(v["usd"], 4), "cache_pct": pct(v)} for k, v in d.items()}

    return {
        "ngay": ngay, "cua_so_utc": [t0, t1],
        "tong": {**tong, "usd": round(tong["usd"], 4), "cache_pct": pct(tong)},
        "theo_model": dict(sorted(gon(theo_model).items(), key=lambda kv: -kv[1]["usd"])),
        "theo_khoa": gon(theo_khoa),
        "theo_gio": {str(k): v for k, v in sorted(gon(theo_gio).items())},
        "lat_model": dict(lat.most_common()), "lat_vi_du": lat_vi_du,
        "fallback": sum(v for k, v in lat.items() if tuple(k.split(" → ")) in FALLBACK_THAT),
        "loi": dict(loi.most_common(10)),
        "top_prompt": [{"prompt": p, "luc": h, "model": m, "cache": c, "usd": round(u, 4)}
                       for p, h, m, c, u in sorted(top, reverse=True)[:5]],
        "rong": dict(rong.most_common()), "rong_vi_du": rong_vi_du,
        "ket_noi": doc_ket_noi(ngay),
        "loi_ket_noi": loi_ket_noi(con, t0, t1),
        "vai": gom_vai(ngay, gon(theo_model), tong),
    }


# ---------------------------------------------------------------- lỗi connection
def loi_ket_noi(con, t0: str, t1: str) -> list:
    """Snapshot providerConnections: connection nào đang unavailable / có lỗi
    trong ngày, mã gì. Trả lời câu "vì sao lật model" thay vì đoán."""
    ra = []
    try:
        rows = con.execute("select name, provider, isActive, data, updatedAt from providerConnections").fetchall()
    except sqlite3.Error:
        return ra
    for name, provider, active, data, upd in rows:
        try:
            d = json.loads(data or "{}")
        except Exception:                                    # noqa: BLE001
            d = {}
        khi = d.get("lastErrorAt") or ""
        trong_ngay = bool(khi) and t0 <= khi < t1
        xau = (d.get("testStatus") not in (None, "active")) or d.get("errorCode") or (d.get("backoffLevel") or 0) > 0
        if trong_ngay or xau:
            ra.append({"ten": name or provider, "trang_thai": d.get("testStatus"), "ma": d.get("errorCode"),
                       "loi": (d.get("lastError") or "").replace("\n", " ")[:90], "luc": _hhmm(khi) if khi else "",
                       "trong_ngay": trong_ngay, "backoff": d.get("backoffLevel") or 0, "bat": bool(active)})
    return ra


# ---------------------------------------------------------------- $ theo vai
def _chuan_model(ten: str) -> str:
    """'ds/deepseek-v4-flash' → 'deepseek-v4-flash'; 'xk/z-ai/glm-5.3' → 'z-ai/glm-5.3'
    (9router ghi tên đã bỏ tiền tố nhà cung cấp), so sánh không phân biệt hoa thường."""
    phan = (ten or "").split("/")
    return ("/".join(phan[1:]) if len(phan) > 1 else phan[0]).lower()


def _don_gia(theo_model: dict, tong: dict) -> tuple[dict, float, dict]:
    """$ trên mỗi token (prompt + out) của từng model trong ngày, đọc từ 9router;
    combo → trung bình có trọng số các thành viên. Thiếu thì dùng giá gộp ngày."""
    gia, tok = collections.defaultdict(float), collections.defaultdict(int)
    for nhan, v in theo_model.items():                       # 'model @ kết nối' → gộp theo model
        m = nhan.split(" @ ")[0].lower()
        gia[m] += v["usd"]
        tok[m] += v["prompt"] + v["out"]
    don = {m: gia[m] / tok[m] for m in gia if tok[m]}
    gop = tong["usd"] / (tong["prompt"] + tong["out"]) if (tong["prompt"] + tong["out"]) else 0.0
    combo = {}
    if DB.exists():
        try:
            con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
            for name, models in con.execute("select name, models from combos"):
                combo[name.lower()] = [_chuan_model(x) for x in json.loads(models or "[]")]
        except Exception:                                    # noqa: BLE001
            pass
    return don, gop, combo


def gom_vai(ngay: str, theo_model: dict, tong: dict) -> dict:
    """Ghép session_model_usage của từng vai (mọi HERMES_HOME) với đơn giá 9router
    → $ ước lượng theo vai, $/task done, $/bài published. 9router không biết vai
    nào gọi nên đây là phân bổ theo token, không phải số hoá đơn."""
    d0 = datetime.strptime(ngay, "%Y-%m-%d").replace(tzinfo=VN)
    e0, e1 = d0.timestamp(), (d0 + timedelta(days=1)).timestamp()
    don, gop, combo = _don_gia(theo_model, tong)

    def gia_cua(model: str) -> float:
        m = _chuan_model(model)
        if m in don:
            return don[m]
        for tv in combo.get(model.lower(), []):
            if tv in don:
                return don[tv]
        return gop

    vai = {}
    for home in HERMES_HOMES:
        brand = home.name.replace(".hermes-", "")
        for p in sorted(home.glob("profiles/*/state.db")):
            try:
                c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
                rows = c.execute(
                    "select model, sum(api_call_count), sum(input_tokens), sum(output_tokens), sum(cache_read_tokens), "
                    "sum(reasoning_tokens), count(distinct session_id) from session_model_usage "
                    "where last_seen >= ? and last_seen < ? group by model", (e0, e1)).fetchall()
            except Exception:                                # noqa: BLE001
                continue
            if not rows:
                continue
            a = {"brand": brand, "api": 0, "in": 0, "out": 0, "cache": 0, "reasoning": 0, "usd": 0.0,
                 "phien": 0, "model": collections.Counter(), "task_done": 0, "usd_task": None}
            for model, api, inp, out, cache, rs, phien in rows:
                a["api"] += api or 0
                a["in"] += inp or 0
                a["out"] += out or 0
                a["cache"] += cache or 0
                a["reasoning"] += rs or 0
                a["phien"] = max(a["phien"], phien or 0)
                a["usd"] += ((inp or 0) + (cache or 0) + (out or 0)) * gia_cua(model)
                a["model"][model] += api or 0
            a["model"] = dict(a["model"].most_common(3))
            a["usd"] = round(a["usd"], 4)
            vai[f"{brand}/{p.parent.name}"] = a
        kb = home / "kanban.db"
        if kb.exists():
            try:
                c = sqlite3.connect(f"file:{kb}?mode=ro", uri=True)
                for ass, n in c.execute("select assignee, count(*) from tasks where status='done' and completed_at >= ? "
                                        "and completed_at < ? group by assignee", (int(e0), int(e1))):
                    k = f"{brand}/{ass}"
                    if k in vai:
                        vai[k]["task_done"] = n
                        vai[k]["usd_task"] = round(vai[k]["usd"] / n, 4) if n else None
            except Exception:                                # noqa: BLE001
                pass
    # $/bài: draft published có mtime trong ngày, theo brand (tên brand trong draft
    # là 'donniechublog'/'dcgr', home là blog/dcgr → khớp bằng chứa chuỗi).
    bai = collections.Counter()
    for p in DRAFTS.glob("*.json"):
        if p.name.endswith((".meta.json", ".img.json", ".writer.json")):
            continue
        try:
            mt = p.stat().st_mtime
            if not (e0 <= mt < e1):
                continue
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        if d.get("status") == "published":
            bai[d.get("brand") or "?"] += 1
    theo_brand = {}
    for k, a in vai.items():
        b = theo_brand.setdefault(a["brand"], {"usd": 0.0, "bai": 0, "usd_bai": None})
        b["usd"] += a["usd"]
    for bname, n in bai.items():
        for b in theo_brand:
            if b in bname:
                theo_brand[b]["bai"] += n
    for b in theo_brand.values():
        b["usd"] = round(b["usd"], 4)
        b["usd_bai"] = round(b["usd"] / b["bai"], 4) if b["bai"] else None
    phu = round(sum(a["usd"] for a in vai.values()) / tong["usd"] * 100) if tong["usd"] else 0
    return {"theo_vai": dict(sorted(vai.items(), key=lambda kv: -kv[1]["usd"])), "theo_brand": theo_brand,
            "phu_pct": phu, "ghi_chu": "ước lượng phân bổ theo token × đơn giá 9router trong ngày; không phải hoá đơn"}


# ---------------------------------------------------------------- IP kết nối
def _tep_ket_noi(ngay: str) -> Path:
    return THU_MUC / f"ket_noi_{ngay}.jsonl"


def doc_ket_noi(ngay: str) -> dict:
    p = _tep_ket_noi(ngay)
    if not p.exists():
        return {"co_watcher": False, "ip": {}}
    ip = collections.defaultdict(lambda: {"ket_noi": 0, "dau": "", "cuoi": "", "ngoai": False})
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except Exception:                                    # noqa: BLE001
            continue
        a = ip[d.get("ip", "?")]
        a["ket_noi"] += 1
        a["dau"] = a["dau"] or d.get("t", "")[11:19]
        a["cuoi"] = d.get("t", "")[11:19]
        a["ngoai"] = d.get("ip") not in LOOPBACK
    return {"co_watcher": True, "ip": dict(sorted(ip.items(), key=lambda kv: -kv[1]["ket_noi"]))}


def _ket_noi_hien_tai() -> set:
    """{(ip, port)} đang ESTABLISHED tới cổng 9router. psutil đọc /proc/net/tcp,
    không cần root; thiếu psutil thì rơi về `ss`."""
    # Lấy MỌI trạng thái trừ LISTEN (kể cả TIME_WAIT/CLOSE_WAIT sống 60s): kết
    # nối ngắn kiểu curl mở-đóng trong <2s vẫn để lại vết, không lọt lưới. Kết
    # nối do máy này tự gọi (raddr = :20128) cũng tính, ghi IP phía gọi.
    try:
        import psutil
        ra = set()
        for c in psutil.net_connections("tcp"):
            if c.status == "LISTEN" or not c.raddr:
                continue
            if c.laddr and c.laddr.port == CONG:
                ra.add((c.raddr.ip, c.raddr.port))
            elif c.raddr.port == CONG and c.laddr:
                ra.add((c.laddr.ip, c.laddr.port))
        return ra
    except Exception:                                        # noqa: BLE001
        pass
    out = subprocess.run(["ss", "-tnaH", f"( sport = :{CONG} or dport = :{CONG} )"],
                         capture_output=True, text=True, timeout=10).stdout
    ra = set()
    for line in out.splitlines():
        phan = line.split()
        if len(phan) >= 5 and phan[0] != "LISTEN":
            local, peer = phan[3], phan[4]
            chon = peer if local.endswith(f":{CONG}") else local
            ip, _, port = chon.rpartition(":")
            ra.add((ip.strip("[]"), int(port or 0)))
    return ra


def canh(chu_ky: float = 2.0) -> None:
    """Watcher: ghi kết nối mới. Không giữ gì trong RAM ngoài tập đang mở."""
    THU_MUC.mkdir(parents=True, exist_ok=True)
    da_thay = _ket_noi_hien_tai()                            # kết nối có sẵn lúc khởi động: bỏ qua
    print(f"[canh] cổng {CONG}, {len(da_thay)} kết nối sẵn có, ghi vào {THU_MUC}", flush=True)
    while True:
        time.sleep(chu_ky)
        try:
            gio = _ket_noi_hien_tai()
        except Exception as e:                               # noqa: BLE001
            print(f"[canh] lỗi đọc socket: {type(e).__name__}: {e}", flush=True)
            continue
        moi = gio - da_thay
        if moi:
            now = datetime.now(VN)
            with _tep_ket_noi(now.strftime("%Y-%m-%d")).open("a", encoding="utf-8") as f:
                for ip, port in sorted(moi):
                    f.write(json.dumps({"t": now.isoformat(timespec="seconds"), "ip": ip, "port": port}) + "\n")
                    if ip not in LOOPBACK:
                        print(f"[canh] IP NGOÀI: {ip}:{port} lúc {now:%H:%M:%S}", flush=True)
        da_thay = gio


# ---------------------------------------------------------------- báo cáo
def viet_md(m: dict) -> str:
    if m.get("loi_doc"):
        return f"# 9router {m['ngay']}\n\n{m['loi_doc']}\n"
    t = m["tong"]
    L = [f"# 9router {m['ngay']} (giờ VN)", "",
         f"**Tổng:** {t['req']} req, {t['prompt']:,} prompt (cache {t['cache_pct']}%), {t['out']:,} out, "
         f"${t['usd']}, {t['loi']} lỗi", ""]
    L += ["## Theo model @ kết nối", "", "| model @ kết nối | req | prompt | cache% | out | $ | lỗi |", "|---|--:|--:|--:|--:|--:|--:|"]
    for k, v in m["theo_model"].items():
        L.append(f"| {k} | {v['req']} | {v['prompt']:,} | {v['cache_pct']} | {v['out']:,} | {v['usd']} | {v['loi']} |")
    L += ["", "## Theo khoá API (client)", ""]
    for k, v in m["theo_khoa"].items():
        L.append(f"- {k}: {v['req']} req, ${v['usd']}")
    L += ["", "## Theo giờ (req / $)", "",
          ", ".join(f"{k}h: {v['req']}/{v['usd']}" for k, v in m["theo_gio"].items()) or "không có request"]
    L += ["", f"## Đổi model giữa 2 request liên tiếp (≤ 2 phút) — fallback thật v4-flash→deepseek-chat: {m['fallback']} lần", "",
          "(các cặp khác đa phần là vai chạy song song, 9router không ghi session nên không tách được)", ""]
    if m["lat_model"]:
        L += [f"- {k}: {v} lần" for k, v in m["lat_model"].items()]
        L += ["", "Ví dụ: " + "; ".join(m["lat_vi_du"])]
    else:
        L.append("Không.")
    L += ["", "## Lỗi", ""] + ([f"- {k}: {v}" for k, v in m["loi"].items()] or ["Không."])
    L += ["", "## 5 prompt nặng nhất", ""]
    L += [f"- {x['luc']} {x['model']}: {x['prompt']:,} prompt (cache {x['cache']:,}), ${x['usd']}" for x in m["top_prompt"]]
    L += ["", f"## Phiên rỗng (ok, ≤{RONG_OUT_MAX} out dù ≥{RONG_PROMPT_MIN:,} prompt)", ""]
    L += ([f"- {k}: {v} lần" for k, v in m["rong"].items()] + ["", "Ví dụ: " + "; ".join(m["rong_vi_du"])]) if m["rong"] else ["Không."]
    L += ["", "## Connection có lỗi / không sẵn sàng (snapshot lúc chốt)", ""]
    if m["loi_ket_noi"]:
        for x in m["loi_ket_noi"]:
            L.append(f"- {x['ten']}: {x['trang_thai']}, mã {x['ma']}, backoff {x['backoff']}"
                     f"{', lỗi trong ngày lúc ' + x['luc'] if x['trong_ngay'] else ''}: {x['loi']}")
    else:
        L.append("Không.")
    v = m["vai"]
    L += ["", f"## $ theo vai (ước lượng, phủ {v['phu_pct']}% tiền 9router) — {v['ghi_chu']}", "",
          "| brand/vai | phiên | api | in | cache | out | $ | task done | $/task | model |", "|---|--:|--:|--:|--:|--:|--:|--:|--:|---|"]
    for k, a in v["theo_vai"].items():
        L.append(f"| {k} | {a['phien']} | {a['api']} | {a['in']:,} | {a['cache']:,} | {a['out']:,} | {a['usd']} | "
                 f"{a['task_done']} | {a['usd_task'] if a['usd_task'] is not None else '-'} | "
                 + ", ".join(f"{mm} ({n})" for mm, n in a["model"].items()) + " |")
    L += ["", "**$/bài published:** " + (", ".join(
        f"{b}: ${x['usd']} / {x['bai']} bài = {('$' + str(x['usd_bai'])) if x['usd_bai'] is not None else 'chưa có bài'}"
        for b, x in v["theo_brand"].items()) or "không có dữ liệu vai")]
    kn = m["ket_noi"]
    L += ["", "## IP máy gọi (theo kết nối TCP mới, watcher `--canh`)", ""]
    if not kn["co_watcher"]:
        L.append("Watcher chưa chạy ngày này — không có dữ liệu IP. Bật: systemctl --user start 9router-ket-noi.")
    elif not kn["ip"]:
        L.append("Không có kết nối mới nào.")
    else:
        for ip, v in kn["ip"].items():
            L.append(f"- {ip}{' **(NGOÀI loopback)**' if v['ngoai'] else ''}: {v['ket_noi']} kết nối, {v['dau']}–{v['cuoi']}")
    return "\n".join(L) + "\n"


def van_de(m: dict) -> list[str]:
    """Những gì đáng đánh thức Ông Chủ: IP lạ, lật model, lỗi."""
    if m.get("loi_doc"):
        return [m["loi_doc"]]
    ra = []
    ngoai = [ip for ip, v in m["ket_noi"]["ip"].items() if v["ngoai"]]
    if ngoai:
        ra.append("IP NGOÀI loopback gọi 9router: " + ", ".join(ngoai))
    if m["fallback"]:
        ra.append(f"Fallback thật v4-flash → deepseek-chat: {m['fallback']} lần (title_generation/cooldown?)")
    if m["loi"]:
        ra.append("Lỗi: " + "; ".join(f"{k} {v}" for k, v in m["loi"].items()))
    if sum(m["rong"].values()) >= 3:
        ra.append("Phiên rỗng: " + "; ".join(f"{k} {v}" for k, v in m["rong"].items()))
    xau = [x for x in m["loi_ket_noi"] if x["trong_ngay"] and x["bat"]]
    if xau:
        ra.append("Connection lỗi trong ngày: " + "; ".join(f"{x['ten']} [{x['ma']}] {x['loi'][:50]}" for x in xau))
    return ra


def tom_tat_tele(m: dict) -> str:
    """Tin Telegram mỗi sáng: 4 số quan trọng + $/bài + vai đắt nhất + cảnh báo
    + link bản đầy đủ. Không bảng (Telegram không render), không ảnh."""
    ngay = m["ngay"]
    if m.get("loi_doc"):
        return f"<b>9router {ngay[8:]}/{ngay[5:7]}</b>: {m['loi_doc']}"
    t = m["tong"]
    L = [f"<b>9router {ngay[8:]}/{ngay[5:7]}</b>: {t['req']} req · ${t['usd']} · cache {t['cache_pct']}% · fallback {m['fallback']}"]
    v = m.get("vai") or {}
    if v.get("theo_brand"):
        L.append("$/bài: " + " · ".join(
            f"{b} {('$' + str(x['usd_bai'])) if x['usd_bai'] is not None else 'chưa có bài'} ({x['bai']} bài)"
            for b, x in v["theo_brand"].items()))
    if v.get("theo_vai"):
        L.append("Đắt nhất: " + ", ".join(f"{k} ${a['usd']}" for k, a in list(v["theo_vai"].items())[:3]))
    for x in van_de(m):
        L.append(f"⚠ {x}")
    L.append(f'Chi tiết: <a href="{WEB_URL}/9router/{ngay}">{WEB_URL}/9router/{ngay}</a>')
    return "\n".join(L)


def dung(ngay: str) -> tuple[dict, Path]:
    """Đọc + ghi json/md cho một ngày. Trả (số liệu, đường dẫn .md)."""
    NHAT_KY.mkdir(parents=True, exist_ok=True)
    m = doc_ngay(ngay)
    (NHAT_KY / f"9router_{ngay}.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    p = NHAT_KY / f"9router_{ngay}.md"
    p.write_text(viet_md(m), encoding="utf-8")
    return m, p


def tai(ngay: str, lam_moi: bool = False) -> dict | None:
    """Cho Ada: lấy số liệu ngày đã chốt; chưa có (hoặc hôm nay) thì dựng tại chỗ."""
    p = NHAT_KY / f"9router_{ngay}.json"
    if p.exists() and not lam_moi:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            pass
    if not DB.exists():
        return None
    return dung(ngay)[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Nhật ký 9router theo ngày + watcher IP")
    ap.add_argument("--ngay", help="YYYY-MM-DD giờ VN (mặc định hôm qua)")
    ap.add_argument("--canh", action="store_true", help="chạy watcher kết nối (mãi)")
    ap.add_argument("--gui", action="store_true", help="gửi tóm tắt ngày + link vào topic analyst (luôn gửi)")
    ap.add_argument("--canh-bao", action="store_true", help="chỉ gửi khi có IP lạ/fallback/lỗi/phiên rỗng/connection chết")
    ap.add_argument("--im", action="store_true")
    a = ap.parse_args()
    if a.canh:
        canh()
        return 0
    ngay = a.ngay or (datetime.now(VN) - timedelta(days=1)).strftime("%Y-%m-%d")
    m, p = dung(ngay)
    if not a.im:
        print(p.read_text(encoding="utf-8"))
        print(f"[xong] {p}")
    vd = van_de(m)
    if a.gui or (a.canh_bao and vd):
        publish.gui_topic(tom_tat_tele(m), "analyst")
    elif not a.im:
        print("\n--- tin Telegram sẽ là ---\n" + tom_tat_tele(m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
