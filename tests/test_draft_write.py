#!/usr/bin/env python3
"""draft_write.py — ghi draft cho vai viết (LOW-307, module 0% độ phủ).

Đây là bước CUỐI trước hàng duyệt: caption của writer + metadata Finn đã chốt
ráp lại thành `drafts/<id>.json`. Sai ở đây không ra lỗi, nó ra một bài đăng
thiếu nguồn, sai brand, hoặc đè lên caption Ông Chủ đã duyệt (đúng LOW-296).

Bốn hợp đồng test này giữ:
  1. sidecar `.meta.json` là nguồn sự thật, cờ dòng lệnh mới được ghi đè;
  2. draft đã `scheduled/publishing/published` thì KHÔNG nộp lại được;
  3. dấu vết thẻ duyệt đang sống (`tg_*`) mang qua lần ghi sau khi còn `pending`
     — mất nó là lần push sau thêm thẻ mới thay vì xoá thẻ cũ;
  4. ảnh phụ `_2.png … _10.png` vào album đủ, kể cả slide thứ 10.

Chay:  venv/bin/python tests/test_draft_write.py
"""
import contextlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import caption_check                                         # noqa: E402
import draft_write                                           # noqa: E402

CAPTION_OK = "Mô hình mới đạt 71.2% trên SWE-bench, hơn bản cũ 9 điểm."


@contextlib.contextmanager
def _sandbox(pass_check=True):
    """Trỏ DRAFTS vào thư mục tạm và (tuỳ chọn) thay cổng caption bằng bản luôn đạt.

    Trả lại cả hai khi ra khỏi khối — `caption_check.check` là hàm dùng chung,
    một test quên trả lại là mọi test sau đó chạy với cổng giả (bài học `so_tam`).
    """
    cu_drafts, cu_check = draft_write.DRAFTS, caption_check.check
    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "drafts"
        d.mkdir()
        draft_write.DRAFTS = d
        if pass_check:
            caption_check.check = lambda caption, tu_lieu="": ([], [], {})
        try:
            yield d
        finally:
            draft_write.DRAFTS = cu_drafts
            caption_check.check = cu_check


def _run(d, draft_id, *args, caption=CAPTION_OK):
    """Chạy `main()` như dòng lệnh; trả về (mã thoát | None, đường dẫn draft)."""
    cap = d / "caption.txt"
    cap.write_text(caption, encoding="utf-8")
    cu_argv = sys.argv
    sys.argv = ["draft_write.py", draft_id, "--caption-file", str(cap), *args]
    try:
        draft_write.main()
        return None, d / f"{draft_id}.json"
    except SystemExit as e:
        return e.code, d / f"{draft_id}.json"
    finally:
        sys.argv = cu_argv


def _meta(d, draft_id, **kv):
    (d / f"{draft_id}.meta.json").write_text(json.dumps(kv, ensure_ascii=False),
                                             encoding="utf-8")


# ---------- đọc bản trước ----------

def test_read_prev_missing_or_corrupt_then_empty_dict():
    """Tệp thiếu và tệp hỏng đều là {} — nhưng không được nổ."""
    with _sandbox() as d:
        assert draft_write._read_prev("khong-co") == {}
        (d / "hong.json").write_text("{khong phai json", encoding="utf-8")
        assert draft_write._read_prev("hong") == {}


def test_locked_reason_by_status():
    """LOW-296: nộp lại sau khi Duyệt từng ghi đè caption đã chốt."""
    with _sandbox() as d:
        for st in ("scheduled", "publishing", "published"):
            (d / "b.json").write_text(json.dumps({"status": st}), encoding="utf-8")
            ly_do = draft_write.locked_reason("b")
            assert ly_do and st in ly_do, (st, ly_do)
        for st in ("pending", "rejected", None):
            (d / "b.json").write_text(json.dumps({"status": st}), encoding="utf-8")
            assert draft_write.locked_reason("b") is None, st
        assert draft_write.locked_reason("chua-co") is None


# ---------- ghi draft ----------

def test_meta_sidecar_is_source_of_truth():
    with _sandbox() as d:
        _meta(d, "b1", source_url="https://x.test/bai", category="Model",
              via="@ai", brand="dcgr")
        ma, p = _run(d, "b1")
        assert ma is None, ma
        j = json.loads(p.read_text(encoding="utf-8"))
        assert j["source_url"] == "https://x.test/bai", j
        assert (j["category"], j["via"], j["brand"]) == ("Model", "@ai", "dcgr"), j
        assert j["status"] == "pending" and j["caption"] == CAPTION_OK


def test_flag_overrides_sidecar():
    with _sandbox() as d:
        _meta(d, "b2", source_url="https://cu.test/x", category="AI", brand="donniechublog")
        ma, p = _run(d, "b2", "--source-url", "https://moi.test/y", "--brand", "dcgr")
        assert ma is None, ma
        j = json.loads(p.read_text(encoding="utf-8"))
        assert j["source_url"] == "https://moi.test/y" and j["brand"] == "dcgr", j


def test_default_when_sidecar_says_nothing():
    """Thiếu category/brand thì rơi về mặc định của dây chuyền, không bỏ trống."""
    with _sandbox() as d:
        _meta(d, "b3", source_url="https://x.test/bai")
        ma, p = _run(d, "b3")
        assert ma is None, ma
        j = json.loads(p.read_text(encoding="utf-8"))
        assert j["category"] == "AI" and j["brand"] == "donniechublog", j


def test_no_sidecar_and_no_flag_then_exit():
    with _sandbox() as d:
        ma, _ = _run(d, "b4")
        assert isinstance(ma, str) and "meta.json" in ma, ma


def test_no_sidecar_but_flag_enough_then_write():
    with _sandbox() as d:
        ma, p = _run(d, "b5", "--source-url", "https://x.test/y", "--category", "AI")
        assert ma is None, ma
        assert json.loads(p.read_text(encoding="utf-8"))["source_url"] == "https://x.test/y"


def test_locked_draft_then_refuse_to_overwrite():
    """LOW-296: bài đã lên lịch thì caption đã chốt — phải dừng, không ghi đè."""
    with _sandbox() as d:
        _meta(d, "b6", source_url="https://x.test/y", category="AI")
        (d / "b6.json").write_text(json.dumps({"caption": "BAN DA DUYET",
                                               "status": "scheduled"}), encoding="utf-8")
        ma, p = _run(d, "b6", caption="Caption moi cua writer")
        assert isinstance(ma, str) and ma.startswith("[LOI]"), ma
        assert json.loads(p.read_text(encoding="utf-8"))["caption"] == "BAN DA DUYET"


def test_empty_caption_then_exit():
    with _sandbox() as d:
        _meta(d, "b7", source_url="https://x.test/y", category="AI")
        ma, p = _run(d, "b7", caption="   \n  ")
        assert isinstance(ma, str) and "rong" in ma.lower(), ma
        assert not p.exists()


def test_missing_required_field_then_exit_and_no_file():
    """source_url rỗng: bài đăng không có nguồn — chặn trước khi ghi."""
    with _sandbox() as d:
        _meta(d, "b8", source_url="", category="AI")
        ma, p = _run(d, "b8", "--source-url", "", "--category", "AI")
        assert isinstance(ma, str) and "source_url" in ma, ma
        assert not p.exists()


# ---------- cổng caption ----------

def test_caption_gate_blocks_and_flag_forces():
    with _sandbox(pass_check=False) as d:
        caption_check.check = lambda caption, tu_lieu="": (["loi gia"], ["nhac gia"], {})
        _meta(d, "b9", source_url="https://x.test/y", category="AI")
        ma, p = _run(d, "b9")
        assert isinstance(ma, str) and "khong dat" in ma.lower(), ma
        assert not p.exists()
        ma, p = _run(d, "b9", "--bo-qua-kiem")
        assert ma is None and p.exists(), ma


def test_real_caption_gate_is_wired():
    """Không mock: cổng THẬT phải chặn em-dash — nếu dây nối đứt, test này xanh giả."""
    with _sandbox(pass_check=False) as d:
        _meta(d, "b10", source_url="https://x.test/y", category="AI")
        ma, p = _run(d, "b10", caption="Mô hình mới — nhanh hơn bản cũ 2 lần.")
        assert isinstance(ma, str) and "khong dat" in ma.lower(), ma
        assert not p.exists()


def test_material_file_is_passed_to_gate():
    """`--tu-lieu` phải tới được cổng: cổng đối chiếu số liệu bằng chính tệp đó."""
    with _sandbox(pass_check=False) as d:
        thay = {}
        caption_check.check = lambda caption, tu_lieu="": (thay.update(tl=tu_lieu) or ([], [], {}))
        tl = d / "tu_lieu.md"
        tl.write_text("so lieu that o day", encoding="utf-8")
        _meta(d, "b11", source_url="https://x.test/y", category="AI")
        ma, _ = _run(d, "b11", "--tu-lieu", str(tl))
        assert ma is None, ma
        assert thay["tl"] == "so lieu that o day", thay


# ---------- album & dấu vết thẻ ----------

def test_album_secondary_includes_slide_ten():
    """Bug thật 06/09: mẫu `_[0-9].png` bỏ sót slide 10, album đăng thiếu một tấm."""
    with _sandbox() as d:
        _meta(d, "b12", source_url="https://x.test/y", category="AI")
        (d / "b12.png").write_bytes(b"x")
        for i in (2, 3, 10):
            (d / f"b12_{i}.png").write_bytes(b"x")
        ma, p = _run(d, "b12")
        assert ma is None, ma
        j = json.loads(p.read_text(encoding="utf-8"))
        assert [Path(x).name for x in j["images"]] == \
            ["b12.png", "b12_2.png", "b12_3.png", "b12_10.png"], j["images"]


def test_no_secondary_then_no_images_key():
    with _sandbox() as d:
        _meta(d, "b13", source_url="https://x.test/y", category="AI")
        ma, p = _run(d, "b13")
        assert ma is None, ma
        assert "images" not in json.loads(p.read_text(encoding="utf-8"))


def test_push_marks_carried_only_while_pending():
    """LOW-296: mất dấu vết thẻ đang sống = lần push sau thêm thẻ MỚI, không xoá thẻ cũ."""
    with _sandbox() as d:
        _meta(d, "b14", source_url="https://x.test/y", category="AI")
        dau = {"tg_card_message_id": 77, "tg_extra_message_ids": [78, 79],
               "tg_push_fingerprint": "abc"}
        (d / "b14.json").write_text(json.dumps({"status": "pending", **dau}), encoding="utf-8")
        ma, p = _run(d, "b14")
        assert ma is None, ma
        j = json.loads(p.read_text(encoding="utf-8"))
        assert {k: j.get(k) for k in dau} == dau, j

        # rejected: thẻ cũ đã đổi thành "đã bỏ" — không mang dấu vết sang nữa
        (d / "b14.json").write_text(json.dumps({"status": "rejected", **dau}), encoding="utf-8")
        ma, p = _run(d, "b14")
        assert ma is None, ma
        j = json.loads(p.read_text(encoding="utf-8"))
        assert not any(k in j for k in dau), j


def test_image_path_default_when_sidecar_has_none():
    with _sandbox() as d:
        _meta(d, "b15", source_url="https://x.test/y", category="AI")
        ma, p = _run(d, "b15")
        assert ma is None, ma
        assert Path(json.loads(p.read_text(encoding="utf-8"))["image"]).name == "b15.png"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
