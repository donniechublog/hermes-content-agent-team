#!/usr/bin/env python3
"""Soi usage that tu 9router: bat fallback am tham va model khong cache.

Vi sao can — hai nguyen tac da chot:

1. BAT BUOC GIAM SAT MODEL. Hermes fallback im lang hoan toan. Te hon nua,
   `try_activate_fallback` doi model NGAY GIUA LUOT roi `restore_primary_runtime`
   lat ve model chinh o luot sau. Nghia la mot hoi thoai co the chay qua 2-3 model
   ma khong dong log nao. `model_watch.py` chi biet model con song hay chet — no
   KHONG biet model nao that su duoc goi. File nay tra loi cau do bang so lieu
   ghi tai 9router, la su that mat dat.

2. GHIM MOI HOI THOAI VAO MOT MODEL. Cache la per-model: lat model giua chung
   lam mat sach prefix da cache, ca ngu canh bi tinh lai gia goc. Cot cache% duoi
   day chinh la thuoc do nguyen tac nay — tut cache la dau hieu dang lat model.

Doc truc tiep SQLite cua 9router o che do CHI DOC, khong dung toi du lieu.
"""
import argparse
import collections
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path

import yaml

import env_load
import publish

DB = Path.home() / ".9router" / "db" / "data.sqlite"
hermes_home = env_load.hermes_home      # per-brand: ~/.hermes-<brand>, roi ve ~/.hermes

# Model co cache ma tut duoi muc nay la dang co van de (lat model, hoac
# prompt qua ngan de cache an)
NGUONG_CACHE = 40.0


def chuoi_da_cau_hinh() -> dict:
    """{ten model tran: [vai dung no]} — doc dung config dang chay."""
    ra = {}
    home = hermes_home()
    # Glob thay vi liet ke tay: tung thieu nova + market va usage cua chung bi
    # bao "LA — khong o chuoi nao" — canh bao gia. Them config goc de model
    # mac dinh cung khong bi bao LA oan.
    targets = [("default", home / "config.yaml")]
    targets += sorted((p.parent.name, p)
                      for p in (home / "profiles").glob("*/config.yaml"))
    for vai, p in targets:
        if not p.exists():
            continue
        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        chain = [(cfg.get("model") or {}).get("default")]
        chain += [f.get("model") for f in (cfg.get("fallback_providers") or [])]
        for i, m in enumerate(chain):
            if not m:
                continue
            nhan = f"{vai}:{'chinh' if i == 0 else f'du phong {i}'}"
            # 9router ghi ten da bo tien to NHA CUNG CAP (phan dau), nhung ten
            # 3 phan thi giu phan giua: config `xk/z-ai/glm-5.3` -> router ghi
            # `z-ai/glm-5.3`. Truoc day chi lay split("/")[-1] ("glm-5.3") nen
            # model chu luc cua writer bi bao "LA — khong o chuoi nao" oan.
            # Dang ky CA HAI bien the cho chac.
            phan = m.split("/")
            for tran in {phan[-1], "/".join(phan[1:]) or phan[-1]}:
                ra.setdefault(tran, []).append(nhan)
    # Model do CONG CU goi thang qua router, khong nam trong config vai nao:
    # vision cua tang chuan bi anh (05/09/2026: 62 req/ngay, $0.004, bi bao
    # "LA — khong o chuoi nao" oan). Doc tu anh_chuan_bi de mot nguon su that.
    try:
        import anh_chuan_bi
        phan = anh_chuan_bi.VISION_MODEL.split("/")
        for tran in {phan[-1], "/".join(phan[1:]) or phan[-1]}:
            ra.setdefault(tran, []).append("anh_chuan_bi:vision")
    except Exception:                                        # noqa: BLE001
        pass
    return ra


def doc_usage(gio: int, api_key: str | None):
    if not DB.exists():
        sys.exit(f"Khong thay CSDL 9router: {DB}")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    # 9router luu timestamp dang ISO co 'T' va 'Z': 2026-08-21T06:28:58.728Z
    # KHONG duoc dung datetime('now',...) lam moc — no tra ve dang co DAU CACH
    # ("2026-08-21 05:10:31"). So sanh chuoi se dung o vi tri 10: 'T' (84) lon
    # hon ' ' (32), nen MOI ban ghi cung ngay deu lot qua bat ke gio, va cua so
    # "6 gio" lang le bien thanh "tu dau ngay". Dung moc cung dinh dang.
    moc = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=gio))
    moc = moc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    q = ("select model, apiKey, tokens, cost, status from usageHistory "
         "where timestamp >= ?")
    args = [moc]
    if api_key:
        q += " and apiKey = ?"
        args.append(api_key)
    agg = collections.defaultdict(lambda: {"req": 0, "prompt": 0, "cache": 0,
                                           "out": 0, "usd": 0.0, "loi": 0})
    keys = collections.defaultdict(set)
    for model, ak, tok, cost, status in con.execute(q, args):
        try:
            t = json.loads(tok or "{}")
        except Exception:                                    # noqa: BLE001
            t = {}
        a = agg[model]
        a["req"] += 1
        a["prompt"] += t.get("prompt_tokens", 0)
        a["cache"] += t.get("cached_tokens", 0)
        a["out"] += t.get("completion_tokens", 0)
        a["usd"] += cost or 0
        if status and status != "ok":
            a["loi"] += 1
        keys[model].add(ak)
    return agg, keys


def main():
    ap = argparse.ArgumentParser(description="Soi usage that, bat fallback am tham")
    ap.add_argument("--gio", type=int, default=24, help="Nhin lai bao nhieu gio")
    ap.add_argument("--api-key", help="Chi soi mot khoa (de tach client)")
    ap.add_argument("--canh-bao", action="store_true", help="Gui canh bao Telegram neu co van de")
    a = ap.parse_args()

    cau_hinh = chuoi_da_cau_hinh()
    agg, keys = doc_usage(a.gio, a.api_key)
    if not agg:
        print(f"Khong co request nao trong {a.gio} gio qua.")
        return

    tong = sum(v["usd"] for v in agg.values())
    print(f"{a.gio} gio qua — {sum(v['req'] for v in agg.values())} request, "
          f"tong ${tong:.4f}\n")
    print(f"{'model':<26s} {'req':>5s} {'prompt':>11s} {'cache':>7s} {'chi phi':>10s}  vai")
    print("-" * 82)

    la, cache_kem = [], []
    for m, v in sorted(agg.items(), key=lambda x: -x[1]["usd"]):
        pct = (v["cache"] / v["prompt"] * 100) if v["prompt"] else 0.0
        vai = cau_hinh.get(m)
        nhan = ", ".join(vai) if vai else "LA — khong o chuoi nao"
        if not vai:
            la.append((m, v, pct))
        elif pct < NGUONG_CACHE and v["prompt"] > 20000:
            cache_kem.append((m, v, pct))
        print(f"{m[:26]:<26s} {v['req']:>5d} {v['prompt']:>11,} {pct:>6.1f}% "
              f"{'$' + format(v['usd'], '.4f'):>10s}  {nhan}")

    van_de = []
    if la:
        van_de.append("Model KHONG nam trong chuoi nao — hoac fallback am tham, "
                      "hoac mot client khac dung chung 9router:")
        for m, v, pct in sorted(la, key=lambda x: -x[1]["usd"]):
            phan = v["usd"] / tong * 100 if tong else 0
            van_de.append(f"  • {m}: {v['req']} req, {v['prompt']:,} token, "
                          f"cache {pct:.1f}%, ${v['usd']:.4f} ({phan:.0f}% tong tien)")
            if len(keys[m]) == 1:
                van_de.append(f"    khoa: {list(keys[m])[0]}")
    if cache_kem:
        van_de.append("Model CUA TA nhung cache thap — dau hieu dang lat model "
                      "giua hoi thoai:")
        for m, v, pct in cache_kem:
            van_de.append(f"  • {m}: cache {pct:.1f}% tren {v['prompt']:,} token")

    if van_de:
        print("\n" + "\n".join(van_de))
    else:
        print("\nKhong co van de: moi model deu nam trong chuoi va cache dat nguong.")

    if a.canh_bao and van_de:
        publish.gui_topic("<b>⚠️ Soi usage 9router</b>\n\n" + "\n".join(van_de).replace("•", "-"), "analyst")


if __name__ == "__main__":
    main()
