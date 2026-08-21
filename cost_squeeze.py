#!/usr/bin/env python3
"""Ep chi phi: tim model RE NHAT ma van dat moi cong kiem tra, chay lap N lan.

Vi sao can: chon model re la de, giu duoc ON DINH moi kho. Mot model co the
viet dep lan dau roi hong lan thu bay — dung mot lan de quyet dinh la danh bac.
Script nay chay lap N lan tren dung viec that cua tung vai, cham bang CODE
(khong nho LLM tu danh gia), roi bao ty le truot va chi phi tren 1000 lan chay.

Moi cong kiem tra deu tat dinh:
  - rong        : model tra ve khong mot chu nao
  - dau         : ty le ky tu co dau, duoi nguong la mat dau
  - giong       : cum tuong thuat ("bai viet"...) — dung chung bo chan cua teaser
  - do dai      : so tu nam ngoai khoang yeu cau
  - tool        : co goi tool that khong (chi voi vai dung tool)

Dung:
    venv/bin/python cost_squeeze.py --vai teaser -n 5
    venv/bin/python cost_squeeze.py --vai writer -n 5
"""
import argparse
import json
import os
import statistics as st
import sys
import unicodedata
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teaser_assemble import tim_giong_tuong_thuat           # noqa: E402

ROOT = Path.home() / "content-team"
HERMES = Path.home() / ".hermes"
ROUTER = "http://127.0.0.1:20128/v1/chat/completions"

# USD / 1 trieu token: (input, output, cache_read) — tuyen router that su di
GIA = {
    "ds/deepseek-chat":      (0.14,  0.28, 0.0028),
    "ds/deepseek-v4-flash":  (0.14,  0.28, 0.0028),
    "ds/deepseek-v4-pro":    (0.435, 0.87, 0.003625),
    "mimo/mimo-v2.5-pro":    (0.14,  0.28, 0.0028),
    "tokenrouter/moonshotai/kimi-k3": (3.0, 15.0, 0.3),
}

UNG_VIEN = ["ds/deepseek-chat", "ds/deepseek-v4-flash",
            "mimo/mimo-v2.5-pro", "ds/deepseek-v4-pro"]

DAU = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
          "ùúủũụưừứửữựỳýỷỹỵđ")


def ty_le_dau(t: str) -> float:
    chu = [c for c in t.lower() if c.isalpha()]
    return sum(1 for c in chu if c in DAU) / len(chu) if chu else 0.0


def nap_khoa() -> str:
    for p in (ROOT / ".secrets.env", HERMES / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("Thieu OPENAI_API_KEY")
    return key


def soul(vai: str) -> str:
    return (HERMES / "profiles" / vai / "SOUL.md").read_text(encoding="utf-8")


def viec_teaser():
    """Viec that cua Jean: tu du lieu bai goc, viet tieu de + doan van 500-800 tu."""
    art = json.loads((ROOT / "state" / "mau_bai_goc.json").read_text(encoding="utf-8"))
    nhac = (f"Du lieu bai goc:\n{json.dumps(art, ensure_ascii=False)[:60000]}\n\n"
            "Viet tieu de va cac doan van thuan theo dung huong dan. "
            'Tra ve JSON: {"title": str, "paragraphs": [str, ...]}')
    return soul("teaser"), nhac, (500, 800), False


def viec_writer():
    """Viec that cua Quinn: viet caption tieng Viet cho mot tin."""
    tin = ("Anthropic cong bo Claude co the dieu khien may tinh, nhung ty le "
           "thanh cong tren cac tac vu van phong thuc te moi dat khoang 60 phan tram.")
    nhac = (f"Tin: {tin}\n\nViet caption tieng Viet co dau day du cho kenh Telegram, "
            "3 den 5 cau. Chi tra ve caption, khong giai thich.")
    return soul("writer"), nhac, (30, 200), False


VIEC = {"teaser": viec_teaser, "writer": viec_writer}


def rut_van(noi_dung: str) -> str:
    """Model co the tra JSON hoac van xuoi — lay ra phan chu de cham."""
    t = noi_dung.strip()
    if "{" in t:
        try:
            d, _ = json.JSONDecoder().raw_decode(t[t.index("{"):])
            if isinstance(d, dict):
                phan = [str(d.get("title", ""))] + [str(x) for x in d.get("paragraphs", [])]
                if any(phan):
                    return "\n\n".join(p for p in phan if p)
        except Exception:                                    # noqa: BLE001
            pass
    return t


def chay(model, key, sys_prompt, nhac, max_tokens=4000):
    body = {"model": model, "temperature": 0.4, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": sys_prompt},
                         {"role": "user", "content": nhac}]}
    try:
        r = httpx.post(ROUTER, timeout=300,
                       headers={"Authorization": f"Bearer {key}"}, json=body)
    except Exception as e:                                   # noqa: BLE001
        return None, f"{type(e).__name__}"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    t = r.text
    try:
        d, _ = json.JSONDecoder().raw_decode(t[t.index("{"):])
    except Exception:                                        # noqa: BLE001
        return None, "parse"
    return d, None


def main():
    ap = argparse.ArgumentParser(description="Ep chi phi ma van giu on dinh")
    ap.add_argument("--vai", required=True, choices=sorted(VIEC))
    ap.add_argument("-n", type=int, default=5, help="So lan chay moi model")
    ap.add_argument("--models", nargs="*", help="Model can thu")
    a = ap.parse_args()

    key = nap_khoa()
    sys_prompt, nhac, (tu_min, tu_max), can_tool = VIEC[a.vai]()

    print(f"Vai: {a.vai} | {a.n} lan/model | do dai yeu cau {tu_min}-{tu_max} tu\n")
    hang = []
    for model in (a.models or UNG_VIEN):
        truot, ly_do, usd, tu = 0, [], [], []
        for i in range(a.n):
            d, loi = chay(model, key, sys_prompt, nhac)
            if loi:
                truot += 1; ly_do.append(loi); continue
            msg = (d["choices"][0].get("message") or {})
            van = rut_van(msg.get("content") or "")
            u = d.get("usage") or {}
            pin, pout, pc = GIA.get(model, (0, 0, 0))
            cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
            moi = max(u.get("prompt_tokens", 0) - cached, 0)
            usd.append((moi * pin + cached * pc + u.get("completion_tokens", 0) * pout) / 1e6)

            sai = []
            if not van:
                sai.append("rong")
            else:
                if ty_le_dau(van) < 0.15:
                    sai.append("mat dau")
                if tim_giong_tuong_thuat("", van.split("\n\n")):
                    sai.append("giong tuong thuat")
                sotu = len(van.split()); tu.append(sotu)
                if not (tu_min <= sotu <= tu_max):
                    sai.append(f"do dai {sotu}")
            if sai:
                truot += 1; ly_do.append("+".join(sai))

        gia1000 = st.mean(usd) * 1000 if usd else float("nan")
        hang.append((model, truot, a.n, gia1000, ly_do, tu))
        print(f"{model:<24s} truot {truot}/{a.n}  USD/1000 = {gia1000:7.2f}"
              f"  tu tb {st.mean(tu):.0f}" if tu else
              f"{model:<24s} truot {truot}/{a.n}")
        if ly_do:
            print(f"{'':24s}   ly do: {', '.join(ly_do[:6])}")

    sach = [h for h in hang if h[1] == 0]
    print("\n" + "=" * 68)
    if sach:
        tot = min(sach, key=lambda h: h[3])
        print(f"RE NHAT ma khong truot lan nao: {tot[0]}  ({tot[3]:.2f} USD/1000)")
    else:
        it = min(hang, key=lambda h: (h[1], h[3]))
        print(f"KHONG model nao sach {a.n}/{a.n}. It truot nhat: {it[0]} "
              f"({it[1]}/{it[2]} truot, {it[3]:.2f} USD/1000)")


if __name__ == "__main__":
    main()
