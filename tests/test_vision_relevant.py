#!/usr/bin/env python3
"""Vision tra loi "LIÊN_QUAN" (có dấu trên chính chữ LIEN) phải được PARSE,
không được lặng lẽ rơi vào None.

Sự cố 12/09/2026: chạy lại task TSMC sau khi hạ ngưỡng slide (6/7) và thêm
tính năng tự tìm ảnh — engine báo "đủ 6 slide dựng được" nhưng cả 5 ảnh CŨ
đều mang lien_quan=None trong khi mo_ta vẫn đầy đủ. Truy tận gốc: model trả
về "LIÊN_QUAN: không" (dấu trên chữ Ê), regex cũ chỉ khớp "LIEN_QUAN" (không
dấu) như đề bài yêu cầu. A1/A4 là hai widget giá cổ phiếu — lần chạy TRƯỚC
vision nói đúng "không", lần này parse hỏng nên lqv=None, mà công thức
count_image_use_ok coi None là "chưa False" tức DÙNG ĐƯỢC — hai ảnh KHÔNG liên
quan xuyên thẳng qua cổng chặn.

Chạy:  venv/bin/python tests/test_vision_relevant.py
"""
import io
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from prepare import vision                                      # noqa: E402


def _catch_stderr(ham):
    cu, sys.stderr = sys.stderr, io.StringIO()
    try:
        kq = ham()
        return kq, sys.stderr.getvalue()
    finally:
        sys.stderr = cu


def _image_1x1(tmp: Path) -> str:
    from PIL import Image
    p = tmp / "a.png"
    Image.new("RGB", (4, 4), (200, 200, 200)).save(p)
    return str(p)


class _Res:
    def __init__(self, content: bytes):
        self._c = content

    def read(self):
        return self._c


def _call(content: str):
    return mock.patch.object(vision, "_call_router", return_value=_Res(content.encode()))


def _body(txt: str) -> str:
    import json
    return json.dumps({"choices": [{"message": {"content": txt}}]})


def test_relevant_has_mark_on_text_connect_still_parse_ok():
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _image_1x1(Path(tmp))
        with _call(_body("MO_TA: widget giá cổ phiếu.\nLIÊN_QUAN: không")):
            (mt, lq), err = _catch_stderr(lambda: vision.description_image(p, "TSMC ...", hang="TSMC"))
        assert lq is False, f"LIÊN_QUAN có dấu vẫn phải parse ra False, được {lq!r}"
        assert "widget" in mt
        assert "khong parse duoc" not in err


def test_relevant_no_mark_still_parse_like_old():
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _image_1x1(Path(tmp))
        with _call(_body("MO_TA: trụ sở TSMC.\nLIEN_QUAN: co")):
            mt, lq = vision.description_image(p, "TSMC ...")
        assert lq is True


def test_relevant_ify_regular_all_match():
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _image_1x1(Path(tmp))
        with _call(_body("MO_TA: x.\nliên_quan: Không")):
            _, lq = vision.description_image(p, "T")
        assert lq is False


def test_parse_real_broken_still_report_out_stderr_no_silent():
    """Mô tả có nhưng LIEN_QUAN không đọc được (định dạng lạ) vẫn phải in cảnh
    báo — khác trước đây: cả hai trường hợp (chưa gọi được / đã gọi nhưng parse
    hỏng) đều trả về None y hệt nhau, không ai phân biệt được qua log.

    Đóng cổng fail-open (Ông Chủ 12/09/2026): mock trả về CÙNG một câu không
    parse được ở cả hai lượt (`_call` không đổi theo lượt gọi), nên sau khi hỏi
    lại đúng một lần vẫn không đọc ra LIÊN_QUAN — kết quả phải ROT (`False`),
    không còn là `None` (khác hành vi cũ trước khi có cổng đóng)."""
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _image_1x1(Path(tmp))
        with _call(_body("MO_TA: x.\nkhông biết có liên quan hay không")):
            (_, lq), err = _catch_stderr(lambda: vision.description_image(p, "T"))
        assert lq is False
        assert "khong parse duoc dong LIEN_QUAN" in err, repr(err)
        assert "COI LA ROT" in err, repr(err)


def test_missing_api_key_no_got_warning_double():
    import os
    with tempfile.TemporaryDirectory() as tmp:
        cu = os.environ.pop("OPENAI_API_KEY", None)
        try:
            p = _image_1x1(Path(tmp))
            # env_load.nap() dung os.environ.setdefault doc lai secret.*.env that
            # tren may that co cau hinh: pop() khong o lai, nen chan luon nap()
            # trong pham vi test nay de mo phong moi truong THAT SU thieu key.
            with mock.patch.object(vision.env_load, "load", lambda *a, **k: None):
                (_, lq), err = _catch_stderr(lambda: vision.description_image(p, "T"))
        finally:
            if cu is not None:
                os.environ["OPENAI_API_KEY"] = cu
        assert lq is None
        assert "thieu OPENAI_API_KEY" in err
        assert "khong parse duoc dong LIEN_QUAN" not in err, "khong co MO_TA thi khong phai cảnh báo parse"


def test_keyword_match_override_relevant_when_name_rank_no_match_text():
    """LOW-164 (15/09/2026): bai co the nhac hang/san pham bang NHIEU TEN goi
    khac nhau (vd tieu de bat cum \"Opus\" nhung anh mo ta lai noi \"Claude\"/
    \"Ryzen\") — so khop chu-doi-chu voi `hang` (mot cum danh tu rieng DUY NHAT
    trich tu dau tieu de) se truot, du vision da tu doc ra DU_TU_KHOA cho chinh
    anh do. Ca that tren bai TSMC/AMD/Claude (Ryzen AI Max 400): anh chip AMD
    bi vision tra LIEN_QUAN: khong (vi hang trich duoc la \"Opus\", khong xuat
    hien trong mo ta) nhung TU_KHOA: co va mo ta la boi canh chip that (khong
    phai man hinh/UI) — phai duoc override thanh lien_quan."""
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _image_1x1(Path(tmp))
        body = _body("MO_TA: Anh chip AMD Ryzen AI Max PRO 400 Series.\n"
                      "LIEN_QUAN: khong\nCLUTTERED: khong\nTU_KHOA: co")
        with _call(body):
            mt, lq = vision.description_image(p, "Notes on gotchas migrating from Opus", hang="Opus")
        assert lq is True, f"TU_KHOA=co + boi canh chip phai override lien_quan, duoc {lq!r}"


def test_keyword_match_no_override_when_is_screen_ui():
    """TU_KHOA: co KHONG duoc override khi mo ta la man hinh/giao dien/terminal
    (khop KHONG) — override chi danh cho anh la BOI CANH hang that (logo/chip/
    tru so/su kien), khong mo cua cho moi anh du_tu_khoa deu lot qua."""
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _image_1x1(Path(tmp))
        body = _body("MO_TA: Anh chup man hinh terminal chay lenh ollama.\n"
                      "LIEN_QUAN: khong\nCLUTTERED: khong\nTU_KHOA: co")
        with _call(body):
            mt, lq = vision.description_image(p, "Notes on gotchas migrating from Opus", hang="Opus")
        assert lq is False, f"man hinh/UI khong duoc override du TU_KHOA=co, duoc {lq!r}"


def test_no_keyword_match_then_no_override():
    """TU_KHOA: khong (vision tu noi anh KHONG the hien du tu khoa chinh) thi
    khong duoc override boi nhanh moi nay — hanh vi cu (rot) giu nguyen."""
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _image_1x1(Path(tmp))
        body = _body("MO_TA: Anh chip AMD Ryzen AI Max PRO 400 Series.\n"
                      "LIEN_QUAN: khong\nCLUTTERED: khong\nTU_KHOA: khong")
        with _call(body):
            mt, lq = vision.description_image(p, "Notes on gotchas migrating from Opus", hang="Opus")
        assert lq is False


# ---------------------------------- cat_ngang_ok hoi chung mot luot (12/09, lan hai)
def test_ask_crop_landscape_when_landscape_height_no_right_chart():
    """Anh ngang, cao >=700, khong phai chart -> hoi THEM cau CAT_NGANG trong
    CUNG mot luot (khong ton HTTP rieng); tra ve luu vao cat_ngang_ok."""
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _image_1x1(Path(tmp))
        body = _body("MO_TA: bien hieu logo cong ty.\nLIEN_QUAN: co\nCAT_NGANG: khong")
        with _call(body):
            mt, lq, cn = vision.description_image(p, "T", hoi_them="co phai nguoi/san pham khong chu?",
                                        nhan_them="CAT_NGANG")
        assert lq is True and cn.lower().startswith("kh")


# ------------------------------- LOW-216: anh giao dien CUA CHINH san pham trong tin
def _ask(mo_ta, tieu_de, hang, lien_quan="co"):
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _image_1x1(Path(tmp))
        body = _body(f"MO_TA: {mo_ta}\nLIEN_QUAN: {lien_quan}\nCLUTTERED: khong\nTU_KHOA: co")
        with _call(body):
            return vision.description_image(p, tieu_de, hang=hang)[1]


def test_ui_of_product_in_title_keeps_relevant():
    """Do that 17/09/2026 (tin "Claude Cowork and chat are now one Claude"):
    vision noi LIEN_QUAN: co cho 9 anh giao dien Claude (menu Docs/Slides,
    MacBook chay Claude, app Claude Cowork) nhung override regex "man hinh/
    giao dien" lat het thanh khong. Voi tin phan mem, giao dien LA san pham."""
    tieu = "Claude Cowork and chat are now one Claude"
    hang = "Claude Cowork, Claude"
    for mt in ('Ảnh minh họa giao diện Claude với ô chat "Coffee and Claude time?" cùng các thẻ tạo Docs.',
               "Anh chup man hinh laptop MacBook hien giao dien Claude voi o nhap How can I help you today?",
               "Ảnh minh họa app Claude Cowork bên trái và cửa sổ trình duyệt chạy tác vụ bên phải."):
        assert _ask(mt, tieu, hang) is True, f"giao dien cua chinh san pham bi lat: {mt!r}"


def test_ui_first_word_of_name_also_counts():
    """hang chi co cum dai ("Claude Cowork") ma mo ta chi goi "Claude" van tinh."""
    assert _ask("Ảnh chụp giao diện Claude với menu Docs, Slides.",
                "Claude Cowork launches", "Claude Cowork") is True


def test_system_screen_naming_brand_still_flipped():
    """Ca goc 05/09 (A10 Ubuntu, tin Broadcom): man hinh driver/he dieu hanh
    nhac ten hang van KHONG phai anh cua tin — override van lat."""
    assert _ask("Anh chup man hinh cai dat driver Broadcom tren Ubuntu.",
                "Broadcom beats earnings", "Broadcom") is False


def test_ui_not_naming_title_still_flipped():
    """Man hinh/giao dien khong nhac ten nao cua tieu de -> van lat nhu cu."""
    assert _ask("Ảnh chụp màn hình giao diện ứng dụng tin tức.",
                "Claude Cowork and chat are now one Claude", "Claude Cowork, Claude") is False


def test_short_name_does_not_rescue():
    """Ten ngan (<4 ky tu, vd "AI") khong du de cuu mot anh man hinh."""
    assert _ask("Ảnh chụp màn hình giao diện AI chung chung.", "AI News today", "AI") is False


if __name__ == "__main__":
    import role
    role.set_active_role("ethan")            # xem tam.chay_tat_ca (LOW-182)
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
