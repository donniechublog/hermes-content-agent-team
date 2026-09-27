#!/usr/bin/env python3
"""Bai blog 27/09/2026 09:51 len FB/IG chi CON 1 ANH du Kite dung du 8 slide.

Chuoi loi (task t_1e834320):
  1. create_pair TAO task anh roi moi CHAN — khe ~1s du cho dispatcher phat mot
     worker Kite; `hermes kanban block` chi doi trang thai, KHONG giet worker do.
  2. Mo chan -> worker thu hai. Hai phien Kite cho cung draft; phien dung dung du
     8 slide, Ong Chu duyet.
  3. Phien thua chay kite_submit lan nua: script XOA <id>_2..8.png TRUOC khi render
     roi bi giet giua chung — con lai dung anh bia.
  4. draft_write gom 1 anh, moat nhan 1 anh; moat_publish con bo qua im lang tep
     khong ton tai.

Tep nay giu ca ba lop sua: phien worker thua tu dung (tao task "chan san" khong
duoc — recompute_ready cua hermes tu nha no); render vao cho tam roi moi thay bo
cu (+ khoa theo draft); va chot chan so anh truoc khi dang.

Chay:  venv/bin/python tests/test_album_race.py
"""
import inspect
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import env_load                                                # noqa: E402


def _png(p: Path, noi_dung: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(noi_dung, encoding="utf-8")
    return p


def _bo(thu_muc: Path, ten: str, n: int, nhan: str) -> list:
    """Mot bo n slide gia: <ten>.png + <ten>_2..n.png, noi dung ghi nhan de phan biet."""
    ra = [_png(thu_muc / f"{ten}.png", f"{nhan}-1")]
    ra += [_png(thu_muc / f"{ten}_{i}.png", f"{nhan}-{i}") for i in range(2, n + 1)]
    return ra


# --- lop 2: render vao cho tam, du tep moi thay --------------------------------

def test_install_album_replaces_then_trims_old_extra_slides():
    with tempfile.TemporaryDirectory() as tmp:
        drafts = Path(tmp) / "drafts"
        _bo(drafts, "d1", 8, "cu")
        out = drafts / "d1.png"
        staged = env_load.staging_out(out)
        _bo(staged.parent, "d1", 6, "moi")

        files = env_load.install_album(staged, out, 6)

        assert [f.name for f in files] == ["d1.png"] + [f"d1_{i}.png" for i in range(2, 7)]
        assert all(f.read_text() .startswith("moi-") for f in files), [f.read_text() for f in files]
        assert not (drafts / "d1_7.png").exists() and not (drafts / "d1_8.png").exists(), \
            "slide cu thua (so > n) phai bi don, khong lot vao album"
        assert json.loads((drafts / "d1.album.json").read_text())["count"] == 6
        assert not staged.parent.exists(), "cho tam phai duoc don"


def test_install_album_with_missing_staged_file_leaves_old_set_intact():
    """Render bao xong nhung thieu tep: KHONG dong gi toi bo cu — nguoc voi ma cu
    (xoa truoc, render sau) de lai dung anh bia."""
    with tempfile.TemporaryDirectory() as tmp:
        drafts = Path(tmp) / "drafts"
        _bo(drafts, "d1", 8, "cu")
        out = drafts / "d1.png"
        staged = env_load.staging_out(out)
        _bo(staged.parent, "d1", 8, "moi")
        (staged.parent / "d1_3.png").unlink()
        try:
            env_load.install_album(staged, out, 8)
        except RuntimeError as e:
            assert "d1_3.png" in str(e), e
        else:
            raise AssertionError("thieu tep ma install_album khong bao loi")
        assert [p.read_text() for p in env_load.album_secondary("d1", drafts)] == \
            [f"cu-{i}" for i in range(2, 9)], "bo cu bi dong vao"
        assert (drafts / "d1.png").read_text() == "cu-1"


def test_submit_scripts_no_longer_delete_before_render():
    """Ca ba script nop bo anh phai di qua install_album, khong tu xoa album cu."""
    import dre_submit
    import hiro_submit
    import kite_submit
    for mod in (kite_submit, dre_submit, hiro_submit):
        src = inspect.getsource(mod.main)
        assert "install_album(" in src, f"{mod.__name__}.main khong dung install_album"
        assert "staging_out(" in src, f"{mod.__name__}.main khong render vao cho tam"
        assert "album_secondary(" not in src and ".unlink(" not in src.split("install_album(")[0], \
            f"{mod.__name__}.main con xoa album cu TRUOC khi render xong"


def test_draft_lock_rejects_second_submit_for_same_draft():
    with tempfile.TemporaryDirectory() as tmp:
        saved = env_load.ROOT
        env_load.ROOT = Path(tmp)
        try:
            with env_load.DraftLock("d1"):
                try:
                    env_load.DraftLock("d1").hold()
                except SystemExit as e:
                    assert "phien khac" in str(e), e
                else:
                    raise AssertionError("phien thu hai lay duoc khoa cua cung draft")
                with env_load.DraftLock("d2"):
                    pass                      # draft khac khong bi chan
            with env_load.DraftLock("d1"):
                pass                          # nha khoa roi thi lay lai duoc
        finally:
            env_load.ROOT = saved


def test_kite_submit_takes_the_draft_lock():
    import kite_submit
    assert "DraftLock(" in inspect.getsource(kite_submit.main)


# --- lop 3: chot chan so anh truoc khi dang ------------------------------------

def test_album_problem_flags_draft_with_fewer_images_than_slides():
    with tempfile.TemporaryDirectory() as tmp:
        drafts = Path(tmp)
        files = _bo(drafts, "d1", 8, "x")
        (drafts / "d1.album.json").write_text(json.dumps({"count": 8}))
        bia = str(files[0])
        # Dung ca cua 27/09: draft chi mang `image`, khong co `images`.
        assert "1/8" in env_load.album_problem("d1", {"image": bia})
        assert env_load.album_problem("d1", {"image": bia, "images": [str(f) for f in files]}) == ""
        files[4].unlink()
        assert "mat 1/8" in env_load.album_problem("d1", {"image": bia, "images": [str(f) for f in files]})


def test_album_problem_leaves_old_drafts_without_manifest_alone():
    with tempfile.TemporaryDirectory() as tmp:
        bia = _png(Path(tmp) / "d0.png", "x")
        assert env_load.album_problem("d0", {"image": str(bia)}) == ""
        assert env_load.album_problem("d0", {"image": "https://x/y.png"}) == ""


def test_moat_intake_refuses_broken_album_instead_of_sending_fewer_images():
    import moat_publish
    with tempfile.TemporaryDirectory() as tmp:
        files = _bo(Path(tmp), "d1", 8, "x")
        (Path(tmp) / "d1.album.json").write_text(json.dumps({"count": 8}))
        draft = {"image": str(files[0]), "caption": "c", "brand": "donniechublog"}
        saved = moat_publish.read_draft, moat_publish.config, moat_publish.images_payload
        goi = []
        moat_publish.read_draft = lambda _id: draft
        moat_publish.config = lambda _b: ("https://moat.example", "k")
        moat_publish.images_payload = lambda d: goi.append(d) or [{"base64": "x"}]
        try:
            ok, why = moat_publish.intake("d1")
        finally:
            moat_publish.read_draft, moat_publish.config, moat_publish.images_payload = saved
        assert not ok and "1/8" in why, (ok, why)


def test_publish_one_checks_album_before_telegram():
    import publish_schedule
    src = inspect.getsource(publish_schedule.publish_one)
    assert "album_problem(" in src
    assert src.index("album_problem(") < src.index("ap.publish("), \
        "kiem bo anh SAU khi dang Telegram thi bai thieu anh da len kenh roi"


def test_draft_write_refuses_incomplete_album():
    src = (ROOT / "draft_write.py").read_text(encoding="utf-8")
    assert "album_problem(" in src
    with tempfile.TemporaryDirectory() as tmp:
        # draft_write duoc viet truoc khi anh bia xong — tep thieu KHONG chan o day.
        assert env_load.album_problem("d9", {"image": str(Path(tmp) / "d9.png")}, check_missing=False) == ""


# --- lop 1: phien worker thua tu dung ------------------------------------------

def _kanban_db(path: Path, rows):
    import sqlite3
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE tasks (id TEXT, status TEXT, worker_pid INTEGER)")
    con.executemany("INSERT INTO tasks VALUES (?, ?, ?)", rows)
    con.commit()
    con.close()


def _with_worker_env(db: Path, fn):
    import os
    keys = ("HERMES_DELEGATED_CHILD_CONTEXT", "HERMES_KANBAN_DB")
    saved = {k: os.environ.get(k) for k in keys}
    os.environ["HERMES_DELEGATED_CHILD_CONTEXT"], os.environ["HERMES_KANBAN_DB"] = "1", str(db)
    try:
        return fn()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_worker_whose_ancestor_holds_a_running_task_is_valid():
    import os
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "kanban.db"
        # To tien that cua tien trinh test dong vai worker hermes dang giu task.
        _kanban_db(db, [("t_ok", "running", os.getppid()), ("t_khac", "running", 999999)])
        assert _with_worker_env(db, env_load.stale_worker_reason) == ""


def test_worker_of_a_blocked_or_reassigned_task_is_stale():
    """Dung ca t_1e834320: worker A bi chan (worker_pid NULL) roi task giao cho
    worker B (pid khac) — A khong con la to tien cua ai dang giu task."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "kanban.db"
        _kanban_db(db, [("t_1e834320", "blocked", None)])
        assert "phien thua" in _with_worker_env(db, env_load.stale_worker_reason)
        db.unlink()
        _kanban_db(db, [("t_1e834320", "running", 999999)])
        assert "phien thua" in _with_worker_env(db, env_load.stale_worker_reason)
        try:
            _with_worker_env(db, lambda: env_load.exit_if_stale_worker("kite_submit"))
        except SystemExit as e:
            assert "KET THUC TASK" in str(e), e
        else:
            raise AssertionError("phien thua khong bi dung")


def test_not_in_a_worker_or_unreadable_kanban_never_blocks():
    """Chay tay (nguoi van hanh, test, --khong-gui) hoac kanban hong: khong chan nham."""
    import os
    saved = os.environ.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
    try:
        assert env_load.stale_worker_reason() == ""
    finally:
        if saved is not None:
            os.environ["HERMES_DELEGATED_CHILD_CONTEXT"] = saved
    with tempfile.TemporaryDirectory() as tmp:
        assert _with_worker_env(Path(tmp) / "khong-co.db", env_load.stale_worker_reason) == ""


def test_scripts_that_touch_the_album_stop_stale_workers_first():
    import dre_submit
    import hiro_submit
    import kite_prepare
    import kite_submit
    for mod in (kite_submit, dre_submit, hiro_submit):
        src = inspect.getsource(mod.main)
        assert "exit_if_stale_worker(" in src, f"{mod.__name__} khong chan phien thua"
        assert src.index("exit_if_stale_worker(") < src.index("install_album("), \
            f"{mod.__name__}: chan phien thua SAU khi da cai bo anh"
    src = inspect.getsource(kite_prepare.main)
    assert src.index("exit_if_stale_worker(") < src.index("cb.run("), \
        "kite_prepare: phien thua kip ghi de tu lieu/spec"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
