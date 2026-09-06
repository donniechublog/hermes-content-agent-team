#!/usr/bin/env python3
"""Gom TU LIEU that cho Miles viet bai — tat dinh, khong LLM.

Vi sao can: truoc day Miles chi nhan 3 cau tom tat cua Finn. Tom tat do khong co
mot con so nao, nen caption viet ra cung khong co so nao — no chi la ban chep
lai tom tat. Da do that tren tin DeepSeek vision: bang benchmark co 11 dong so,
caption co 0 con so, va bo sot ca chi tiet quan trong nhat (model nay thang
Opus-4.8 o dau, thua o dau).

Miles khong the viet du y neu khong duoc doc nguon. File nay lo phan do:

  1. Boc chu tu chinh link goc (article_extract.py)
  2. Boc chu tu 1-2 bai bao khac dua cung tin — noi thuong co bang so va binh
     luan ma trang tai lieu goc khong co
  3. Rut ra cac CON SO va cau chua so, xep rieng thanh mot muc de Miles khong
     phai doi mat trong ca bai

Dung:
    venv/bin/python tu_lieu.py --tieu-de "..." --link "..." --out /tmp/tu_lieu.md
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

SO_BAI_KHAC = 2
CHU_TOI_DA = 6000          # moi nguon, du de Miles doc ma khong phinh prompt

# Cau co so lieu — thu Miles thuc su can. Bat ca % , diem, gia, kich thuoc model.
CO_SO = re.compile(
    r"\d+[.,]?\d*\s*(%|percent|B\b|M\b|K\b|tokens?|USD|\$|ms\b|GB\b|billion|million)"
    r"|\$\s*\d|\b\d+\.\d+\b|\b\d{2,}\b")


def boc(url: str) -> dict:
    """Goi article_extract.py — dung lai bo boc da co thay vi viet lai.

    Ghi ra tep tam chu khong doc stdout: article_extract in CA JSON lan duong
    dan ra stdout, nen json.loads se vap vao phan duoi.
    """
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as fh:
            tam = fh.name
        r = subprocess.run(
            [str(ROOT / "venv/bin/python"), str(ROOT / "article_extract.py"), url,
             "--out", tam],
            capture_output=True, text=True, timeout=90, cwd=str(ROOT))
        # Truoc 06/09/2026 khong ai nhin returncode va cung khong in stderr cua
        # tien trinh con: article_extract chet vi thieu bs4/lxml thi tu_lieu chi
        # tra {} im lang, vai thay "0 nguon" ma khong co dau vet nao (da xay ra
        # tren dcgr).
        if r.returncode != 0:
            cuoi = [d for d in (r.stderr or "").strip().splitlines() if d.strip()]
            print(f"[tu_lieu] article_extract loi rc={r.returncode} cho {url[:50]}: "
                  + (cuoi[-1][:200] if cuoi else "khong co stderr"), file=sys.stderr)
            Path(tam).unlink(missing_ok=True)
            return {}
        d = json.loads(Path(tam).read_text(encoding="utf-8"))
        Path(tam).unlink(missing_ok=True)
        return d
    except Exception as e:                                   # noqa: BLE001
        print(f"[tu_lieu] boc hong {url[:50]}: {type(e).__name__}: {e}", file=sys.stderr)
        return {}


def cau_co_so(doan: list) -> list:
    """Cac cau mang con so, giu thu tu xuat hien."""
    ra, thay = [], set()
    for p in doan:
        for c in re.split(r"(?<=[.!?])\s+", p):
            c = c.strip()
            if len(c) < 25 or len(c) > 320:
                continue
            if not CO_SO.search(c):
                continue
            k = re.sub(r"\W+", "", c.lower())[:60]
            if k in thay:
                continue
            thay.add(k)
            ra.append(c)
    return ra


def gom(tieu_de: str, link: str, so_bai_khac=SO_BAI_KHAC, tu_nguon=None) -> dict:
    """tu_nguon: tep JSON do anh_bai.py --luu-nguon sinh ra.

    Uu tien dung lai nguon da co. Hai ly do: khong tra cuu hai lan, va quan
    trong hon — bai viet giai thich dung nhung gi doc gia nhin thay tren tam anh.
    Moi ben tu tim thi de ra hai bo bai khac nhau.
    """
    nguon = []
    goc = boc(link)
    if goc.get("paragraphs"):
        nguon.append({"nhan": "bài gốc", "url": link,
                      "tieu_de": goc.get("title", ""),
                      "doan": goc["paragraphs"]})

    dsach = []
    if tu_nguon and Path(tu_nguon).exists():
        try:
            j = json.loads(Path(tu_nguon).read_text(encoding="utf-8"))
            dsach = [(t["url"], "") for t in j.get("trang", [])
                     if t.get("url") and t["url"] != link][:so_bai_khac]
            print(f"[tu_lieu] dung lai {len(dsach)} nguon co san", file=sys.stderr)
        except Exception:                                    # noqa: BLE001
            dsach = []
    if not dsach:
        try:
            import anh_bai
            dsach = anh_bai.bao_khac(tieu_de, link, so=so_bai_khac * 2)[:so_bai_khac]
        except Exception as e:                               # noqa: BLE001
            print(f"[tu_lieu] khong lay duoc bao khac: {type(e).__name__}",
                  file=sys.stderr)
    for u, td in dsach:
        d = boc(u)
        if d.get("paragraphs"):
            nguon.append({"nhan": "báo đưa tin", "url": u,
                          "tieu_de": d.get("title", td), "doan": d["paragraphs"]})

    tat_ca_doan = [p for n in nguon for p in n["doan"]]
    return {"tieu_de": tieu_de, "link": link, "nguon": nguon,
            "cau_co_so": cau_co_so(tat_ca_doan)}


def dung_trang(tl: dict) -> str:
    L = [f"# Tư liệu: {tl['tieu_de']}", ""]
    cs = tl["cau_co_so"]
    if cs:
        L += ["## Câu có số liệu (đọc kỹ phần này — caption phải có số)", ""]
        L += [f"- {c}" for c in cs[:25]]
        L.append("")
    else:
        L += ["## Câu có số liệu", "", "*Không tìm thấy câu nào mang số liệu.*", ""]
    for n in tl["nguon"]:
        L += [f"## {n['nhan']}: {n['tieu_de'][:90]}", f"<{n['url']}>", ""]
        chu = 0
        for p in n["doan"]:
            if chu > CHU_TOI_DA:
                L.append("*(cắt bớt)*")
                break
            L.append(p)
            chu += len(p)
        L.append("")
    if not tl["nguon"]:
        L.append("*Không bóc được nội dung từ nguồn nào — Miles phải nói rõ là "
                 "thiếu tư liệu, không được đoán.*")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Gom tu lieu that cho Miles")
    ap.add_argument("--tieu-de", required=True)
    ap.add_argument("--link", required=True)
    ap.add_argument("--out", help="Ghi ra tep thay vi in ra man hinh")
    ap.add_argument("--so-bai-khac", type=int, default=SO_BAI_KHAC)
    ap.add_argument("--tu-nguon", help="Tep nguon do anh_bai.py --luu-nguon sinh ra")
    a = ap.parse_args()

    tl = gom(a.tieu_de, a.link, a.so_bai_khac, a.tu_nguon)
    trang = dung_trang(tl)
    if a.out:
        Path(a.out).write_text(trang, encoding="utf-8")
        print(a.out)
        print(f"  {len(tl['nguon'])} nguồn, {len(tl['cau_co_so'])} câu có số liệu",
              file=sys.stderr)
    else:
        print(trang)


if __name__ == "__main__":
    main()
