#!/usr/bin/env python3
"""trace_mutations.py — chung minh luoi LOW-311 DO khi pha dung nhanh no bao ve.

Tieu chi nghiem thu cua LOW-311: "moi kich ban phai DO khi pha dung nhanh no bao
ve". Test xanh khong noi len dieu do — mot test khang dinh long leo cung xanh. Tep
nay PHA tung nhanh san xuat (doi dieu kien / bo cong chan), chay tep test tuong
ung, doi test duoc neu ten phai HONG, roi tra tep ve nguyen trang.

CANH BAO: no SUA TEP SAN XUAT TAI CHO trong vai giay moi dot bien (luon tra lai
trong `finally`). Chi chay trong worktree rieng cua minh, KHONG chay trong thu
muc goc dung chung, KHONG chay tren may chu. Khong nam trong tests/run.sh / CI
(ten khong bat dau bang test_): ~30 lan chay tep test, vai phut.

Dung:
    venv/bin/python tests/trace_mutations.py              # tat ca
    venv/bin/python tests/trace_mutations.py approve_chat # chi module khop chuoi

Them kich ban moi vao luoi thi them mot dong vao MUTATIONS. Neo (`old`) phai xuat
hien DUNG MOT lan trong tep — code doi lam neo troi thi dong do bao SKIP va ma
thoat khac 0, de biet ma cap nhat.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (tep san xuat, doan goc, doan thay, tep test, tien to ten test phai DO)
MUTATIONS = [
    # --- approve_service ---------------------------------------------------
    ("approve_service.py", '        if not la_reply:\n', '        if False:\n',
     "test_trace_approve_service.py", "test_low25_reply_to_old_report"),
    ("approve_service.py",
     '                offset = u["update_id"] + 1\n                _write_offset(offset)\n',
     '                offset = u["update_id"] + 1\n',
     "test_trace_approve_service.py", "test_loop_writes_offset_before"),
    ("approve_service.py", '        if already_len_channel(d):\n', '        if False:\n',
     "test_trace_approve_service.py", "test_rescue_splits"),
    ("approve_service.py", '    if not is_boss(msg):\n        uid', '    if False:\n        uid',
     "test_trace_approve_service.py", "test_stranger_is_refused"),
    ("approve_service.py", '                if loai_loi_dang_bao != mo_ta:\n', '                if True:\n',
     "test_trace_approve_service.py", "test_loop_409"),
    ("approve_service.py",
     '    if _label_reason_redo(token, group, msg, thread_id, text):\n        return\n', '    pass\n',
     "test_trace_approve_service.py", "test_redo_reason_swallows"),
    ("approve_service.py", 're.fullmatch(r"[A-Za-z0-9]{1,5}", duoi)', 'True',
     "test_trace_approve_service.py", "test_document_filename_cannot_escape"),
    ("approve_service.py",
     '    if live and not force and live.get("tg_push_fingerprint") == push_fingerprint(live):',
     '    if False:',
     "test_trace_approve_service.py", "test_low296_identical"),
    # --- approve_command ---------------------------------------------------
    ("approve_command.py",
     '    if url_chuan in so:\n        cu = so[url_chuan]\n        tra_loi("URL',
     '    if False:\n        cu = so[url_chuan]\n        tra_loi("URL',
     "test_trace_approve_command.py", "test_bai_same_article_twice"),
    ("approve_command.py",
     '    if _HOST_CAM.search(p.hostname) or scan_common.host_say_drop(p.hostname):', '    if False:',
     "test_trace_approve_command.py", "test_bai_refuses_internal"),
    ("approve_command.py",
     '    if err:\n        tra_loi("❌ " + html_escape(err))\n        return\n',
     '    if err:\n        tra_loi("❌ " + html_escape(err))\n',
     "test_trace_approve_command.py", "test_bai_create_pair_error"),
    ("approve_command.py",
     '    if lenh not in ("/bai", "/vai", "/hd", "/help") and qua_gateway:', '    if False:',
     "test_trace_approve_command.py", "test_two_bots_one_group"),
    # --- approve_chat ------------------------------------------------------
    ("approve_chat.py", '    if _story_pass_job(msg, text):\n        return None',
     '    if False:\n        return None',
     "test_trace_approve_chat.py", "test_toolset_gate"),
    ("approve_chat.py", '    return chat_router.DROP_ONLY_READ', '    return None',
     "test_trace_approve_chat.py", "test_bare_chat_runs_read_only"),
    ("approve_chat.py", '    hang.doi(so)\n', '',
     "test_trace_approve_chat.py", "test_same_role_second_message"),
    ("approve_chat.py", '    finally:\n        hang.release()\n', '    finally:\n        pass\n',
     "test_trace_approve_chat.py", "test_queue_is_released"),
    ("approve_chat.py", '    if chat_router.profile_missing(profile):', '    if False:',
     "test_trace_approve_chat.py", "test_topic_without_profile"),
    # --- approve_post ------------------------------------------------------
    ("approve_post.py", '    if images and d.get("channel_album_mid"):', '    if False:',
     "test_trace_approve_post.py", "test_album_lands_then_text_fails"),
    ("approve_post.py", '    if not is_boss(cq):', '    if False:',
     "test_trace_approve_post.py", "test_stranger"),
    ("approve_post.py", '        if im.get("kite_task_id"):', '        if False:',
     "test_trace_approve_post.py", "test_send_to_kite"),
    # --- moat_publish ------------------------------------------------------
    ("moat_publish.py",
     '    if isinstance(d.get("moat"), dict) and d["moat"].get("workflow_id"):', '    if False:',
     "test_trace_moat_publish.py", "test_intake_twice"),
    ("moat_publish.py", '        if not tid or status == reported.get(tid):', '        if not tid:',
     "test_trace_moat_publish.py", "test_poll"),
    ("moat_publish.py", '        if cua_toi and brand != cua_toi:', '        if False:',
     "test_trace_moat_publish.py", "test_bottom_again_leaves_other_brands"),
    # --- publish -----------------------------------------------------------
    ("publish.py",
     '            mids = [r.get("message_id") for r in cac_manh] or [res.get("message_id")]',
     '            mids = [res.get("message_id")]',
     "test_trace_publish.py", "test_long_report_is_split"),
    ("publish.py", '        if a.thread_name not in topics:', '        if False:',
     "test_trace_publish.py", "test_unknown_topic"),
]


def run_one(prod, old, new, test_file, expect):
    """'RED' | 'GREEN' | 'SKIP'. Luon tra tep san xuat ve nguyen trang."""
    path = ROOT / prod
    src = path.read_text(encoding="utf-8")
    if src.count(old) != 1:
        return "SKIP", f"neo xuat hien {src.count(old)} lan"
    path.write_text(src.replace(old, new), encoding="utf-8")
    # -B + xoa .pyc: dot bien CUNG KICH THUOC ghi trong cung mot giay voi ban goc thi
    # Python tin .pyc cu (khoa cache = mtime theo giay + kich thuoc) va chay code
    # CHUA dot bien -> "GREEN" gia. Gap that 20/09/2026 khi doi cho hai dong.
    for pyc in (ROOT / "__pycache__").glob(path.stem + ".*.pyc"):
        pyc.unlink(missing_ok=True)
    try:
        r = subprocess.run([sys.executable, "-B", "-X", "utf8", str(ROOT / "tests" / test_file)],
                           capture_output=True, text=True, timeout=180, cwd=ROOT)
        failed = [ln.split()[1] for ln in r.stdout.splitlines() if ln.startswith("FAIL")]
    except subprocess.TimeoutExpired:
        return "RED", "treo (timeout) — dot bien lam ket hang doi"
    finally:
        path.write_text(src, encoding="utf-8")
        for pyc in (ROOT / "__pycache__").glob(path.stem + ".*.pyc"):
            pyc.unlink(missing_ok=True)
    hit = [f for f in failed if f.startswith(expect)]
    return ("RED" if hit else "GREEN"), f"{len(failed)} test do" + (f": {hit[0]}" if hit else "")


def main():
    pick = sys.argv[1] if len(sys.argv) > 1 else ""
    missed = 0
    for prod, old, new, test_file, expect in MUTATIONS:
        if pick not in prod:
            continue
        verdict, note = run_one(prod, old, new, test_file, expect)
        missed += verdict != "RED"
        print(f"{verdict:5} {prod:20} {expect:42} {note}")
    print(f"\n{missed} dot bien KHONG bi bat" if missed else "\nmoi dot bien deu bi bat (RED)")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
