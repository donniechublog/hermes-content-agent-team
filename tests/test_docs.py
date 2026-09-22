#!/usr/bin/env python3
"""Cổng chặn TRÔI TÀI LIỆU (06/09/2026).

Audit bắt được README mô tả sai hiện trạng ở ≥6 chỗ và nhắc 5 lần một tệp đã
xoá (`usage_audit.py`). Đó không phải lỗi viết ẩu — không có gì kiểm nên nó trôi
dần theo mỗi lần đổi code. Ba test dưới là thứ rẻ nhất chặn được đúng lớp đó:
tệp được nhắc phải có thật, và những con số mà code nói ra thì tài liệu không
được ghi khác.

Chạy:  venv/bin/python tests/test_docs.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ARCHITECTURE.md va hermes/README.md them o audit lượt 2 (ADF-r2-7): ARCHITECTURE.md
# lech ngay truoc khi vao git (Jean/Cape, create_pair o sai module). SKILL.md
# va SOUL.md CHUA vao day: chung nhac duong dan tuong doi trong thu muc skill
# va lenh chay tren server, cong nay se bao oan — can mot cong rieng.
TAI_LIEU = ["README.md", "IMAGE_RULES_ETHAN.md", "IMAGE_RULES_DRE.md", "IMAGE_RULES_KITE.md",
          "STYLE_TEXT_SPEC.md", "ARCHITECTURE.md", "hermes/README.md"]

# INCIDENT_LOG.md va incident_journal/*.md CO CHU DICH nam ngoai cong nay: chung la NHAT
# KY, nen viec chung nhac toi script da xoa (`usage_audit.py`, `doi_model_combo.py`)
# hay tep cua repo khac (`hermes_cli/env_loader.py`) chinh la noi dung cua chung.
# Bat chung phai tro toi tep con song la bat chung noi doi ve qua khu.

# Chỉ soi thứ TRÔNG NHƯ đường dẫn trong repo: có đuôi mã/tài liệu, không có
# khoảng trắng, không phải đường tuyệt đối hay biến (`~/…`, `<id>`, `state/…`).
DUONG_DAN = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|md|sh|json|js|css|yaml))`")
# Ten tep RUNTIME (sinh luc chay, khong nam trong git) — khong phai tep repo.
BO_QUA = ("~", "<", "$", "config.yaml", "jobs.json", "xong.json", "da_dung.json",
          "candidates.json",      # scan_sources sinh ra luc chay (/tmp), khong o repo
          "meta.json", "spec.json", "vung_ocr.json", "nop_lan.json", "img.json",
          "writer.json", "handoff.md", "caption.txt", "brief.md",
          "models_seen.json", "AGENTS.md", "package.json", "emoji-map.json",
          "boost.spec.json", "vung.json", "kanban.db", "agent.log", "gateway.log",
          "usageHistory",
          # LOW-228: ten English cua tep trong state/<brand>/prepare/<draft_id>/
          "manifest.json", "previous_submission.json", "submit_count.json",
          "find_more.json", "crash_count.json", "material.md",
          "profile.yaml",         # tep cua hermes (~/.hermes-*/profiles/*/), khong o repo
          # LOW-313: tep plugin kanban song o hermes-agent + <home>/plugins/, repo chi giu ban va
          "plugin_api.py", "dist/index.js", "dist/style.css",
          "regions_ocr.json", "regions.json",   # LOW-231: ten English cua tep Gin (vung_ocr/vung)
          "dist.index.js")        # hermes/README nhac TEN PHANG CU de noi "khong con dung"


def _file_ok_mention(vb: str) -> set:
    ra = set()
    for d in DUONG_DAN.findall(vb):
        if d.startswith(BO_QUA) or any(x in d for x in BO_QUA):
            continue
        if d.startswith("state/") or d.startswith("drafts/") or d.startswith("logs/"):
            continue
        ra.add(d)
    return ra


def test_docs_no_mention_file_already_delete():
    """Tệp bị xoá mà tài liệu vẫn nhắc thì người đọc đi tìm một thứ không có —
    đúng chuyện `usage_audit.py` (xoá 05/09/2026, README nhắc 5 lần)."""
    thieu = []
    for ten in TAI_LIEU:
        p = ROOT / ten
        if not p.exists():
            continue
        for d in _file_ok_mention(p.read_text(encoding="utf-8")):
            if not (ROOT / d).exists() and not list(ROOT.glob(f"**/{d}")):
                thieu.append(f"{ten}: `{d}`")
    assert not thieu, "tài liệu nhắc tệp không tồn tại:\n  " + "\n  ".join(thieu)


def test_readme_no_write_wrong_count_kind_of_render_edu():
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


def test_readme_no_write_wrong_kind_card_default():
    """README từng ghi Ethan dựng 'kiểu tràn' trong khi card.build mặc định là
    `quote` — vai đọc README rồi truyền cờ thừa, hoặc tưởng thẻ ra khác."""
    import inspect

    import card
    mac_dinh = inspect.signature(card.build).parameters["kieu"].default
    vb = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"mặc định thẻ **{mac_dinh}**" in vb, \
        f"card.build mặc định kieu={mac_dinh!r}, README phải nói đúng thế"


def test_board_change_figure_match_with_profile_real():
    """README noi vai nao co o brand nao — doi chieu voi ban chup profile that.

    Dung lop troi nay da xay ra hai lan: README ghi Kite "chua deploy dcgr" (do
    04/09, mot ngay TRUOC khi dcgr deploy 05/09) va khong ai sua; roi ban viet
    lai 06/09 chep tiep thanh "chi donniechublog". Ban chup
    hermes/profiles/live_config_snapshot.yaml gio cho phep kiem bang code.
    """
    import re
    try:
        import yaml
    except ImportError:
        return                       # khong co pyyaml thi bo qua, dung lam do test
    chup = ROOT / "hermes/profiles/live_config_snapshot.yaml"
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

def test_item_model_match_with_profile_real():
    """Muc "## Model" cua README khong duoc goi ten mot model ma KHONG profile nao
    dang chay. README tung ghi "Ada giu `ds/deepseek-reasoner`" suot nhieu ngay
    sau khi ca 20 profile da chuyen sang combo DS-v4Flash."""
    import re
    try:
        import yaml
    except ImportError:
        return
    chup = ROOT / "hermes/profiles/live_config_snapshot.yaml"
    if not chup.exists():
        return
    d = yaml.safe_load(chup.read_text(encoding="utf-8")) or {}
    dang_chay = {v.get("model/default") for v in d.values() if v.get("model/default")}
    vb = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"^## Model\n(.*?)(?=^## )", vb, re.S | re.M)
    assert m, "README khong con muc '## Model'"
    # Quy uoc: trong muc Model, ten trong backtick la model DANG chay. Model cu
    # nhac lai cho lich su thi viet chu thuong, khong backtick. Duong dan tep
    # (co duoi .yaml/.md/.py/.json) khong phai model.
    ten_model = {t for t in re.findall(r"`([^`\s]+)`", m.group(1))
                 if ("/" in t or t.startswith("DS-") or "deepseek" in t.lower())
                 and not re.search(r"\.(yaml|yml|md|py|json)$", t)}
    la = sorted(t for t in ten_model if t not in dang_chay)
    assert not la, ("muc Model nhac model KHONG profile nao dang chay: "
                    + ", ".join(la) + f" (dang chay: {sorted(dang_chay)})")

def _vietnamese_tokens(stem: str) -> list:
    """Tu/cum Viet khong dau trong mot ten tep, theo chinh tu dien docs/tu_dien_ten
    (cum.json + don.json, tru PASS). Tu English la chua co trong tu dien -> khong bat."""
    sys.path.insert(0, str(ROOT / "docs" / "tu_dien_ten"))
    from tudien import TuDien
    td = TuDien(ROOT / "docs" / "tu_dien_ten")
    parts = [p for p in re.split(r"[-_.]", stem.lower()) if p and not p.isdigit()]
    hits = ["_".join(parts[i:i + n]) for n in (4, 3, 2) for i in range(len(parts) - n + 1)
            if "_".join(parts[i:i + n]) in td.cum]
    return hits + [p for p in parts if p in td.don and p not in td.pass_]


def test_incident_journal_names_english():
    """LOW-367 (Ong Chu 22/09/2026: "tat ca folder Nhat_ky bo het tieng viet ko dau").
    Thu muc `nhat_ky/` -> `incident_journal/`, ten tep -> English; NOI DUNG giu tieng
    Viet co dau. Cong nay chan hai duong quay lai: nhanh cu tao tep o `nhat_ky/`, va
    tep moi dat ten kieu `2026-09-22-cron-troi-7-tieng...`. Bao nham (tu English
    trung tu Viet trong tu dien, vd `the`) -> them PASS vao docs/tu_dien_ten/them.json."""
    assert not (ROOT / "nhat_ky").exists(), \
        "thu muc nhat_ky/ quay lai o goc repo — chuyen tep sang incident_journal/ (LOW-367)"
    d = ROOT / "incident_journal"
    assert d.is_dir(), "khong thay incident_journal/"
    sai = {f.name: _vietnamese_tokens(f.stem) for f in d.iterdir() if f.is_file()}
    sai = {k: v for k, v in sai.items() if v}
    assert not sai, f"ten tep nhat ky con tieng Viet khong dau (dat ten English): {sai}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
