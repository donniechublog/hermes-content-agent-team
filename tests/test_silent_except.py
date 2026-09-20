#!/usr/bin/env python3
"""Cổng: `except` rộng NUỐT lỗi im lặng trong 4 tệp ưu tiên (LOW-306).

Đo 20/09/2026 (audit LOW-294 lượt 2): 274 `except` rộng trong mã của đội, **137
chỗ im lặng hoàn toàn** — không `raise`, không in/log, không dùng biến lỗi. Khi
hỏng thật thì không có dòng nào để lần. Hai lần đã trả giá: LOW-275 (approve nuốt
nguyên nhân "không tìm được nguồn"), LOW-277 (`_trong_feed` nuốt timeout 80s).

Cổng này giữ 4 tệp đã dọn (31 chỗ → 0). Ba đường hợp lệ cho một chỗ mới:

  1. một dòng log/print kèm `type(e).__name__`;
  2. thu hẹp kiểu lỗi (`ValueError`, `OSError`, `httpx.HTTPError`…) — hết rộng
     thì cổng không xét nữa;
  3. thật sự im lặng nhưng CÓ CHỦ Ý: viết `IM LANG CO Y` trong thân handler kèm
     một câu vì sao (ví dụ vòng đoán 6 đường RSS, 404 là kết quả bình thường).

Script đo trước đây chỉ nằm trong một comment Linear; để ở đây thì đợt sau còn
chạy lại được.

Chay:  venv/bin/python tests/test_silent_except.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 4 tệp của LOW-306. Các tệp còn lại (image_rules_*, get_source, scan_sources,
# article_images…) tách ticket sau — thêm vào đây khi dọn tới.
FILES_WATCHED = ("article_sources.py", "approve_dispatch.py", "approve_post.py",
                 "monitor_9router.py")

MARK_ON_PURPOSE = "IM LANG CO Y"

# Tên hàm coi là "có lên tiếng". `log`/`warn`/`error` là write_log; `print` ra
# stderr; `exit`/`kanban_block` đẩy lên người.
SPEAK = {"print", "log", "warn", "warning", "error", "exception", "critical",
         "exit", "die", "kanban_block", "report_progress_kanban"}


def _broad(h: ast.ExceptHandler) -> bool:
    """Handler này có bắt `Exception`/`BaseException`/trần không."""
    if h.type is None:
        return True
    names = list(h.type.elts) if isinstance(h.type, ast.Tuple) else [h.type]
    return any(isinstance(n, ast.Name) and n.id in ("Exception", "BaseException")
               for n in names)


def _speaks(h: ast.ExceptHandler) -> bool:
    """Thân handler có `raise`, có gọi hàm lên tiếng, hay có dùng biến lỗi không."""
    for n in ast.walk(ast.Module(body=h.body, type_ignores=[])):
        if isinstance(n, ast.Raise):
            return True
        if isinstance(n, ast.Name) and h.name and n.id == h.name:
            return True
        if isinstance(n, ast.Call):
            f = n.func
            ten = (f.id if isinstance(f, ast.Name)
                   else f.attr if isinstance(f, ast.Attribute) else "")
            if ten in SPEAK:
                return True
    return False


def silent_handlers(src: str) -> list:
    """[(dòng, có dấu chủ ý)] cho mỗi `except` rộng mà thân không lên tiếng."""
    lines = src.splitlines()
    ra = []
    for h in ast.walk(ast.parse(src)):
        if not isinstance(h, ast.ExceptHandler) or not _broad(h) or _speaks(h):
            continue
        het = max(getattr(n, "end_lineno", h.lineno) for n in h.body)
        than = "\n".join(lines[h.lineno - 1:het])
        ra.append((h.lineno, MARK_ON_PURPOSE in than))
    return ra


def test_no_new_silent_broad_except_in_watched_files():
    """Chỗ im lặng mà KHÔNG có `IM LANG CO Y` = lỗi sẽ biến mất không dấu vết."""
    loi = []
    for ten in FILES_WATCHED:
        for dong, co_y in silent_handlers((ROOT / ten).read_text(encoding="utf-8")):
            if not co_y:
                loi.append(f"{ten}:{dong}")
    assert loi == [], (
        "`except` rộng nuốt lỗi im lặng (LOW-306) — thêm một dòng log, thu hẹp "
        f"kiểu lỗi, hoặc ghi `{MARK_ON_PURPOSE}` kèm lý do:\n  " + "\n  ".join(loi))


def test_on_purpose_count_is_small_and_known():
    """Dấu chủ ý là ngoại lệ, không phải cách lách. Tăng thì phải sửa test + nói rõ."""
    co_y = [f"{ten}:{d}" for ten in FILES_WATCHED
            for d, y in silent_handlers((ROOT / ten).read_text(encoding="utf-8")) if y]
    assert len(co_y) <= 2, f"quá nhiều chỗ tự nhận 'có chủ ý': {co_y}"


def test_gate_catches_silent_and_lets_the_rest_through():
    """Vết vàng mà rỗng thì 0-lệch không chứng minh gì: tự kiểm chính máy đo."""
    im = "try:\n    x()\nexcept Exception:\n    pass\n"
    assert silent_handlers(im) == [(3, False)], silent_handlers(im)

    co_y = "try:\n    x()\nexcept Exception:\n    # IM LANG CO Y: ly do\n    pass\n"
    assert silent_handlers(co_y) == [(3, True)], silent_handlers(co_y)

    noi = 'try:\n    x()\nexcept Exception as e:\n    print(type(e).__name__)\n'
    assert silent_handlers(noi) == [], silent_handlers(noi)

    hep = "try:\n    x()\nexcept ValueError:\n    pass\n"
    assert silent_handlers(hep) == [], silent_handlers(hep)

    nem = "try:\n    x()\nexcept Exception:\n    raise\n"
    assert silent_handlers(nem) == [], silent_handlers(nem)


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
