#!/usr/bin/env python3
"""ranking.py: dang ky nguon (NGUON/CHU_DE) va tach ten model — sinh sau su co
09/09/2026. Ong Chu gui hai anh chup Arena ("Image Edit Arena" va "Text-to-Image
Arena" deu xep GPT-Image-2.5 #1&#2) va noi "lam thong tin ve model ma khong dua
duoc 2 chart nay vao la qua kem". Do ra hai lo hong CHONG NHAU, ca hai deu hong
cau lang (khong loi, chi la khong bao gio ra anh dung):

  - "Image Edit Arena" (arena.ai/leaderboard/image-edit) KHONG co trong NGUON —
    xac nhan bang WebFetch truoc khi them, board that, 55 model, du lieu khop
    hoan toan anh Ong Chu gui (sunburst 1520, flare 1491, gpt-image-2 medium 1461).
  - `_DUOI` khong co "Sunburst"/"Flare" (ten ma cua HAI bien the CUNG mot ho tren
    CUNG mot bang) nen `extract_model` dung o "GPT Image 2.5" — khop nhap nhang ca
    hai hang, engine khoanh hang nao tim thay truoc bat ke tin noi ve bien the nao.

Sau khi sua xong ca hai, Ong Chu bac lai de xuat "chi lay MOT anh xep hang moi
tin" (ban dau cua `find_and_capture`): *"đã làm social media thì làm gì có chuyện bị
giới hạn ở nguồn tư liệu"*, và hai bang vi du *"một bảng là top model tạo sinh,
một bảng là top model chỉnh sửa, đâu có trùng lặp"*. `find_and_capture_many` +
`_skip_source` la ket qua: nguon `doc_lap: True` (nang luc rieng, khong phai
cach do khac cua cung mot thu) khong bao gio bi mot thanh cong khac chan lai.

Chay:  venv/bin/python tests/test_xep_hang.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import ranking as xh   # noqa: E402


# --------------------------------------------------------------- registry
def test_co_nguon_image_edit_arena():
    """arena-image-edit phai co trong NGUON, dung URL that (da WebFetch xac
    nhan truoc khi them: 55 model, du lieu khop anh Ong Chu gui 09/09/2026)."""
    ma = {n["ma"]: n for n in xh.SOURCE}
    assert "arena-image-edit" in ma, "thieu nguon Image Edit Arena trong NGUON"
    n = ma["arena-image-edit"]
    assert n["url"] == "https://arena.ai/leaderboard/image-edit"
    assert n["site"] == "ARENA.AI"


def test_khong_trung_ma_nguon():
    ma = [n["ma"] for n in xh.SOURCE]
    assert len(ma) == len(set(ma)), f"trung ma nguon: {ma}"


# ----------------------------------------------------------------- tach_model
def test_tach_model_giu_ten_ma_bien_the():
    """Sunburst/Flare la ten ma CUA CHINH HAI HANG dang xep #1 va #2 tren cung
    mot bang (Image Edit Arena, du lieu that 09/09/2026). Mat ten ma thi ca hai
    hang deu chi con "GPT Image 2.5", khong con phan biet duoc dung hang nao."""
    assert xh.extract_model("GPT-Image-2.5 Sunburst dung dau Image Edit Arena")[0] \
        == "GPT-Image-2.5 Sunburst"
    assert xh.extract_model("GPT Image 2.5 Flare xep #2 bang chinh sua anh")[0] \
        == "GPT Image 2.5 Flare"


def test_tach_model_van_co_ten_ngan_du_phong():
    """Ten day nhat dung truoc, nhung ban ngan hon ("GPT Image 2.5" tran) van
    phai con trong danh sach — trang xep hang co the ghi khac chinh ta ten ma,
    luc do engine lui ve ban ngan de con co gang khop."""
    ra = xh.extract_model("GPT-Image-2.5 Sunburst dung dau Image Edit Arena")
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
        assert xh.extract_model(tieu_de) == ky_vong, f"{tieu_de!r}: {xh.extract_model(tieu_de)} != {ky_vong}"
    # "seed" mot minh KHONG duoc nhan (_HO_CAN_SO doi di kem so) — tin goi von
    # "vong seed" khong duoc keo vao engine xep hang.
    assert xh.extract_model("vong seed do Nvidia dan dau") == []


# --------------------------------------------------------------- goi_y_nguon
def test_link_image_edit_uu_tien_dung_bang_do():
    """Tin CO LINK toi image-edit thi nguon do phai len DAU danh sach (nhac
    truc tiep, +500 diem) — khong bi bang t2i chen truoc chi vi dung tu 'image'."""
    ds = xh.suggest_sources("GPT-Image-2.5 Sunburst dung #1 Image Edit Arena",
                        "https://arena.ai/leaderboard/image-edit", "", "")
    assert ds[0]["ma"] == "arena-image-edit", [n["ma"] for n in ds[:3]]
    assert ds[0]["duoc_nhac"] is True


def test_tin_tao_anh_chung_chung_van_xet_ca_hai_bang():
    """Tin ve tao anh (khong noi ro edit) khong co link: arena-t2i va
    arena-image-edit phai CUNG nam trong top nguon thu — mot model tao anh manh
    thuong len ca hai bang (du lieu that: GPT-Image-2.5 #1&#2 CA HAI bang cung
    luc), tim_va_chup se lan luot thu tung nguon."""
    ds = xh.suggest_sources("GPT Image 2.5 dan dau bang tao anh AI", "", "", "")
    top5 = [n["ma"] for n in ds[:5]]
    assert "arena-t2i" in top5 and "arena-image-edit" in top5, top5


def test_tin_chinh_sua_anh_uu_tien_bang_edit_hon_t2i():
    """Tu khoa 'chỉnh sửa ảnh' phai keo arena-image-edit len TRUOC arena-t2i —
    hai bang do khac nang luc (sua anh vs tao anh tu dau), khong the lan nhau.
    Chuoi tieu de PHAI giu dau tieng Viet: regex khop dau, "chinh sua anh"
    khong dau se khong khop gi ca (tu ky nghiem 09/09/2026, ban dau viet
    khong dau lam test nay bao FAIL nham khi code dung)."""
    ds = xh.suggest_sources("Model X dẫn đầu bảng chỉnh sửa ảnh bằng AI", "", "", "")
    ma_thu_tu = [n["ma"] for n in ds]
    assert ma_thu_tu.index("arena-image-edit") < ma_thu_tu.index("arena-t2i"), ma_thu_tu[:5]


# ------------------------------------------------------- doc_lap / _bo_qua_nguon
def test_hai_nguon_doc_lap_khong_chan_nhau():
    """Ca hai bang GPT-Image-2.5 dung dau (tao anh, sua anh) deu doc_lap: da
    chup duoc mot cai KHONG duoc chan cai kia — dung yeu cau cua Ong Chu 09/09."""
    t2i = {"ma": "arena-t2i", "doc_lap": True}
    edit = {"ma": "arena-image-edit", "doc_lap": True}
    assert xh._skip_source(edit, da_chup_thuong=False) is False
    # da chup MOT nguon "thuong" khac (khong lien quan) truoc do van khong chan
    # nguon doc_lap:
    assert xh._skip_source(t2i, da_chup_thuong=True) is False
    assert xh._skip_source(edit, da_chup_thuong=True) is False


def test_nguon_thuong_dung_sau_thanh_cong_dau_tien():
    """arena-code/swebench/aider/livecodebench la BON CACH DO cua CUNG mot nang
    luc — thanh cong o mot nguon THUONG phai chan cac nguon THUONG con lai,
    dung hanh vi cu cua `find_and_capture` (khong lap lai cung mot bang chung)."""
    code = {"ma": "arena-code"}                          # khong doc_lap
    swebench = {"ma": "swebench"}
    assert xh._skip_source(code, da_chup_thuong=False) is False
    assert xh._skip_source(swebench, da_chup_thuong=True) is True


def test_kich_ban_that_gpt_image_2_5_lay_ca_hai_bang():
    """Mo phong DUNG trinh tu quyet dinh cua vong lap trong tim_va_chup_nhieu
    (khong dung Playwright that) cho ca that: tieu de nhac thang link Image Edit
    Arena — arena-image-edit len dau danh sach, arena-t2i theo sau, roi cac bang
    khong lien quan (arena-text...). Ket qua ca hai bang GPT-Image-2.5 deu duoc
    thu, khong bang nao bi bo vi bang kia da thanh cong."""
    ds = xh.suggest_sources("GPT-Image-2.5 Sunburst dung #1 Image Edit Arena",
                        "https://arena.ai/leaderboard/image-edit", "", "")
    da_chup_thuong = False
    thu = []
    for n in ds[:6]:                      # tran gio han/toi_da khong can mo phong o day
        if xh._skip_source(n, da_chup_thuong):
            continue
        thu.append(n["ma"])               # gia dinh MOI nguon duoc thu deu "chup thanh cong"
        if not n.get("doc_lap"):
            da_chup_thuong = True
    assert "arena-image-edit" in thu and "arena-t2i" in thu, thu
    # Tin CHI ve mot nang luc (code) thi khong duoc keo them nguon thuong khac
    ds2 = xh.suggest_sources("Kimi-K3 leo len #1 Frontend Code Arena", "", "", "")
    da_chup_thuong2 = False
    thu2 = []
    for n in ds2[:6]:
        if xh._skip_source(n, da_chup_thuong2):
            continue
        thu2.append(n["ma"])
        if not n.get("doc_lap"):
            da_chup_thuong2 = True
    assert thu2 == ["arena-code"], f"tin code bi keo them nguon thuong khac: {thu2}"


def test_ca_ba_bang_anh_cua_gpt_image_2_5():
    """Ca that dung tieu de draft (09/09/2026): tweet cong bo cua @arena xep
    gpt-image-2.5-sunburst #1 CA BA bang — Text-to-Image, Image Edit, Multi-Image
    Edit — trong cung mot tweet. Mo phong voi tran TOI_DA_XH nhu vong lap that."""
    ds = xh.suggest_sources(
        "gpt-image-2.5-sunburst mới vào arena, giữ #1 cả bảng tạo ảnh lẫn sửa ảnh",
        "https://arena.ai/leaderboard/text-to-image", "", "")
    da_chup_thuong, thu = False, []
    for n in ds:
        if len(thu) >= xh.MAX_XH:
            break
        if xh._skip_source(n, da_chup_thuong):
            continue
        thu.append(n["ma"])
        if not n.get("doc_lap"):
            da_chup_thuong = True
    assert thu == ["arena-t2i", "arena-image-edit", "arena-multi-image-edit"], thu


def test_khong_doi_hop_dong_tim_va_chup_cu():
    """`find_and_capture` (so, khong "_nhieu") phai con nguyen — `_ranking_context_edge`
    trong image_prepare.py va CLI main() van goi ham nay, doi dung MOT dict."""
    import inspect
    sig = inspect.signature(xh.find_and_capture)
    assert "toi_da" not in sig.parameters, "tim_va_chup bi doi hop dong, se vo hieu _xep_hang_boi_canh"
    src = inspect.getsource(xh.find_and_capture)
    assert "return kq_cuoi" in src and "break" in src, "tim_va_chup khong con dung o thanh cong dau tien"


def test_hang_tu_tieu_de_khong_lay_sang_bang_doc_lap():
    """R-r2-5: hang tach tu tieu de la hang tren bang CHINH; bang doc lap
    (do nang luc khac, nguon svg tra hang=None) khong duoc muon "#1" do."""
    goi_y = 1
    assert xh._rank_of({"hang": 3}, {"doc_lap": True}, goi_y) == 3, "hang doc duoc tu bang thi giu"
    assert xh._rank_of({"hang": None}, {"doc_lap": False}, goi_y) == 1, "bang chinh muon hang tieu de"
    assert xh._rank_of({"hang": None}, {"doc_lap": True}, goi_y) is None, "bang doc lap KHONG muon"
    assert xh._rank_of({}, {}, None) is None


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
