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
  - do dai      : chi tinh la truot khi HONG THAT (qua mong / lan man),
                  khong cham theo moc mong muon — do dai khong phai thuoc do
                  chat luong, mien dien dat dung va du
  - tool        : co goi tool that khong (chi voi vai dung tool)

Dung:
    venv/bin/python cost_squeeze.py --vai teaser -n 5
    venv/bin/python cost_squeeze.py --vai writer -n 5
"""
import argparse
import json
import statistics as st
import sys
from pathlib import Path

import httpx

import env_load

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teaser_assemble import DAI_HONG, tim_giong_tuong_thuat  # noqa: E402

import os

ROOT = Path.home() / "content-team"
# Home theo container (systemd/cron dat HERMES_HOME per-brand); roi ve ~/.hermes
# o che do don cu — cung ly do voi model_watch/usage_audit.
HERMES = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
ROUTER = "http://127.0.0.1:20128/v1/chat/completions"

# USD / 1 trieu token: (input, output, cache_read) — tuyen router that su di.
# BANG TAY, se cu dan: doi chieu voi 9router (bang usage co cot cost) hoac trang
# gia cua provider truoc khi tin ket luan "re nhat". Model KHONG co trong bang
# se bi bao ro va loai khoi xep hang gia — truoc day am tham tinh $0.00 va
# "thang" giai re nhat, sai dung cai script nay sinh ra de do.
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


def suy_luan_cua_vai(vai: str) -> dict:
    """Doc dung cau hinh suy luan ma production dang chay cho vai nay.

    Neu khong doc theo, phep do se sai lech: Miles chay reasoning_effort=none
    nhung bo do lai de model suy luan thoai mai -> ra con so khong phai cai
    that su tinh tien.
    """
    import yaml
    sys.path.insert(0, str(Path.home() / "hermes-agent"))
    try:
        from hermes_constants import resolve_reasoning_config
    except Exception as e:                                   # noqa: BLE001
        # Khong im lang: thieu hermes-agent thi phep do chay voi suy luan mac
        # dinh, co the LECH so voi production — nguoi doc phai biet.
        print(f"[canh bao] khong doc duoc cau hinh suy luan production "
              f"({type(e).__name__}) — do voi thiet lap mac dinh", file=sys.stderr)
        return {}
    cfg = yaml.safe_load((HERMES / "profiles" / vai / "config.yaml").read_text())
    r = resolve_reasoning_config(cfg)
    return {"reasoning_effort": "none"} if r == {"enabled": False} else {}


def soul(vai: str) -> str:
    return (HERMES / "profiles" / vai / "SOUL.md").read_text(encoding="utf-8")


def viec_teaser():
    """Viec that cua Jean: tu du lieu bai goc, viet tieu de + doan van 500-800 tu."""
    # KHONG doc tu state/ — thu muc do bi gitignore, ban sao moi se khong co tep.
    # Trich thang tu bai that, va noi ro cach tao lai neu thieu mang.
    mau = ROOT / "mau_bai_goc.json"
    if not mau.exists():
        raise SystemExit(
            f"Thieu {mau}. Tao bang:\n"
            f"  venv/bin/python article_extract.py <url bai> --out {mau}")
    art = json.loads(mau.read_text(encoding="utf-8"))
    nhac = (f"Du lieu bai goc:\n{json.dumps(art, ensure_ascii=False)[:60000]}\n\n"
            "Viet tieu de va cac doan van thuan theo dung huong dan. "
            'Tra ve JSON: {"title": str, "paragraphs": [str, ...]}')
    return soul("teaser"), nhac, DAI_HONG


# Nhieu tin khac nhau, KHONG lap mot tin. Lap mot tin lam bo do mu: v4-flash
# tung sach 5/5 khi lap mot tin, nhung khi doi tin that thi rong mot bai va mat
# sach dau mot bai. Xoay tin moi lo ra duoc nhung loi phu thuoc noi dung.
TIN_WRITER = [
    "Anthropic cong bo Claude co the dieu khien may tinh, nhung ty le thanh cong "
    "tren cac tac vu van phong thuc te moi dat khoang 60 phan tram.",
    "Mot nhom nghien cuu chi ra co the trich xuat chuoi suy luan an tu API cua "
    "cac hang lon, da giai ma 315.320 khoi thinking va tim thay 182 credential.",
    "OpenRouter duoc Stripe mua lai, gia tri thuong vu chua cong bo.",
    "Google cong bo chip TPU the he moi, tuyen bo nhanh gap doi doi truoc.",
    "Meta phat hanh mo hinh nguon mo ho tro tieng Viet, giay phep cho phep dung "
    "thuong mai nhung gioi han so nguoi dung hoat dong hang thang.",
    "Mot ban vá bao mat cua thu vien pho bien lam hong tuong thich nguoc, hang "
    "nghin du an phai ghim lai phien ban cu.",
]


def viec_writer():
    """Viec that cua Miles: viet caption tieng Viet, moi lan mot tin KHAC nhau."""
    def nhac(i):
        tin = TIN_WRITER[i % len(TIN_WRITER)]
        return (f"Tin: {tin}\n\nViet caption tieng Viet co dau day du cho kenh "
                "Telegram, 3 den 5 cau. Chi tra ve caption, khong giai thich.")
    return soul("writer"), nhac, (15, 400)


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


def chay(model, key, sys_prompt, nhac, max_tokens=4000, extra=None):
    body = {"model": model, "temperature": 0.4, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": sys_prompt},
                         {"role": "user", "content": nhac}]}
    body.update(extra or {})
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

    key = env_load.bat_buoc("OPENAI_API_KEY")
    sys_prompt, nhac, (tu_min, tu_max) = VIEC[a.vai]()

    them = suy_luan_cua_vai(a.vai)
    print(f"Vai: {a.vai} | {a.n} lan/model | chan do dai ngoai {tu_min}-{tu_max} tu"
          f"{' | suy luan TAT (theo production)' if them else ''}\n")
    hang = []
    for model in (a.models or UNG_VIEN):
        truot, ly_do, usd, tu = 0, [], [], []
        for i in range(a.n):
            nhac_i = nhac(i) if callable(nhac) else nhac
            d, loi = chay(model, key, sys_prompt, nhac_i, extra=them)
            if loi:
                truot += 1; ly_do.append(loi); continue
            msg = (d["choices"][0].get("message") or {})
            van = rut_van(msg.get("content") or "")
            u = d.get("usage") or {}
            gia = GIA.get(model)
            if gia:
                pin, pout, pc = gia
                cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
                moi = max(u.get("prompt_tokens", 0) - cached, 0)
                usd.append((moi * pin + cached * pc
                            + u.get("completion_tokens", 0) * pout) / 1e6)

            sai = []
            if not van:
                sai.append("rong")
            else:
                if ty_le_dau(van) < 0.15:
                    sai.append("mat dau")
                if tim_giong_tuong_thuat("", van.split("\n\n")):
                    sai.append("giong tuong thuat")
                sotu = len(van.split()); tu.append(sotu)
                if sotu < tu_min:
                    sai.append(f"qua mong {sotu}")
                elif sotu > tu_max:
                    sai.append(f"lan man {sotu}")
            if sai:
                truot += 1; ly_do.append("+".join(sai))

        co_gia = model in GIA
        gia1000 = st.mean(usd) * 1000 if (usd and co_gia) else float("nan")
        hang.append((model, truot, a.n, gia1000, ly_do, tu))
        do_dai = f"  tu tb {st.mean(tu):.0f}" if tu else ""
        gia_hien = f"{gia1000:7.2f}" if co_gia else "  ?????"
        print(f"{model:<24s} truot {truot}/{a.n}  USD/1000 = {gia_hien}{do_dai}")
        if not co_gia:
            print(f"{'':24s}   CHUA CO GIA trong bang GIA — them gia truoc khi "
                  f"so tien, model nay bi loai khoi xep hang gia")
        if ly_do:
            print(f"{'':24s}   ly do: {', '.join(ly_do[:6])}")

    # NaN (model chua co gia) khong duoc du giai "re nhat" — min() voi NaN
    # cho ket qua tuy thu tu, co the len nham.
    sach = [h for h in hang if h[1] == 0 and h[3] == h[3]]
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
