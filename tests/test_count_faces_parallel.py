#!/usr/bin/env python3
"""`image_rules.count_faces` phải cho cùng kết quả khi gọi từ nhiều luồng (audit lượt 2, B-r2-1).

B2 (ca167c3) đưa `classify` vào ThreadPoolExecutor 4 luồng, và khoá `_YUNET_LOCK`
chỉ bảo vệ lúc NẠP model. Một `cv2.FaceDetectorYN` dùng chung thì không
thread-safe khi DÙNG: `setInputSize` của luồng này chen giữa `setInputSize` và
`detect` của luồng kia → cv2 ném → `None`. Đo 09/09/2026 với 24 ảnh KHÁC CỠ, 4
luồng: tuần tự 0/24 None, song song 22–23/24. `vision.py` làm `or 0` nên cổng mặt
người (LUẬT ẢNH §6) tắt câm cho gần hết ảnh trong sản xuất.

Ảnh khác cỡ là điều kiện bắt buộc để tái hiện: cùng cỡ thì setInputSize
idempotent và cuộc đua không lộ.

Chạy:  venv/bin/python tests/test_count_faces_parallel.py
"""
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image                                         # noqa: E402
import image_rules_ethan as image_rules                       # noqa: E402


def _image_other_has(tmp, n=24):
    ra = []
    for i in range(n):
        p = Path(tmp) / f"a{i}.png"
        Image.new("RGB", (640 + 37 * i, 480 + 23 * i), (120, 130, 140)).save(p)
        ra.append(str(p))
    return ra


def test_parallel_no_face_result_which():
    if image_rules._load_yunet() is None:
        print("   (bo qua: may nay khong co cv2/model YuNet)")
        return
    with tempfile.TemporaryDirectory() as t:
        anh = _image_other_has(t)
        tuan_tu = [image_rules.count_faces(p) for p in anh]
        assert not any(v is None for v in tuan_tu), "tuan tu da None: khong phai loi dua"
        for lan in range(3):
            with ThreadPoolExecutor(max_workers=4) as ex:
                song = list(ex.map(image_rules.count_faces, anh))
            hong = sum(v is None for v in song)
            assert hong == 0, f"lan {lan + 1}: {hong}/24 anh mat ket qua khi chay 4 luong"
            assert song == tuan_tu, "song song ra khac tuan tu"


def test_seen_notes_when_gate_face_no_run():
    """None (khong chay) phai LO ra o ghi_chu, khong lang le thanh 0 mat (C1)."""
    import prepare.vision as vision
    cu = image_rules.count_faces
    image_rules.count_faces = lambda p: None
    try:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.png"
            Image.new("RGB", (900, 700), (200, 200, 200)).save(p)
            a = {"ma": "X", "goc": str(p)}
            vision.classify(a, Path(t), "")       # tieu_de rong -> khong goi vision
    finally:
        image_rules.count_faces = cu
    assert a["mat"] == 0
    assert any("cổng mặt" in g for g in a["ghi_chu"]), a["ghi_chu"]


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
