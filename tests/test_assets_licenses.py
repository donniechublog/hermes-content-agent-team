#!/usr/bin/env python3
"""Cổng chặn tài sản nhị phân vào repo mà không ghi nguồn và giấy phép (LOW-302).

Repo chứa sẵn font và mô hình YuNet và được chia sẻ ra ngoài (GitHub), nên mỗi tệp trong
assets/ phải có nguồn và giấy phép ghi kèm. OFL bắt buộc kèm thông báo bản quyền khi phân
phối lại font; MIT bắt buộc giữ thông báo trong mọi bản sao mô hình. Các test dưới chặn
đúng lớp "thêm tệp mới mà quên ghi", và lớp "đổi tệp mô hình mà tài liệu vẫn khẳng định
nguồn cũ" (so mã băm).

Chạy:  venv/bin/python tests/test_assets_licenses.py
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"
FONT_SUFFIXES = {".ttf", ".otf", ".woff", ".woff2"}


def _fonts_on_disk() -> list:
    return sorted(p.name for p in FONTS.iterdir() if p.suffix.lower() in FONT_SUFFIXES)


def test_every_font_is_listed_in_licenses():
    text = (FONTS / "LICENSES.md").read_text(encoding="utf-8")
    fonts = _fonts_on_disk()
    assert fonts, "không thấy font nào trong assets/fonts/"
    missing = [f for f in fonts if f"`{f}`" not in text]
    assert not missing, ("font chưa có mục trong assets/fonts/LICENSES.md: " + ", ".join(missing)
                         + " — ghi bản quyền đọc từ bảng `name` của tệp font (ID 0/13/14)")


def test_licenses_does_not_list_a_font_that_is_gone():
    text = (FONTS / "LICENSES.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"`([A-Za-z0-9_.-]+\.(?:ttf|otf|woff2?))`", text))
    gone = sorted(f for f in listed if not (FONTS / f).exists())
    assert not gone, "LICENSES.md nhắc font không còn trong assets/fonts/: " + ", ".join(gone)


def test_every_top_level_asset_is_described_in_readme():
    readme = (ASSETS / "README.md").read_text(encoding="utf-8")
    files = sorted(p.name for p in ASSETS.iterdir() if p.is_file() and p.name != "README.md")
    assert files, "assets/ không có tệp nào ngoài README.md"
    missing = [f for f in files if f not in readme]
    assert not missing, "tệp trong assets/ chưa có mô tả nguồn/giấy phép ở assets/README.md: " + ", ".join(missing)


def test_readme_hash_matches_every_model_file():
    readme = (ASSETS / "README.md").read_text(encoding="utf-8")
    models = sorted(ASSETS.glob("*.onnx"))
    assert models, "không thấy mô hình .onnx nào trong assets/"
    for model in models:
        sha = hashlib.sha256(model.read_bytes()).hexdigest()
        assert sha in readme, (f"{model.name}: sha256 thật {sha} không có trong assets/README.md — tệp mô hình "
                               "đã đổi mà nguồn/giấy phép ghi ở đó có thể không còn đúng")


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bắt cả Exception, luôn in N/M
    chay_tat_ca(globals())
