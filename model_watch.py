#!/usr/bin/env python3
"""Canh bao qua Telegram khi model khong phan hoi.

Vi sao can: hermes fallback HOAN TOAN IM LANG. Da kiem chung — dat model chinh
thanh mot model chet (410 Gone), agent van tra loi binh thuong, khong mot dong
nao bao da chuyen model. Nghia la model chinh co the hong nhieu ngay ma khong
ai biet, cho toi khi nhin bang usage moi phat hien (dung nhu vu Grok chiem 80%
token du chi la du phong).

Script nay doc dung nhung model tung profile that su dung (chinh + du phong),
thu tung cai, va CHI bao khi trang thai DOI — khong spam moi lan chay.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

import env_load
import tele_util

ROOT = Path.home() / "content-team"
HERMES_HOME = Path.home() / ".hermes"
STATE_FILE = ROOT / "state" / "model_health.json"
ROUTER = "http://127.0.0.1:20128/v1/chat/completions"
# DU 9 vai. Tung thieu nova + market: model cua hai vai do hong khong ai thu,
# va usage cua chung bi bao "LA — khong o chuoi nao" — canh bao gia dung loai
# script nay sinh ra de chong.
PROFILES = ["scout", "nova", "market", "ethan", "designer", "writer", "miles",
            "analyst", "teaser"]

TIMEOUT = 25
PROBE = {"messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}

# Ma loi -> giai thich ngan, de canh bao doc duoc ngay khong phai tra cuu
REASONS = {
    401: "khoa API sai hoac het han",
    402: "het tien / chua nap credit",
    403: "chua mo quyen truy cap",
    404: "model khong ton tai o dau kia",
    410: "nha cung cap DA GO model nay",
    429: "het quota / vuot gioi han tan suat",
    500: "loi phia nha cung cap",
    502: "backend cua nha cung cap chet",
    503: "dich vu qua tai",
}


def models_in_use() -> dict:
    """Tra ve {model: [mo ta vai tro]} — chi nhung model that su duoc cau hinh."""
    used = {}
    targets = [("default", HERMES_HOME / "config.yaml")]
    targets += [(p, HERMES_HOME / "profiles" / p / "config.yaml") for p in PROFILES]
    for name, path in targets:
        if not path.exists():
            continue
        try:
            cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:                                    # noqa: BLE001
            continue
        main = (cfg.get("model") or {}).get("default")
        if main:
            used.setdefault(main, []).append(f"{name}:chinh")
        for i, fb in enumerate(cfg.get("fallback_providers") or [], 2):
            m = fb.get("model")
            if m:
                used.setdefault(m, []).append(f"{name}:du phong {i}")
    return used


def probe(model: str, key: str) -> tuple:
    """Tra ve (ok, ma_loi_hoac_None, mo_ta)."""
    try:
        r = httpx.post(ROUTER, timeout=TIMEOUT,
                       headers={"Authorization": f"Bearer {key}"},
                       json={"model": model, **PROBE})
    except Exception as e:                                   # noqa: BLE001
        return False, None, f"khong ket noi duoc ({type(e).__name__})"
    if r.status_code == 200:
        return True, 200, "ok"
    # 9router boc loi that trong body, ma HTTP ngoai co the khac
    inner = None
    try:
        msg = json.dumps(r.json())
        for code in REASONS:
            if f"[{code}]" in msg:
                inner = code
                break
    except Exception:                                        # noqa: BLE001
        pass
    code = inner or r.status_code
    return False, code, REASONS.get(code, f"loi HTTP {code}")


def send(text: str):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_GROUP_ID") or os.environ.get("TELEGRAM_CHANNEL_ID")
    if not (tok and chat):
        print("[canh bao] thieu TELEGRAM_BOT_TOKEN/GROUP_ID — in ra man hinh thay vi gui")
        print(text)
        return
    thread = None
    tp = env_load.topics_path()
    if tp.exists():
        thread = json.loads(tp.read_text(encoding="utf-8")).get("analyst")
    try:
        # Tin dai -> chia thanh nhieu tin gui lien tiep thay vi de Telegram
        # tu choi ca tin khi vuot 4096.
        for phan in tele_util.chia_tin(text):
            payload = {"chat_id": chat, "text": phan, "parse_mode": "HTML"}
            if thread:
                payload["message_thread_id"] = int(thread)
            httpx.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                       json=payload, timeout=30)
    except Exception as e:                                   # noqa: BLE001
        print(f"[canh bao] khong gui duoc Telegram: {type(e).__name__}: {e}")


def main():
    ap = argparse.ArgumentParser(description="Theo doi suc khoe model, bao khi hong")
    ap.add_argument("--force-report", action="store_true",
                    help="Gui bao cao du khong co gi thay doi (de kiem tra)")
    ap.add_argument("--quiet", action="store_true", help="Khong in ra man hinh")
    a = ap.parse_args()

    env_load.nap()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("Thieu OPENAI_API_KEY")

    used = models_in_use()
    prev = {}
    if STATE_FILE.exists():
        prev = json.loads(STATE_FILE.read_text(encoding="utf-8")).get("models", {})

    now, changes = {}, []
    for model, roles in sorted(used.items()):
        ok, code, why = probe(model, key)
        now[model] = {"ok": ok, "code": code, "why": why, "roles": roles}
        was = prev.get(model, {}).get("ok")
        if was is None:
            if not ok:                       # lan dau thay, va dang hong
                changes.append(("MOI", model, roles, why))
        elif was != ok:
            changes.append(("HOI PHUC" if ok else "HONG", model, roles, why))
        if not a.quiet:
            mark = "OK " if ok else "HONG"
            print(f"  {mark:5s} {model:<52s} {why}")

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(
        {"checked_at": datetime.now(timezone.utc).isoformat(), "models": now},
        ensure_ascii=False, indent=2), encoding="utf-8")

    broken = [m for m, v in now.items() if not v["ok"]]

    if not changes and not a.force_report:
        if not a.quiet:
            print(f"\nKhong co thay doi. {len(now) - len(broken)}/{len(now)} model khoe.")
        return

    lines = ["<b>⚠️ Trạng thái model thay đổi</b>", ""]
    for kind, model, roles, why in changes:
        icon = {"HONG": "🔴", "HOI PHUC": "🟢", "MOI": "🟠"}[kind]
        lines.append(f"{icon} <b>{kind}</b> — <code>{model}</code>")
        lines.append(f"    {why}")
        lines.append(f"    dùng cho: {', '.join(roles)}")
        lines.append("")
    if broken:
        lines.append(f"<i>Hiện {len(broken)}/{len(now)} model đang hỏng.</i>")
        # Canh bao nang: mot vai mat CA model chinh lan moi du phong
        for p in PROFILES:
            mine = [m for m, v in now.items()
                    if any(r.startswith(p + ":") for r in v["roles"])]
            if mine and all(not now[m]["ok"] for m in mine):
                lines.append(f"🚨 <b>{p} mất toàn bộ chuỗi model — không chạy được.</b>")
    else:
        lines.append(f"<i>Cả {len(now)} model đều khỏe.</i>")

    send("\n".join(lines))
    if not a.quiet:
        print(f"\nDa gui canh bao: {len(changes)} thay doi.")


if __name__ == "__main__":
    main()
