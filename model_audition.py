#!/usr/bin/env python3
"""Audition model: viet tieng Viet du dau + goi tool + do prompt caching.

Vi sao can: chon model khong the doan. Ba thu phai do that truoc khi dua vao
luoi chay: (1) co viet duoc tieng Viet CO DAU khong, (2) co goi duoc tool that
qua hermes khong hay chi in ra JSON gia, (3) co prompt caching khong — cai nay
quan trong ngang gia token (vu Grok dot 14 trieu token trong 35 request).

Do caching bang cach goi HAI LAN y het nhau voi mot doan dem dai co dinh, roi
doc usage.prompt_tokens_details.cached_tokens. Khong cache -> cached_tokens = 0
o ca hai lan.

Luu y: router 20128 tra ve JSON co the kem khoang trang keepalive o dau va
chuoi 'data: [DONE]' o cuoi, nen phai raw_decode chu khong dung r.json().

Dung:
    venv/bin/python model_audition.py                  # audition ca danh sach
    venv/bin/python model_audition.py MODEL [MODEL...] # chi vai model
    venv/bin/python model_audition.py --no-tool MODEL  # thu che do khong tool
"""
import argparse
import json
import time
from pathlib import Path

import httpx

import env_load

ROOT = Path.home() / "content-team"
ROUTER = "http://127.0.0.1:20128/v1/chat/completions"

UNGVIEN = [
    "tokenrouter/qwen/qwen3.8-max",
    "tokenrouter/moonshotai/kimi-k3",
    "tokenrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "tokenrouter/tencent/hy3-preview",
]

TOOLS = [{
    "type": "function",
    "function": {
        "name": "luu_caption",
        "description": "Luu caption tieng Viet vao hang doi duyet",
        "parameters": {
            "type": "object",
            "properties": {
                "caption": {"type": "string", "description": "Caption tieng Viet"},
                "chu_de": {"type": "string", "description": "Chu de ngan"},
            },
            "required": ["caption", "chu_de"],
        },
    },
}]

SYS = ("Ban la cay viet tieng Viet cua mot kenh tin AI. "
       "Luon tra loi bang tieng Viet co dau day du.")
# Doan dem DAI va CO DINH — de lan goi thu hai trung prefix, do duoc cache
DEM = ("Boi canh bien tap (khong doi): kenh dang tin AI cho doc gia Viet Nam, "
       "giong van ngan gon, khong sao roi, khong cuong dieu, uu tien su that "
       "kiem chung duoc. ") * 60
TIN = "OpenAI vua ra mat mo hinh moi giam 40% chi phi suy luan."

DAU = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
          "ùúủũụưừứửữựỳýỷỹỵđ")

# Nguong dat: van ban tieng Viet co dau that thuong tren 0.15
NGUONG_DAU = 0.15


def ty_le_dau(text: str) -> float:
    chu = [c for c in text.lower() if c.isalpha()]
    if not chu:
        return 0.0
    return sum(1 for c in chu if c in DAU) / len(chu)


def goi(model: str, key: str, dung_tool: bool, max_tokens: int) -> dict:
    nhac = (f"{DEM}\n\nTin: {TIN}\n" + (
        "Hay viet caption 3 cau tieng Viet co dau day du, roi GOI TOOL "
        "luu_caption de luu lai." if dung_tool else
        "Viet dung 3 cau tieng Viet co dau day du. Chi tra ve 3 cau."))
    body = {"model": model, "temperature": 0.3, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": nhac}]}
    if dung_tool:
        body["tools"] = TOOLS
    t0 = time.time()
    try:
        r = httpx.post(ROUTER, timeout=180,
                       headers={"Authorization": f"Bearer {key}"}, json=body)
    except Exception as e:                                   # noqa: BLE001
        return {"loi": f"{type(e).__name__}: {e}", "giay": round(time.time() - t0, 1)}
    giay = round(time.time() - t0, 1)
    if r.status_code != 200:
        return {"loi": f"HTTP {r.status_code}: {r.text[:200]}", "giay": giay}
    txt = r.text
    try:
        d, _ = json.JSONDecoder().raw_decode(txt[txt.index("{"):])
        lc = d["choices"][0]
    except Exception:                                        # noqa: BLE001
        return {"loi": f"body la khong doc duoc: {txt[:200]}", "giay": giay}

    msg = lc.get("message") or {}
    u = d.get("usage") or {}
    ct = msg.get("content") or ""
    tc = msg.get("tool_calls") or []
    # Model co the viet caption vao content HOAC vao tham so tool — tinh ca hai
    args = tc[0].get("function", {}).get("arguments", "") if tc else ""
    return {
        "giay": giay,
        "ket": lc.get("finish_reason"),
        "content": ct.strip(),
        "tool": [t.get("function", {}).get("name") for t in tc],
        "tool_args": args,
        "van_ban": (ct.strip() or args),
        "reason_tok": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
        "prompt_tok": u.get("prompt_tokens"),
        "out_tok": u.get("completion_tokens"),
        "cached": (u.get("prompt_tokens_details") or {}).get(
            "cached_tokens", u.get("prompt_cache_hit_tokens")),
    }


def main():
    ap = argparse.ArgumentParser(description="Audition model cho content-team")
    ap.add_argument("models", nargs="*", help="Model can thu (mac dinh: danh sach ung vien)")
    ap.add_argument("--no-tool", action="store_true",
                    help="Thu che do khong tool — de soi loi 'suy luan mai khong viet'")
    ap.add_argument("--max-tokens", type=int, default=2000)
    a = ap.parse_args()

    key = env_load.bat_buoc("OPENAI_API_KEY")
    ket_qua = {}
    for m in (a.models or UNGVIEN):
        print(f"\n{'=' * 72}\n{m}", flush=True)
        r1 = goi(m, key, not a.no_tool, a.max_tokens)
        if "loi" in r1:
            print(f"  LOI: {r1['loi']}")
            ket_qua[m] = {"dat": False, "vi_sao": r1["loi"]}
            continue
        time.sleep(2)
        r2 = goi(m, key, not a.no_tool, a.max_tokens)   # y het -> do cache

        vb = r1["van_ban"]
        td = ty_le_dau(vb)
        co_tool = bool(r1["tool"]) if not a.no_tool else None
        # cached_tokens > 0 o bat ky lan nao => nha cung cap co cache prefix
        cache_ok = bool((r1["cached"] or 0) or (r2.get("cached") or 0))

        print(f"  thoi gian  : {r1['giay']}s (lan 2: {r2.get('giay')}s)")
        print(f"  ket thuc   : {r1['ket']}")
        if not a.no_tool:
            print(f"  goi tool   : {r1['tool'] or 'KHONG — truot'}")
        print(f"  tieng Viet : {len(vb)} ky tu, ty le dau {td:.2f} "
              f"({'du dau' if td >= NGUONG_DAU else 'MAT DAU — truot'})")
        print(f"  suy luan   : {r1['reason_tok']} token")
        print(f"  token      : prompt {r1['prompt_tok']} | out {r1['out_tok']}")
        print(f"  cache      : lan1 {r1['cached']} | lan2 {r2.get('cached')} "
              f"({'CO cache' if cache_ok else 'KHONG cache — dat do'})")
        if vb:
            print(f"  --- ket qua ---\n  {vb[:400]}")
        else:
            print("  --- KHONG VIET RA CHU NAO ---")

        dat = td >= NGUONG_DAU and bool(vb) and (a.no_tool or co_tool) and cache_ok
        ket_qua[m] = {"dat": dat, "ty_le_dau": round(td, 2), "tool": r1["tool"],
                      "cache": cache_ok, "giay": r1["giay"],
                      "reason_tok": r1["reason_tok"]}
        print(f"  => {'DAT' if dat else 'TRUOT'}")

    print(f"\n{'=' * 72}\nTONG KET")
    for m, v in ket_qua.items():
        print(f"  {'DAT   ' if v.get('dat') else 'TRUOT '} {m}")
    out = ROOT / "state" / "model_audition.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ket_qua, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDa ghi {out}")


if __name__ == "__main__":
    main()
