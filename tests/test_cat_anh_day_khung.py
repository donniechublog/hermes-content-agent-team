#!/usr/bin/env python3
"""Anh chup NGANG duoc CAT BOT HAI BEN roi PHONG LEN cho gan day khung 4:5 —
khong con khoang trong lon vo ich phia tren (Ong Chu 13/09/2026, sau khi xem
4 slide render thu: "khoảng trống phía trên vẫn quá lớn... crop hình về [4:5]
nhưng vẫn giữ được chủ thể rõ ràng, ko bị mất đi phần quan trọng"; "vệt nhạt
cần được xử lý cho sạch").

Ba lop loi da bat duoc bang cach render THAT truoc khi sua:
  1. cat CAN GIUA HINH HOC lam dut chu "t" cua logo TSMC (chu the dat lech trai
     trong khung) -> phai do BIEN THAT cua chu the, khong bao gio cat vao trong.
  2. anh sau khi cat nho hon 1080px nhung KHONG duoc phong lai -> nam co lai
     giua khung voi vien trang bon phia, nhin nhu hinh vuong chu khong phai 4:5
     day khung -> phai CONTAIN-FIT (phong to duoc, khong chi thu nho).
  3. lap day GAN NHU TOAN BO chieu cao khien tieu de de thang len anh, cong bao
     ve tuong phan cua carousel.py (_lop_neu_can) phai phu mot dai xam day —
     chinh la "vet nhat" — vi khong con nen PHANG nao ngay tren cho chu se nam
     de cong do bo qua -> phai CHUA lap day 100%, danh lai mot dai nen phang
     (via `lap_day` + `cao_tren` thap) lam nen sach cho tieu de.

Chay:  venv/bin/python tests/test_cat_anh_day_khung.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import chup_trang                                              # noqa: E402


def _anh_don_sac(tmp: Path, w, h, nen=(10, 10, 12), chu_the=(220, 30, 30),
                 x0=None, x1=None) -> Path:
    """Anh gia: nen don sac + mot khoi CHU THE mau khac tu cot x0..x1 (mac
    dinh gan het be ngang, giong logo TSMC that: tran ca hai canh)."""
    from PIL import Image
    if x0 is None:
        x0, x1 = int(w * 0.03), int(w * 0.94)
    im = Image.new("RGB", (w, h), nen)
    px = im.load()
    for x in range(x0, x1):
        for y in range(int(h * 0.3), int(h * 0.7)):
            px[x, y] = chu_the
    p = tmp / "in.png"
    im.save(p)
    return p


def test_cat_can_giua_hinh_hoc_se_dut_nhung_bien_that_thi_khong():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        # Chu the tran gan het be ngang (nhu "tsmc" that) — cat theo trong tam/
        # tam hinh hoc deu se dut, chi bien That moi giu tron.
        p = _anh_don_sac(tmp, 1242, 828)
        bien = chup_trang._bien_chu_the_x(__import__("PIL.Image", fromlist=["Image"]).open(p))
        assert bien is not None
        trai_px, phai_px = round(bien[0] * 1241), round(bien[1] * 1241)
        assert trai_px <= int(1242 * 0.03) + 2 and phai_px >= int(1242 * 0.94) - 2, bien
        ra = tmp / "out.png"
        w, h = chup_trang.dem_nen(p, ra, "rgb(10,10,12)")
        assert abs(w / h - 0.8) < 0.01
        from PIL import Image
        im = Image.open(ra).convert("RGB")
        # Diem gan MEP TRAI cua chu the (nam trong anh da cat) phai VAN la mau
        # chu the (220,30,30), khong bi cat mat.
        # Tim toa do x cua chu the trong anh KET QUA bang cach do sang tu trai.
        w_ra, h_ra = im.size
        # Nen gia dinh dat 0.78 lap day + cao_tren nho -> anh nam gan dinh khung
        # va PHONG cho gan day be ngang (PAD_MIN=40 nen w_img >= W-40) -> quet
        # tu hai bien canvas la du de kiem chu the CO con hay khong.
        hang = [im.getpixel((x, int(h_ra * 0.45))) for x in range(w_ra)]
        # PAD_MIN=40 -> anh (du da phong het co) van co ~20px vien nen moi ben;
        # quet mot dai 30px ngay sau vien do, khong phai dung 1-2px dau/cuoi.
        assert any(c == (220, 30, 30) for c in hang[15:45]), "mep trai cua chu the bi cat mat"
        assert any(c == (220, 30, 30) for c in hang[-45:-15]), "mep phai cua chu the bi cat mat"


def test_anh_sau_khi_cat_duoc_phong_len_gan_day_khung_khong_con_nho_giua_nen():
    """Bug thu hai: truoc day anh cat gon van GIU NGUYEN kich thuoc nho, khong
    duoc phong len — nam co lai giua khung 1080x1350 voi vien nen bon phia,
    nhin nhu mot hinh vuong nho co khung trang bao quanh."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        p = _anh_don_sac(tmp, 1600, 900, x0=700, x1=900)  # ngang manh + chu the hep, GIUA khung
        ra = tmp / "out.png"
        w, h = chup_trang.dem_nen(p, ra, "#ffffff")
        assert (w, h) == (1080, 1350)
        from PIL import Image
        im = Image.open(ra).convert("RGB")
        # Anh (mau nen toi (10,10,12)) phai chiem GAN HET be ngang canvas —
        # truoc sua no chi rong bang be ngang GOC (nho hon 1080 nhieu).
        hang_tren = [im.getpixel((x, 100)) for x in range(w)]
        rong_anh = sum(1 for c in hang_tren if sum(c) < 100)
        assert rong_anh > w * 0.85, f"anh chi chiem {rong_anh}/{w} px be ngang — chua duoc phong day khung"


def test_khong_lap_day_100_phan_tram_de_lai_nen_phang_cho_tieu_de():
    """Bug thu ba (vet nhat): lap day toan bo chieu cao khien tieu de de len
    anh, cong bao ve tuong phan cua carousel.py phai phu lop xam day. Phai
    con lai mot dai NEN PHANG (mau_nen) ngay duoi anh."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        p = _anh_don_sac(tmp, 1600, 900, nen=(5, 5, 5))
        ra = tmp / "out.png"
        w, h = chup_trang.dem_nen(p, ra, "#ffffff")
        from PIL import Image
        im = Image.open(ra).convert("RGB")
        # Vung gan DAY canvas (noi tieu de/chip se nam) phai la MAU NEN (trang),
        # khong phai con dinh vao anh toi.
        duoi = im.getpixel((w // 2, h - 30))
        assert sum(duoi) > 700, f"gan day canvas van la anh toi ({duoi}), khong con nen phang cho chu"


def test_du_nguyen_lieu_khong_can_cat_khi_anh_da_du_dung():
    """Anh da gan 4:5 (khong ngang) thi khong cham vao — chi nhanh NGANG moi cat.
    Dung mot anh MAU DAC TOAN BO KHUNG (khong phan biet nen/chu the) de do
    dung khoi da dan trong canvas: ti le CUA CHINH KHOI DO phai giu nguyen 0.8
    (goc), khong bi hep lai — neu co crop lam meo ti le se lo ngay o day."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        p = tmp / "in.png"
        Image.new("RGB", (900, 1125), (30, 30, 200)).save(p)   # 0.8, dung 4:5 roi
        ra = tmp / "out.png"
        chup_trang.dem_nen(p, ra, "#ffffff")
        im = Image.open(ra).convert("RGB")
        w_c, h_c = im.size

        def la_anh(px):
            return abs(px[0] - 30) < 20 and abs(px[1] - 30) < 20 and abs(px[2] - 200) < 20

        cols = [x for x in range(w_c) if any(la_anh(im.getpixel((x, y))) for y in range(0, h_c, 5))]
        rows = [y for y in range(h_c) if any(la_anh(im.getpixel((x, y))) for x in range(0, w_c, 5))]
        assert cols and rows, "khong tim thay anh trong canvas ra"
        w_khoi, h_khoi = max(cols) - min(cols) + 1, max(rows) - min(rows) + 1
        assert abs(w_khoi / h_khoi - 0.8) < 0.03, (w_khoi, h_khoi)


if __name__ == "__main__":
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
