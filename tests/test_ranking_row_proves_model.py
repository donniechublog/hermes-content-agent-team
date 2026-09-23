#!/usr/bin/env python3
"""Anh xep hang phai CHUNG MINH claim cua bai — su co 15/09/2026 (LOW-177/179/180).

Ba bai lien cua Ethan (dcgr) ra anh sai, doc tu xong.json tren may chu:

  bai "V4 Flash hang 2"          -> khoanh '9. | DeepSeek Harness | new | 138Btokens'
  bai "V4 Pro lot top 10"        -> khoanh '5. | DeepSeek V4.1 Flash | by | deepseek | 14.4M'
  bai "HuggingFace tha trong so" -> khoanh '9. | DeepSeek Harness | new | 138Btokens'

md5 ba PNG khac nhau: khong phai cache anh, ma chup lai ba lan va lan nao cung
khoanh trung hang sai. Ba tang gop lai:

  1. `extract_model` bot ten model toi "DeepSeek" — TEN HANG TRAN. Bang Apps cua
     openrouter co hang "DeepSeek Harness" (app cua nguoi khac) nen no "chua
     model", thang ca cot model that. (LOW-177)
  2. `_rank_of` muon hang o TIEU DE khi hang chup duoc khong doc ra so hang, nen
     alt ghi "#2" de len tam anh dang khoanh hang 9. (LOW-177)
  3. Nguon khong duoc bai nhac, khong dung chu de bai van duoc chup lam anh
     chinh — tin HuggingFace ra bang luot dung openrouter. (LOW-179)
  4. Cau ta anh khang dinh "da khoanh hang model" ma khong bao gio in `dong`, nen
     ca vai lan nguoi duyet deu khong co gi de soat. (LOW-180)

Luat Ong Chu 16/09/2026: tuyet doi khong chup dai chart roi dua vao minh hoa.

DIEU KIEN BIEN trong JS (`matchesModel`: ky tu sau cho khop khong duoc la chu so,
de "deepseekv4" khong an "deepseekv41flash") KHONG test duoc o day — no chay
trong trinh duyet, repo khong co harness DOM. Da kiem tay tren openrouter.ai
thay: truoc va la 'DeepSeek' -> hang 9 "DeepSeek Harness", sau va khong con nhom
nao khop.

Chay:  venv/bin/python tests/test_ranking_row_proves_model.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import ranking as xh                                        # noqa: E402
from prepare.manifest import describe_ranking_image         # noqa: E402

# Ba tieu de THAT cua ba task 15/09/2026.
TD_FLASH = "DeepSeek V4 Flash 0423 leo một bậc lên hạng 2 OpenRouter"
TD_PRO = "DeepSeek V4 Pro lần đầu lọt top 10 lượt dùng trên OpenRouter"
TD_HF = "deepseek-ai/DeepSeek-V4.1-Flash thả trọng số HuggingFace, trending 2327"


# ------------------------------------------------- LOW-177: khong nha ten hang tran
def test_khong_nha_ten_hang_tran_lam_ung_vien():
    """'DeepSeek' mot minh khop ca "DeepSeek Harness" — hang KHONG PHAI model."""
    for td in (TD_FLASH, TD_PRO, TD_HF):
        ms = xh.extract_model(td)
        assert ms, td
        assert "DeepSeek" not in ms, f"{td!r}: {ms}"


def test_van_giu_ung_vien_mot_tu_CO_SO():
    """Khong duoc vet qua rong: "GPT-6" mot tu nhung co so, van dinh danh model."""
    assert xh.extract_model("GPT-6 Astra vuot moc 55 diem") == ["GPT-6 Astra", "GPT-6"]


def test_van_giu_ung_vien_hai_tu_khong_so():
    """"Muse Spark" hai tu nen con la ten model, khong phai ten hang."""
    assert xh.extract_model("Muse Spark 1.2 duoc danh gia cao") == ["Muse Spark 1.2", "Muse Spark"]


# ------------------------------------------------- LOW-177: khong muon hang tieu de
def test_anh_chup_khong_ro_hang_thi_de_trong():
    """Log that cua task V4 Flash: "khớp 'DeepSeek' hàng #?" — hang khong doc ra
    duoc. Truoc va, alt ghi "#2" (hang o tieu de) de len anh khoanh hang 9."""
    kq = {"kind": "list-stitched", "model": "DeepSeek", "rank": None,
          "row": "9. | DeepSeek Harness | new | 138Btokens"}
    assert xh._rank_of(kq, {"id": "openrouter"}, 2) is None


def test_anh_chup_co_hang_thi_dung_hang_cua_chinh_no():
    kq = {"kind": "table", "model": "GPT-6 Astra", "rank": 3, "row": "3. | GPT-6 Astra"}
    assert xh._rank_of(kq, {"id": "arena-text"}, 1) == 3


def test_the_du_phong_van_duoc_dung_hang_tieu_de():
    """The la CHU engine tu in, khong phai bang chung chup tu bang nao."""
    kq = {"kind": "card", "model": "GPT-6 Astra", "rank": None, "row": ""}
    assert xh._rank_of(kq, {"id": "arena-text"}, 1) == 1


# ------------------------------------------------- LOW-179: khong thay bang khac
def test_nguon_vo_duoc_trong_registry_khong_du_tu_cach():
    assert xh.source_proves_story({"id": "openrouter"}) is False
    assert xh.source_proves_story({"id": "openrouter", "mentioned": False,
                                   "on_topic": False}) is False


def test_nguon_duoc_nhac_hoac_dung_chu_de_thi_du():
    assert xh.source_proves_story({"id": "x", "mentioned": True}) is True
    assert xh.source_proves_story({"id": "x", "on_topic": True}) is True


def test_doc_lap_mot_minh_khong_phai_tu_cach():
    """Voi tin HuggingFace tha trong so, ba bang arena anh (doc_lap) la nhung
    nguon DUY NHAT lot qua neu tinh doc_lap — bang dau model tao anh minh hoa
    cho tin tha trong so mot model van ban. Viec that cua doc_lap o _skip_source."""
    assert xh.source_proves_story({"id": "arena-t2i", "independent": True}) is False


def test_ca_nhieu_bang_doc_lap_van_du_tu_cach_qua_on_topic():
    """Khong duoc pha ca doc_lap sinh ra de phuc vu: GPT-Image len ca bang tao
    anh lan bang chinh sua anh — ca ba bang do deu on_topic."""
    ds = {n["id"]: n for n in xh.suggest_sources("GPT-Image-2.5 Sunburst dựng #1 Image Edit Arena",
                                                 "", "", "")}
    for ma in ("arena-t2i", "arena-image-edit", "arena-multi-image-edit"):
        assert xh.source_proves_story(ds[ma]) is True, ma


def test_tin_luot_dung_gio_khong_con_nguon_nao():
    """LOW-389 (23/09/2026): openrouter ra khoi duong ANH han — Ong Chu bo no tu
    LOW-185 nhung luc do chi go o `scan_models`. Cai gia da biet truoc: hai tin
    luot dung nay tu nay ra THE CHU."""
    for td in (TD_FLASH, TD_PRO):
        assert "openrouter" not in {n["id"] for n in xh.suggest_sources(td, "", "", "")}
        assert [n["id"] for n in xh.suggest_sources(td, "", "", "")
                if xh.source_proves_story(n)] == [], td


def test_tin_tha_trong_so_khong_duoc_lay_bang_nao():
    """Bai hoc goc (LOW-179): tin tha trong so tung ra anh bang LUOT DUNG. Gio bang
    do khong con, va khong bang arena nao du tu cach — dung ra the chu."""
    assert [n["id"] for n in xh.suggest_sources(TD_HF, "", "", "")
            if xh.source_proves_story(n)] == []


def test_on_topic_doc_o_tieu_de_khong_doc_than_bai():
    """Bai hoc LOW-22: than bai lam moi nguon trong nhu duoc nhac."""
    ds = {n["id"]: n for n in xh.suggest_sources(
        TD_HF, "", "", "Bang text-to-image arena cho thay diem tang manh.")}
    assert ds["arena-t2i"]["on_topic"] is False
    assert ds["arena-t2i"]["mentioned"] is False


def test_loc_nguon_noi_ra_da_bo_bao_nhieu():
    ghi = []
    ds = xh.suggest_sources(TD_HF, "", "", "")
    assert xh._sources_proving_story(ds, ghi.append) == []
    assert ghi and "không chứng minh" in ghi[0], ghi


# ------------------------------------------------- LOW-180: in ra hang that
def test_cau_ta_anh_in_ra_hang_da_khoanh():
    xhd = {"site": "OPENROUTER.AI", "board": "LLM Rankings (lượt dùng)", "kind": "list-stitched",
           "model": "DeepSeek", "rank": 2, "mentioned": True,
           "row": "9. | DeepSeek Harness | new | 138Btokens"}
    cau = describe_ranking_image({"ranking": xhd})
    assert "DeepSeek Harness" in cau, cau
    assert "đã khoanh hàng model" not in cau, cau


def test_the_du_phong_van_noi_ro_la_the():
    cau = describe_ranking_image({"ranking": {"site": "S", "board": "B", "kind": "card",
                                              "model": "M", "rank": 1}})
    assert "THẺ DỰ PHÒNG" in cau, cau


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
