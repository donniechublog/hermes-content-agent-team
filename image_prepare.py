#!/usr/bin/env python3
"""image_prepare.py — ENGINE CHUAN BI dung chung cho moi vai lam anh/chu tu mot tin
(Dre carousel, Ethan hero, Kite edu, va tu lieu cho Miles). Tat dinh, chay MOT lan,
o NEN ngay luc Ong Chu chon tin (approve_service.create_pair goi `image_prepare.py
<draft_id> --im`).

Nguyen tac Ong Chu: CODE TOI DA, LLM TOI THIEU. Do 04/09/2026: moi task anh ton
19-60 tool call, 60k-260k token input, phan lon la viec CO HOC (curl tai anh,
ls/grep do file, ghi roi doc lai spec, mo tung anh, crop lap, web_search lai
tin vi link Google News doc ra rong). Toan bo phan do nam o day:

  1. NGUON: doc bo nguon Finn/Vera da research (`state/<brand>/nguon_<id>.json`),
     giai ma link Google News, lay tieu de tieng Anh, hoi Bing News RSS tim bao
     khac khi nguon mong (ghi nguoc vao nguon json de moi vai sau cung dung).
  2. ANH: mot phien chromium (chu bai, <img> lon, chup table/figure/canvas full
     be ngang) + article_images (tinh) + Wikimedia Commons khi < 5 anh. Thieu thi tim
     rong sang bao khac cung tin (_round_widen_search). Anh THAT cua chinh hang trong
     tin (image_brand.py: logo, chan dung founder/CEO, tru so, campus) chay
     cho MOI tin co hang trong watchlist — du anh hay khong (10/09/2026). Van
     thieu nua thi anh khai niem cua chu de (image_concept.py: co nuoc, rack).
     Tai ve, bo trung (dHash), bo anh be, logo, co anh AI sinh.
  3. DO va PHAN LOAI bang `image_rules` + luat bo sung (nen trang >=45% & canh
     >=8% -> chart): chart/anh chup, ti le, mat nguoi, day sang. Cat san
     1:1/4:5 qua crop_ratio (co dau vet), cap anh ngang ghep duoc (cung tone),
     bang anh thu nho `contact_sheet.png`.
  4. TU LIEU: material.gather (fallback chu tu browser cho trang JS) -> cau co so.
  5. Ghi `manifest.json` (manifest role-neutral). Moi vai co tep rieng in BRIEF theo
     cach nhin cua vai do: dre_prepare.py, ethan_prepare.py, kite_prepare.py,
     miles_prepare.py — deu doc chung manifest.json nay, khong lam lai.

Tu 09/09/2026 (audit A1) than engine nam trong goi `prepare/`, tach theo PHA;
tep nay chi con `prepare_article()` (noi 9 pha), `run()` (khoa + idempotent) va CLI —
nen cron, SOUL va cac vai KHONG phai doi lenh. Phu thuoc mot chieu:

    common  <- source, browser, download_filter <- vision <- fallback_rounds ;  manifest <- common

  prepare/common.py            hang so, header HTTP, doc/ghi JSON, ten mien
  prepare/source.py            nap nguon Finn/Vera, ung vien tinh/social, Commons
  prepare/browser.py           phien Chromium, boc anh trong trang, giai link Google News
  prepare/download_filter.py   tai song song + loc rac/trung/do hoa, cat san
  prepare/vision.py            vision tung anh, do hinh hoc, quyet dinh dung o dau
  prepare/fallback_rounds.py   ba vong bu khi kho mong (bao khac, xep hang, thuong hieu, khai niem)
  prepare/manifest.py          bang anh, cau tu lieu, brief

Idempotent + khoa: `state/<brand>/prepare/<draft_id>/` (manifest.json, running.pid).
`--lam-moi` de lam lai tu dau.

Dung:
    venv/bin/python image_prepare.py <draft_id> --im       # chay nen (approve_service)
    venv/bin/python image_prepare.py <draft_id> --lam-moi  # bo cache, lam lai
"""
import argparse
import contextlib
import faulthandler
import os
import sys
import time
from pathlib import Path

try:
    import fcntl                 # POSIX (server) — khoa tep that
except ImportError:              # Windows (chay tay/test): xem `_wait_for_slot`
    fcntl = None


sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
from browser_session import BrowserSession                       # noqa: E402
import schema                                                # noqa: E402
import state_paths                                           # noqa: E402
from prepare import decision_log                              # noqa: E402
import role                                                   # noqa: E402

from prepare.common import (  # noqa: E402
    DRAFTS, ROOT, UA, _brand_of, _read_json, _write_json, _hdr,
)
from prepare.manifest import (  # noqa: E402
    _article_material, contact_sheet, describe_ranking_image, ranking_brief_line, build_manifest,
)
from prepare.source import _summary_from_img_json, load_source, set_story_text      # noqa: E402
from prepare.vision import _seen_image, description_image                  # noqa: E402
from prepare.download_filter import _save_crop                          # noqa: E402
from prepare.fallback_rounds import (  # noqa: E402
    _image_item_ranking, _supplement_source, _capture_ranking, _gather_and_download_image,
    _take_from_browser, _extra_announcement_page, _round_capture_source, _round_concept, _round_entity,
    capability_block_headline,
    _round_brand, _round_widen_search,
)

# MAT TIEN cua goi `prepare`: nhung ten ma cac vai/test VAN goi qua
# `image_prepare.X` sau khi tach goi (audit A1). Khai bao __all__ chu khong de
# import "thua" lang le: pyflakes ton trong __all__, va danh sach nay chinh la
# hop dong cong khai — them/bot o day la co y, khong phai vo tinh.
#
# KHAC voi shim 79 ten da go khoi approve_service (A2): moi ten duoi day deu co
# nguoi goi that (do bang `grep -o "cb\.[a-z_]*"` trong repo), khong phai keo
# ca module sang cho co.
__all__ = [
    "DRAFTS", "ROOT", "UA", "_image_item_ranking", "_brand_of", "_wait_for_slot",
    "_read_json", "_write_json", "_gather_and_download_image", "_hdr", "_save_crop",
    "_description_missing_image", "_seen_image", "contact_sheet", "describe_ranking_image", "run",
    "prepare_article", "ranking_brief_line", "build_manifest", "description_image",
    "load_meta", "load_source", "workdir",
]

NAME_CT = {"dcgr": "dcgr", "donniechublog": "blog"}      # brand -> CT_BRAND


def prepare_article(draft_id: str, meta: dict, state: Path, wd: Path, khong_browser=False) -> dict:
    """Engine anh cho MOT bai: nguon -> browser -> (xep hang) -> tai anh -> nhin
    -> tim rong neu thieu -> anh khai niem neu van thieu/khong co bia -> tu lieu -> manifest. Tach 07/09/2026 tu mot ham 231
    dong; doi chieu bang vet voi moi ham anh em thay bang ban gia (13 kich ban)."""
    import carousel
    t_start = time.time()           # LOW-225: moc gom ban ghi anh bi bo cua CHINH lan chay nay
    title = meta.get("title", draft_id)
    # `tom`/`vai_anh` doc SOM, TRUOC ca browser (doi cho tu duoi len 16/09/2026,
    # LOW-182): `role.set_active_role` phai chay TRUOC bat cu anh nao duoc tai/
    # nhin, vi tu day moi ham "co tieu chi" sau trong ham nay (`_seen_image` ->
    # `prepare.vision.classify`, `_gather_and_download_image`, `_take_from_browser`...)
    # doc module luat qua `role.active_rules()` — bien tien trinh, khong phai
    # tham so — nen phai dat gia tri TRUOC khi chung chay, khong phai sau. `tom`
    # chi doc `.img.json` tren dia (`_summary_from_img_json`), khong dung gi tu
    # `load_source`/browser nen doi len day an toan.
    set_story_text("")            # LOW-222: xoa than bai cua draft truoc (neu co) truoc moi vong
    tom = _summary_from_img_json(draft_id)
    # NGUONG DI THEO VAI (su co 10/09/2026). Truoc day dong nay la
    # `carousel.FLAGSHIP_MIN if flagship else carousel.MIN_SLIDE` — engine
    # chay chung cho ca ba vai dung anh nen Ethan (card.py, MOT anh la du)
    # cung bi doi 5 anh, roi ca day "thieu anh" ban cho Ethan cau hoi cua
    # carousel. `tom["image_role"]` da co san tu sidecar .img.json ngay tren
    # (`_summary_from_img_json`), chi la truoc gio khong ai dung toi.
    vai_anh = role.canonical_slug(tom.get("image_role") or "")
    if vai_anh not in role.ROLE:
        # Chay tay, hoac sidecar mat/chua kip ghi. Khong im: nguong sai lam
        # lech ca `missing_images` o manifest lan cau bao gui Ong Chu.
        print(f"[chuan bi] khong biet vai cua {draft_id} "
              f"(vai_anh={tom.get('image_role')!r}) -> dung nguong cua "
              f"{role.DEFAULT_IMAGE}", file=sys.stderr)
        vai_anh = role.DEFAULT_IMAGE
    role.set_active_role(vai_anh)
    # MOT phien Chromium cho ca bai (audit B4): truoc day load_source (giai link
    # Google News), browser_pass va xep_hang moi cho tu launch mot tien trinh —
    # toi BON lan cho mot bai. Phien mo LUOI nen `--khong-browser` khong ton
    # tien trinh nao, va giu tien trinh RIENG cho moi bo tham so (xep_hang ep
    # srgb) de khong lang le doi cach xu ly mau anh chup.
    with BrowserSession() as phien:
        nguon, nguon_path, link = load_source(draft_id, meta, state, phien=phien)
        trang = nguon.get("trang", [])

        trang = _supplement_source(nguon, nguon_path, trang, link)
        # Trang cong bo CHINH CHU cua model (LOW-21): chay cho moi tin nhac model
        # cua hang trong watchlist, TRUOC browser de browser ghe lay chart.
        trang = _extra_announcement_page(nguon, nguon_path, trang, title, tom.get("summary", ""))
        bp = {"tieu_de_en": "", "chu": "", "cands": [], "trang_them": []}
        if not khong_browser:
            bp, trang = _take_from_browser(trang, wd, nguon, nguon_path, phien=phien)
        # LOW-222: than bai cua tin la bang chung tach ten rieng cho MOI vong sau
        # (Commons, Yandex, bao thuc the, thuong hieu, cau hoi vision).
        set_story_text("\n".join([bp.get("chu") or "", tom.get("summary") or ""]))
        xhs, tin_xep_hang = _capture_ranking(title, nguon, tom, link, meta, bp, wd,
                                           khong_browser, phien=phien)
        anh = _gather_and_download_image(title, link, nguon_path, nguon, trang, bp, wd, xhs)
        anh, dung_duoc, chua_nhin = _seen_image(anh, nguon, title, wd)
        flagship = bool(carousel._FLAGSHIP_RE.search(title + " " + tom.get("summary", "")))
        toi_thieu = role.min_images(vai_anh, flagship)
        # HAI CAU HOI KHAC NHAU, dung lan nhau la hong ca hai chieu:
        #   `toi_thieu`             — nguong CHAN: duoi no thi bai bi coi la
        #                             thieu anh, Ong Chu bi hoi, bai co the bi
        #                             day sang Kite.
        #   `role.has_enough_material()`  — CON PHAI DI TIM NUA KHONG.
        # Cau thu hai truoc LOW-12 do bang so cua carousel (5, hay 8 voi tin
        # flagship) cho CA BA vai. Ong Chu 10/09/2026: *"cach lam anh cua Ethan
        # dau phai la carousel? nhung gi thuoc ve carousel ma lien quan toi Ethan
        # la nhung thu ko dung"* va *"carousel la nhieu anh con Ethan lam single
        # image, nen 'so luong' ko the la thu ap vao duoc"*. Nay ban dang ky vai
        # tra loi: vai xep nhieu anh moi dem tam, vai mot anh chi hoi da co tam
        # nao dung lam anh chinh chua — tieu chi CHAT LUONG (LOW-182, 16/09/2026)
        # gio cung di theo vai, qua `role.active_rules()`, khong con chung nua.
        # Bo hau to site khoi tieu de dung de NHIN/tim hang (LOW-35): " · Hugging
        # Face" tung lam Hugging Face thanh "hang trong tin" cua mot tin DeepSeek.
        import article_sources
        tieu_de_nhin = article_sources.strip_site_suffix(nguon.get("tieu_de_en") or "") or title
        # THU TU (Ong Chu 13/09/2026): CHUP MAN HINH BAO CUNG TIN TRUOC, tim kiem
        # anh tren web sau. Mot tin hot co hang tram bao dua, moi bao mot anh hero
        # dung chu de san — chup ve roi dem nen la co slide, khong phai doan xem
        # mot tam anh la tren mang co dinh dang gi. Truoc do `_round_widen_search`
        # (Yandex + og:image) chay truoc, la duong dai va de lac de hon han.
        if not role.has_enough_material(vai_anh, dung_duoc, flagship):
            anh, dung_duoc, chua_nhin = _round_capture_source(anh, link, trang, wd,
                                                         khong_browser, phien=phien,
                                                         tieu_de=tieu_de_nhin)
        if not role.has_enough_material(vai_anh, dung_duoc, flagship) and not khong_browser:
            anh, dung_duoc, chua_nhin = _round_widen_search(anh, trang, tieu_de_nhin, toi_thieu,
                                                       dung_duoc, wd, phien=phien)
        # ANH CUA CHINH HANG trong tin (logo, chan dung founder/CEO, tru so,
        # campus): chay cho MOI tin nhac toi mot hang trong watchlist, KHONG doi
        # toi luc thieu anh. Ong Chu 10/09/2026, lan thu hai cua cung mot cau:
        # "Dre van ko chiu di tim cac hinh lien quan nhu logo, brand, founder,
        # tru so... cua chu de duoc nhac toi". Ban 09/09 treo vong nay sau dieu
        # kien thieu anh, nen tin nao bai goc du anh la khong bao gio hoi toi
        # Commons/Wikidata — ma vai bi cam tu tai them ("chi dung MA ANH"), nen bo
        # anh giao cho Dre trang tron du may moc da san. Tin khong nhac hang nao:
        # `vendors_in_story` tra rong va vong thoat ngay, khong mot request nao.
        # Chi mang, chay ca khi --khong-browser; tran +4 anh nam trong vong.
        # So truyen vao chi dieu khien MOT thu trong vong do: nhanh mo browser di
        # chup bang xep hang lam boi canh. Voi vai mot anh no la 0 — mot cai chart
        # khong bao gio la nen hero duoc, di chup la tra tien browser lay mot tam
        # Ethan khong dung duoc.
        # `category` da duoc Finn/Vera gan tu luc quet va nam san trong meta —
        # toi 12/09/2026 engine anh chua doc no o dau (story_type.py).
        category = meta.get("category", "")
        anh, dung_duoc, chua_nhin = _round_brand(anh, tieu_de_nhin, tom.get("summary", ""),
                                                      wd, role.search_target_for(vai_anh, flagship),
                                                      khong_browser, phien=phien,
                                                      category=category)
        # (Vong chup trang nguon da chay o TREN — xem ghi chu thu tu 13/09/2026.)
        # Van thieu, hoac co anh ma khong tam nao lam anh chinh cua VAI NAY duoc
        # -> anh khai niem chung chung cua chu de, sau anh cua chinh hang (chi
        # mang, khong browser; chay ca khi --khong-browser).
        # ANH THUC THE truoc, KHAI NIEM sau cung (LOW-35, 12/09/2026): anh dai dien cua
        # chinh thuc the trong tieu de (Wikipedia/Commons) chac hon tu khoa LLM — do tren
        # may chu: khai niem nhan bua "computer server room" cho tin toan, the can cuoc
        # Quoc xa cho tin xac minh tuoi. Khai niem chi con la nac CUOI CUNG.
        if not role.has_enough_material(vai_anh, dung_duoc, flagship):
            anh, dung_duoc, chua_nhin = _round_entity(anh, tieu_de_nhin, wd)
        if not role.has_enough_material(vai_anh, dung_duoc, flagship):
            anh, dung_duoc, chua_nhin = _round_concept(anh, tieu_de_nhin, tom.get("summary", ""), wd,
                                                        category=category)
        # Khoi tit chup tu trang nguon (bai khong anh hero) la NAC CUOI CUNG:
        # chi lam bia khi thuc the + khai niem deu rong (12/09/2026).
        if not role.has_enough_material(vai_anh, dung_duoc, flagship):
            anh, dung_duoc, chua_nhin = capability_block_headline(anh)
        tl = _article_material(title, link, nguon_path, wd, nguon, bp)
        m = build_manifest(draft_id, meta, title, link, nguon, nguon_path, tom, wd, anh, xhs,
                          tin_xep_hang, bp, tl, flagship, toi_thieu, vai_anh=vai_anh,
                          dropped=decision_log.collect(wd, since=t_start))
    contact_sheet(anh, wd / state_paths.CONTACT_SHEET_FILE)     # ngoai phien: khong dung browser
    return m


# ---- chay + khoa + idempotent (dung chung cho moi vai) -----------------------
def workdir(state: Path, draft_id: str) -> Path:
    return state_paths.workdir(state, draft_id)

def load_meta(draft_id: str) -> dict:
    meta = _read_json(DRAFTS / f"{draft_id}.meta.json")
    if not meta:
        sys.exit(f"Khong thay drafts/{draft_id}.meta.json — task nay khong do approve_service tao?")
    os.environ.setdefault("CT_BRAND", NAME_CT.get(_brand_of(meta), "blog"))
    return meta


# Tran so engine chay CUNG LUC tren ca may (chung hai brand): moi engine mo mot
# Chromium 1600x1200 DPR2 + goi vision tung anh. Ong Chu chon 7 tin la 7 engine
# khoi chay cung luc (audit 05/09/2026). Het cho thi doi, khong bo.
COUNT_ENGINE_PARALLEL = max(1, int(os.environ.get("CT_CHUAN_BI_SONG_SONG", "2") or 2))

# Doi khoa `running.pid` cua MOT draft toi da bay nhieu giay (LOW-26, 12/09/2026).
# Truoc do la 300 — bang dung tran bash tool cua vai (~300s), nen lan chay dau
# cua t_24b214a6 doi tron 300s roi bi chinh tool cat (`exit 124`), nhanh don khoa
# phia sau vong doi khong bao gio duoc cham toi. Phai NHO HAN tran ngoai de khi
# het gio engine con kip thoat bang mot cau vai doc duoc.
WAIT_LOCK_SECONDS = 60
# Doi CHO TRONG trong tran engine song song toi da bay nhieu giay (LOW-25). Cung
# ly do voi WAIT_LOCK_SECONDS: phai nho hon tran bash tool (~300s) de khi het gio
# engine tu noi ra thay vi bi cat cau. `_ngu` tach ra de test khong ngu that.
WAIT_SLOT_SECONDS = 240
_ngu = time.sleep
# Engine chet BAT THUONG (khoa mo coi = tien trinh truoc khong toi `finally`) bay
# nhieu lan tren MOT draft thi DUNG va bao, khong cho vai chay lai nua (LOW-28).
# t_24b214a6 12/09/2026: SIGSEGV 3 lan, vai tu xoa khoa va goi lai 16 lan trong
# 50 phut vi khong co gi noi "thoi". Hai lan la du de biet khong phai ngau nhien.
MAX_CRASH = 2

# Chet bang tin hieu (SIGSEGV trong PIL/torch/playwright...) thi `try/except`
# khong thay gi va log khong co traceback — t_24b214a6 chet `exit 139` ba lan ma
# prepare.log im lang. faulthandler in khung ngan xep Python ra stderr dung luc
# do, la manh moi duy nhat de truy (LOW-27).
faulthandler.enable()


@contextlib.contextmanager
def _wait_for_slot():
    """Giu mot trong N khoa tep state/prepare.<i>.lock (flock) trong luc chuan bi.

    Thieu fcntl (Windows) thi CHAY KHONG KHOA kem mot dong canh bao — tran
    CT_CHUAN_BI_SONG_SONG khong con hieu luc, nhung may do chi mot nguoi chay
    tay/chay test, khong phai server hai brand. Truoc 09/09/2026 cho nay
    `import fcntl` tran nen `chay()` KHONG chay duoc tren Windows chut nao
    (audit C3); emoji_deck.py da co san mau nay tu lau."""
    if fcntl is None:
        print("[cho] khong co fcntl (khong phai POSIX) -> chay KHONG khoa, "
              f"tran {COUNT_ENGINE_PARALLEL} engine song song khong duoc ap",
              file=sys.stderr)
        yield
        return
    thu_muc = ROOT / "state"
    thu_muc.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    da_bao_giay = -30
    while True:
        for i in range(COUNT_ENGINE_PARALLEL):
            fh = open(thu_muc / state_paths.LOCK_FILE.format(i), "w")
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                fh.close()
                continue
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
                fh.close()
            return
        troi = int(time.time() - t0)
        # Bao moi 30s (LOW-25): truoc 12/09/2026 chi in MOT dong roi im, va vong
        # `while True` khong co tran — doi hang trong nhin y het treo, roi bi
        # bash tool cua vai cat o 300s ma khong mot cau nao noi vi sao.
        if troi - da_bao_giay >= 30:
            da_bao_giay = troi
            print(f"[cho] da co {COUNT_ENGINE_PARALLEL} engine dang chay, doi toi luot... "
                  f"{troi}s/{WAIT_SLOT_SECONDS}s", file=sys.stderr)
        if troi >= WAIT_SLOT_SECONDS:
            sys.exit(f"[LOI] doi {WAIT_SLOT_SECONDS}s van chua co cho trong "
                     f"(tran {COUNT_ENGINE_PARALLEL} engine song song). Khong phai loi cua "
                     "draft nay — chay lai sau vai phut, dung chay lai ngay.")
        _ngu(5)


def _description_missing_image(m: dict) -> dict | None:
    """Bai nay co THIEU anh that khong, thieu bao nhieu — None neu du.

    Engine chi MO TA, khong quyet dinh (audit A1): hoi Ong Chu hay chuyen Kite
    la viec cua tang dieu phoi, xem `route_missing_images.after_prepare`."""
    so, tt = int(m.get("usable_count", 0)), int(m.get("min_images", 5))
    return None if so >= tt else {"count": so, "min_images": tt}


def _handle_lock(khoa: Path, cho: int, draft_id: str, ngu=time.sleep) -> None:
    """Xu ly `running.pid` cua MOT draft truoc khi engine chay (LOW-26).

    Ba truong hop, theo thu tu:
      1. Khong co khoa                 -> di tiep.
      2. Khoa MO COI (pid da chet)     -> DON NGAY, noi ra, di tiep. Khong doi
         mot giay nao: tien trinh chet bang SIGSEGV khong chay toi `finally`
         nen khoa nam lai; t_24b214a6 (12/09/2026) phai tu `ps -p` roi `rm -f`.
      3. pid CON SONG                  -> doi toi da `cho` giay, bao moi 30s;
         het gio ma van song thi thoat bang mot cau vai doc duoc. KHONG ghi de
         khoa (06/09/2026: hai engine tren cung draft de len manifest.json cua nhau).

    Tach ra khoi `chay()` de test duoc bang mot tep khoa gia, khong can meta
    draft hay browser. `ngu` chi de test khong phai ngu that.

    Tra ve True khi gap KHOA MO COI (tien trinh truoc chet bat thuong) — `chay()`
    dem so lan do de dung lai (LOW-28)."""
    if not khoa.exists():
        return False
    try:
        pid = int(khoa.read_text().strip() or 0)
        os.kill(pid, 0)
    except (ValueError, ProcessLookupError, PermissionError):
        print(f"[cho] khoa mo coi (pid {khoa.read_text().strip() or '?'} da chet) "
              "-> don khoa, chay tiep khong doi", file=sys.stderr)
        khoa.unlink(missing_ok=True)
        return True
    print(f"[cho] tien trinh {pid} dang chuan bi, doi toi da {cho}s...", file=sys.stderr)
    t0 = time.time()
    da_bao_giay = 0
    while khoa.exists() and time.time() - t0 < cho:
        ngu(3)
        troi = int(time.time() - t0)
        # Bao dinh ky: doi trong im lang thi nguoi doc log (va nguoi chay tay)
        # khong phan biet duoc "dang doi binh thuong" voi "treo han".
        if troi - da_bao_giay >= 30:
            da_bao_giay = troi
            print(f"[cho] ...{troi}s/{cho}s, tien trinh {pid} van giu khoa", file=sys.stderr)
    if not khoa.exists():
        return False
    try:
        con = int(khoa.read_text().strip() or 0)
        os.kill(con, 0)
    except (ValueError, ProcessLookupError, PermissionError):
        khoa.unlink(missing_ok=True)          # chet trong luc doi -> don khoa
        return True
    sys.exit(f"[LOI] tien trinh {con} van dang chuan bi {draft_id} sau {cho}s. "
             "KHONG chay engine thu hai tren cung mot draft (hai ban se de len "
             "manifest.json cua nhau). Doi them roi chay lai, hoac `--lam-moi` neu "
             "chac tien trinh kia treo.")


def count_crashes(wd: Path, mo_coi: bool, lam_moi: bool = False) -> int:
    """So lan engine chet bat thuong LIEN TIEP tren draft nay (LOW-28). Ham thuan
    tren mot tep `crash_count.json` trong wd: `mo_coi` -> +1; `lam_moi` -> ve 0;
    manifest.json ghi duoc -> `chay()` goi lai voi lam_moi=True de ve 0."""
    tep = wd / state_paths.CRASH_COUNT_FILE
    n = 0
    if not lam_moi:
        try:
            n = int(_read_json(tep).get("n", 0)) if tep.exists() else 0
        except Exception:                                    # noqa: BLE001
            n = 0
        if mo_coi:
            n += 1
    _write_json(tep, {"n": n})
    return n


def _report_crash_loop(draft_id: str, so_chet: int) -> None:
    """Mot dong Telegram vao topic cua vai anh khi engine chet lap — im lang la
    cai da khien 50 phut cua t_24b214a6 khong ai thay (INV-3)."""
    try:
        import publish
        tom = _summary_from_img_json(draft_id)
        slug = role.canonical_slug(tom.get("image_role") or "") or role.DEFAULT_IMAGE
        publish.send_topic(
            f"⛔ Engine chuẩn bị ảnh chết bất thường <b>{so_chet} lần liên tiếp</b> trên draft "
            f"<code>{draft_id}</code> — đã DỪNG, không chạy lại. Xem "
            f"<code>state/&lt;brand&gt;/{state_paths.PREPARE_DIR}/{draft_id}/{state_paths.PREPARE_LOG}</code> (faulthandler in "
            "chỗ chết). Sửa xong thì chạy lại với <code>--lam-moi</code>.", slug)
    except Exception as e:                                   # noqa: BLE001
        print(f"[chet] khong bao duoc Telegram: {type(e).__name__}: {e}", file=sys.stderr)


def run(draft_id: str, lam_moi=False, khong_browser=False, cho=WAIT_LOCK_SECONDS,
         sau_chuan_bi=None) -> tuple:
    """Bao dam manifest.json co san (chay neu chua, doi neu tien trinh khac dang chay).
    Tra ve (manifest, workdir, meta).

    `cho`: so giay toi da doi mot engine KHAC dang giu `running.pid` con song.
    Mac dinh WAIT_LOCK_SECONDS (60) — xem chu thich o hang so do: 300 bang dung tran
    bash tool cua vai nen "doi het khoa" chua bao gio thanh cong tu trong tay vai.

    `sau_chuan_bi(draft_id, m)`: moc cho tang GHEP NOI xu ly `m["missing_images"]`
    (hoi Ong Chu / chuyen Kite) — truyen `route_missing_images.after_prepare` vao.
    Engine khong tu import cai do: lam vay la lop CHUAN BI goi nguoc len lop
    dieu phoi (audit A1). Goi TRONG khoa va TRUOC khi ghi `manifest.json`, nen moi
    nguoi doc `manifest.json` deu thay quyet dinh da chot — day la ly do no la moc
    dong bo chu khong phai mot viec day sang vong poll khac."""
    meta = load_meta(draft_id)
    state = env_load.state_dir()
    wd = workdir(state, draft_id)
    wd.mkdir(parents=True, exist_ok=True)
    xong, khoa = wd / state_paths.MANIFEST_FILE, wd / state_paths.RUNNING_PID_FILE
    mo_coi = _handle_lock(khoa, cho, draft_id) if not lam_moi else False
    so_chet = count_crashes(wd, mo_coi, lam_moi)
    if so_chet >= MAX_CRASH and not xong.exists():
        _report_crash_loop(draft_id, so_chet)
        sys.exit(f"[LOI] engine da chet bat thuong {so_chet} lan lien tiep tren {draft_id} "
                 "— DUNG, KHONG chay lai. Da bao Ong Chu. Chi chay lai voi `--lam-moi` "
                 "sau khi sua nguyen nhan (xem prepare.log).")
    if xong.exists() and not lam_moi:
        # read_manifest bu khoa dan xuat cho ban cu (F2) — moi nguoi doc
        # thay cung mot so, khong ai phai tu doan nua.
        return schema.read_manifest(xong), wd, meta
    khoa.write_text(str(os.getpid()))
    try:
        with _wait_for_slot():
            m = prepare_article(draft_id, meta, state, wd, khong_browser=khong_browser)
        thieu = _description_missing_image(m)
        if thieu:
            m["missing_images"] = thieu
        if sau_chuan_bi is not None:
            t_route = time.time()
            try:
                sau_chuan_bi(draft_id, m)
            except (Exception, SystemExit) as e:             # noqa: BLE001
                # SystemExit cung phai bat: vai ham thu vien (send_telegram, crop_ratio)
                # bao loi bang sys.exit, lot qua thi mat luon manifest.json (audit 05/09).
                print(f"[route] {type(e).__name__}: {e}", file=sys.stderr)
            giay = time.time() - t_route
            # Moc nay chay TRONG khoa draft: cham la moi tien trinh khac phai
            # doi theo. Noi ra de con truy, thay vi chi thay ben kia "doi lau".
            if giay > 10:
                print(f"[route] mat {giay:.0f}s — khoa draft bi giu suot thoi gian do",
                      file=sys.stderr)
        _write_json(xong, m)
        count_crashes(wd, False, lam_moi=True)     # di toi cuoi -> xoa bo dem chet
    finally:
        khoa.unlink(missing_ok=True)
    return m, wd, meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Engine chuan bi (tat dinh) cho cac vai lam anh/chu")
    ap.add_argument("draft_id")
    ap.add_argument("--lam-moi", action="store_true")
    ap.add_argument("--im", action="store_true", help="Chay nen: chi in mot dong tom tat")
    ap.add_argument("--khong-browser", action="store_true")
    ap.add_argument("--cho", type=int, default=300)
    a = ap.parse_args()
    # Import o DAY chu khong o dau tep: `main()` la diem vao CLI, tuc cho ghep
    # noi — con than module `image_prepare` phai sach bong tang dieu phoi (audit
    # A1). Dat import nay len dau tep la keo approve_dispatch/approve_post vao lai
    # dung cai vua go ra.
    import route_missing_images
    m, wd, _ = run(a.draft_id, a.lam_moi, a.khong_browser, a.cho,
                    sau_chuan_bi=route_missing_images.after_prepare)
    print(f"[xong] {len(m['images'])} anh, {len(m.get('material', {}).get('number_sentences', []))} cau so lieu -> {wd}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
