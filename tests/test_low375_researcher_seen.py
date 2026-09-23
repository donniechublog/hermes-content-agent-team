#!/usr/bin/env python3
"""LOW-375 — luat Ong Chu 23/09/2026: *"chung ta ko dan lai tin da research duoc"*.

Bon vai researcher (Finn/Nova/Vera/Qinn) phai co CUNG mot bo nho da-thay. Truoc
LOW-375 chi Vera va Qinn co; Finn va Nova thieu han, va do duoc tren may chu:

  - Nova: 9/20 dong bao cao 23/09 la model da nam trong bao cao 22/09; muc
    "TIN TU HANG" lap 9/10 giua 21/09 va 22/09, 3 tin co mat ca ba ngay.
  - Finn: `--top` 40 nhung `manifest_build.MAX_PICK` 8, ma bo nho chi ghi cai
    DA NOP -> ~32 ung vien/ngay khong duoc nho, quay lai 3 ngay lien (cua so 72h).

CAC TEST DUOI DAY FAIL TREN CODE CU:
  - `test_nova_state_write_keeps_the_seen_stores`  (ban cu ghi dict CO DINH bon
    khoa -> xoa sach hf_seen/story_seen/github_seen moi sang)
  - `test_finn_has_a_real_seen_store`              (ban cu khong co ham nao)
  - `test_finn_store_catches_what_seen_keys_cannot` (chinh la con bug)
  - `test_every_researcher_exposes_the_same_contract`

Chay:  venv/bin/python tests/test_low375_researcher_seen.py
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import scan_seen                                             # noqa: E402
import scan_models as nova                                   # noqa: E402
import scan_sources as finn                                  # noqa: E402
import scan_business as vera                                 # noqa: E402
import scan_x as qinn                                        # noqa: E402


def _tmp(ten: str) -> Path:
    return Path(tempfile.mkdtemp(prefix="low375_")) / ten


# =========================================================================
# NOVA — ba kho tin, va cai bay lam chung bien mat
# =========================================================================
def test_nova_state_write_keeps_the_seen_stores():
    """FAIL TREN CODE CU. `write_timestamp` chay TRUOC cac lan `mark()` moi
    luot. Ban cu ghi mot dict CO DINH bon khoa, nen bo nho ngay-qua-ngay bi
    xoa sach moi sang — dung thu no sinh ra de chan. Day la su co `note` cua
    business_seen (26/08) lap lai o tep cua Nova."""
    old = nova.STATE
    try:
        nova.STATE = _tmp("models_seen.json")
        nova.seen_store(nova.HF_SEEN_FIELD, 7).mark(["org/model-hom-qua"])
        nova.seen_store(nova.STORY_SEEN_FIELD, 7).mark(["https://hang.com/tin-hom-qua"])
        nova.seen_store(nova.GITHUB_SEEN_FIELD, 7).mark(["vllm-project/vllm@v1"])

        nova.write_timestamp({"id-a"}, {"text": {"M": 1}}, {"AA": "2026-09-01"})

        d = json.loads(nova.STATE.read_text(encoding="utf-8"))
        assert "org/model-hom-qua" in d[nova.HF_SEEN_FIELD], \
            "write_timestamp da xoa hf_seen — Nova se bao lai tin hom qua"
        assert "https://hang.com/tin-hom-qua" in d[nova.STORY_SEEN_FIELD]
        assert "vllm-project/vllm@v1" in d[nova.GITHUB_SEEN_FIELD]
        # va ba truong cu van dung
        assert d["ids"] == ["id-a"] and d["aa_reported"] == {"AA": "2026-09-01"}
    finally:
        nova.STATE = old


def test_nova_repo_is_filtered_by_id_not_by_headline():
    """Ca that 22-23/09: cung `convaiinnovations/laya` ma hom truoc bao la
    "dung dau trending", hom sau bao la "tha trong so"; `Altworld/Hemmingway-1`
    ghi 20/09 roi lai ghi 16/09. Loc bang chu hay bang ngay deu hong — khoa
    phai la repo id."""
    old = nova.STATE
    try:
        nova.STATE = _tmp("models_seen.json")
        kho = nova.seen_store(nova.HF_SEEN_FIELD, 7)
        hom_qua = [{"id": "convaiinnovations/laya", "released": "2026-09-18",
                    "title": "dung dau trending"}]
        kho.mark(m["id"] for m in hom_qua)

        hom_nay = [{"id": "convaiinnovations/laya", "released": "2026-09-16",
                    "title": "tha trong so"},              # CHU va NGAY deu doi
                   {"id": "XiaomiMiMo/MiMo-V2.6-Pro-RL", "released": "2026-09-21"}]
        con, bo = kho.unseen(hom_nay, key=lambda m: m["id"])
        assert [m["id"] for m in con] == ["XiaomiMiMo/MiMo-V2.6-Pro-RL"]
        assert bo == 1
    finally:
        nova.STATE = old


def test_nova_github_key_is_repo_and_tag():
    """Cung mot repo ra ban moi VAN la tin moi — khoa phai co tag."""
    a = nova.github_key({"repo": "ggml-org/llama.cpp", "tag": "b1234"})
    b = nova.github_key({"repo": "ggml-org/llama.cpp", "tag": "b1235"})
    assert a != b and a.startswith("ggml-org/llama.cpp")


def test_nova_story_key_survives_utm_and_scheme():
    """Cung mot tin ma RSS doi tu http sang https, hoac them utm, khong duoc
    tinh la tin moi."""
    import scan_common
    k1 = scan_common.standard_link("http://blog.google/a/b/")
    k2 = scan_common.standard_link("https://www.blog.google/a/b?utm_source=rss")
    assert k1 == k2


# =========================================================================
# FINN — kho nho THAT, ben canh cai suy ra tu manifest/draft
# =========================================================================
def test_finn_has_a_real_seen_store():
    """FAIL TREN CODE CU: khong co `seen_store`."""
    old = finn.SEEN_PATH
    try:
        finn.SEEN_PATH = _tmp("finn_seen.json")
        kho = finn.seen_store()
        assert isinstance(kho, scan_seen.SeenStore)
        kho.mark(["example.com/a"])
        assert "example.com/a" in finn.seen_store().read()
    finally:
        finn.SEEN_PATH = old


def test_finn_store_catches_what_seen_keys_cannot():
    """CHINH LA CON BUG. Mot ung vien da DUA CHO FINN XEM nhung KHONG duoc
    chon (khong vao manifest, khong thanh draft) thi `seen_keys()` khong the
    biet — no chi doc `finn_candidates_*.json` va `drafts/*.json`. Khong co kho
    rieng thi ung vien do quay lai moi ngay cho toi khi het cua so 72h."""
    old = finn.SEEN_PATH
    try:
        finn.SEEN_PATH = _tmp("finn_seen.json")
        link = "https://news.ycombinator.com/item?id=999"
        khoa = finn._norm_url(link)

        # hom qua: dua cho Finn xem, Finn khong chon
        finn.seen_store().mark([khoa])

        # hom nay: `seen_keys()` khong biet gi ve no...
        assert khoa not in finn.seen_keys(), \
            "tien de cua test sai: seen_keys khong duoc biet ung vien chua nop"
        # ...nhung hop cua HAI bo nho thi biet, va do la cach main() loc
        da_dua = set(finn.seen_store().read())
        assert khoa in (finn.seen_keys() | da_dua)
    finally:
        finn.SEEN_PATH = old


def test_finn_keeps_protecting_in_flight_drafts():
    """Khong duoc danh doi: kho moi la THEM, khong thay `seen_keys()`. Mot URL
    dang co vai viet do (moi co .meta.json) van phai tinh la da dung."""
    assert callable(finn.seen_keys), "seen_keys bi go mat"
    old = finn.SEEN_PATH
    try:
        finn.SEEN_PATH = _tmp("finn_seen.json")
        assert finn.seen_store().read() == {}
        # kho rong thi hop hai bo nho == dung `seen_keys()` nhu truoc LOW-375
        assert (finn.seen_keys() | set(finn.seen_store().read())) == finn.seen_keys()
    finally:
        finn.SEEN_PATH = old


# =========================================================================
# CHUAN CHUNG — bon vai, mot hop dong
# =========================================================================
def test_every_researcher_exposes_the_same_contract():
    """FAIL TREN CODE CU (Finn khong co `seen_store`). Bon vai phai cung mot
    cach goi, neu khong thi lan sau lai moi vai mot kieu."""
    for vai, mod in (("finn", finn), ("nova", nova), ("vera", vera), ("qinn", qinn)):
        assert hasattr(mod, "seen_store"), f"{vai} thieu seen_store()"
    # Nova nhan (field, window) vi ba kho nam chung mot tep; ba vai kia mot kho
    assert nova.seen_store.__code__.co_argcount == 2
    for mod in (finn, vera, qinn):
        assert mod.seen_store.__code__.co_argcount == 0


def test_every_researcher_prunes_by_time_and_keeps_the_scan_window():
    """Luat 6: kho phai nho lau hon cua so quet, neu khong thi muc con trong
    cua so ma da bi quen -> quay lai bao cao."""
    cua_so = {"finn": 3, "nova": 7, "vera": 3, "qinn": 0.5}   # ngay
    old_f, old_v, old_q, old_n = finn.SEEN_PATH, vera.STATE, qinn.STATE, nova.STATE
    try:
        finn.SEEN_PATH = _tmp("finn_seen.json")
        vera.STATE = _tmp("business_seen.json")
        qinn.STATE = _tmp("x_seen.json")
        nova.STATE = _tmp("models_seen.json")
        kho = {"finn": finn.seen_store(), "vera": vera.seen_store(),
               "qinn": qinn.seen_store(),
               "nova": nova.seen_store(nova.HF_SEEN_FIELD, cua_so["nova"])}
        for vai, k in kho.items():
            assert k.keep_days >= 2 * cua_so[vai], \
                f"{vai}: kho {k.keep_days} ngay, qua ngan cho cua so {cua_so[vai]} ngay"
            # muc nam trong cua so quet khong bao gio duoc het han
            now = time.time()
            k.mark(["trong-cua-so"], now=now - cua_so[vai] * 86400)
            assert "trong-cua-so" in k.read(), f"{vai}: quen mot muc VAN con trong cua so"
    finally:
        finn.SEEN_PATH, vera.STATE, qinn.STATE, nova.STATE = old_f, old_v, old_q, old_n


def test_two_days_in_a_row_report_nothing_twice():
    """Hop dong cuoi cung, bang dung hinh cua su co: lo hom qua va lo hom nay
    trung nhau 9/10 thi hom nay chi duoc bao 1 muc."""
    kho = scan_seen.SeenStore(_tmp("bat_ky.json"), keep_days=30)
    hom_qua = [f"tin-{i}" for i in range(10)]
    kho.mark(hom_qua)
    hom_nay = hom_qua[:9] + ["tin-that-su-moi"]
    con, bo = kho.unseen([{"k": k} for k in hom_nay], key=lambda it: it["k"])
    assert [it["k"] for it in con] == ["tin-that-su-moi"]
    assert bo == 9


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
