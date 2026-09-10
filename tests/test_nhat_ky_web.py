#!/usr/bin/env python3
"""`md_sang_html` dựng đúng bốn cú pháp mà 9router sinh ra (issue D2).

Bo `markdown` khoi requirements duoc vi dau vao KHONG phai markdown bat ky:
chinh `theo_doi_9router.py` sinh ra tep .md do, nen tap cu phap dong — `#`/`##`,
bang `|`, muc `- `, `**dam**`. Tep nay giu hai thu:

  1. Bon cu phap do dung ra HTML dung.
  2. ESCAPE TRUOC, dung the SAU. Ten model / `status` / `lastError` trong tep
     deu chep tu usageHistory cua 9router, tuc tu client goi router. Mot ten
     model dat la `<img src=x onerror=...>` ma lot ra HTML tho la chay trong
     trinh duyet cua Ong Chu luc 6h sang. Day la ly do ban cu (python-markdown)
     cung phai escape truoc.

Chay:  venv/bin/python tests/test_nhat_ky_web.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import nhat_ky_web as w                                       # noqa: E402


def test_tieu_de_hai_muc():
    assert w.md_sang_html("# Mot") == "<h1>Mot</h1>"
    assert w.md_sang_html("## Hai") == "<h2>Hai</h2>"


def test_dam_trong_doan_va_trong_muc():
    assert w.md_sang_html("**Tổng:** 120 req") == "<p><b>Tổng:</b> 120 req</p>"
    assert "<li>a <b>b</b></li>" in w.md_sang_html("- a **b**")


def test_bang_bo_vach_ngan_va_hang_dau_la_th():
    ra = w.md_sang_html("| model | req |\n|---|---:|\n| a | 1 |\n| b | 2 |")
    assert "<tr><th>model</th><th>req</th></tr>" in ra, ra
    assert "<tr><td>a</td><td>1</td></tr>" in ra, ra
    assert "<tr><td>b</td><td>2</td></tr>" in ra, ra
    assert "---" not in ra, f"vach ngan cua bang lot ra HTML: {ra}"
    assert ra.count("<table>") == 1 and ra.count("</table>") == 1, ra


def test_hai_bang_roi_nhau_khong_dinh_lam_mot():
    ra = w.md_sang_html("| a |\n|---|\n| 1 |\n\n## Giua\n\n| b |\n|---|\n| 2 |")
    assert ra.count("<table>") == 2, ra
    assert ra.index("<h2>Giua</h2>") < ra.rindex("<table>"), "bang thu hai phai sau tieu de"


def test_muc_lien_tiep_gom_mot_ul_va_dong_dung_cho():
    ra = w.md_sang_html("- a\n- b\n\n## Sau")
    assert ra.count("<ul>") == 1 and ra.count("</ul>") == 1, ra
    assert ra.index("</ul>") < ra.index("<h2>"), "ul phai dong truoc tieu de ke tiep"


def test_ul_dong_o_cuoi_tep():
    ra = w.md_sang_html("- a\n- b")
    assert ra.endswith("</ul>"), ra


# ------------------------------------------------------------------ an toan
def test_ten_model_hiem_bi_escape_trong_bang():
    """Dung thu du lieu that: 9router tra ve ten model do client dat."""
    ra = w.md_sang_html("| model |\n|---|\n| <img src=x onerror=alert(1)> |")
    assert "<img" not in ra, f"HTML tho lot vao trang: {ra}"
    assert "&lt;img src=x onerror=alert(1)&gt;" in ra, ra


def test_the_script_trong_doan_va_tieu_de_deu_bi_escape():
    for mau in ("<script>alert(1)</script>",
                "# <script>alert(1)</script>",
                "- <script>alert(1)</script>"):
        ra = w.md_sang_html(mau)
        assert "<script>" not in ra, f"{mau!r} -> {ra}"
        assert "&lt;script&gt;" in ra, f"{mau!r} -> {ra}"


def test_dam_khong_bien_HTML_da_escape_thanh_the_that():
    """`**` chay SAU escape, nen mot doan vua co ** vua co the HTML van an toan."""
    ra = w.md_sang_html("**<b>x</b>**")
    assert ra == "<p><b>&lt;b&gt;x&lt;/b&gt;</b></p>", ra


def test_khong_con_phu_thuoc_goi_markdown():
    """Kiem MA NGUON, khong kiem goi da cai: may nao con markdown trong venv thi
    van chay duoc du da bo — cai can chan la co ai goi lai no khong."""
    # Doc bang ast (E-r2-4): quet chuoi tho bao hong oan voi mot comment nhac
    # `import markdown`.
    import ast
    cay = ast.parse((ROOT / "nhat_ky_web.py").read_text(encoding="utf-8"))
    nhap = [n for n in ast.walk(cay)
            if (isinstance(n, ast.Import) and any(a.name.split(".")[0] == "markdown" for a in n.names))
            or (isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "markdown")]
    assert not nhap, "van con import markdown"
    goi = [n for n in ast.walk(cay) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and isinstance(n.func.value, ast.Name) and n.func.value.id == "markdown"]
    assert not goi, "van con goi markdown.*(...)"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
