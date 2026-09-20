#!/usr/bin/env python3
"""LOW-318 (20/09/2026) — brief phai goi vai bang DUNG ten cua no.

Brief cua Finn in lenh nop `scan_submit.py --vai scout`, brief cua Vera in
`--vai market` — slug CU tu truoc LOW-14, go cung trong `scan_prepare.py`. Lenh
van chay (argparse giai qua `role.canonical_slug`) nen khong ai thay, cho toi
sang 20/09: Finn tu chan va neu dung dong do nhu mot dau hieu "sai vai, loi
generator" (LOW-317) — mot vong chan doan mat trang chi vi tai lieu goi vai
bang ten khac.

SOUL cua Finn/Vera cung day dung hai lenh do, nen phai doi cung luc: SOUL la thu
vai doc TRUOC khi doc brief.

Chay:  venv/bin/python tests/test_low318_brief_role_slug.py
"""
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import role  # noqa: E402
import scan_prepare as sp  # noqa: E402

VAI_BRIEF = {"finn": sp.brief_scout, "nova": sp.brief_nova,
             "vera": sp.brief_market, "qinn": sp.brief_qinn}
SLUG_CU = ("scout", "market", "designer", "writer", "carousel")


def test_submit_command_carries_the_role_own_slug():
    for vai in VAI_BRIEF:
        dong = sp.submit_command(vai)
        assert dong.endswith(f"scan_submit.py --vai {vai}"), (vai, dong)
        assert not any(f"--vai {cu}" in dong for cu in SLUG_CU), dong


def test_every_brief_builder_receives_the_role():
    """Brief nao quen nhan `vai` la lai go cung ten mot lan nua."""
    for vai, ham in VAI_BRIEF.items():
        assert "vai" in inspect.signature(ham).parameters, vai


def test_no_hardcoded_submit_line_left_in_the_source():
    src = (ROOT / "scan_prepare.py").read_text(encoding="utf-8")
    go_cung = re.findall(r'scan_submit\.py --vai (\w+)"', src)
    assert not go_cung, f"con dong nop go cung ten vai: {go_cung}"
    assert src.count("submit_command(vai)") == len(VAI_BRIEF), "moi brief mot dong nop"


def test_dispatch_passes_the_canonical_slug():
    """`a.vai` da qua `role.canonical_slug`, nen brief luon nhan ten hien tai
    ke ca khi cron cu goi `--vai scout`."""
    src = (ROOT / "scan_prepare.py").read_text(encoding="utf-8")
    assert "(wd, a.lam_moi, a.vai)" in src
    assert role.canonical_slug("scout") == "finn"
    assert role.canonical_slug("market") == "vera"


def test_soul_of_finn_and_vera_teach_their_own_slug():
    for tep, vai, cu in ((ROOT / "hermes/profiles/blog/finn.SOUL.md", "finn", "scout"),
                         (ROOT / "hermes/profiles/dcgr/vera.SOUL.md", "vera", "market")):
        s = tep.read_text(encoding="utf-8")
        for lenh in ("scan_prepare.py", "scan_submit.py"):
            assert f"{lenh} --vai {vai}" in s, (tep.name, lenh)
            assert f"{lenh} --vai {cu}" not in s, (tep.name, lenh, cu)


def test_incident_notes_keep_the_old_name():
    """Cho KE LAI su co 13/09 (vai chay `--vai finn` roi nop `--vai scout`) phai
    giu nguyen chu cu — sua o do la ke sai chuyen da xay ra."""
    qinn = (ROOT / "hermes/profiles/blog/qinn.SOUL.md").read_text(encoding="utf-8")
    assert "--vai scout" in qinn


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
