#!/usr/bin/env python3
"""LOW-437 (30/09/2026): hang doi day lai moat (`moat_republish_queue.json`)
bi BA tien trinh doc-sua-ghi khong khoa — cron publish-due, cron
moat-publish-watch va nut `mlai` cua approve — va ghi bang `write_text` thang.

Hai cach mat muc, deu im lang:
  - hai tien trinh cung doc ban cu roi lan luot ghi de: muc cua ben ghi truoc mat;
  - `write_text` CAT NGAN tep truoc khi ghi, ben kia doc dung luc do -> JSON hong
    -> `_read_queue` tra {} -> ghi lai CHI con muc cua no, ca hang doi bien mat.

Test chay nhieu tien trinh con cung them muc qua DUONG CODE THAT (`refill`,
`_list_mark_form_bottom`, `_drop_block_queue`) va dem muc con lai. Do tren code
cu (Mac, 3 tien trinh x 200 muc): mat hang tram muc moi lan chay.

Chay:  venv/bin/python tests/test_low437_moat_queue_lock.py
"""
import inspect
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import state_paths                                            # noqa: E402
import tam                                                    # noqa: E402

N = 200
TRANSIENT_ERROR = "khong goi duoc moat: ConnectError: test"   # loi thu lai duoc -> refill ghi

# Ba kieu tien trinh, ung voi ba duong ghi that:
#   refill      -- intake truot (publish-due / moat-publish-watch / nut mlai)
#   mark        -- intake ghi "dang day" truoc khi POST
#   mark_drop   -- intake thanh cong: ghi truoc roi xoa khoi hang doi
CHILD = r"""
import sys
sys.path.insert(0, sys.argv[1])
import moat_publish as mp
kind, tag, n = sys.argv[2], sys.argv[3], int(sys.argv[4])
for i in range(n):
    draft_id = tag + "-" + str(i)
    if kind == "refill":
        mp.refill(draft_id, "donniechublog", None, sys.argv[5])
    elif kind == "mark":
        mp._list_mark_form_bottom(draft_id, "donniechublog", None)
    else:
        mp._list_mark_form_bottom(draft_id + "-tmp", "donniechublog", None)
        mp._drop_block_queue(draft_id + "-tmp")
        mp.refill(draft_id, "donniechublog", None, sys.argv[5])
"""


def _env(state_dir: Path) -> dict:
    env = dict(os.environ)
    env["CT_STATE_DIR"] = str(state_dir)
    env["CT_BRAND"] = "blog"
    return env


def _run_children(state_dir: Path, kinds) -> dict:
    env = _env(state_dir)
    procs = [subprocess.Popen([sys.executable, "-c", CHILD, str(ROOT), kind, kind, str(N),
                               TRANSIENT_ERROR], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for kind in kinds]
    for p in procs:
        out, err = p.communicate(timeout=300)
        assert p.returncode == 0, (p.args[3], out[-500:], err[-1500:])
    queue = state_dir / "blog" / state_paths.MOAT_REPUBLISH_QUEUE_FILE
    return json.loads(queue.read_text(encoding="utf-8"))


def test_concurrent_writers_lose_no_entries():
    kinds = ["refill", "mark", "mark_drop"]
    state_dir = tam.temp_dir("low437-")
    d = _run_children(state_dir, kinds)
    expected = {f"{k}-{i}" for k in kinds for i in range(N)}
    lost = sorted(expected - set(d))
    assert not lost, (f"mat {len(lost)}/{len(expected)} muc hang doi khi "
                      f"{len(kinds)} tien trinh cung ghi (vd {lost[:5]})")
    leftovers = sorted(k for k in d if k.endswith("-tmp"))
    assert not leftovers, f"_drop_block_queue bi ghi de, muc da xoa song lai: {leftovers[:5]}"
    assert all(d[f"refill-{i}"]["attempts"] == 1 for i in range(N)), "attempts bi dem sai"


def _fresh_module(state_dir: Path):
    """Nap moat_publish voi QUEUE/SPOOL tro vao state_dir tam (hang cap module)."""
    import importlib
    os.environ["CT_STATE_DIR"] = str(state_dir)
    os.environ["CT_BRAND"] = "blog"
    import moat_publish
    return importlib.reload(moat_publish)


def test_corrupt_queue_is_logged_not_silent():
    state_dir = tam.temp_dir("low437-")
    mp = _fresh_module(state_dir)
    mp.QUEUE.parent.mkdir(parents=True, exist_ok=True)
    mp.QUEUE.write_text('{"a": {"attempts": 1', encoding="utf-8")   # JSON cut
    buf = io.StringIO()
    with redirect_stdout(buf):
        got = mp._read_queue()
    assert got == {}, got                              # hanh vi tra ve giu nguyen
    assert "hang doi day lai" in buf.getvalue() and "hong" in buf.getvalue(), buf.getvalue()

    # Tep chua co la chuyen binh thuong (hang doi rong) -> KHONG log.
    mp.QUEUE.unlink()
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert mp._read_queue() == {}
    assert buf.getvalue() == "", buf.getvalue()


def test_queue_and_spool_writes_are_atomic():
    import moat_publish
    src = inspect.getsource(moat_publish)
    assert "QUEUE.write_text" not in src and "SPOOL.write_text" not in src, \
        "hang doi/spool con ghi write_text thang (cat ngan tep truoc khi ghi)"
    state_dir = tam.temp_dir("low437-")
    mp = _fresh_module(state_dir)
    mp.refill("d1", "donniechublog", None, TRANSIENT_ERROR)
    assert json.loads(mp.QUEUE.read_text(encoding="utf-8"))["d1"]["attempts"] == 1
    assert [p.name for p in mp.QUEUE.parent.iterdir() if ".tmp." in p.name] == []


def test_every_queue_mutation_holds_the_shared_lock():
    """Ca ba ham doc-sua-ghi phai khoa CUNG mot tep; khong ham nao duoc giu khoa
    roi goi sang ham khac cung khoa (flock hai fd trong mot tien trinh = tu khoa)."""
    import moat_publish as mp
    for fn in (mp._list_mark_form_bottom, mp.refill, mp._drop_block_queue):
        src = inspect.getsource(fn)
        assert "_queue_locked()" in src, f"{fn.__name__} doc-sua-ghi khong khoa"
    for fn in (mp.intake, mp.bottom_again):
        assert "_queue_locked()" not in inspect.getsource(fn), \
            f"{fn.__name__} giu khoa hang doi quanh intake -> tu khoa khi intake ghi"
    assert "state_paths.MOAT_QUEUE_LOCK" in inspect.getsource(mp._queue_locked)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
