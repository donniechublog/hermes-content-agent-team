#!/usr/bin/env python3
"""Cong chan cho bo bang xep hang cua Nova.

Vi sao co tep nay: 06/09/2026 mo tu 12 len 20 bang. Ba loi ben duoi deu la loai
KHONG BAO GI CA — script van chay, bao cao van in, chi la Nova mat tin hoac mat
link, va phai vai ngay sau moi co nguoi de y:

  1. Them bang ma quen khai LABEL_BOARD  -> muc "leo hang" in ra ma khoa tho
  2. Them bang ma quen khai LINK_BOARD  -> muc BAT BUOC ra link RONG, vai nop
     tin khong co nguon
  3. In danh sach BAT BUOC hai lan     -> ton 5.600 ky tu o cuoi bao cao, dung
     cho de bi tran cat mat truoc tien

Chay: venv/bin/python tests/test_bang_nova.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import required                                             # noqa: E402
import scan_models as s                                     # noqa: E402

KHOA_BANG = s.LOCK_BOARD

qua = loi = 0


def kiem(ten, dieu_kien, ghi_chu=""):
    global qua, loi
    if dieu_kien:
        qua += 1
        print(f"OK   {ten}")
    else:
        loi += 1
        print(f"HONG {ten}  {ghi_chu}")


def test_moi_bang_co_nhan():
    thieu = [k for k in KHOA_BANG if k not in s.LABEL_BOARD]
    kiem("test_moi_bang_co_nhan", not thieu,
         f"thieu LABEL_BOARD cho: {thieu}")


def test_moi_bang_co_link():
    # `hf` khong nam trong KHOA_BANG (khong phai bang xep hang) nhung muc bat
    # buoc cua no tu mang link rieng — kiem rieng o duoi.
    thieu = [k for k in KHOA_BANG if not required.LINK_BOARD.get(k)]
    kiem("test_moi_bang_co_link", not thieu,
         f"thieu LINK_BOARD cho: {thieu} -> muc bat buoc se ra link rong")


def test_link_bang_deu_la_url():
    xau = [k for k, v in required.LINK_BOARD.items() if not v.startswith("https://")]
    kiem("test_link_bang_deu_la_url", not xau, f"khong phai https: {xau}")


def test_muc_hf_co_link_rieng():
    l = required.link_call_y({"loai": "hf", "ten": "deepseek-ai/X",
                             "link": "https://huggingface.co/deepseek-ai/X"})
    kiem("test_muc_hf_co_link_rieng", l == "https://huggingface.co/deepseek-ai/X")


def test_so_bang_khop_ban_ke_khai():
    kiem("test_so_bang_khop_ban_ke_khai", s.COUNT_BOARD == len(KHOA_BANG),
         f"COUNT_BOARD={s.COUNT_BOARD} nhung ke khai {len(KHOA_BANG)} bang")
    kiem("test_khong_trung_khoa_bang", len(set(KHOA_BANG)) == len(KHOA_BANG),
         "co khoa bang bi khai hai lan")


def test_main_kiem_lech_ban_ke_khai():
    """main() phai tu doi chieu bang_so voi LOCK_BOARD — them bang ma quen khai
    thi state khong co moc, va 'leo hang' cua bang do im lang mai mai."""
    src = Path(s.__file__).read_text(encoding="utf-8")
    kiem("test_main_kiem_lech_ban_ke_khai",
         "set(bang_so) ^ set(LOCK_BOARD)" in src)


def test_khong_in_bat_buoc_hai_lan():
    """scan_prepare PHAI goi scan_models voi --khong-bat-buoc, vi chinh no da
    in danh sach do mot lan roi (qua _required, nam NGOAI vung cat)."""
    src = (ROOT / "scan_prepare.py").read_text(encoding="utf-8")
    i = src.find("def brief_nova")
    j = src.find("def brief_market", i)
    kiem("test_khong_in_bat_buoc_hai_lan", "--khong-bat-buoc" in src[i:j],
         "brief_nova goi scan_models ma khong co --khong-bat-buoc")


def test_bao_cao_bi_cat_thi_noi_ra():
    """Cat cam lang la loi cu: Nova doc het bao cao roi ket luan 'khong co gi',
    trong khi that ra phan duoi da bi xen mat."""
    import scan_prepare as q
    dai = "x" * (q.CEILING_REPORT + 5000)
    ra = q._crop(dai)
    kiem("test_bao_cao_bi_cat_thi_noi_ra",
         "BAO CAO BI CAT" in ra and len(ra) < len(dai),
         "cat ma khong bao -> vai tuong nham la da doc het")
    ngan = "y" * 100
    kiem("test_bao_cao_ngan_thi_khong_dong_gi", q._crop(ngan) == ngan)


def test_tran_in_an_co_can_tren():
    """Ba muc nay truoc 06/09 khong co `[:n]`, mot ngay xau nuot sach phan duoi."""
    kiem("test_tran_in_an_co_can_tren",
         all(isinstance(v, int) and 0 < v < 100
             for v in (s.CEILING_GH, s.CEILING_HF, s.CEILING_BOARD)))


def test_bang_hong_thi_noi_ra():
    """Bang hong truoc day chi... khong in ra. Nova doc bao cao khong thay
    Terminal-Bench dau thi ket luan 'khong co gi moi o do' — trong khi that ra
    la khong lay duoc. Hai ket luan khac han nhau."""
    import contextlib
    import io as _io
    b = _io.StringIO()
    with contextlib.redirect_stdout(b):
        s._in_report({"bang_hong": ["tbench", "hle"]})
    ra = b.getvalue()
    kiem("test_bang_hong_thi_noi_ra",
         "NGUON KHONG LAY DUOC" in ra and "Terminal-B" in ra and "HLE" in ra,
         "khong bao ten bang hong -> vai tuong la bang do khong co tin")
    b2 = _io.StringIO()
    with contextlib.redirect_stdout(b2):
        s._in_report({"bang_hong": []})
    kiem("test_khong_hong_thi_im", "NGUON KHONG LAY DUOC" not in b2.getvalue())


def test_diem_cao_hon_la_tot_hon():
    """count_rank() gia dinh hang 1 = tot nhat. Bang STT cua AA cho ti le LOI (WER,
    THAP hon la tot hon) nen fetch_aa_media phai doi thanh do chinh xac; quen
    doi thi bang xep nguoc ma khong co gi bao."""
    src = s.__file__ and Path(s.__file__).read_text(encoding="utf-8")
    i = src.find("if ma == \"stt\"")
    doan = src[i:i + 700]
    kiem("test_diem_cao_hon_la_tot_hon", "(1 - float(wer))" in doan,
         "STT phai doi WER -> do chinh xac truoc khi vao bang")


def test_hang_rao_khong_de_mot_nguon_giet_ca_luot():
    """`_thu` phai nuot loi cua MOT nguon va ghi ten no lai.

    Truoc 06/09/2026 phan PARSE cua tung fetcher nam NGOAI try cua chinh no
    (`max(r["date"] ...)`, `float(v)`, `h < h_cu` khi thieu ranking...), nen mot
    thay doi schema o mot nguon giet ca 23 bang: stdout rong, khong ghi moc, va
    brief_nova van dua bao cao rong cho Nova -> "hom nay khong co gi"."""
    cu = list(s._HONG_KHAC)
    s._HONG_KHAC.clear()
    try:
        def nem():
            raise KeyError("date")
        kiem("test_hang_rao_nguon_nem", s._try("nguon-x", nem, ([], None)) == ([], None),
             "nguon nem phai tra ve gia tri rong dung hinh, khong nem tiep")
        kiem("test_hang_rao_ghi_ten", "nguon-x" in s._HONG_KHAC,
             "nguon hong phai duoc ghi ten de in vao muc NGUON KHONG LAY DUOC")
        kiem("test_hang_rao_nguon_lanh", s._try("nguon-y", lambda: [1, 2], []) == [1, 2]
             and "nguon-y" not in s._HONG_KHAC, "nguon chay duoc khong duoc bao hong")
    finally:
        s._HONG_KHAC[:] = cu


def test_moi_fetcher_trong_main_deu_qua_hang_rao():
    """Doc bang AST, khong grep chuoi: trong than `main`, moi loi goi `fetch_*`
    phai nam BEN TRONG mot loi goi `_try(...)`. Them nguon moi ma goi thang la
    mo lai dung cai cua da dong.

    Nhan HAI hinh dang (tu 09/09/2026, khi cac nguon chay song song):
      _try("ten", fn, mac_dinh)             — goi thang
      ex.submit(_thu, "ten", fn, mac_dinh)  — nop vao ThreadPoolExecutor
    Hinh thu hai VAN qua hang rao: submit goi chinh `_thu` trong luong con. Doi
    HOI `_thu` la tham so DAU tien, nen `ex.submit(fetch_x, ...)` — bo qua hang
    rao that su — van bi bat nhu truoc."""
    import ast
    cay = ast.parse(Path(s.__file__).read_text(encoding="utf-8"))
    main = next(n for n in cay.body
                if isinstance(n, ast.FunctionDef) and n.name == "main")

    def qua_hang_rao(n):
        if not isinstance(n, ast.Call):
            return False
        if isinstance(n.func, ast.Name) and n.func.id == "_try":
            return True
        return (isinstance(n.func, ast.Attribute) and n.func.attr == "submit"
                and bool(n.args) and isinstance(n.args[0], ast.Name)
                and n.args[0].id == "_try")

    trong_thu = set()
    ten_qua = set()                 # ham con trong main duoc DUA vao _thu theo ten
    for n in ast.walk(main):
        if qua_hang_rao(n):
            for con in ast.walk(n):
                trong_thu.add(id(con))
            ten_qua |= {a.id for a in n.args if isinstance(a, ast.Name)}
    # E-r2-5: `def _lay(): return fetch_x(...)` roi `_thu("x", _lay, {})` VAN qua
    # hang rao — chinh kieu refactor lambda -> def da bi bao oan mot lan.
    for n in ast.walk(main):
        if isinstance(n, ast.FunctionDef) and n.name in ten_qua:
            for con in ast.walk(n):
                trong_thu.add(id(con))

    thang = sorted({n.func.id for n in ast.walk(main)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id.startswith("fetch_") and id(n) not in trong_thu})
    kiem("test_moi_fetcher_trong_main_deu_qua_hang_rao", not thang,
         f"goi thang khong qua _thu: {thang}")


# ---------------------------------------------------------------- ban dang ky
# Tu 07/09/2026 sau cho khai bang (ARENA_BOARDS, KHOA_BANG, LABEL_BOARD, LINK_BOARD,
# khoi in trong _in_bao_cao, phan `ket` cua cac bang top) deu dan xuat tu
# model_boards.BOARD. Ba test dau cua tep nay gio la hien nhien — giu lai lam
# cong, nhung cai can canh chuyen sang chinh ban dang ky.
def test_ban_dang_ky_moi_bang_du_truong():
    import model_boards as bm
    xau = [b.khoa for b in bm.BOARD
           if not (b.khoa and b.nhan and b.tieu_de and b.link.startswith("https://")
                   and b.nguon in ("arena", "aa", "media", "top"))]
    kiem("test_ban_dang_ky_moi_bang_du_truong", not xau, f"thieu truong: {xau}")
    kiem("test_ban_dang_ky_arena_co_duong_dan",
         all(b.duong_dan for b in bm.BOARD if b.nguon == "arena"),
         "bang arena khong co duong dan API thi fetch_arena bo qua no")
    kiem("test_ban_dang_ky_khong_trung_khoa",
         len({b.khoa for b in bm.BOARD}) == len(bm.BOARD))


def test_ban_dang_ky_dung_bang_in_rieng():
    """coding AA (da co muc TOP CODING) in theo khuon rieng. Them mot bang
    `in_bang=False` nua ma khong viet khoi in rieng cho no la bang do bien
    mat khoi bao cao."""
    import model_boards as bm
    rieng = sorted(b.khoa for b in bm.BOARD if not b.in_bang)
    kiem("test_ban_dang_ky_dung_bang_in_rieng", rieng == ["coding"],
         f"bang in rieng: {rieng}")


def test_hang_va_ngay_doc_dung_bon_hinh():
    """Bon nguon, bon cho nam trong tep ket qua. Doc sai mot hinh la bang do in
    rong ma `hong` khong bao (bang_so van co no)."""
    import model_boards as bm
    ket = {"bang_xep_hang": {"text": [{"ten": "a"}]},
           "cham_diem": {"bang_tri_tue_goc": [{"ten": "b"}]},
           "media": {"tts": [{"ten": "c"}]},
           "tbench": {"rows": [{"ten": "d"}], "ngay": "2026-09-01"},
           "gia_usage": {"rows": [{"ten": "e"}], "ngay": "2026-09-02"}}
    lay = {b.khoa: b for b in bm.BOARD}
    kiem("test_hang_va_ngay_arena", bm.rank_and_date(ket, lay["text"]) == ([{"ten": "a"}], None))
    kiem("test_hang_va_ngay_aa", bm.rank_and_date(ket, lay["tri_tue"]) == ([{"ten": "b"}], None))
    kiem("test_hang_va_ngay_media", bm.rank_and_date(ket, lay["tts"]) == ([{"ten": "c"}], None))
    kiem("test_hang_va_ngay_top",
         bm.rank_and_date(ket, lay["tbench"]) == ([{"ten": "d"}], "2026-09-01"))
    # Khong con bang nao trong ban dang ky dung ket_khoa khac khoa (kiem tra
    # truc tiep co che nay bang mot Board gia, doc lap voi registry).
    gia = bm.Board("gia", "gia", "GIA", "https://vi.du/", "top", ket_khoa="gia_usage")
    kiem("test_hang_va_ngay_ket_khoa",
         bm.rank_and_date(ket, gia) == ([{"ten": "e"}], "2026-09-02"),
         "ket_khoa phai tro toi khoa khac trong ket khi duoc khai")
    kiem("test_hang_va_ngay_thieu_thi_None",
         bm.rank_and_date({}, lay["hle"]) == (None, None))


def test_ket_cua_main_co_du_bang_top():
    """`ket` (tep --out) phai co MOI bang kieu top cua ban dang ky — day la cho
    duy nhat `hong` khong canh duoc: bang_so co ma ket thieu thi bao cao im."""
    src = Path(s.__file__).read_text(encoding="utf-8")
    i = src.find("def main")
    kiem("test_ket_cua_main_co_du_bang_top",
         'for b in model_boards.BOARD if b.nguon == "top"' in src[i:],
         "phan bang top cua `ket` phai dan xuat tu ban dang ky")


def test_link_bat_buoc_dan_tu_ban_dang_ky():
    import model_boards as bm
    lech = [k for k, v in bm.LINK_BOARD.items() if required.LINK_BOARD.get(k) != v]
    kiem("test_link_bat_buoc_dan_tu_ban_dang_ky", not lech, f"lech: {lech}")
    kiem("test_link_ra_mat_van_con", required.LINK_BOARD.get("ra_mat", "").startswith("https://"),
         "`ra_mat` khong phai bang nhung muc BAT BUOC ra mat can link")


if __name__ == "__main__":
    # Tep nay dem bang kiem() thay vi assert, nen khong dung tam.chay_tat_ca —
    # nhung cung phai bat Exception (E-r2-2): mot loi giua chung khong duoc giet
    # ca tep va nuot dong N/M.
    for f in list(globals()):
        if f.startswith("test_"):
            try:
                globals()[f]()
            except Exception as e:                           # noqa: BLE001
                loi += 1
                print(f"ERR  {f}: {type(e).__name__}: {e}")
    print(f"\n{qua}/{qua + loi} test qua")
    sys.exit(1 if loi else 0)
