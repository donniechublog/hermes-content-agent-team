#!/usr/bin/env python3
"""MOT lan quet = MOT bao cao, va reply vao bao cao do thi phai chay.

Su co 12/09/2026 (ticket "Vera"): trong MOT task, Vera chay `scan_submit.py` ba
lan — lan 1 ghi `k` sai dinh dang nen 20/27 muc bi bo, lan 2 viet tieu de ASCII
mat dau, lan 3 sach — va CA BA lan deu gui mot bao cao len topic. Ong Chu thay
ba ban gan giong nhau, reply "1, 7 - Dre" vao ban thu hai (msg 2004) va khong
nhan duoc gi ca: `--luu-mid` chi giu mid cua ban CUOI (2005) nen cong
`_is_reply_report` tra False, tin roi xuong hoi thoai, ma hoi thoai tren dcgr
lai nhuong cho gateway dang dat `require_mention: true` — khong ai tra loi.

Bon cong trong tep nay, theo dung thu tu chung da hong hom do:
  1. `scan_submit.error_block_send`  — ban hong thi KHONG gui (het canh ba bao cao).
  2. `publish --luu-mid`      — nho mid cua MOI manh, khong chi manh cuoi.
  3. `_is_reply_report`      — reply vao manh dau van tinh la lenh.
  4. `manifest_already_send`        — so thu tu doc tren ban DA GUI, khong phai ban
                                moi nhat theo mtime (hai thu do tach nhau ke tu
                                khi cong 1 chan gui ma van ghi manifest).

Chay:  venv/bin/python tests/test_report_one_attempt.py
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import manifest_common as mc                                  # noqa: E402
import scan_submit                                              # noqa: E402
from tam import bat_buoc_tam                                 # noqa: E402


# Nguyen van stderr cua manifest_write trong su co 12/09/2026 (rut gon).
CANH_MAT_TIN = "[bo qua] muc 1: k=#15 ngoai danh sach 1..80"
CANH_MAT_DAU = ("[canh bao] muc 1 title tieng Viet mat dau (AI, dat, doanh): "
                "Moonshot AI (Kimi) dat muc tieu 2 ty USD doanh thu nam")
CANH_TU_THEM = "[tu them] muc BAT BUOC vai bo sot: OpenAI ra ban ChatGPT rieng"
CANH_TOM_TAT = "[canh bao] summary_vi 16 tu (> 15), giu nguyen nhung nen rut (muc 4)"


# ======================================================= 1. cong chan gui
def test_error_block_send_block_copy_face_story():
    """`[bo qua]` = mat tron mot tin. Ban nay len topic la Ong Chu doc thieu."""
    assert scan_submit.error_block_send([CANH_MAT_TIN]) == [CANH_MAT_TIN]


def test_error_block_send_block_title_face_mark():
    """Headline la thu DUY NHAT Ong Chu doc tren topic."""
    assert scan_submit.error_block_send([CANH_MAT_DAU]) == [CANH_MAT_DAU]


def test_error_block_send_no_block_warning_script_already_self_processed():
    """`[tu them]` va summary dai: script da xu ly xong, chan la ket task ma
    Ong Chu khong nhan duoc gi ca."""
    assert scan_submit.error_block_send([CANH_TU_THEM, CANH_TOM_TAT]) == []


class _KetQua:
    """Gia lap CompletedProcess cua manifest_write/manifest_build."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def _run_main(tmp, stderr, stdout=None, manifest=None):
    """Chay scan_submit.main() cho Vera voi ket qua manifest_write gia lap.

    Tra ve (ma thoat, danh sach lan goi gui). `gui` bi thay bang ban ghi nhan
    de test khong dung toi Telegram."""
    d = Path(tmp)
    os.environ["CT_STATE_DIR"] = str(d)
    wd = d / "scan" / f"vera_{datetime.now(scan_submit.qb.VN).strftime('%Y%m%d')}"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "list.json").write_text("[]", encoding="utf-8")
    (wd / "report.txt").write_text("<b>Vera</b>\n<b>1.</b> Tin", encoding="utf-8")

    da_gui = []
    cu_chay, cu_gui, cu_argv = scan_submit._run, scan_submit.send, sys.argv
    scan_submit._run = lambda *a, **k: _KetQua(stdout or str(manifest or ""), stderr)
    scan_submit.send = lambda *a, **k: (da_gui.append((a, k)), True)[1]
    sys.argv = ["scan_submit.py", "--vai", "vera"]
    try:
        with bat_buoc_tam(tmp, vera={}):
            ma = scan_submit.main()
    finally:
        scan_submit._run, scan_submit.send, sys.argv = cu_chay, cu_gui, cu_argv
    return ma, da_gui


def test_scan_submit_no_send_copy_face_story():
    """Dung chuoi viec cua lan chay THU NHAT hom 12/09: 20/27 muc bi bo, rc=0,
    va ban cu van gui thang len topic."""
    with tempfile.TemporaryDirectory() as t:
        ma, da_gui = _run_main(t, stderr="\n".join([CANH_MAT_TIN, CANH_TU_THEM]))
    assert da_gui == [], f"ban mat tin KHONG duoc gui, nhung send() da chay: {da_gui}"
    assert ma == 1, f"phai tra ma khac 0 de vai biet ma sua, duoc {ma}"


def test_scan_submit_no_send_copy_title_face_mark():
    """Lan chay THU HAI hom 12/09 — chinh ban Ong Chu reply vao."""
    with tempfile.TemporaryDirectory() as t:
        ma, da_gui = _run_main(t, stderr=CANH_MAT_DAU)
    assert da_gui == [] and ma == 1, (ma, da_gui)


def test_scan_submit_still_send_when_only_has_warning_light():
    with tempfile.TemporaryDirectory() as t:
        man = Path(t) / "vera_candidates_2026-09-12.json"
        man.write_text("{}", encoding="utf-8")
        ma, da_gui = _run_main(t, stderr=CANH_TU_THEM, manifest=man)
    assert len(da_gui) == 1 and ma == 0, (ma, da_gui)


def test_scan_submit_pin_manifest_fit_send():
    """Ghim de approve_pick doc so thu tu tren dung ban da gui."""
    with tempfile.TemporaryDirectory() as t:
        man = Path(t) / "vera_candidates_2026-09-12.json"
        man.write_text("{}", encoding="utf-8")
        _ma, da_gui = _run_main(t, stderr="", manifest=man)
    assert da_gui, "phai gui"
    args = da_gui[0][0]
    assert Path(args[3]) == man, f"send() phai nhan duong dan manifest vua ghi: {args}"


def test_path_manifest_read_ok_all_two_kind_stdout():
    """manifest_write in `<duong dan>`, manifest_build in `da ghi N muc -> <...>`."""
    with tempfile.TemporaryDirectory() as t:
        man = Path(t) / "nova_candidates_2026-09-12.json"
        man.write_text("{}", encoding="utf-8")
        assert scan_submit.path_manifest(str(man)) == man
        assert scan_submit.path_manifest(f"da ghi 7 muc -> {man}") == man
        assert scan_submit.path_manifest(f"{Path(t) / 'khong-co.json'}") is None


# ============================================ 2. publish: mid cua MOI manh
def _send_fake(handler, text, luu_mid):
    """Chay `publish.main()` voi Telegram gia lap, tra ve tep mid da ghi."""
    import publish
    cu_client, cu_argv = httpx.Client, sys.argv
    cu_secrets = publish.load_secrets

    def _client_gia(*a, **k):
        k.pop("transport", None)
        return cu_client(*a, transport=httpx.MockTransport(handler), **k)

    httpx.Client = _client_gia
    publish.load_secrets = lambda: ("token-gia", "-100123")
    tep_text = Path(luu_mid).with_name("bao_cao.txt")
    tep_text.write_text(text, encoding="utf-8")
    sys.argv = ["publish.py", "--file", str(tep_text), "--luu-mid", str(luu_mid)]
    try:
        publish.main()
    finally:
        httpx.Client, sys.argv, publish.load_secrets = cu_client, cu_argv, cu_secrets
    return json.loads(Path(luu_mid).read_text(encoding="utf-8"))


def test_save_mid_small_new_fragment_of_report_long():
    """Bao cao 27 muc vuot 4096 ky tu bi Telegram chia doi; muc so 1 nam o manh
    DAU va Ong Chu reply vao do. Ban cu chi luu manh cuoi."""
    dem = {"n": 0}

    def handler(request):
        dem["n"] += 1
        return httpx.Response(200, json={"ok": True,
                                         "result": {"message_id": 2000 + dem["n"]}})

    with tempfile.TemporaryDirectory() as t:
        dai = "\n".join(f"<b>{i}.</b> Tin so {i} " + "x" * 120 for i in range(1, 40))
        d = _send_fake(handler, dai, Path(t) / "report_message_id.vera.json")
    assert dem["n"] > 1, "test hong: van ban nay phai bi chia thanh nhieu manh"
    assert d["message_ids"] == [2000 + i for i in range(1, dem["n"] + 1)], d
    assert d["message_id"] == d["message_ids"][-1], d


# ====================================== 3 + 4. cong reply va manifest da gui
def _set_mid(tmp, **noi_dung):
    """Ghi report_message_id.vera.json va tro STATE_DIR cua approve_pick vao tmp."""
    import approve_pick as dct
    d = Path(tmp)
    (d / "report_message_id.vera.json").write_text(json.dumps(noi_dung), encoding="utf-8")
    dct.STATE_DIR = d
    return dct


def _story(reply_mid):
    """Tin trong topic: Telegram luon gan san reply_to_message = tin goc topic,
    nen day dung payload that (xem _reply_real)."""
    return {"message_id": 2007, "message_thread_id": 83,
            "text": "1, 7 - Dre",
            "reply_to_message": {"message_id": reply_mid, "message_thread_id": 83,
                                 "from": {"id": 1, "is_bot": True}}}


def test_reply_into_fragment_mark_still_is_pick_command():
    with tempfile.TemporaryDirectory() as t:
        dct = _set_mid(t, message_id=2005, message_ids=[2004, 2005])
        try:
            assert dct._is_reply_report("vera", _story(2004)), \
                "reply vao manh DAU cua chinh bao cao do phai tinh la lenh"
            assert dct._is_reply_report("vera", _story(2005))
        finally:
            dct.STATE_DIR = Path(t)


def test_reply_into_report_old_still_got_reject():
    """Cong 06/09/2026 phai giu nguyen: bao cao CU co so thu tu khac."""
    with tempfile.TemporaryDirectory() as t:
        dct = _set_mid(t, message_id=2005, message_ids=[2004, 2005])
        assert not dct._is_reply_report("vera", _story(1976))


def test_go_drift_no_right_command():
    """Tin khong bam Reply: trong topic Telegram van co reply_to_message tro
    toi tin goc topic — khong duoc nham (su co 06/09/2026)."""
    with tempfile.TemporaryDirectory() as t:
        dct = _set_mid(t, message_id=2005, message_ids=[2005])
        msg = {"message_id": 2007, "message_thread_id": 83, "text": "1, 7 - Dre",
               "reply_to_message": {"message_id": 83, "message_thread_id": 83,
                                    "forum_topic_created": {"name": "vera"},
                                    "from": {"id": 1, "is_bot": True}}}
        assert not dct._is_reply_report("vera", msg)


def test_manifest_already_send_straight_copy_latest_by_mtime():
    """Ban bi cong BLOCK_SEND chan van nam tren dia va MOI hon ban da gui — neu
    van di theo mtime thi so thu tu tro vao mot bao cao chua ai nhin thay."""
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        da_gui = d / "vera_candidates_2026-09-12.json"
        da_gui.write_text("{}", encoding="utf-8")
        moi_hon = d / "vera_candidates_2026-09-12_t050203.json"
        moi_hon.write_text("{}", encoding="utf-8")
        os.utime(moi_hon, (10**9, 10**9 + 500))       # moi hon han
        os.utime(da_gui, (10**9, 10**9))
        dct = _set_mid(t, message_id=2005, message_ids=[2005], manifest=str(da_gui))
        assert dct.latest_manifest("vera") == moi_hon, "test hong: mtime phai lech"
        assert dct.manifest_already_send("vera") == da_gui


def test_manifest_already_send_return_none_when_not_yet_pin():
    """Bao cao gui truoc khi co co che ghim -> nguoi goi lui ve latest_manifest."""
    with tempfile.TemporaryDirectory() as t:
        dct = _set_mid(t, message_id=2005)
        assert dct.manifest_already_send("vera") is None
        dct2 = _set_mid(t, message_id=2005, manifest=str(Path(t) / "da-xoa.json"))
        assert dct2.manifest_already_send("vera") is None, "tep khong con thi khong ghim"


# ================================================== ngay VN, khong phai UTC
class _GioGia:
    """05:01 gio VN ngay 12/09 = 22:01 UTC ngay 11/09 — dung khoang gio cron quet."""

    @staticmethod
    def now(tz=None):
        t = datetime(2026, 9, 11, 22, 1, tzinfo=timezone.utc)
        return t.astimezone(tz) if tz else t


def test_name_manifest_and_report_by_date_vn():
    import manifest_write as mg
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "list.json").write_text(json.dumps(
            [{"title": "Oracle tăng doanh thu cloud", "link": "https://a.vn/1",
              "summary_vi": "Oracle tăng mạnh"}]), encoding="utf-8")
        cu_state, cu_dt, cu_argv = mg.STATE, mg.datetime, sys.argv
        mg.STATE, mg.datetime = d, _GioGia
        sys.argv = ["manifest_write.py", "--vai", "vera", "--in", str(d / "list.json"),
                    "--bao-cao", str(d / "report.txt")]
        try:
            with bat_buoc_tam(t, vera={}):
                mg.main()
        finally:
            mg.STATE, mg.datetime, sys.argv = cu_state, cu_dt, cu_argv
        ten = [p.name for p in d.glob("vera_candidates_*.json")]
        assert ten == ["vera_candidates_2026-09-12.json"], ten
        assert "2026-09-12" in (d / "report.txt").read_text(encoding="utf-8")


def test_path_out_new_not_placed_onto_copy_run_same_minutes():
    """Ba lan chay trong cung mot phut (12/09/2026) tung ra CUNG mot ten."""
    with tempfile.TemporaryDirectory() as t:
        goc = Path(t) / "vera_candidates_2026-09-12.json"
        goc.write_text("{}", encoding="utf-8")
        a = mc.path_out_new(goc)
        a.write_text("{}", encoding="utf-8")
        b = mc.path_out_new(goc)
        assert a != b, f"ban ghi lai thu hai de len ban thu nhat: {a}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
