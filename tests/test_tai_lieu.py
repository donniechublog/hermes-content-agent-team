#!/usr/bin/env python3
"""Cổng chặn TRÔI TÀI LIỆU (06/09/2026).

Audit bắt được README mô tả sai hiện trạng ở ≥6 chỗ và nhắc 5 lần một tệp đã
xoá (`usage_audit.py`). Đó không phải lỗi viết ẩu — không có gì kiểm nên nó trôi
dần theo mỗi lần đổi code. Ba test dưới là thứ rẻ nhất chặn được đúng lớp đó:
tệp được nhắc phải có thật, và những con số mà code nói ra thì tài liệu không
được ghi khác.

Chạy:  venv/bin/python tests/test_tai_lieu.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TAI_LIEU = ["README.md", "LUAT_ANH.md", "STYLE_TEXT_SPEC.md"]

# NHAT_KY_SU_CO.md CO CHU DICH nam ngoai cong nay: no la NHAT KY, nen viec no
# nhac toi script da xoa (`usage_audit.py`, `doi_model_combo.py`) hay tep cua
# repo khac (`hermes_cli/env_loader.py`) chinh la noi dung cua no. Bat no phai
# tro toi tep con song la bat no noi doi ve qua khu.

# Chỉ soi thứ TRÔNG NHƯ đường dẫn trong repo: có đuôi mã/tài liệu, không có
# khoảng trắng, không phải đường tuyệt đối hay biến (`~/…`, `<id>`, `state/…`).
DUONG_DAN = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|md|sh|json|js|css|yaml))`")
BO_QUA = ("~", "<", "$", "config.yaml", "jobs.json", "xong.json", "da_dung.json",
          "models_seen.json", "AGENTS.md", "package.json", "emoji-map.json",
          "boost.spec.json", "vung.json", "kanban.db", "agent.log", "gateway.log",
          "usageHistory")


def _tep_duoc_nhac(vb: str) -> set:
    ra = set()
    for d in DUONG_DAN.findall(vb):
        if d.startswith(BO_QUA) or any(x in d for x in BO_QUA):
            continue
        if d.startswith("state/") or d.startswith("drafts/") or d.startswith("logs/"):
            continue
        ra.add(d)
    return ra


def test_tai_lieu_khong_nhac_tep_da_xoa():
    """Tệp bị xoá mà tài liệu vẫn nhắc thì người đọc đi tìm một thứ không có —
    đúng chuyện `usage_audit.py` (xoá 05/09/2026, README nhắc 5 lần)."""
    thieu = []
    for ten in TAI_LIEU:
        p = ROOT / ten
        if not p.exists():
            continue
        for d in _tep_duoc_nhac(p.read_text(encoding="utf-8")):
            if not (ROOT / d).exists() and not list(ROOT.glob(f"**/{d}")):
                thieu.append(f"{ten}: `{d}`")
    assert not thieu, "tài liệu nhắc tệp không tồn tại:\n  " + "\n  ".join(thieu)


def test_readme_khong_ghi_sai_so_kind_cua_render_edu():
    """README từng ghi render_edu có '5 kind' trong khi code có 7 — loại sai mà
    người đọc không cách nào biết nếu không mở code ra đếm."""
    import render_edu
    vb = (ROOT / "README.md").read_text(encoding="utf-8")
    n = len(render_edu.BUILDERS)
    m = re.search(r"\*\*(\d+) kind\*\*", vb)
    assert m, "README không còn nói số kind của render_edu — sửa test hoặc README"
    assert int(m.group(1)) == n, f"README ghi {m.group(1)} kind, code có {n}"
    for k in render_edu.BUILDERS:
        assert f"`{k}`" in vb, f"README không liệt kê kind {k!r}"


def test_readme_khong_ghi_sai_kieu_the_mac_dinh():
    """README từng ghi Ethan dựng 'kiểu tràn' trong khi card.build mặc định là
    `quote` — vai đọc README rồi truyền cờ thừa, hoặc tưởng thẻ ra khác."""
    import inspect

    import card
    mac_dinh = inspect.signature(card.build).parameters["kieu"].default
    vb = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"mặc định thẻ **{mac_dinh}**" in vb, \
        f"card.build mặc định kieu={mac_dinh!r}, README phải nói đúng thế"


def test_bang_doi_hinh_khop_voi_profile_that():
    """README noi vai nao co o brand nao — doi chieu voi ban chup profile that.

    Dung lop troi nay da xay ra hai lan: README ghi Kite "chua deploy dcgr" (do
    04/09, mot ngay TRUOC khi dcgr deploy 05/09) va khong ai sua; roi ban viet
    lai 06/09 chep tiep thanh "chi donniechublog". Ban chup
    hermes/profiles/cau_hinh_that.yaml gio cho phep kiem bang code.
    """
    import re
    try:
        import yaml
    except ImportError:
        return                       # khong co pyyaml thi bo qua, dung lam do test
    chup = ROOT / "hermes/profiles/cau_hinh_that.yaml"
    if not chup.exists():
        return
    d = yaml.safe_load(chup.read_text(encoding="utf-8")) or {}
    co = {}
    for k in d:
        brand, slug = k.split("/", 1)
        co.setdefault(slug, set()).add(brand)

    vb = (ROOT / "README.md").read_text(encoding="utf-8")
    loi = []
    for dong in vb.splitlines():
        m = re.match(r"\|\s*[^|]+\|\s*`([a-z-]+)`\s*\|", dong)
        if not m:
            continue
        slug, brand_co = m.group(1), co.get(m.group(1))
        if not brand_co:
            continue
        thap = dong.lower()
        if "chỉ donniechublog" in thap or "blog only" in thap:
            if "dcgr" in brand_co:
                loi.append(f"README noi `{slug}` chi co o blog, nhung profile that co ca dcgr")
        if "chỉ dcgr" in thap and "blog" in brand_co:
            loi.append(f"README noi `{slug}` chi co o dcgr, nhung profile that co ca blog")
    assert not loi, "bang doi hinh lech voi profile that:\n  " + "\n  ".join(loi)

if __name__ == "__main__":
    ham = [v for k, v in list(globals().items()) if k.startswith("test_")]
    loi = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"FAIL {h.__name__}: {e}")
    print(f"\n{len(ham) - loi}/{len(ham)} test qua")
    sys.exit(1 if loi else 0)
