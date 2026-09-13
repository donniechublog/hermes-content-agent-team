#!/usr/bin/env python3
"""Vision tra loi "LIÊN_QUAN" (có dấu trên chính chữ LIEN) phải được PARSE,
không được lặng lẽ rơi vào None.

Sự cố 12/09/2026: chạy lại task TSMC sau khi hạ ngưỡng slide (6/7) và thêm
tính năng tự tìm ảnh — engine báo "đủ 6 slide dựng được" nhưng cả 5 ảnh CŨ
đều mang lien_quan=None trong khi mo_ta vẫn đầy đủ. Truy tận gốc: model trả
về "LIÊN_QUAN: không" (dấu trên chữ Ê), regex cũ chỉ khớp "LIEN_QUAN" (không
dấu) như đề bài yêu cầu. A1/A4 là hai widget giá cổ phiếu — lần chạy TRƯỚC
vision nói đúng "không", lần này parse hỏng nên lqv=None, mà công thức
so_anh_dung_duoc coi None là "chưa False" tức DÙNG ĐƯỢC — hai ảnh KHÔNG liên
quan xuyên thẳng qua cổng chặn.

Chạy:  venv/bin/python tests/test_vision_lien_quan.py
"""
import io
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from chuan_bi import vision                                      # noqa: E402


def _bat_stderr(ham):
    cu, sys.stderr = sys.stderr, io.StringIO()
    try:
        kq = ham()
        return kq, sys.stderr.getvalue()
    finally:
        sys.stderr = cu


def _anh_1x1(tmp: Path) -> str:
    from PIL import Image
    p = tmp / "a.png"
    Image.new("RGB", (4, 4), (200, 200, 200)).save(p)
    return str(p)


class _Res:
    def __init__(self, content: bytes):
        self._c = content

    def read(self):
        return self._c


def _goi(content: str):
    return mock.patch.object(vision, "_call_router", return_value=_Res(content.encode()))


def _body(txt: str) -> str:
    import json
    return json.dumps({"choices": [{"message": {"content": txt}}]})


def test_lien_quan_co_dau_tren_chu_lien_van_parse_duoc():
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _anh_1x1(Path(tmp))
        with _goi(_body("MO_TA: widget giá cổ phiếu.\nLIÊN_QUAN: không")):
            (mt, lq), err = _bat_stderr(lambda: vision.description_image(p, "TSMC ...", hang="TSMC"))
        assert lq is False, f"LIÊN_QUAN có dấu vẫn phải parse ra False, được {lq!r}"
        assert "widget" in mt
        assert "khong parse duoc" not in err


def test_lien_quan_khong_dau_van_parse_nhu_cu():
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _anh_1x1(Path(tmp))
        with _goi(_body("MO_TA: trụ sở TSMC.\nLIEN_QUAN: co")):
            mt, lq = vision.description_image(p, "TSMC ...")
        assert lq is True


def test_lien_quan_hoa_thuong_deu_khop():
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _anh_1x1(Path(tmp))
        with _goi(_body("MO_TA: x.\nliên_quan: Không")):
            _, lq = vision.description_image(p, "T")
        assert lq is False


def test_parse_that_hong_van_bao_ra_stderr_khong_im_lang():
    """Mô tả có nhưng LIEN_QUAN không đọc được (định dạng lạ) vẫn phải in cảnh
    báo — khác trước đây: cả hai trường hợp (chưa gọi được / đã gọi nhưng parse
    hỏng) đều trả về None y hệt nhau, không ai phân biệt được qua log.

    Đóng cổng fail-open (Ông Chủ 12/09/2026): mock trả về CÙNG một câu không
    parse được ở cả hai lượt (`_goi` không đổi theo lượt gọi), nên sau khi hỏi
    lại đúng một lần vẫn không đọc ra LIÊN_QUAN — kết quả phải ROT (`False`),
    không còn là `None` (khác hành vi cũ trước khi có cổng đóng)."""
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _anh_1x1(Path(tmp))
        with _goi(_body("MO_TA: x.\nkhông biết có liên quan hay không")):
            (_, lq), err = _bat_stderr(lambda: vision.description_image(p, "T"))
        assert lq is False
        assert "khong parse duoc dong LIEN_QUAN" in err, repr(err)
        assert "COI LA ROT" in err, repr(err)


def test_thieu_api_key_khong_bi_canh_bao_kep():
    import os
    with tempfile.TemporaryDirectory() as tmp:
        cu = os.environ.pop("OPENAI_API_KEY", None)
        try:
            p = _anh_1x1(Path(tmp))
            # env_load.nap() dung os.environ.setdefault doc lai secret.*.env that
            # tren may that co cau hinh: pop() khong o lai, nen chan luon nap()
            # trong pham vi test nay de mo phong moi truong THAT SU thieu key.
            with mock.patch.object(vision.env_load, "load", lambda *a, **k: None):
                (_, lq), err = _bat_stderr(lambda: vision.description_image(p, "T"))
        finally:
            if cu is not None:
                os.environ["OPENAI_API_KEY"] = cu
        assert lq is None
        assert "thieu OPENAI_API_KEY" in err
        assert "khong parse duoc dong LIEN_QUAN" not in err, "khong co MO_TA thi khong phai cảnh báo parse"


# ---------------------------------- cat_ngang_ok hoi chung mot luot (12/09, lan hai)
def test_hoi_cat_ngang_khi_ngang_cao_khong_phai_chart():
    """Anh ngang, cao >=700, khong phai chart -> hoi THEM cau CAT_NGANG trong
    CUNG mot luot (khong ton HTTP rieng); tra ve luu vao cat_ngang_ok."""
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        p = _anh_1x1(Path(tmp))
        body = _body("MO_TA: bien hieu logo cong ty.\nLIEN_QUAN: co\nCAT_NGANG: khong")
        with _goi(body):
            mt, lq, cn = vision.description_image(p, "T", hoi_them="co phai nguoi/san pham khong chu?",
                                        nhan_them="CAT_NGANG")
        assert lq is True and cn.lower().startswith("kh")


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
