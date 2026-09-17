#!/usr/bin/env python3
"""migrate_approve_stores.py (LOW-241): approve-bot stores -> English keys.

Guards: the script's maps equal the approved table, and the code writes/reads the table's
new names (blackboard entries, env vars, boss_ids.json); dry-run writes nothing; a real run
renames the keys of drafts (only those mentioning old keys), writer sidecars, redo_waiting,
article_request_counts and telegram_sent lines (other lines byte-identical, order kept) in
both brands and the single-brand layout, renames ong_chu.json, leaves .meta/.img/.bak
files alone, keeps unknown keys (journal), backs up originals; the result reads back
through the readers (approve_post marks + redo reply, submit_common.writer_for_article,
approve_command dedup reply); an unknown shape refuses the whole run; re-run is a no-op."""
import ast
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import state_paths as sp                                      # noqa: E402

TABLE = json.loads((ROOT / "docs" / "tu_dien_ten" / "approve_keys_v2.json").read_text(encoding="utf-8"))

DRAFT = {"caption": "bai", "status": "published", "channel_album_mid": 10, "channel_anh_mid": 11,
         "channel_chu_mid": True, "ghi_chu_cuu": "dich vu khoi dong lai", "tg_card_message_id": 5}
DRAFT_NEW = {"caption": "bai", "status": "published", "channel_album_mid": 10, "channel_photo_mid": 11,
             "channel_text_mid": True, "rescue_note": "dich vu khoi dong lai", "tg_card_message_id": 5}
WRITER = {"vai_viet": "jika", "title": "Tin", "body": "than", "created": True, "root_task": "t_root",
          "dre_task": "t_kite", "dre_task_truoc_kite": "t_dre", "writer_task": "t_w", "extra_note": 1}
WRITER_NEW = {"writer_role": "jika", "title": "Tin", "body": "than", "created": True, "root_task": "t_root",
              "dre_task": "t_kite", "dre_task_before_kite": "t_dre", "writer_task": "t_w", "extra_note": 1}
WRITER_NO_KITE = {"vai_viet": "miles", "title": "T", "body": "b", "created": False, "root_task": None,
                  "dre_task": "t_1"}
REDO = {"d1": {"draft_id": "d1", "thread_id": 7, "ts": 1.5, "title": "Tin", "hoi_mid": 900},
        "8": {"draft_id": "d2", "ts": 2.0}}
REDO_NEW = {"d1": {"draft_id": "d1", "thread_id": 7, "ts": 1.5, "title": "Tin", "question_mid": 900},
            "8": {"draft_id": "d2", "ts": 2.0}}
COUNTS = {"https://a.example/x": {"ngay": "2026-09-17 08:30", "draft_id": "d1", "vai": "dre", "brand": "blog",
                                  "tasks": ["t_1"], "title": "Bài A"}}
COUNTS_NEW = {"https://a.example/x": {"requested_at": "2026-09-17 08:30", "draft_id": "d1", "image_role": "dre",
                                      "brand": "blog", "tasks": ["t_1"], "title": "Bài A"}}
SENT_LINES = [
    {"ts": 1, "message_id": 3, "message_ids": [2, 3], "files": ["/a.png"], "md5": ["x"], "mo_ta": "Nền\u2028AI",
     "button_draft": "d1", "button_message_id": 4},
    "not json at all",
    {"ts": 2, "message_id": 5, "message_ids": [5], "files": [], "md5": [], "description": "đã mới"},
    {"ts": 3, "message_id": 6, "message_ids": [6], "files": [], "md5": [], "mo_ta": ""},
]


def _sent_text(lines) -> str:
    return "".join((x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)) + "\n" for x in lines)


def _layout(tmp: Path, extra=None) -> dict:
    st, dr = tmp / "state", tmp / "drafts"
    files = {
        "draft": dr / "d1.json",
        "draft_plain": dr / "d2.json",
        "draft_caption_only": dr / "d3.json",
        "meta": dr / "d1.meta.json",
        "img": dr / "d1.img.json",
        "bak": dr / "d1.json.bak",
        "writer": dr / "d1.writer.json",
        "writer_no_kite": dr / "d2.writer.json",
        "writer_done": dr / "d3.writer.json",
        "redo": st / "dcgr" / sp.REDO_WAITING_FILE,
        "redo_empty": st / "blog" / sp.REDO_WAITING_FILE,
        "counts": st / "blog" / sp.ARTICLE_REQUEST_COUNTS_FILE,
        "counts_empty": st / "dcgr" / sp.ARTICLE_REQUEST_COUNTS_FILE,
        "sent": st / "blog" / "telegram_sent" / "itachi.jsonl",
        "sent_single": st / "telegram_sent" / "gin.jsonl",
        "sent_done": st / "dcgr" / "telegram_sent" / "kite.jsonl",
        "boss": st / "blog" / "ong_chu.json",
    }
    data = {
        "draft": DRAFT, "draft_plain": {"caption": "x", "channel_album_mid": 1},
        "draft_caption_only": {"caption": "chu ghi_chu_cuu trong caption"},
        "meta": {"channel_anh_mid": 1}, "img": {"vai_viet": "x"}, "bak": {"channel_anh_mid": 1},
        "writer": WRITER, "writer_no_kite": WRITER_NO_KITE,
        "writer_done": {"writer_role": "miles", "title": "T", "body": "b", "created": False},
        "redo": REDO, "redo_empty": {}, "counts": COUNTS, "counts_empty": {},
        "boss": [8112291996],
    }
    data.update(extra or {})
    for k, p in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        if k.startswith("sent"):
            continue
        indent = None if k.startswith("redo") else 2
        p.write_text(json.dumps(data[k], ensure_ascii=False, indent=indent), encoding="utf-8")
    files["sent"].write_text(data.get("sent", _sent_text(SENT_LINES)), encoding="utf-8")
    files["sent_single"].write_text(data.get("sent_single", _sent_text(SENT_LINES[:1])), encoding="utf-8")
    files["sent_done"].write_text(_sent_text(SENT_LINES[2:3]), encoding="utf-8")
    return files


def _run(tmp: Path, *extra, env=None):
    import os
    e = dict(os.environ, **(env or {}))
    return subprocess.run([sys.executable, str(ROOT / "migrate_approve_stores.py"), "--state", str(tmp / "state"),
                           "--drafts", str(tmp / "drafts"), *extra], capture_output=True, text=True, cwd=ROOT,
                          env=e)


def _bytes(files: dict) -> dict:
    return {k: p.read_bytes() for k, p in files.items() if p.exists()}


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def test_maps_equal_approved_table():
    import migrate_approve_stores as m

    def _clean(d):
        return {k: v for k, v in d.items() if not k.startswith("_")}
    pairs = {
        "draft": m.DRAFT_KEY_MAP,
        "writer_sidecar": m.WRITER_SIDECAR_KEY_MAP,
        "redo_waiting_entry": m.REDO_WAITING_ENTRY_KEY_MAP,
        "blackboard_entry_keys": m.BLACKBOARD_ENTRY_KEY_MAP,
        "blackboard.redo": m.BLACKBOARD_REDO_KEY_MAP,
        "blackboard.kite_transfer": m.BLACKBOARD_KITE_TRANSFER_KEY_MAP,
        "article_request_count_entry": m.ARTICLE_REQUEST_COUNT_ENTRY_KEY_MAP,
        "telegram_sent_line": m.TELEGRAM_SENT_LINE_KEY_MAP,
        "files": m.FILE_RENAMES,
        "sync_hermes_snapshot_marker": m.SNAPSHOT_MARKER_RENAMES,
        "env": m.ENV_RENAMES,
    }
    data_sections = {k for k in TABLE if not k.startswith("_")}
    assert set(pairs) == data_sections, sorted(set(pairs) ^ data_sections)
    for section, mp in pairs.items():
        assert mp == _clean(TABLE[section]), section
    assert set(m.VALUE_TYPES) == {v for mp in (m.DRAFT_KEY_MAP, m.WRITER_SIDECAR_KEY_MAP,
                                                m.REDO_WAITING_ENTRY_KEY_MAP, m.ARTICLE_REQUEST_COUNT_ENTRY_KEY_MAP,
                                                m.TELEGRAM_SENT_LINE_KEY_MAP) for v in mp.values()}


def _blackboard_writes() -> dict:
    """{entry key: set of inner dict keys} of every `_blackboard_write(...)` in approve_post."""
    tree = ast.parse((ROOT / "approve_post.py").read_text(encoding="utf-8"))
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_blackboard_write":
            key, value = n.args[1], n.args[2]
            assert isinstance(key, ast.Constant) and isinstance(value, ast.Dict), ast.dump(n)
            out[key.value] = {k.value for k in value.keys}
    return out


def test_code_uses_table_names():
    import migrate_approve_stores as m
    import approve_base
    import approve_post
    import schema
    writes = _blackboard_writes()
    assert set(writes) == set(m.BLACKBOARD_ENTRY_KEY_MAP.values()), writes
    assert set(m.BLACKBOARD_REDO_KEY_MAP.values()) <= writes["redo"], writes
    assert not set(m.BLACKBOARD_REDO_KEY_MAP) & writes["redo"], writes
    assert set(m.BLACKBOARD_KITE_TRANSFER_KEY_MAP.values()) <= writes["kite_transfer"], writes
    assert not set(m.BLACKBOARD_KITE_TRANSFER_KEY_MAP) & writes["kite_transfer"], writes
    assert set(approve_post.MARK_LEN_CHANNEL) >= {m.DRAFT_KEY_MAP["channel_anh_mid"],
                                                   m.DRAFT_KEY_MAP["channel_chu_mid"]}
    assert approve_base.BOSS_IDS.name == sp.BOSS_IDS_FILE == m.FILE_RENAMES["ong_chu.json"]
    assert set(m.WRITER_SIDECAR_KEY_MAP.values()) <= set(schema._kind(schema.SidecarWrite))
    for mod in ("approve_dispatch.py", "approve_chat.py", "approve_command.py", "approve_service.py"):
        src = (ROOT / mod).read_text(encoding="utf-8")
        for old in m.ENV_RENAMES:
            assert old not in src, (mod, old)
    env_src = "".join((ROOT / mod).read_text(encoding="utf-8") for mod in
                      ("approve_dispatch.py", "approve_chat.py", "approve_command.py", "approve_service.py"))
    for new in m.ENV_RENAMES.values():
        assert f'"{new}"' in env_src, new
    sync_src = (ROOT / "sync_hermes.py").read_text(encoding="utf-8")
    for old, new in m.SNAPSHOT_MARKER_RENAMES.items():
        assert f'"{old}"' not in sync_src and f'"{new}"' in sync_src, (old, new)


def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = _bytes(f)
        r = _run(tmp, "--dry-run")
        assert r.returncode == 0 and "DRY RUN" in r.stdout and "7 file(s)" in r.stdout \
            and "1 renamed" in r.stdout, (r.stdout, r.stderr)
        assert "unchanged drafts/d3.writer.json" in r.stdout, r.stdout
        assert _bytes(f) == before and not list(tmp.glob("*.tar.gz")) and not list(tmp.glob("*.jsonl"))


def test_real_run_renames_backs_up_and_journals():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = _bytes(f)
        r = _run(tmp, env={"CT_BANG_DEN": "dcgr,blog"})
        assert r.returncode == 0, (r.stdout, r.stderr)
        assert "CT_BANG_DEN -> CT_BLACKBOARD_BRANDS" in r.stderr, r.stderr
        assert _load(f["draft"]) == DRAFT_NEW and list(_load(f["draft"])) == list(DRAFT_NEW)
        assert _load(f["writer"]) == WRITER_NEW and list(_load(f["writer"])) == list(WRITER_NEW)
        assert _load(f["writer_no_kite"])["writer_role"] == "miles"
        assert _load(f["redo"]) == REDO_NEW
        assert "\n" not in f["redo"].read_text(encoding="utf-8"), "redo_waiting.json stays on one line"
        assert _load(f["counts"]) == COUNTS_NEW
        for k in ("draft_plain", "draft_caption_only", "meta", "img", "bak", "writer_done", "redo_empty",
                  "counts_empty", "sent_done"):
            assert f[k].read_bytes() == before[k], f"{k} must not be rewritten"

        old_lines = before["sent"].decode("utf-8").split("\n")
        new_lines = f["sent"].read_text(encoding="utf-8").split("\n")
        assert len(new_lines) == len(old_lines) == 5 and new_lines[-1] == ""
        assert new_lines[1] == old_lines[1] and new_lines[2] == old_lines[2], "untouched lines byte-identical"
        first = json.loads(new_lines[0])
        assert list(first) == ["ts", "message_id", "message_ids", "files", "md5", "description",
                               "button_draft", "button_message_id"], first
        assert first["description"] == "Nền\u2028AI" and first["button_message_id"] == 4
        assert json.loads(new_lines[3]) == {"ts": 3, "message_id": 6, "message_ids": [6], "files": [], "md5": [],
                                            "description": ""}
        assert json.loads(f["sent_single"].read_text(encoding="utf-8").split("\n")[0])["description"] == "Nền\u2028AI"

        assert not f["boss"].exists()
        assert f["boss"].with_name(sp.BOSS_IDS_FILE).read_bytes() == before["boss"]

        (backup,) = tmp.glob("low241_approve_stores_backup_*.tar.gz")
        with tarfile.open(backup) as tar:
            names = set(tar.getnames())
            assert "drafts/d1.json" in names and "state/blog/ong_chu.json" in names, names
            assert tar.extractfile("state/blog/telegram_sent/itachi.jsonl").read() == before["sent"]
            assert len(names) == 8, names
        (journal,) = tmp.glob("low241_approve_stores_*.journal.jsonl")
        rows = {r_["file"]: r_ for r_ in (json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines())}
        assert len(rows) == 8, rows
        assert rows[str(f["writer"])]["kept_unknown_keys"] == ["extra_note"]
        assert rows[str(f["sent"])]["lines"] == 2
        assert rows[str(f["boss"])]["renamed_to"] == str(f["boss"].with_name(sp.BOSS_IDS_FILE))

        # readers see the migrated stores the way they saw the old ones
        from unittest import mock
        import approve_post
        import approve_base
        import submit_common
        assert approve_post.already_len_channel({"channel_photo_mid": _load(f["draft"])["channel_photo_mid"]})
        assert approve_post.already_len_channel({"channel_text_mid": _load(f["draft"])["channel_text_mid"]})
        with mock.patch.object(submit_common.cb, "DRAFTS", tmp / "drafts"):
            assert submit_common.writer_for_article("d1", "dcgr") == "jika"
        with mock.patch.object(approve_base, "BOSS_IDS", f["boss"].with_name(sp.BOSS_IDS_FILE)):
            assert approve_base.is_boss({"from": {"id": 8112291996}}) is True
            assert approve_base.is_boss({"from": {"id": 1}}) is False
        with mock.patch.object(approve_post, "REDO_WAIT", f["redo"]), \
                mock.patch.object(approve_post, "BOSS_IDS", tmp / "none.json"), \
                mock.patch.object(approve_post, "_run_background", lambda *a, **k: None), \
                mock.patch.object(approve_post, "_write_json", lambda *a, **k: None):
            msg = {"from": {"id": 1}, "reply_to_message": {"message_id": 900, "from": {"is_bot": True}}}
            assert approve_post._label_reason_redo("tok", "grp", msg, 7, "doi anh") is True


def test_article_request_count_reply_text_unchanged():
    """The /bai duplicate reply reads requested_at/image_role and prints the same words."""
    import approve_command
    from unittest import mock
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        assert _run(tmp).returncode == 0
        said = []
        with mock.patch.object(approve_command, "SET_ARTICLE_COUNT", f["counts"]), \
                mock.patch.object(approve_command, "_url_valid", lambda u: ""), \
                mock.patch.object(approve_command, "_standard_ify_url", lambda u: u):
            name = next(iter(approve_command.NAME_BRIGHT_CAP))
            approve_command._command_article(said.append, ["https://a.example/x", name])
        assert said == ["URL này đã đặt 2026-09-17 08:30 — draft <code>d1</code>, giao dre. Không tạo lại."], said


def test_bad_shape_or_conflict_refuses_everything():
    cases = (("draft", {"channel_anh_mid": 1, "channel_photo_mid": 1}, "both"),
             ("draft", {"channel_chu_mid": "abc"}, "expected int"),
             ("draft", ["channel_anh_mid"], "expected object"),
             ("writer", {"vai_viet": None}, "expected str"),
             ("writer", {"vai_viet": "a", "writer_role": "a"}, "both"),
             ("writer", "x", "expected object"),
             ("redo", {"d1": ["hoi_mid"]}, "expected object"),
             ("redo", {"d1": {"hoi_mid": "900"}}, "expected int"),
             ("redo", [], "expected object"),
             ("counts", {"u": {"ngay": "t", "requested_at": "t"}}, "both"),
             ("counts", {"u": {"vai": 3}}, "expected str"),
             ("sent", '{"mo_ta": "x", "description": "y"}\n', "both"),
             ("sent", '{"mo_ta": \n', "does not parse"),
             ("sent", '["mo_ta"]\n', "expected object"),
             ("sent_single", '{"mo_ta": 5}\n', "expected str"))
    for key, bad, word in cases:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            f = _layout(tmp, {key: bad})
            before = _bytes(f)
            r = _run(tmp)
            assert r.returncode == 1 and word in r.stderr and "nothing written" in r.stderr, (key, bad, r.stderr)
            assert _bytes(f) == before and not list(tmp.glob("*.tar.gz")), (key, bad)


def test_unparseable_draft_mentioning_old_keys_or_boss_ids_conflict_refuses():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _layout(tmp)
        (tmp / "drafts" / "broken.json").write_text('{"channel_chu_mid": ', encoding="utf-8")
        (tmp / "drafts" / "broken_other.json").write_text('{"caption": ', encoding="utf-8")   # not ours: ignored
        r = _run(tmp)
        assert r.returncode == 1 and "broken.json" in r.stderr and "broken_other" not in r.stderr, r.stderr
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        f["boss"].with_name(sp.BOSS_IDS_FILE).write_text("[]", encoding="utf-8")
        before = _bytes(f)
        r = _run(tmp)
        assert r.returncode == 1 and "already exists" in r.stderr, r.stderr
        assert _bytes(f) == before


def test_rerun_is_noop():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        assert _run(tmp).returncode == 0
        f["boss"] = f["boss"].with_name(sp.BOSS_IDS_FILE)
        after = _bytes(f)
        r = _run(tmp)
        assert r.returncode == 0 and "nothing to do" in r.stdout, r.stdout
        assert _bytes(f) == after
        assert len(list(tmp.glob("*.tar.gz"))) == 1


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
