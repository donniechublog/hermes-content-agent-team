#!/usr/bin/env python3
"""Cac ham THUAN chua ai canh — re nhat de test, dat nhat khi hong im.

Audit 06/09/2026: nhung ham duoi day khong goi mang, khong doc dia, khong can
Hermes — nhung khong ham nao co test, va phan lon quyet dinh nhung viec khong
lo ra khi hong:

  - `has_vietnamese`  quyet dinh co nem tieu de Viet vao Google News/Bing khong
                     (luat Ong Chu 05/09). Hong = hai tieng tim kiem vo ich va
                     Dre bo cuoc vi khong co anh.
  - `_url_valid`    cong chan URL noi bo cho lenh /bai.
  - `route`          topic nao thi vai nao tra loi.
  - `_HangFIFO`      thu tu tra loi chat trong mot phien; cau truc dong bo tu
                     viet, sinh ra sau su co 04/09 (Itachi doi Gin 108 giay).
  - `gather_duplicate`      gop nhieu bao dua cung mot su kien. Docstring cua no ke
                     hai lan hoi quy that; ca hai o day thanh test.
  - `standard_ify`      khoa dedup ghi vao business_seen.json.
  - `env_load.brand_long` doi CT_BRAND (ten NGAN cho state, "blog"/"dcgr") ra slug
                     thuong hieu DAI ("donniechublog"/"dcgr") ma card.py doi.
                     Sinh 09/09/2026: lan thang CT_BRAND vao card.set_brand
                     lam SystemExit "Khong biet thuong hieu 'blog'", giet ca
                     `prepare_article()" — bat HAI cho lam sai giong het nhau trong cung
                     mot lan chay lai (image_prepare.py va image_brand.py).

Chay:  venv/bin/python tests/test_function_pure.py
"""
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ------------------------------------------------------------- approve_pick.slugify
def test_slugify_keep_raw_negative_has_mark_see_vi_delete():
    """LOW-138: regex `[^a-z0-9]+` cu xoa THANG ky tu co dau (khong chuyen ve
    khong dau), nen "nhom" -> "nh-m", "thang 10" -> "th-ng-10" — slug cut chu,
    kho doc/kho tra log. Sua bang _strip_diacritics truoc khi loc ascii."""
    import approve_pick as ap
    assert ap.slugify("Anthropic nhóm IPO Nasdaq tháng 10 nhận giá", "fb") == \
        "anthropic-nhom-ipo-nasdaq-thang-10-nhan"
    assert ap.slugify("Đường dẫn tệp đặc biệt", "fb") == "duong-dan-tep-dac-biet"
    assert ap.slugify("", "fallback-rong") == "fallback-rong"


# ------------------------------------------------------------- env_load.brand_long
def test_brand_long_change_use_all_two_dimension():
    """CT_BRAND ('blog') phai ra 'donniechublog' — chinh loi bat 09/09/2026 (hai
    cho trong image_brand.py truyen thang CT_BRAND vao card.set_brand,
    nem 'Khong biet thuong hieu blog' vi card.py chi biet slug DAI)."""
    import env_load
    cu = os.environ.get("CT_BRAND")
    try:
        os.environ["CT_BRAND"] = "blog"
        assert env_load.brand_long() == "donniechublog"
        os.environ["CT_BRAND"] = "dcgr"
        assert env_load.brand_long() == "dcgr"          # trung ca hai chieu, sao cung dung
    finally:
        if cu is None:
            os.environ.pop("CT_BRAND", None)
        else:
            os.environ["CT_BRAND"] = cu


def test_brand_long_no_distinguish_then_about_default():
    """CT_BRAND rong/la (che do don, hoac gia tri khong ro) -> mac_dinh, khong nem."""
    import env_load
    cu = os.environ.get("CT_BRAND")
    try:
        os.environ.pop("CT_BRAND", None)
        assert env_load.brand_long() == "donniechublog"
        os.environ["CT_BRAND"] = "khong-ro"
        assert env_load.brand_long("dcgr") == "dcgr"
    finally:
        if cu is None:
            os.environ.pop("CT_BRAND", None)
        else:
            os.environ["CT_BRAND"] = cu


# ------------------------------------------------------------ has_vietnamese
def test_has_vietnamese_start_no_catch_ascii():
    import article_sources as nb
    for t in ["Nvidia đàm phán rót 2,5 tỷ USD", "Mô hình mở", "đ", "Ý"]:
        assert nb.has_vietnamese(t), f"bo sot dau: {t!r}"
    for t in ["Nvidia in talks to invest $2.5B", "GPT-5 Codex Max", "",
              "Qwen3-Max: 1 trieu token context"]:
        assert not nb.has_vietnamese(t), f"bao nham co dau: {t!r}"


def test_has_vietnamese_label_none():
    import article_sources as nb
    assert nb.has_vietnamese(None) is False


def test_query_bing_reject_vietnamese():
    """Chan cung, khong phai loi khuyen: tieu de Viet -> khong sinh truy van."""
    import article_sources as nb
    assert nb._query_bing("Nvidia đàm phán rót 2,5 tỷ USD") == []
    assert nb._query_bing("Nvidia in talks to invest $2.5B") != []


# -------------------------------------------------------------- _url_valid
def test_url_valid_block_host_say_drop():
    import approve_command as dl
    for u in ["http://localhost:9130/", "http://127.0.0.1:9121/x",
              "http://10.0.0.5/", "http://192.168.1.61:20128/v1",
              "http://169.254.169.254/latest/meta-data/",
              "http://172.16.0.1/", "http://172.31.255.1/",
              "http://may.local/", "http://x.internal/"]:
        assert dl._url_valid(u), f"khong chan host noi bo: {u}"


def test_url_valid_label_url_real_and_block_scheme_is():
    import approve_command as dl
    assert dl._url_valid("https://openai.com/index/abc") is None
    assert dl._url_valid("http://vnexpress.net/bai-1.html") is None
    # 172.32 KHONG thuoc dai rieng (dai la 172.16-172.31)
    assert dl._url_valid("http://172.32.0.1/") is None
    for u in ["file:///etc/passwd", "ftp://x.com/a", "khong-phai-url",
              "https://", "javascript:alert(1)"]:
        assert dl._url_valid(u), f"khong chan scheme/URL la: {u}"


def test_standard_ify_url_drop_tracking_keep_part_remaining_again():
    import approve_command as dl
    assert (dl._standard_ify_url("https://X.com/Bai?utm_source=a&id=7#doan2")
            == "https://x.com/Bai?id=7")
    assert (dl._standard_ify_url("https://x.com/a/") == dl._standard_ify_url("https://x.com/a"))


# -------------------------------------------------------------------- route
def test_route_topic_out_use_role():
    import chat_router as cr
    topics = {"finn": 11, "miles": 22, "kite": 33}
    assert cr.route(11, topics) == ("finn", "tele-finn")
    assert cr.route(33, topics) == ("kite", "tele-kite")


def test_route_topic_is_no_out_profile_but_still_has_session():
    """Topic khong co trong TOPIC_PROFILE: profile None (hermes dung profile mac
    dinh) nhung phien van rieng theo topic — hai topic la khong duoc dung chung
    mot phien chat."""
    import chat_router as cr
    assert cr.route(99, {}) == (None, "tele-general")
    assert cr.route(44, {"la_hoac": 44}) == (None, "tele-la_hoac")


# ---------------------------------------------------------------- _HangFIFO
def test_rank_fifo_use_order_below_many_flow():
    import approve_chat as dc
    h = dc.RankFIFCell()
    ra, khoa = [], threading.Lock()

    # lay so TUAN TU (dung nhu vong poll: mot thread nhan tin), roi tha ra
    sos = []
    for i in range(5):
        sos.append(h.lay_so())
    assert [s[1] for s in sos] == [0, 1, 2, 3, 4], "so nguoi dung truoc sai"
    # phuc vu theo dung thu tu ve
    for _ in range(5):
        h.release()

    h2 = dc.RankFIFCell()
    ts = []
    for i in range(5):
        so, _ = h2.lay_so()               # lay so trong thread chinh -> thu tu chac chan
        t = threading.Thread(target=_serve, args=(h2, so, i, ra, khoa))
        ts.append(t)
    for t in ts:
        t.start()
    for t in ts:
        t.join(5)
    assert ra == [0, 1, 2, 3, 4], f"khong FIFO: {ra}"


def _serve(h, so, i, ra, khoa):
    h.doi(so)
    with khoa:
        ra.append(i)
    h.release()


def test_rank_fifo_report_use_count_person_form_change():
    """Con so nay di thang vao tin 'dang tra loi N tin truoc' gui cho Ong Chu."""
    import approve_chat as dc
    h = dc.RankFIFCell()
    assert h.lay_so() == (0, 0)           # nguoi dau: khong ai truoc
    assert h.lay_so() == (1, 1)
    assert h.lay_so() == (2, 2)
    h.release()                           # nguoi 0 xong
    assert h.lay_so() == (3, 2)           # con 2 nguoi truoc, khong phai 3


# ------------------------------------------------------- gather_duplicate / standard_ify
def _story(td, ts, toa="x"):
    return {"tieu_de": td, "ts": ts, "toa_soan": toa, "link": "", "goc": "g"}


def test_gather_duplicate_merge_same_event_other_line_from():
    """Ca Cloverleaf kinh dien trong docstring cua gather_duplicate: Reuters viet
    'invests in', TechCrunch viet 'partners with' — mot su kien."""
    import scan_business as sb
    tin = [_story("Nvidia invests in data center developer Cloverleaf Infrastructure", 100, "reuters"),
           _story("Nvidia partners with data center developer Cloverleaf", 200, "techcrunch")]
    ra = sb.gather_duplicate(tin)
    assert len(ra) == 1, [t["tieu_de"] for t in ra]
    assert ra[0]["so_bao"] == 2
    assert ra[0]["ts"] == 100, "phai giu ban som nhat"


def test_gather_duplicate_no_merge_two_story_reverse_other():
    """Phan con lai cua cung docstring: mau so la MAX chu khong phai MIN, neu
    khong thi 'Nvidia stock jumps' nuot 'Nvidia stock slides after...' — hai tin
    NGUOC nhau thanh mot va Vera bao nham chieu."""
    import scan_business as sb
    tin = [_story("Nvidia stock jumps", 100),
           _story("Nvidia stock slides after Beijing bans chip purchases", 200)]
    ra = sb.gather_duplicate(tin)
    assert len(ra) == 2, f"gop nham hai tin nguoc nhau: {[t['tieu_de'] for t in ra]}"


def test_dedup_merges_same_deal_reworded_across_outlets():
    """LOW-184: Vera 16/09 dua 5 dong cho MOT vong goi von Euclyd — cac bao lech
    dong tu, lech so (230/231), lech tien te (€200M), nguong 60% khong bat duoc."""
    import scan_business as sb
    tin = [_story("Samsung backs Nvidia AI chip rival in $230 million funding round as GPU alternatives boom - CNBC", 100, "CNBC"),
           _story("Samsung Co-Led $231 Million Funding Round for Nvidia AI Chip Rival - SammyGuru", 200, "SammyGuru"),
           _story("Dutch AI chipmaker Euclyd pulled in $231 million with Samsung's backing - qz.com", 300, "qz.com"),
           _story("Samsung Leads $230 Mn Funding for European Chip Co EUCLYD Amid Memory Shortage - analyticsindiamag.com", 400, "analyticsindiamag.com"),
           _story("Euclyd secures over €200M in Series A co-led by Samsung and Somerset Capital - Crypto Briefing", 500, "Crypto Briefing"),
           _story("Samsung's Taylor Fab Begins Mass Production of Tesla AI5 Chips, Targets Full Capacity by Year-End", 600, "biggo")]
    ra = sb.gather_duplicate(tin)
    assert len(ra) == 2, [t["tieu_de"] for t in ra]
    assert ra[0]["so_bao"] == 5 and ra[0]["ts"] == 100


def test_dedup_keeps_different_deals_with_same_amount_apart():
    """Cung so tien nhung chi chung tu goi von, hoac chi chung MOT ten hang, la hai vu khac nhau."""
    import scan_business as sb
    tin = [_story("Acme Robotics raises $100 million in Series A round led by Sequoia for warehouse arms", 100),
           _story("Zeta Health lands $100 million Series A funding round for cancer screening", 200),
           _story("Nvidia invests $1 billion in Nokia to push telecom gear", 300),
           _story("Nvidia commits $1 billion to Anthropic compute partnership", 400),
           _story("OpenAI acquires camera maker Glass Imaging for $300 million", 500),
           _story("Glass Imaging valued at $3 billion as OpenAI talks stall", 600)]
    for i in range(0, 6, 2):
        a, b = tin[i]["tieu_de"], tin[i + 1]["tieu_de"]
        ka, kb = sb._keyword(a), sb._keyword(b)
        assert len(ka & kb) / max(len(ka), len(kb)) < 0.6, "cap nay phai thu luat so tien, khong phai luat 60%"
    ra = sb.gather_duplicate(tin)
    assert len(ra) == 6, [t["tieu_de"] for t in ra]


def test_dedup_merges_same_deal_sharing_only_a_rare_name():
    """LOW-193: tin that 15-16/09 chi chung MOT ten hang le (Cornelis, Profound)."""
    import scan_business as sb
    tin = [_story("AI infrastructure company Cornelis raises $205M to chip away at Nvidia's dominance", 100),
           _story("Cornelis Expands into Scale-Up Networking with Active Compute Fabric, $205M in Funding, and Qualcomm Collaboration at AI Infra Summit - Business Wire", 200),
           _story("Profound Lands $180M In Series D Funding, Reaching $1.8B Valuation - Unite.AI", 300),
           _story("AEO startup Profound hits unicorn valuation, raises $180M Series D 7 months after last round - TechCrunch", 400)]
    ra = sb.gather_duplicate(tin)
    assert len(ra) == 2, [t["tieu_de"] for t in ra]


def test_dedup_single_word_rule_rejects_common_words_and_verbs():
    """Tu don phai la TEN: 'factory' co trong tin robot khong lien quan; 'considers'
    viet thuong o mot ben va lech tien te (tin that 13/09 va 16/09)."""
    import scan_business as sb
    tin = [_story("Factory Raises $200M at $5B Valuation to Scale Enterprise Software Platform - HPCwire", 100),
           _story("Exclusive | AI Coding Startup Factory More Than Triples Valuation to $5 Billion - WSJ", 200),
           _story("Factory robots long posed a safety threat to human workers. This company says it has solved that problem.", 300),
           _story("Anthropic IPO: Nvidia Considers $10 Billion Anchor Investment in Potential $2 Trillion AI Startup Valuation", 400),
           _story("Finland considers data centre permitting system after Google's €13bn AI investment", 500)]
    ra = sb.gather_duplicate(tin)
    assert len(ra) == 5, [t["tieu_de"] for t in ra]


def test_dedup_keeps_follow_up_story_apart_from_announcement():
    """LOW-197: so tien sau 'After' la boi canh cua tin moi (tin that 11/09)."""
    import scan_business as sb
    tin = [_story("Google deepens commitment to Finland with two-year €13 Billion investment in AI infrastructure", 100),
           _story("Google's EUR13 Billion Finland AI Investment: Nuclear PPA, Data Centers, Jobs - IndexBox", 200),
           _story("Finland's Opposition Calls for Data Center Controls After Google's €13 Billion AI Investment", 300)]
    ra = sb.gather_duplicate(tin)
    assert [t["so_bao"] for t in ra] == [2, 1], [(t["so_bao"], t["tieu_de"]) for t in ra]


def test_dedup_merges_same_story_without_amount():
    """LOW-213: tin that 17/09 khong co so tien o mot/ca hai ben."""
    import scan_business as sb
    tin = [_story("Anthropic inks deal for $32 billion mega data centre in Queensland - SMH.com.au", 100),
           _story("Anthropic inks Queensland data centre deal worth five times Olympics budget - ABC News", 200),
           _story("SK Hynix reportedly in talks with Intel to build memory chips in US", 300),
           _story("SK Hynix in talks with Intel to produce memory chips in US for the first time amid Washington pressure, sources say", 400)]
    ra = sb.gather_duplicate(tin)
    assert [t["so_bao"] for t in ra] == [2, 2], [(t["so_bao"], t["tieu_de"]) for t in ra]


def test_dedup_no_amount_rule_needs_same_lead_subject():
    """Hai may khac hang cung chip Intel Wildcat Lake (tin that 15/09) khong phai mot tin."""
    import scan_business as sb
    tin = [_story("HP OmniDesk Mini: Compact Desktop Launches with Intel Wildcat Lake and up to Core 5 320 - igor´sLAB", 100),
           _story("Acemagic launches Kron K5 mini PC powered by Intel Wildcat Lake chip - ARYnews.tv", 200)]
    assert len(sb.gather_duplicate(tin)) == 2


def test_dedup_trillion_amount_merges_only_same_valuation():
    """LOW-213: $1.5T chi chung `openai` van la mot vu; $1.2T la con so khac.
    Duoi $1T thi chi chung mot hang watchlist van khong du."""
    import scan_business as sb
    tin = [_story("OpenAI Considers New Financing at a $1.5 Trillion Valuation - GV Wire", 100),
           _story("OpenAI weighs funding round at over $1.5 trillion valuation - The Straits Times", 200),
           _story("OpenAI weighs fresh funding at $1.2 trillion valuation ahead of IPO - business-standard.com", 300),
           _story("Nvidia pledges $100 billion to OpenAI for data center buildout", 400),
           _story("OpenAI Stargate expansion adds $100 billion in Texas campuses", 500)]
    ra = sb.gather_duplicate(tin)
    assert [t["so_bao"] for t in ra] == [2, 1, 1, 1], [(t["so_bao"], t["tieu_de"]) for t in ra]


def test_dedup_rare_name_ignores_no_amount_title_already_in_group():
    """LOW-214: tin that 17/09. UA.NEWS khong co so tien nhung da cung nhom Euclyd
    (qua digitimes) nen khong duoc chan IO+ €200M; lech tien te €/$ van la mot vong."""
    import scan_business as sb
    tin = [_story("Samsung backs Dutch AI chip startup Euclyd in US$230M funding round - digitimes", 100),
           _story("Samsung co-leads funding round for Dutch AI startup Euclyd - UA.NEWS", 200),
           _story("Eindhoven-based AI startup EUCLYD raises more than €200M - IO+", 300)]
    ra = sb.gather_duplicate(tin)
    assert [t["so_bao"] for t in ra] == [3], [(t["so_bao"], t["tieu_de"]) for t in ra]


def test_dedup_group_keeps_seen_keys_of_every_variant():
    """LOW-213: bo nho da-thay phai co khoa cua MOI bien the. Chi luu dai dien thi
    hom sau dai dien doi (Euclyd, Glass Imaging 17/09) va tin cu bao lai."""
    import scan_business as sb
    tin = [_story("OpenAI acquires smartphone camera maker Glass Imaging for over $300 million", 100),
           _story("OpenAI acquires Israeli-founded camera startup Glass Imaging for over $300 million", 200)]
    ra = sb.gather_duplicate(tin)
    assert len(ra) == 1
    assert ra[0]["seen_keys"] == [sb.standard_ify(t["tieu_de"]) for t in tin]


def test_standard_ify_make_lock_dedup_on_fixed():
    import scan_business as sb
    a = sb.standard_ify("Nvidia's Q3 Revenue Jumps 34%!")
    b = sb.standard_ify("nvidia's  q3 revenue jumps 34%")
    assert a == b, f"{a!r} != {b!r}"
    assert a, "chuoi rong -> moi tin cung mot khoa"
    assert sb.standard_ify("Nvidia buys X") != sb.standard_ify("Nvidia sells X")


def test_name_watchlist_by_border_from():
    """Docstring khai 'arm' khong duoc khop 'harm'."""
    import scan_business as sb
    assert sb.name_watchlist("Arm raises guidance") is not None
    assert sb.name_watchlist("New harm reduction policy for AI") is None


# ------------------------------------------------------------- cap_fallback
def test_cap_fallback_read_from_config_form_run():
    """Hang so `FALLBACK_REAL` chi co cap (v4-flash -> deepseek-chat), von khong
    con profile nao dung tu khi doi combo 05/09/2026 — nen `m["fallback"]` luon
    0 va `still_for()` khong bao gio danh thuc ai. Cap phai duoc dung TU config."""
    import tempfile
    import monitor_9router as t
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / ".hermes-blog"
        (home / "profiles" / "miles").mkdir(parents=True)
        (home / "profiles" / "miles" / "config.yaml").write_text(
            "model:\n  default: DS-v4Flash\n"
            "fallback_providers:\n  - model: ds/deepseek-v4-pro\n"
            "  - model: ds/deepseek-chat\n", encoding="utf-8")
        cu = t.HERMES_HOMES
        t.HERMES_HOMES = [home]
        try:
            cap = t.cap_fallback()
        finally:
            t.HERMES_HOMES = cu
    assert ("ds-v4flash", "deepseek-v4-pro") in cap, sorted(cap)
    assert ("deepseek-v4-pro", "deepseek-chat") in cap, sorted(cap)
    assert ("deepseek-v4-flash", "deepseek-chat") in cap, "phai giu ca hang so cu"


def test_cap_fallback_skip_string_duplicate_name():
    """Combo lat giua ba route CUNG mot model khong phai fallback — usage ghi
    cung mot `model` nen dem vao la bao dong gia moi ngay."""
    import tempfile
    import monitor_9router as t
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / ".hermes-dcgr"
        home.mkdir(parents=True)
        (home / "config.yaml").write_text(
            "model:\n  default: ds/deepseek-v4-flash\n"
            "fallback_providers:\n  - model: ds/deepseek-v4-flash\n", encoding="utf-8")
        cu = t.HERMES_HOMES
        t.HERMES_HOMES = [home]
        try:
            cap = t.cap_fallback()
        finally:
            t.HERMES_HOMES = cu
    assert cap == set(t.FALLBACK_REAL), f"them cap trung ten: {sorted(cap)}"


# --------------------------------------------------- allowlist va ma bai
def test_is_boss_no_has_file_then_wait_over():
    """Chua co state/ong_chu.json = giu hanh vi cu (group rieng). Neu doi thanh
    "chan het" thi bat cai nay len la khoa chet may dang chay."""
    import tempfile
    import approve_base as cs
    with tempfile.TemporaryDirectory() as tmp:
        cu = cs.BOSS_IDS
        cs.BOSS_IDS = Path(tmp) / "khong-co.json"
        try:
            assert cs.is_boss({"from": {"id": 999}}) is True
        finally:
            cs.BOSS_IDS = cu


def test_is_boss_has_file_then_block_person_is():
    import json as _j
    import tempfile
    import approve_base as cs
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "ong_chu.json"
        p.write_text(_j.dumps([8112291996]), encoding="utf-8")
        cu = cs.BOSS_IDS
        cs.BOSS_IDS = p
        try:
            assert cs.is_boss({"from": {"id": 8112291996}}) is True
            assert cs.is_boss({"from": {"id": 12345}}) is False
            assert cs.is_boss({}) is False          # nut khong co `from`
            assert cs.is_boss(None) is False
        finally:
            cs.BOSS_IDS = cu


def test_code_article_from_button_right_match_color():
    """`draft_id` trong callback_data den tu client va di THANG vao duong dan
    tep. `_draft_id` sinh no bang slugify nen moi id that deu khop mau nay."""
    import approve_post as db
    import approve_pick as dct
    hop_le = db._DRAFT_ID_HOP_LE
    # id that do chinh he thong sinh ra phai qua duoc
    tin = {"title": "Nvidia đàm phán rót 2,5 tỷ USD vào Thinking Machines", "index": 3}
    that = dct._draft_id(tin, "donniechublog", "dre")
    assert hop_le.match(that), that
    for xau in ["../../state/blog/lam_lai_cho", "a/b", "..", "", "A-Hoa",
                "x" * 60, "tin_gach_duoi", "-mo-dau-bang-gach"]:
        assert not hop_le.match(xau), f"nhan ma bai xau: {xau!r}"


# ------------------------------------------------------------- host noi bo
NOI_BO = ["127.0.0.1", "127.1", "127.0.1", "2130706433", "0x7f.0.0.1",
          "::1", "[::1]", "localhost", "10.0.0.5", "192.168.1.61",
          "169.254.169.254", "172.16.0.1", "172.31.255.1", "0.0.0.0",
          "may.local", "x.internal", "abc.netbird.mated"]
CONG_KHAI = ["openai.com", "172.32.0.1", "8.8.8.8", "1.1.1.1",
             "vnexpress.net", "news.ycombinator.com", "arxiv.org"]


def test_host_say_drop_catch_all_form_write_shorten():
    """Cong cu chi so khop CHUOI nen "127.0.0.1" bi chan con "127.1",
    "2130706433" va "[::1]" thi khong — dung ba cach vong qua ma libc (curl,
    chromium, httpx) van hieu."""
    import scan_common as qc
    sot = [h for h in NOI_BO if not qc.host_say_drop(h)]
    assert not sot, f"khong chan: {sot}"


def test_host_gate_declare_no_got_block_wrongly():
    """Chan oan con te hon bo lot: day chuyen se im lang khong tai duoc anh."""
    import scan_common as qc
    oan = [h for h in CONG_KHAI if qc.host_say_drop(h)]
    assert not oan, f"chan oan: {oan}"


def test_check_url_block_scheme_no_right_http():
    """capture_chart tai bang urllib, ma urllib nhan ca `file://`."""
    import scan_common as qc
    for u in ["file:///etc/passwd", "ftp://x.com/a", "data:text/html,x", "x"]:
        assert not qc.url_hide_whole(u), u
    assert qc.url_hide_whole("https://openai.com/index/abc")


def test_new_path_download_all_over_gate():
    """Doc bang AST: cac ham tai da duoc noi vao cong. Them mot duong tai moi
    ma quen goi cong la mo lai cua da dong."""
    import ast
    # `_download_bytes` sang prepare/download_filter.py khi tach goi 09/09/2026 (audit A1) —
    # cong host van phai duoc goi y nhu cu, chi doi cho tim.
    for tep, ham in [("prepare/download_filter.py", "_download_bytes"), ("article_images.py", "_download"),
                     ("capture_chart.py", "download_image"), ("article_extract.py", "fetch")]:
        cay = ast.parse((ROOT / tep).read_text(encoding="utf-8"))
        f = next((n for n in ast.walk(cay)
                  if isinstance(n, ast.FunctionDef) and n.name == ham), None)
        assert f, f"{tep}: khong thay ham {ham}"
        goi = {ast.unparse(n.func) for n in ast.walk(f) if isinstance(n, ast.Call)}
        assert any("check_url" in g or "url_hide_whole" in g or "_kiem_host" in g
                   for g in goi), f"{tep}:{ham} khong goi cong host"


# --------------------------------------------------------- use_argv (chat)
def test_argv_chat_no_report_hours_has_z():
    """Dung doan da gay su co 04/09: `-z` duoc hermes_cli xu ly TRUOC va thoat
    ngay, nen `--continue` bi bo qua IM LANG va MOI tin mo mot phien moi — vai
    nao cung "khong nho gi". Truoc day muon kiem dong lenh nay phai chay ca mot
    tien trinh hermes that."""
    import chat_router as cr
    a = cr.use_argv("miles", "tele-writer", "xin chao", "safe")
    assert "-z" not in a, a
    assert a[a.index("chat") + 1:a.index("chat") + 3] == ["-c", "tele-writer"]
    for co in ("--create-if-missing", "--no-restore-cwd", "-Q", "-q"):
        assert co in a, f"thieu {co}: {a}"
    assert a[a.index("--toolsets") + 1] == "safe"
    assert a[:2] == [a[0], "-m"] and a[2] == "hermes_cli.main"


def test_argv_no_profile_then_no_has_has_p():
    import chat_router as cr
    a = cr.use_argv(None, "tele-general", "x")
    assert "-p" not in a, a
    assert "--toolsets" not in a


def test_argv_match_copy_itemize_declare_of_check_hermes():
    """`check_hermes.HAS_CHAT` la danh sach co ma script kiem sau moi
    `hermes update`. Hai ban ke khai nay phai khop, khong thi check_hermes bao
    xanh cho mot dong lenh khong con dung."""
    import chat_router as cr
    import check_hermes as kh
    a = set(cr.use_argv("miles", "tele-writer", "x"))
    thieu = [c for c in kh.HAS_CHAT if c not in a]
    assert not thieu, f"check_hermes doi co {thieu} ma use_argv khong sinh ra"


# ------------------------------------------------------------ aggregate (9router)
# Tach khoi `read_date` 07/09/2026. Phep dem o day quyet dinh nhung thu khong lo
# ra khi sai: nhan khoa API (chi duoc 4 ky tu cuoi — bao cao nay duoc ghi ra dia
# VA phuc vu qua journal_web), cap lat model nao tinh la fallback, model nao bi
# goi la "tra rong".
def _line(giay, model="ds/deepseek-v4-pro", cid="c1", ak="sk-abcd1234efgh",
          status=None, ptok=2000, ctok=500, cost=0.01, cache=0):
    """Mot dong usageHistory, dung thu tu SELECT cua read_date."""
    import json as _j
    from datetime import datetime, timedelta, timezone
    ts = (datetime(2026, 9, 5, 17, 0, tzinfo=timezone.utc)
          + timedelta(seconds=giay)).isoformat().replace("+00:00", "Z")
    return (ts, model.split("/")[0], model, cid, ak, status, ptok, ctok, cost,
            _j.dumps({"cached_tokens": cache}))


def test_aggregate_no_report_hours_write_api_key_raw():
    """Khoa da xoay khong con trong bang `apiKeys` — ban truoc 06/09/2026 lay
    CHINH CHUOI KHOA lam nhan, roi nhan do di vao json/md va ra trang HTTP."""
    import monitor_9router as tr
    d, _ = tr.aggregate([_line(0, ak="sk-SIEU-BI-MAT-9999")], cap_fb=set())
    nhan = list(d["theo_khoa"])
    assert nhan == ["khoa la …9999"], nhan
    assert "SIEU-BI-MAT" not in repr(d), "khoa tho lot vao bao cao"


def test_aggregate_take_name_lock_when_remaining_within_board():
    import monitor_9router as tr
    d, _ = tr.aggregate([_line(0, ak="sk-x1")], {"sk-x1": "blog"}, cap_fb=set())
    assert list(d["theo_khoa"]) == ["blog"]


def test_aggregate_count_flip_model_within_threshold_and_skip_outside_threshold():
    """Lat model = hai lan goi LIEN TIEP khac model, cach nhau <= SECONDS_FLIP."""
    import monitor_9router as tr
    gan = [_line(0, "a"), _line(tr.SECONDS_FLIP - 1, "b")]
    xa = [_line(0, "a"), _line(tr.SECONDS_FLIP + 1, "b")]
    lap = [_line(0, "a"), _line(10, "a")]
    assert tr.aggregate(gan, cap_fb=set())[0]["lat_model"] == {"a → b": 1}
    assert tr.aggregate(xa, cap_fb=set())[0]["lat_model"] == {}
    assert tr.aggregate(lap, cap_fb=set())[0]["lat_model"] == {}


def test_aggregate_only_count_fallback_use_cap_ok_declare():
    """`fallback` la con so Ong Chu doc de biet model chinh co dang chet khong.
    Dem moi lan lat vao day la bao dong gia moi ngay."""
    import monitor_9router as tr
    rows = [_line(0, "chinh"), _line(5, "phu"), _line(200, "chinh"), _line(205, "la")]
    d, _ = tr.aggregate(rows, cap_fb={("chinh", "phu")})
    assert d["fallback"] == 1, d["lat_model"]
    assert tr.aggregate(rows, cap_fb=set())[0]["fallback"] == 0


def test_aggregate_catch_return_error_empty_and_no_catch_attempt_report_error():
    """Prompt to ma out ~0 nhung status ok = model nuot tien khong tra gi. Lan
    BAO LOI thi da co muc `loi` roi, dem hai lan la doc ra hai su co."""
    import monitor_9router as tr
    rows = [_line(0, "a", ptok=tr.EMPTY_PROMPT_MIN, ctok=tr.EMPTY_OUT_MAX),
            _line(300, "b", ptok=tr.EMPTY_PROMPT_MIN, ctok=tr.EMPTY_OUT_MAX + 1),
            _line(600, "c", ptok=tr.EMPTY_PROMPT_MIN - 1, ctok=0),
            _line(900, "d", ptok=99999, ctok=0, status="error 429")]
    d, _ = tr.aggregate(rows, cap_fb=set())
    assert d["rong"] == {"a": 1}, d["rong"]
    assert d["loi"] == {"d: error 429": 1}, d["loi"]
    assert d["tong"]["loi"] == 1


def test_aggregate_cache_pct_and_total_money():
    import monitor_9router as tr
    rows = [_line(0, ptok=1000, cache=250, cost=0.5),
            _line(300, ptok=3000, cache=750, cost=0.25)]
    d, tho = tr.aggregate(rows, cap_fb=set())
    assert d["tong"]["cache_pct"] == 25.0, d["tong"]
    assert d["tong"]["usd"] == 0.75
    assert tho["tong"]["usd"] == 0.75, "tho phai la ban CHUA lam tron"


def test_aggregate_top_prompt_take_5_attempt_most_expensive():
    import monitor_9router as tr
    rows = [_line(i * 300, ptok=(i + 1) * 1000) for i in range(8)]
    d, _ = tr.aggregate(rows, cap_fb=set())
    assert [x["prompt"] for x in d["top_prompt"]] == [8000, 7000, 6000, 5000, 4000]


def test_aggregate_date_empty_no_no():
    """Ngay khong co luot goi nao (9router vua restart) van phai ra bao cao."""
    import monitor_9router as tr
    d, tho = tr.aggregate([], cap_fb=set())
    assert d["tong"]["req"] == 0 and d["tong"]["cache_pct"] == 0.0
    assert d["theo_model"] == {} and d["top_prompt"] == []
    assert tho["tong"]["prompt"] == 0


def test_aggregate_no_touch_into_disk():
    """Ham THUAN — no khong duoc mo CSDL hay doc config. Neu mot ban sau lai
    goi `cap_fallback()` vo dieu kien thi test nay do (cap_fb da truyen vao)."""
    import monitor_9router as tr
    goi = []
    that = tr.cap_fallback
    tr.cap_fallback = lambda: goi.append(1) or set()
    try:
        tr.aggregate([_line(0)], cap_fb=set())
    finally:
        tr.cap_fallback = that
    assert goi == [], "aggregate van tu doc config du da duoc truyen cap_fb"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
