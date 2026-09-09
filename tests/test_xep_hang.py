#!/usr/bin/env python3
"""xep_hang.py: dang ky nguon (NGUON/CHU_DE) va tach ten model — sinh sau su co
09/09/2026. Ong Chu gui hai anh chup Arena ("Image Edit Arena" va "Text-to-Image
Arena" deu xep GPT-Image-2.5 #1&#2) va noi "lam thong tin ve model ma khong dua
duoc 2 chart nay vao la qua kem". Do ra hai lo hong CHONG NHAU, ca hai deu hong
cau lang (khong loi, chi la khong bao gio ra anh dung):

  - "Image Edit Arena" (arena.ai/leaderboard/image-edit) KHONG co trong NGUON —
    xac nhan bang WebFetch truoc khi them, board that, 55 model, du lieu khop
    hoan toan anh Ong Chu gui (sunburst 1520, flare 1491, gpt-image-2 medium 1461).
  - `_DUOI` khong co "Sunburst"/"Flare" (ten ma cua HAI bien the CUNG mot ho tren
    CUNG mot bang) nen `tach_model` dung o "GPT Image 2.5" — khop nhap nhang ca
    hai hang, engine khoanh hang nao tim thay truoc bat ke tin noi ve bien the nao.

Chay:  venv/bin/python tests/test_xep_hang.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import xep_hang as xh   # noqa: E402


# --------------------------------------------------------------- registry
def test_co_nguon_image_edit_arena():
    """arena-image-edit phai co trong NGUON, dung URL that (da WebFetch xac
    nhan truoc khi them: 55 model, du lieu khop anh Ong Chu gui 09/09/2026)."""
    ma = {n["ma"]: n for n in xh.NGUON}
    assert "arena-image-edit" in ma, "thieu nguon Image Edit Arena trong NGUON"
    n = ma["arena-image-edit"]
    assert n["url"] == "https://arena.ai/leaderboard/image-edit"
    assert n["site"] == "ARENA.AI"


def test_khong_trung_ma_nguon():
    ma = [n["ma"] for n in xh.NGUON]
    assert len(ma) == len(set(ma)), f"trung ma nguon: {ma}"


# ----------------------------------------------------------------- tach_model
def test_tach_model_giu_ten_ma_bien_the():
    """Sunburst/Flare la ten ma CUA CHINH HAI HANG dang xep #1 va #2 tren cung
    mot bang (Image Edit Arena, du lieu that 09/09/2026). Mat ten ma thi ca hai
    hang deu chi con "GPT Image 2.5", khong con phan biet duoc dung hang nao."""
    assert xh.tach_model("GPT-Image-2.5 Sunburst dung dau Image Edit Arena")[0] \
        == "GPT-Image-2.5 Sunburst"
    assert xh.tach_model("GPT Image 2.5 Flare xep #2 bang chinh sua anh")[0] \
        == "GPT Image 2.5 Flare"


def test_tach_model_van_co_ten_ngan_du_phong():
    """Ten day nhat dung truoc, nhung ban ngan hon ("GPT Image 2.5" tran) van
    phai con trong danh sach — trang xep hang co the ghi khac chinh ta ten ma,
    luc do engine lui ve ban ngan de con co gang khop."""
    ra = xh.tach_model("GPT-Image-2.5 Sunburst dung dau Image Edit Arena")
    assert "GPT-Image-2.5" in ra, ra


def test_tach_model_khong_doi_hanh_vi_cu():
    """Cac vi du CHINH module tu ghi trong docstring/comment cua no — khong duoc
    doi khi them Sunburst/Flare vao _DUOI."""
    ca = [
        ("GPT-6 Astra (max) vuot moc 55 diem",
         ["GPT-6 Astra (max)", "GPT-6 Astra", "GPT-6"]),
        ("Kimi-K3 leo len #1 Frontend Code Arena", ["Kimi-K3"]),
        ("Qwen3.8-27B ra mat", ["Qwen3.8-27B"]),
        ("GLM-5.2 (Max) xep hang 3", ["GLM-5.2 (Max)", "GLM-5.2"]),
        ("Muse Spark 1.2 duoc danh gia cao", ["Muse Spark 1.2", "Muse Spark", "Muse"]),
    ]
    for tieu_de, ky_vong in ca:
        assert xh.tach_model(tieu_de) == ky_vong, f"{tieu_de!r}: {xh.tach_model(tieu_de)} != {ky_vong}"
    # "seed" mot minh KHONG duoc nhan (_HO_CAN_SO doi di kem so) — tin goi von
    # "vong seed" khong duoc keo vao engine xep hang.
    assert xh.tach_model("vong seed do Nvidia dan dau") == []


# --------------------------------------------------------------- goi_y_nguon
def test_link_image_edit_uu_tien_dung_bang_do():
    """Tin CO LINK toi image-edit thi nguon do phai len DAU danh sach (nhac
    truc tiep, +500 diem) — khong bi bang t2i chen truoc chi vi dung tu 'image'."""
    ds = xh.goi_y_nguon("GPT-Image-2.5 Sunburst dung #1 Image Edit Arena",
                        "https://arena.ai/leaderboard/image-edit", "", "")
    assert ds[0]["ma"] == "arena-image-edit", [n["ma"] for n in ds[:3]]
    assert ds[0]["duoc_nhac"] is True


def test_tin_tao_anh_chung_chung_van_xet_ca_hai_bang():
    """Tin ve tao anh (khong noi ro edit) khong co link: arena-t2i va
    arena-image-edit phai CUNG nam trong top nguon thu — mot model tao anh manh
    thuong len ca hai bang (du lieu that: GPT-Image-2.5 #1&#2 CA HAI bang cung
    luc), tim_va_chup se lan luot thu tung nguon."""
    ds = xh.goi_y_nguon("GPT Image 2.5 dan dau bang tao anh AI", "", "", "")
    top5 = [n["ma"] for n in ds[:5]]
    assert "arena-t2i" in top5 and "arena-image-edit" in top5, top5


def test_tin_chinh_sua_anh_uu_tien_bang_edit_hon_t2i():
    """Tu khoa 'chỉnh sửa ảnh' phai keo arena-image-edit len TRUOC arena-t2i —
    hai bang do khac nang luc (sua anh vs tao anh tu dau), khong the lan nhau.
    Chuoi tieu de PHAI giu dau tieng Viet: regex khop dau, "chinh sua anh"
    khong dau se khong khop gi ca (tu ky nghiem 09/09/2026, ban dau viet
    khong dau lam test nay bao FAIL nham khi code dung)."""
    ds = xh.goi_y_nguon("Model X dẫn đầu bảng chỉnh sửa ảnh bằng AI", "", "", "")
    ma_thu_tu = [n["ma"] for n in ds]
    assert ma_thu_tu.index("arena-image-edit") < ma_thu_tu.index("arena-t2i"), ma_thu_tu[:5]


if __name__ == "__main__":
    ham = [v for k, v in list(globals().items()) if k.startswith("test_")]
    loi = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"FAIL {h.__name__}: {e}")
    print(f"\n{len(ham) - loi}/{len(ham)} test qua")
    sys.exit(1 if loi else 0)
