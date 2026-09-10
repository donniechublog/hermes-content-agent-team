#!/usr/bin/env python3
"""duyet_chon_tin.py — Ong Chu REPLY SO trong topic quet -> doc manifest ->
create_pair: meta.json + nguon_bai + task vai anh + sidecar vai viet + bang den.
Khoa theo duong dan manifest (hai lenh chon cung topic xep hang, khong nuot
da_giao cua nhau). Tach tu approve_service.py 06/09/2026 (di chuyen thuan).
"""
import json
import re
import subprocess
import sys
import threading
from pathlib import Path



sys.path.insert(0, str(Path(__file__).resolve().parent))
import ghi_log                                              # noqa: E402
import schema                                                # noqa: E402

from duyet_co_so import (  # noqa: E402
    BRAND, DRAFTS, ROOT, STATE_DIR, _ghi_json, _gui_chu, _nap_json, _reply_that, call, log,
)
from duyet_giao_viec import (  # noqa: E402
    BANG_DEN_NHAC, MAC_DINH_ANH, MAC_DINH_VIET, TEN_SANG_CAP, TEN_VAI_ANH, VAI_CAROUSEL, VAI_EDU, _bang_den_root, _bao_nhan_viec, chuan_nhan, kanban_create,
)
# Khuon body task (van ban dai) tach sang task_bodies.py — xem ghi chu o do.
import task_bodies                                            # noqa: E402
from task_bodies import ILLU_BODY, CAROUSEL_BODY, EDU_BODY, WRITER_BODY  # noqa: E402


def slugify(title, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (s[:40].strip("-") or fallback)

# Topic nao chon tin tu manifest nao. Finn, Nova va Vera deu la vai DI TIM TIN,
# nen ca ba phai chon duoc bang cach tra loi so — truoc day chi Finn lam duoc,
# bao cao cua Nova va Vera la van xuoi khong so nen Ong Chu khong biet rep gi.
MANIFEST_THEO_TOPIC = {
    "scout": "finn_candidates_*.json",
    "nova": "nova_candidates_*.json",
    "market": "vera_candidates_*.json",
}

def latest_manifest(vai="scout"):
    """Manifest MOI NHAT theo mtime, khong phai theo ten.

    Truoc day sap theo ten tep. Nhung ten khong phan anh thu tu ghi: dem 23/08
    ban `_t2327` ghi luc 23:27 sap TRUOC ban `2026-08-24` ghi luc 23:25 (cron
    dat ten theo ngay VN, quet lai dat hau to gio). Ong Chu tra loi so theo bao
    cao moi -> mo nham manifest cu -> tao bai SAI TIN. Thu tu ghi la thu duy
    nhat dung voi cau hoi "bao cao gan nhat Ong Chu vua doc la cai nao".
    """
    files = list(STATE_DIR.glob(MANIFEST_THEO_TOPIC.get(vai, "finn_candidates_*.json")))
    return max(files, key=lambda f: f.stat().st_mtime) if files else None

def _la_reply_bao_cao(vai: str, msg: dict) -> bool:
    """Tin nay co phai REPLY dung vao bao cao danh so MOI NHAT cua `vai` khong
    (Ong Chu 06/09/2026: chi tin REPLY moi tinh la lenh, go troi trong topic la
    hoi thoai — du co dung so). Cung nguyen tac voi _nhan_ly_do_lam_lai o tren,
    va giai luon mot ke ho khac: truoc day tra loi mot bao cao CU van bi hieu
    la chon tu manifest MOI NHAT (_xu_ly_chon luon doc latest_manifest), sai bai
    ma khong ai biet. Gio reply phai khop dung mid bao cao gan nhat moi qua.

    quet_nop.py ghi mid nay qua `publish.py --luu-mid` ngay khi gui bao cao.
    Chua co tep (bao cao gui truoc khi co co che nay, hoac ghi loi) thi lui ve
    kiem "co phai reply toi mot tin CUA BOT" — long hon nhung van chan duoc
    hoi thoai thuong. Phai loc qua _reply_that truoc: trong topic, Telegram tu
    gan reply_to_message = tin goc topic (do bot tao) cho MOI tin, nen thieu
    buoc loc do thi ca hai nhanh deu luon dung — dung bug 06/09/2026."""
    rt = _reply_that(msg)
    if not rt:
        return False
    mid = _nap_json(STATE_DIR / f"bao_cao_mid.{vai}.json", {}).get("message_id")
    if mid:
        return rt.get("message_id") == mid
    return bool(rt.get("from", {}).get("is_bot"))

def doc_lenh_chon(text: str):
    """Phan tich lenh chon tin. Tra ve [(so, vai_anh, thuong_hieu)] hoac None.

    Quy tac: ten vai ap cho MOI SO dung truoc no, tinh tu ten vai gan nhat.
    So nao khong co ten vai nao phia sau thi ve mac dinh (Ethan).

        1                    -> Ethan
        1, 2, 3              -> ca ba Ethan
        1, 2, 3 - Ethan      -> ca ba Ethan
        1 - Ethan, 2 - Ethan  -> 1 Ethan, 2 Ethan
        1, 2 - Ethan, 3      -> 1 va 2 Ethan, 3 Ethan

    Ten nguoi VIET cung nhan, va cho ra dung cap do: "1 - Miles" giong het
    "1 - Ethan", "1 - Miles" giong het "1 - Ethan".

    Tra None neu co phan khong hieu duoc, de tin nhan roi ve luong hoi thoai
    thay vi bao loi — Ong Chu con dung chinh topic do de tro chuyen.
    """
    if not text or not text.strip():
        return None

    # Tach thanh cac manh: moi manh la mot SO hoac mot TEN VAI
    manh = []
    for c in re.split(r"[,\n;]+", text.strip()):
        c = c.strip()
        if not c:
            continue
        for phan in c.split():
            phan = phan.strip("-\u2013\u2012:")
            if not phan:
                continue
            if phan.isdigit():
                manh.append(("so", int(phan)))
            elif re.fullmatch(r"[A-Za-zÀ-ỹ]+", phan):
                if phan.lower() not in TEN_SANG_CAP:
                    return None          # ten la -> khong phai lenh chon
                manh.append(("vai", phan.lower()))
            else:
                return None
    if not any(k == "so" for k, _ in manh):
        return None

    ra, cho, thay = [], [], set()
    def _xa(ten):
        for n in cho:
            if n in thay:
                continue
            thay.add(n)
            ra.append((n, TEN_SANG_CAP[ten], BRAND))
        cho.clear()

    for kind, v in manh:
        if kind == "so":
            cho.append(v)
        else:
            _xa(v)                        # ten vai ap cho moi so dang cho
    _xa(MAC_DINH_ANH)                     # so con lai ve mac dinh
    return ra or None

def write_meta(draft_id, item, out_png, brand="donniechublog"):
    """Ghi san metadata cho draft — writer khoi phai go lai bang tay.

    Nhung gia tri nay Finn da quyet tu luc quet; bat LLM go lai chi tao co hoi
    go sai. draft_write.py se doc file nay khi ghep draft cuoi cung.

    `brand` di theo duong nay chu khong qua tham so dong lenh: vai viet goi
    draft_write.py khong kem co nao, nen sidecar la cho DUY NHAT mang duoc
    thuong hieu tu luc Ong Chu chon tin toi luc bam Duyet. Thieu no thi bai
    dcgr.tech day nham sang org social cua donniechublog.
    """
    meta = {
        "source_url": item["link"],
        "category": chuan_nhan(item.get("category")),
        "via": item.get("via", ""),
        "image": out_png,
        "title": item["title"],
        "score": item.get("score"),
        "score_reason": item.get("score_reason", ""),
        "brand": brand,
    }
    # TRON, khong ghi de: bang_den ghi `root_task` vao cung tep tu mot tien
    # trinh khac, va write_meta con chay lan hai sau khi giai xong link Google
    # News. Ghi de ca dict thi ai ghi sau xoa cua ai ghi truoc — hom nay chua
    # mat chi vi thu tu goi tinh co dung (F2).
    p_meta = DRAFTS / (draft_id + ".meta.json")
    _ghi_json(p_meta, schema.hop_nhat_meta(_nap_json(p_meta, {}), meta))

def _draft_id(item, brand, vai_anh):
    """Khoa draft DUY NHAT theo (tin, brand, role lam anh).

    Mot tin hot co the giao cho NHIEU role lam anh (dang nhieu noi, nhieu cach
    dien dat) -> moi lan giao phai co draft_id rieng, neu khong hai san pham
    song song dung chung file png/meta/sidecar va nut Duyet -> de len nhau.

    GIOI HAN DO DAI: draft_id di vao callback_data cua nut Duyet/Lam lai/Bo
    ("imgredo:" + draft_id). Telegram chan callback_data > 64 byte va lang le
    tu choi ca ban phim -> anh dang len KHONG co nut. Giu draft_id <= 55 ky tu
    (ASCII) de "imgredo:" + draft_id <= 63 byte. Dat `vai` truoc trong khoa de
    role luon con nguyen; phan tieu de bi cat bot khi thieu cho."""
    khoa = slugify(f"{vai_anh}-{brand}", "x")[:20]           # vai truoc -> luon con
    base = slugify(item["title"], "item-" + str(item["index"]))[: 55 - 1 - len(khoa)]
    base = base.strip("-") or ("item-" + str(item["index"]))
    return f"{base}-{khoa}"

def _research_nguon(item, draft_id, out_png, brand):
    """Tim nguon cho bai (nguon_bai.py) va doi link chuyen huong Google News
    thanh link that; ghi lai meta neu link doi. Mot lan o day cho ca vai anh
    lan vai viet."""
    # BUOC RESEARCH — thuoc khau cua Finn, chay ngay khi Ong Chu chon tin.
    # Tim nguon la viec research, khong phai viec cua nguoi dung anh hay nguoi
    # viet chu. Lam mot lan o day thay vi de hai ben tu tim: khoi
    # tra cuu hai lan, va quan trong hon la ca hai cung doc MOT bo nguon nen bai
    # viet giai thich dung nhung gi doc gia nhin thay tren tam anh.
    nguon_path = STATE_DIR / f"nguon_{draft_id}.json"
    # C-r2-6: truoc day khong nhin returncode va `except: pass` khi doc ket qua —
    # nguon_bai chet (thieu module, traceback) thi khong mot dong log, khong tep
    # nguon, vai nhan link Google News chua giai ma; dung trieu chung "Dre/Miles
    # doc ra rong" 04/09 ma khong ai thay nguyen nhan. `sys.executable` thay
    # duong venv go cung theo quy uoc tu_lieu.boc().
    loi = None
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "nguon_bai.py"),
             "--tieu-de", item["title"], "--link", item["link"],
             "--out", str(nguon_path)],
            capture_output=True, text=True, timeout=180, cwd=str(ROOT))
        if r.returncode != 0:
            loi = f"nguon_bai exit {r.returncode}: {(r.stderr or '').strip()[-300:]}"
    except Exception as e:                                   # noqa: BLE001
        loi = f"{type(e).__name__}: {e!r}"
    if loi:
        print(f"[research] {draft_id}: khong tim duoc nguon — {loi}")
        return loi
    # Link cua Vera la duong chuyen huong Google News; nguon_bai da giai ma ra
    # bai that (link_gnews/link_goc). Dung link THAT cho moi vai sau va cho
    # meta — truoc day Dre/Miles nhan link chuyen huong, doc ra rong, phai tu
    # web_search lai (do 04/09/2026).
    try:
        _ng = json.loads(nguon_path.read_text(encoding="utf-8"))
        _that = _ng.get("link_goc") or ""
        if _ng.get("link_gnews") and _that and _that != item["link"]:
            item["link_gnews"], item["link"] = item["link"], _that
            write_meta(draft_id, item, out_png, brand)
    except Exception as e:                                   # noqa: BLE001
        loi = f"doc {nguon_path.name}: {type(e).__name__}: {e!r}"
        print(f"[research] {draft_id}: {loi}")
        return loi
    return None


def _khoi_chay_engine(draft_id):
    """Chay NEN anh_chuan_bi.py ngay khi Ong Chu chon tin — toi luc vai nhan
    viec thi brief da san. Khong chan reply cho Ong Chu."""
    # Phan CO HOC cua vai anh (nguon, tai/do/cat anh, tu lieu) chay NEN ngay bay
    # gio bang engine dung chung anh_chuan_bi.py — toi luc Dre/Ethan/Kite nhan
    # viec thi brief da san, task chi con viet chu; Miles doc lai cung tu lieu.
    # Khong chan reply cho Ong Chu.
    try:
        _wd = STATE_DIR / "chuan_bi" / draft_id
        _wd.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(
            [str(ROOT / "venv/bin/python"), str(ROOT / "anh_chuan_bi.py"), draft_id, "--im"],
            cwd=str(ROOT), stdout=open(_wd / "chuan_bi.log", "ab"),
            stderr=subprocess.STDOUT, start_new_session=True)
    except Exception as e:                                   # noqa: BLE001
        print(f"[chuan_bi] khong khoi chay nen: {type(e).__name__}: {e}")


def _cat_sidecar(draft_id, vai_anh, brand, item, illu_body, la_carousel, la_edu, root_id, illu_id):
    """Hai sidecar: <id>.img.json de LAM LAI duoc, <id>.writer.json de task viet
    CHI sinh khi Ong Chu bam Duyet anh. Tra ve vai_viet."""
    # Cat lai body task anh de LAM LAI duoc: Ong Chu bam "Lam lai" tren anh chua
    # dat thi tao lai dung task nay (them ghi chu doi anh khac). Thieu file nay
    # thi nut Lam lai bao khong co thong tin.
    _ghi_json(DRAFTS / (draft_id + ".img.json"),
              {"vai_anh": vai_anh, "carousel": la_carousel or la_edu,
               "title": item["title"], "body": illu_body, "remakes": 0,
               "link": item.get("link", ""), "summary": item.get("summary", ""),
               "source_note": item.get("source_note", ""), "via": item.get("via", "")})

    # KHONG tao task viet ngay nua. Tinh san writer_body + vai_viet roi cat vao
    # sidecar `<draft_id>.writer.json`; task viet CHI sinh khi Ong Chu bam
    # "Duyet anh" (imgok) tren tam anh ma designer (Ethan)/Dre/Dre vua day len
    # topic. Anh chua dat thi khong co writer nao ca — dung y Ong Chu: khong
    # nhat thiet phai co writer sau khi tao hinh, o thi moi viet caption.
    # Nhan diem phai theo VAI QUET that: dong "Diem Finn cham" hien tren ca task
    # cua dcgr, noi Vera quet — va Vera/Nova khong cham diem nen `score` ra None.
    diem = item.get("score")
    writer_body = WRITER_BODY.format(
        title=item["title"], link=item["link"],
        source_note=item.get("source_note", ""), via=item.get("via", ""),
        # Chi Finn cham diem; Nova/Vera khong co bo cham nao nen `score` ra None.
        vai_quet="Finn" if isinstance(diem, (int, float)) else "vai quet",
        score=f"{diem}/100" if isinstance(diem, (int, float)) else "khong cham diem",
        score_reason=item.get("score_reason", "") or "(khong co)",
        draft_id=draft_id, brand=brand, goc=str(ROOT))
    vai_viet = MAC_DINH_VIET
    _ghi_json(DRAFTS / (draft_id + ".writer.json"),
              {"vai_viet": vai_viet, "title": item["title"],
               "body": writer_body, "created": False,
               "root_task": root_id, "dre_task": illu_id})
    return vai_viet


def create_pair(item, vai_anh="designer", brand="donniechublog"):
    draft_id = _draft_id(item, brand, vai_anh)
    out_png = str(DRAFTS / (draft_id + ".png"))
    write_meta(draft_id, item, out_png, brand)

    # Loi research ghi vao item de nguoi goi (_xu_ly_chon) dua len dong tra loi
    # Ong Chu — khong chi nam trong log (C-r2-6).
    loi_nguon = _research_nguon(item, draft_id, out_png, brand)
    if loi_nguon:
        item["nguon_loi"] = loi_nguon

    # carousel (Dre) dung carousel nhieu slide, cac vai anh khac dung the bia.
    # Cung bo bien nhu nhau nen chon khuon roi format chung; .format bo qua
    # key thua.
    la_carousel = vai_anh in VAI_CAROUSEL
    la_edu = vai_anh in VAI_EDU
    khuon = EDU_BODY if la_edu else (CAROUSEL_BODY if la_carousel else ILLU_BODY)
    # Chi truyen khoa cac template THAT SU dung. Truoc 06/09/2026 cho nay truyen
    # 9 khoa thua (image_url, out_png, out_png_goc, category, vai, nguon,
    # hermes_py, co_brand) — `str.format` bo qua khoa thua IM LANG, nen chung cu
    # nam do sau khi template da bo dung cai chung phuc vu, va nguoi doc tuong
    # body van co nhung thu do.
    illu_body = khuon.format(
        source_note=item.get("source_note", ""), link=item["link"],
        title=item["title"], summary=item.get("summary_vi", ""),
        draft_id=draft_id, brand=brand, goc=str(ROOT),
        ket_thuc=task_bodies.KET_THUC_VAI_ANH)
    tieu_de_task = ("Carousel deck: " if la_edu
                    else ("Carousel: " if la_carousel else "Anh: ")) + item["title"]
    # Bang den: the goc cua bai truoc, task anh la con cua no. Khong co goc
    # (loi) thi van tao task nhu cu — bang den la lop them, khong phai dieu kien.
    root_id = _bang_den_root(draft_id, item["title"],
                             goal=f"{item['title']} — {brand}: {vai_anh} dung anh, "
                                  f"{MAC_DINH_VIET} viet caption sau khi Ong Chu duyet anh.")
    if root_id:
        illu_body += BANG_DEN_NHAC.format(root=root_id)
    illu_id, err = kanban_create(tieu_de_task, vai_anh, illu_body, parent=root_id)
    if err:
        return None, "Loi tao task anh: " + err

    # SIDECAR TRUOC, ENGINE SAU. Engine doc `<draft_id>.img.json` ngay dau
    # (`_tom_tat_tu_img_json`) de lay tom tat, source_note VA — tu 10/09/2026 —
    # `vai_anh` de biet can bao nhieu anh that. Chay engine truoc la de no doc
    # mot tep chua ai ghi: truoc gio chi mat tom tat (im lang), nay con mat ca
    # nguong nen Ethan lai bi doi du anh cho carousel. Doi cho hai dong nay la
    # du — _cat_sidecar khong can gi tu engine.
    vai_viet = _cat_sidecar(draft_id, vai_anh, brand, item, illu_body, la_carousel, la_edu, root_id, illu_id)
    _khoi_chay_engine(draft_id)

    item["picked"] = True
    item["vai_anh"], item["brand"], item["vai_viet"] = vai_anh, brand, vai_viet
    item["task_anh"], item["task_viet"] = illu_id, None
    # Ghi lai TUNG lan giao (mot tin co the giao nhieu role) — dung de chan
    # trung y het (cung role + cung brand) o vong chon, xem handle_pick.
    item.setdefault("da_giao", []).append(
        {"vai_anh": vai_anh, "brand": brand, "draft_id": draft_id, "task_anh": illu_id})
    return illu_id, None

_KHOA_MANIFEST = {}                    # manifest path -> Lock

_KHOA_KHOA_MANIFEST = threading.Lock()

def _khoa_manifest(path):
    with _KHOA_KHOA_MANIFEST:
        return _KHOA_MANIFEST.setdefault(str(path), threading.Lock())

def _xu_ly_chon(token, group, thread_id, vai, lenh):
    """Tao cap task tu lenh chon so. Chay nen qua _chay_nen."""
    manifest_path = latest_manifest(vai)
    if not manifest_path:
        mau = MANIFEST_THEO_TOPIC.get(vai, "?")
        log("chon", f"khong co manifest {mau} trong {STATE_DIR}")
        call(token, "sendMessage", chat_id=group, message_thread_id=thread_id,
             text=f"Chưa có danh sách tin nào để chọn trong topic này.\n"
                  f"(tìm {mau} trong {STATE_DIR.name}/ — vai {vai} chưa gửi báo cáo "
                  f"nào cho container {ghi_log.brand()}, hoặc báo cáo ghi sai thư mục)")
        return
    log("chon", f"manifest={manifest_path.name}")
    # SAP THEO VAI, giu thu tu vai xuat hien lan dau: "1, 3 - Ethan, 2 - Dre"
    # -> [1 Ethan, 3 Ethan, 2 Dre]. Dispatcher chay FIFO theo created_at voi
    # kanban.max_in_progress=1, nen tao task theo thu tu nay = Ethan lam het
    # bai cua minh roi Dre moi bat dau (yeu cau Ong Chu 03/09/2026: khong giao
    # cho tat ca cung lam).
    thu_tu_vai = list(dict.fromkeys(v for _n, v, _b in lenh))
    lenh = sorted(lenh, key=lambda x: thu_tu_vai.index(x[1]))

    # KHOA THEO MANIFEST, om CA vong tao task. Vi sao 06/09/2026: moi lenh chon
    # chay mot thread rieng (_chay_nen), ma ca ba buoc "doc ca manifest ->
    # create_pair (toi 180s moi tin vi nguon_bai chay dong bo) -> ghi lai ca
    # manifest" deu khong khoa. Lenh thu hai doc ban CU roi ghi de, nuot mat
    # `da_giao`/`picked` cua lenh truoc — ma chinh `da_giao` la cong chan giao
    # trung, nen lan chon sau se tao task doi cho tin da giao.
    #
    # Khoa theo MANIFEST chu khong phai mot khoa chung: moi vai di tim tin
    # (Finn/Nova/Vera) mot tep rieng, nen hai topic khac nhau van chay song song
    # y nhu cu — chi hai lenh chon TRONG CUNG mot topic moi xep hang, va do dung
    # la nhung lenh dam vao nhau. Xep hang cung khong lam cham viec that:
    # dispatcher kanban chay tuan tu (max_in_progress=1) roi. Nhung doi co the
    # toi vai phut nen phai BAO mot dong, khong duoc im (cung luat voi chat).
    khoa = _khoa_manifest(manifest_path)
    if not khoa.acquire(blocking=False):
        log("chon", f"xep hang sau mot lenh chon dang chay tren {manifest_path.name}")
        call(token, "sendMessage", chat_id=group, message_thread_id=thread_id,
             text="⏳ Đang chạy lệnh chọn trước trong topic này (mỗi tin mất tới 3 "
                  "phút tìm nguồn) — xong sẽ tới lệnh này, không cần gõ lại.")
        khoa.acquire()
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        items = {it["index"]: it for it in data.get("items", [])}
        lines = []
        for n, vai_anh, brand in lenh:
            it = items.get(n)
            if not it:
                lines.append("#" + str(n) + ": không tìm thấy")
                continue
            # Cho phep giao MOT tin cho NHIEU role lam anh (tin hot dang nhieu noi,
            # nhieu cach dien dat). Chi chan lap Y HET: cung role + cung brand da
            # giao roi -> khoi tao trung task va de file len nhau.
            if any(g.get("vai_anh") == vai_anh and g.get("brand") == brand
                   for g in it.get("da_giao", [])):
                ten_da = TEN_VAI_ANH.get(vai_anh, vai_anh)
                lines.append(f"#{n}: đã giao {ten_da} ({brand}) trước đó — bỏ qua")
                continue
            tid, err = create_pair(it, vai_anh=vai_anh, brand=brand)
            if err:
                lines.append("#" + str(n) + ": lỗi — " + err)
                continue
            ten_hien = TEN_VAI_ANH.get(vai_anh, "Ethan")
            # Ong Chu 08/09/2026: bo cum "X viet caption sau khi duyet anh" — thua,
            # ai cung biet quy trinh nay, khong can nhac lai moi lan giao task.
            lines.append(f"#{n}: {ten_hien} dựng ảnh ({brand}) — task {tid}")
            if it.get("nguon_loi"):
                # C-r2-6: research hong thi Ong Chu phai thay ngay o day, khong
                # phai doi vai bao "doc ra rong" roi di lan log.
                lines.append(f"   ⚠️ không tìm được nguồn cho #{n}: {it['nguon_loi'][:160]}")
            # Ong Chu 08/09/2026: "cac vai can phan hoi ngay khi duoc giao task la da
            # nhan task" — truoc day chi hang CHUYEN (Dre->Miles, ->Kite) duoc bao
            # ngay qua _bao_nhan_viec, con task MOI tao o day thi im lang cho toi khi
            # dispatcher thuc su chay (co the toi 1 phut). Bao luon cho vai_anh o day.
            _bao_nhan_viec(token, group, vai_anh, None, it["title"], tid)
            # Ghi NGAY sau TUNG tin (create_pair da danh dau vao `it`), khong doi
            # het vong nhu truoc: tin sau no giua chung thi cac tin truoc do van
            # co `da_giao` tren dia, chon lai khong tao task doi.
            _ghi_json(manifest_path, data)
    finally:
        khoa.release()
    log("chon", "ket qua: " + " | ".join(lines))
    _gui_chu(token, group, "<b>Kết quả chọn:</b>\n" + "\n".join(lines),
             thread=thread_id)
