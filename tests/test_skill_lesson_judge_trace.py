#!/usr/bin/env python3
"""LOW-309 — lưới ĐỐI CHIẾU VẾT cho `skill_lesson_filter.judge` trước khi tách.

`judge` (độ phức tạp 53) là cổng quyết định một bài học của vai được tự nhận hay
phải đẩy lên Ông Chủ. Nó thuần tính toán nhưng dài, và THỨ TỰ các cờ là một phần
của kết quả (Ông Chủ đọc cờ đầu tiên).

Cách kiểm ở đây, đúng luật 07/09/2026:

  1. KỊCH BẢN = một bản ghi pending + một `index` giả (thuần, không git, không
     mạng) — mỗi kịch bản chạm đúng một nhánh hoặc một cờ.
  2. VẾT = TOÀN BỘ dict `judge` trả về, kể cả thứ tự `flags`, `added`, `removed`.
  3. Vết của bản TRƯỚC khi tách đã ghi vào `tests/golden/judge_verdicts.json`.
     Bản sau khi tách phải cho ra ĐÚNG vết đó — 0 lệch mới commit.

Cố ý đổi hành vi thì ghi lại vết và giải thích phần lệch trong PR:
    venv/bin/python tests/test_skill_lesson_judge_trace.py --write-golden

Chay:  venv/bin/python tests/test_skill_lesson_judge_trace.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import skill_lesson_filter as slf                            # noqa: E402

GOLDEN = Path(__file__).resolve().parent / "golden" / "judge_verdicts.json"
T0 = 1_757_400_000.0


class _Index:
    """`index` giả: thuần, không git, không đọc đĩa ngoài `repo`.

    `symbols`: {ký hiệu: (còn_không, đường_dẫn, gợi_ý)} — đúng hợp đồng của
    `RepoIndex.check_symbol`. `commits`: {đường_dẫn: [dòng commit]}.
    """

    def __init__(self, repo, symbols=None, commits=None):
        self.repo = Path(repo)
        self._symbols = symbols or {}
        self._commits = commits or {}

    def check_symbol(self, symbol):
        return self._symbols.get(symbol, (None, None, None))

    def commits_since(self, path, created_at):
        return list(self._commits.get(path, []))


SKILL_CU = """# carousel

## Cách dùng

Chạy `venv/bin/python dre_prepare.py <draft_id>` rồi viết spec vào `spec.json`.
Mỗi slide một ảnh, một ý; chart chỉ ở slide thân.

## Bẫy đã gặp

Ảnh ngang mà chủ thể không gọn trong khung 4:5 thì phải dùng `stack`, không thì
chữ đè lên mặt người và cổng chặn bắt dựng lại từ đầu.
"""


def _ho_so(t):
    """Dựng cây repo giả: hermes/skills/carousel/SKILL.md."""
    p = Path(t) / "hermes" / "skills" / "carousel"
    p.mkdir(parents=True, exist_ok=True)
    (p / "SKILL.md").write_text(SKILL_CU, encoding="utf-8")
    return Path(t)


def _ban_ghi(**payload):
    goc = {"name": "carousel", "file_path": "SKILL.md", "action": "patch"}
    goc.update(payload)
    return {"id": "pend-01", "created_at": T0, "origin": "dre",
            "summary": "bài học thử", "payload": goc}


# Mỗi kịch bản: (tên, bản ghi, symbols, commits). `index.repo` gắn lúc chạy.
SCENARIOS = {
    # Thêm THUẦN (không xoá dòng nào, không chạm luật nào) — đường SẠCH, phải accepted.
    "patch_them_thuan_thi_accepted": (
        _ban_ghi(old_string="## Bẫy đã gặp",
                 new_string="## Bẫy đã gặp\n\nMột câu ngắn không chạm luật nào."), {}, {}),
    "patch_co_doi_dong_cu": (
        _ban_ghi(old_string="Mỗi slide một ảnh, một ý;",
                 new_string="Mỗi slide một ảnh, một ý, không hai;"), {}, {}),
    "patch_khong_ap_duoc": (
        _ban_ghi(old_string="Câu này không có trong SKILL", new_string="X"), {}, {}),
    "patch_nhieu_lan_khong_replace_all": (
        _ban_ghi(old_string="slide", new_string="trang"), {}, {}),
    "patch_nhieu_lan_co_replace_all": (
        _ban_ghi(old_string="slide", new_string="trang", replace_all=True), {}, {}),
    "action_la_thi_manual_action": (
        _ban_ghi(action="write", content="Một dòng mới hoàn toàn."), {}, {}),
    "file_khac_skill_md_thi_manual_action": (
        _ban_ghi(file_path="README.md", content="Một dòng mới hoàn toàn."), {}, {}),
    "skill_khong_co_thi_unknown_skill": (
        _ban_ghi(name="khong-co-skill-nay", content="Một dòng mới."), {}, {}),
    "edit_ghi_de_ca_tep": (
        _ban_ghi(action="edit", content="# carousel\n\n## Cách dùng\n\nMột câu ngắn.\n"), {}, {}),
    "ky_hieu_da_doi_ten": (
        _ban_ghi(old_string="## Bẫy đã gặp",
                 new_string="## Bẫy đã gặp\n\nGọi `tim_anh_moi.py` trước khi dựng."),
        {"tim_anh_moi.py": (False, None, "find_new_image.py")}, {}),
    "ky_hieu_con_nhung_code_da_doi": (
        _ban_ghi(old_string="## Bẫy đã gặp",
                 new_string="## Bẫy đã gặp\n\nGọi `dre_submit.py` sau khi viết spec."),
        {"dre_submit.py": (True, "dre_submit.py", None)},
        {"dre_submit.py": ["abc1234 fix(dre): doi cong so slide", "def5678 them test"]}),
    "ne_loi_thay_vi_sua": (
        _ban_ghi(old_string="## Bẫy đã gặp",
                 new_string="## Bẫy đã gặp\n\nGặp lỗi TypeError ở bước ghép thì né nó bằng cách bỏ slide cuối."),
        {}, {}),
    "doan_moi_trung_doan_cu": (
        _ban_ghi(old_string="## Bẫy đã gặp",
                 new_string="## Bẫy đã gặp\n\nẢnh ngang mà chủ thể không gọn trong khung 4:5 thì phải dùng `stack`, "
                            "không thì chữ đè lên mặt người và cổng chặn bắt dựng lại từ đầu."), {}, {}),
    "xoa_dong_dang_co": (
        _ban_ghi(old_string="Mỗi slide một ảnh, một ý; chart chỉ ở slide thân.\n", new_string=""), {}, {}),
    "nhac_nguon_su_that": (
        _ban_ghi(old_string="## Bẫy đã gặp",
                 new_string="## Bẫy đã gặp\n\nXem IMAGE_RULES §1.2c trước khi chọn ảnh khái niệm."), {}, {}),
    "nhac_ten_brand": (
        _ban_ghi(old_string="## Bẫy đã gặp",
                 new_string="## Bẫy đã gặp\n\nBên dcgr thì hook phải nói tiền, không nói tham số."), {}, {}),
    "them_qua_nhieu_dong": (
        _ban_ghi(old_string="## Bẫy đã gặp",
                 new_string="## Bẫy đã gặp\n" + "\n".join(f"Dòng thêm số {i}." for i in range(40))), {}, {}),
    "skill_thanh_qua_dai": (
        _ban_ghi(action="edit",
                 content="# carousel\n" + "\n".join(f"Dòng {i}." for i in range(300))), {}, {}),
    "skill_thanh_qua_nhieu_muc": (
        _ban_ghi(action="edit",
                 content="# carousel\n" + "\n".join(f"## Mục {i}\n\nNội dung." for i in range(14))), {}, {}),
    "khong_created_at_thi_bo_qua_commit": (
        {**_ban_ghi(old_string="## Bẫy đã gặp",
                    new_string="## Bẫy đã gặp\n\nGọi `dre_submit.py` sau khi viết spec."), "created_at": 0},
        {"dre_submit.py": (True, "dre_submit.py", None)},
        {"dre_submit.py": ["abc1234 mot commit"]}),
}


def _chay(ten, tmp):
    ban_ghi, symbols, commits = SCENARIOS[ten]
    repo = _ho_so(tmp)
    idx = _Index(repo, symbols, commits)
    return slf.judge(ban_ghi, brand="donniechublog", profile="dre", index=idx)


def _tat_ca():
    import tempfile
    ra = {}
    for ten in SCENARIOS:
        with tempfile.TemporaryDirectory() as t:
            ra[ten] = _chay(ten, t)
    return json.loads(json.dumps(ra, ensure_ascii=False))


def _make_test(ten):
    def _test():
        import tempfile
        muon = json.loads(GOLDEN.read_text(encoding="utf-8"))[ten]
        with tempfile.TemporaryDirectory() as t:
            duoc = json.loads(json.dumps(_chay(ten, t), ensure_ascii=False))
        for khoa in sorted(set(muon) | set(duoc)):
            assert duoc.get(khoa) == muon.get(khoa), (
                f"{ten} lệch ở `{khoa}`:\n  muốn: {json.dumps(muon.get(khoa), ensure_ascii=False)}"
                f"\n  được: {json.dumps(duoc.get(khoa), ensure_ascii=False)}")
    _test.__name__ = "test_" + ten
    return _test


for _ten in SCENARIOS:
    globals()["test_" + _ten] = _make_test(_ten)


def test_golden_has_no_stale_or_missing_scenarios():
    assert sorted(json.loads(GOLDEN.read_text(encoding="utf-8"))) == sorted(SCENARIOS)


def test_scenarios_touch_every_rule():
    """Vết vàng mà rỗng thì 0-lệch không chứng minh gì: mọi cờ phải có mặt."""
    co = {f["rule"] for v in json.loads(GOLDEN.read_text(encoding="utf-8")).values()
          for f in v["flags"]}
    for luat in ("manual_action", "unknown_skill", "does_not_apply", "stale_symbol",
                 "code_changed_since", "workaround", "duplicate", "rewrites_guidance",
                 "source_of_truth", "brand_specific", "too_large"):
        assert luat in co, luat
    assert any(v["verdict"] == "accepted" for v in
               json.loads(GOLDEN.read_text(encoding="utf-8")).values()), "không kịch bản nào SẠCH"


if __name__ == "__main__":
    if "--write-golden" in sys.argv:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(_tat_ca(), ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
        print(f"da ghi {GOLDEN}")
        raise SystemExit(0)
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
