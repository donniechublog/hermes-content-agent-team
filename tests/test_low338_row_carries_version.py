#!/usr/bin/env python3
"""LOW-338: ảnh xếp hạng không được khoanh hàng KHÔNG mang phiên bản của bài.

Bài "Alibaba ra mắt … Qwen Image 2.1" (Kite, blog, 21/09/2026): `extract_model` ra
['Qwen Image 2.1', 'Qwen Image'], ứng viên ngắn khớp ba hàng cùng họ trên ba bảng
Arena — không bảng nào có Qwen Image 2.1. Ba dòng dưới đây chép từ `prepare.log`
thật của bài đó.

Chạy:  venv/bin/python tests/test_low338_row_carries_version.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import ranking as xh                                        # noqa: E402

TITLE = "Alibaba ra mắt mô hình tạo ảnh Qwen Image 2.1"
REAL_ROWS = (
    "33 | 32 34 | qwen-image-edit Alibaba · Apache 2.0 | 1241 ±3 | 1,981,11",
    "31 | 31 32 | qwen-image-edit-2511 Alibaba · Apache 2.0 | 1173 ±4 | 218",
    "59 | 59 62 | qwen-image-prompt-extend Alibaba · Apache 2.0 | 1061 ±3",
)


def test_cause_stays_documented():
    """Nguyên nhân gốc: ứng viên ngắn bỏ mất số phiên bản. Nếu ai sửa
    `extract_model` thì test này đổi theo; hàng rào thật là ở `row_carries_version`."""
    assert xh.extract_model(TITLE) == ["Qwen Image 2.1", "Qwen Image"]


def test_real_sibling_rows_are_rejected():
    models = xh.extract_model(TITLE)
    for row in REAL_ROWS:
        kq = {"model": "Qwen Image", "row": row}
        assert not xh.row_carries_version(models, kq), row


def test_row_with_the_version_is_accepted():
    models = xh.extract_model(TITLE)
    for row in ("12 | 11 13 | qwen-image-2.1 Alibaba · Apache 2.0 | 1250 ±3",
                "12 | 11 13 | Qwen Image 2-1 Alibaba | 1250 ±3",
                "12 | 11 13 | qwen-image-21 Alibaba | 1250 ±3"):
        assert xh.row_carries_version(models, {"model": "Qwen Image", "row": row}), row


def test_version_in_score_cell_does_not_count():
    """'21' trong ô số (điểm, hạng) không được tính là phiên bản."""
    models = xh.extract_model(TITLE)
    row = "33 | 32 34 | qwen-image-edit Alibaba · Apache 2.0 | 1241 ±3 | 1,981,21"
    assert not xh.row_carries_version(models, {"model": "Qwen Image", "row": row})


def test_candidate_that_keeps_the_version_needs_no_row_check():
    models = xh.extract_model("GPT-6 Astra (max) vượt mốc 55 điểm")
    assert xh.row_carries_version(models, {"model": "GPT-6", "row": "3 | GPT-6 mini | 1400"})
    models = xh.extract_model("GPT Image 2.5 Flare xếp #2 bảng chỉnh sửa ảnh")
    assert xh.row_carries_version(models, {"model": "GPT Image 2.5", "row": "2 | gpt-image-2.5 | 1300"})


def test_same_hole_other_names_are_caught():
    """Cùng lỗ hổng chưa gây sự cố: ứng viên `GPT Image` / `Grok Imagine Video` bỏ số."""
    models = xh.extract_model("GPT Image 2.5 Flare xếp #2 bảng chỉnh sửa ảnh")
    assert not xh.row_carries_version(models, {"model": "GPT Image", "row": "9 | gpt-image-1 | 1100"})
    models = xh.extract_model("Grok Imagine Video 1.5 Agent ra mắt")
    assert not xh.row_carries_version(models, {"model": "Grok Imagine Video", "row": "4 | grok-imagine-video | 1200"})


def test_story_without_version_is_untouched():
    """Không có số phiên bản trong tên thì không có gì để kiểm (Muse Spark không số)."""
    assert xh.row_carries_version(["Muse Spark"], {"model": "Muse Spark", "row": "1 | Muse Spark | 1500"})
    assert xh.row_carries_version([], {"model": "x", "row": "y"})


def test_drop_removes_the_captured_png_and_reports_reason():
    """Ảnh chụp sai phải bị HUỶ khỏi đĩa, không được nằm lại trong original/ cho bước
    sau nhặt nhầm. Lý do đi vào nhánh "bỏ nguồn" sẵn có."""
    models = xh.extract_model(TITLE)
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "ranking_arena-image-edit.png"
        out.write_bytes(b"png")
        kq, ly_do = xh._drop_row_without_version(
            models, {"model": "Qwen Image", "row": REAL_ROWS[0]}, "x", out)
        assert kq is None and not out.exists()
        assert "qwen-image-edit" in ly_do and "Qwen Image 2.1" in ly_do, ly_do
        # hàng đúng thì giữ nguyên cả ảnh lẫn kết quả
        out.write_bytes(b"png")
        good = {"model": "Qwen Image", "row": "12 | qwen-image-2.1 Alibaba | 1250"}
        kq2, _ = xh._drop_row_without_version(models, good, None, out)
        assert kq2 is good and out.exists()


def test_find_and_capture_falls_back_when_no_board_has_the_row():
    """Nối dây thật: cả ba bảng chỉ có hàng cùng họ -> không ảnh khoanh, ra thẻ dự phòng."""
    models = xh.extract_model(TITLE)
    sources = [{"id": s, "site": "ARENA.AI", "board": s, "url": "u"}
               for s in ("arena-image-edit", "arena-multi-image-edit", "arena-t2i")]

    def fake_try(phien, n, models_, out, in_log):
        out.write_bytes(b"png")
        return {"kind": "table", "model": "Qwen Image", "rank": 33, "row": REAL_ROWS[0]}, None, mock.Mock()

    logs = []
    with tempfile.TemporaryDirectory() as d, \
            mock.patch.object(xh, "_sources_proving_story", side_effect=lambda ds, log: ds), \
            mock.patch.object(xh, "_try_source", side_effect=fake_try), \
            mock.patch.object(xh, "capture_logo", return_value=None), \
            mock.patch.object(xh, "fallback_card") as card, \
            mock.patch.object(xh, "SessionCapture"), \
            mock.patch("browser_session.session_or_new") as session:
        session.return_value.__enter__.return_value = mock.Mock()
        res = xh.find_and_capture(models, sources, Path(d), in_log=logs.append)
        assert res["kind"] == "card", res
        assert card.called
        assert not list(Path(d).glob("ranking_arena-*.png")), "ảnh khoanh sai còn nằm lại trên đĩa"
    assert any("không mang phiên bản" in x for x in logs), logs


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
