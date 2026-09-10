#!/usr/bin/env python3
"""anh_chuan_bi.py — ENGINE CHUAN BI dung chung cho moi vai lam anh/chu tu mot tin
(Dre carousel, Ethan hero, Kite edu, va tu lieu cho Miles). Tat dinh, chay MOT lan,
o NEN ngay luc Ong Chu chon tin (approve_service.create_pair goi `anh_chuan_bi.py
<draft_id> --im`).

Nguyen tac Ong Chu: CODE TOI DA, LLM TOI THIEU. Do 04/09/2026: moi task anh ton
19-60 tool call, 60k-260k token input, phan lon la viec CO HOC (curl tai anh,
ls/grep do file, ghi roi doc lai spec, mo tung anh, crop lap, web_search lai
tin vi link Google News doc ra rong). Toan bo phan do nam o day:

  1. NGUON: doc bo nguon Finn/Vera da research (`state/<brand>/nguon_<id>.json`),
     giai ma link Google News, lay tieu de tieng Anh, hoi Bing News RSS tim bao
     khac khi nguon mong (ghi nguoc vao nguon json de moi vai sau cung dung).
  2. ANH: mot phien chromium (chu bai, <img> lon, chup table/figure/canvas full
     be ngang) + anh_bai (tinh) + Wikimedia Commons khi < 5 anh. Thieu thi tim
     rong sang bao khac cung tin (_vong_tim_rong). Anh THAT cua chinh hang trong
     tin (anh_thuong_hieu.py: logo, chan dung founder/CEO, tru so, campus) chay
     cho MOI tin co hang trong watchlist — du anh hay khong (10/09/2026). Van
     thieu nua thi anh khai niem cua chu de (anh_khai_niem.py: co nuoc, rack).
     Tai ve, bo trung (dHash), bo anh be, logo, co anh AI sinh.
  3. DO va PHAN LOAI bang `luat_anh` + luat bo sung (nen trang >=45% & canh
     >=8% -> chart): chart/anh chup, ti le, mat nguoi, day sang. Cat san
     1:1/4:5 qua crop_ti_le (co dau vet), cap anh ngang ghep duoc (cung tone),
     bang anh thu nho `bang_anh.png`.
  4. TU LIEU: tu_lieu.gom (fallback chu tu browser cho trang JS) -> cau co so.
  5. Ghi `xong.json` (manifest role-neutral). Moi vai co tep rieng in BRIEF theo
     cach nhin cua vai do: dre_chuan_bi.py, ethan_chuan_bi.py, kite_chuan_bi.py,
     miles_chuan_bi.py — deu doc chung xong.json nay, khong lam lai.

Tu 09/09/2026 (audit A1) than engine nam trong goi `chuan_bi/`, tach theo PHA;
tep nay chi con `chuan_bi()` (noi 9 pha), `chay()` (khoa + idempotent) va CLI —
nen cron, SOUL va cac vai KHONG phai doi lenh. Phu thuoc mot chieu:

    chung  <- nguon, browser, tai_loc <- nhin <- vong_bu ;  manifest <- chung

  chuan_bi/chung.py     hang so, header HTTP, doc/ghi JSON, ten mien
  chuan_bi/nguon.py     nap nguon Finn/Vera, ung vien tinh/social, Commons
  chuan_bi/browser.py   phien Chromium, boc anh trong trang, giai link Google News
  chuan_bi/tai_loc.py   tai song song + loc rac/trung/do hoa, cat san
  chuan_bi/nhin.py      vision tung anh, do hinh hoc, quyet dinh dung o dau
  chuan_bi/vong_bu.py   ba vong bu khi kho mong (bao khac, xep hang, thuong hieu, khai niem)
  chuan_bi/manifest.py  bang anh, cau tu lieu, brief

Idempotent + khoa: `state/<brand>/chuan_bi/<draft_id>/` (xong.json, dang_chay.pid).
`--lam-moi` de lam lai tu dau.

Dung:
    venv/bin/python anh_chuan_bi.py <draft_id> --im       # chay nen (approve_service)
    venv/bin/python anh_chuan_bi.py <draft_id> --lam-moi  # bo cache, lam lai
"""
import argparse
import contextlib
import os
import sys
import time
from pathlib import Path

try:
    import fcntl                 # POSIX (server) — khoa tep that
except ImportError:              # Windows (chay tay/test): xem `_cho_luot`
    fcntl = None


sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
from phien_browser import PhienBrowser                       # noqa: E402
import schema                                                # noqa: E402
import vai                                                   # noqa: E402

from chuan_bi.chung import (  # noqa: E402
    DRAFTS, ROOT, UA, _brand_cua, _doc_json, _ghi_json, _hdr,
)
from chuan_bi.manifest import (  # noqa: E402
    _tu_lieu_bai, bang_anh, cau_xep_hang, dong_brief_xep_hang, dung_manifest,
)
from chuan_bi.nguon import _tom_tat_tu_img_json, nap_nguon      # noqa: E402
from chuan_bi.nhin import _nhin_anh, mo_ta_anh                  # noqa: E402
from chuan_bi.tai_loc import _luu_crop                          # noqa: E402
from chuan_bi.vong_bu import (  # noqa: E402
    _anh_muc_xep_hang, _bo_sung_nguon, _chup_xep_hang, _gom_va_tai_anh,
    _lay_tu_browser, _vong_khai_niem, _vong_thuong_hieu, _vong_tim_rong,
)

# MAT TIEN cua goi `chuan_bi`: nhung ten ma cac vai/test VAN goi qua
# `anh_chuan_bi.X` sau khi tach goi (audit A1). Khai bao __all__ chu khong de
# import "thua" lang le: pyflakes ton trong __all__, va danh sach nay chinh la
# hop dong cong khai — them/bot o day la co y, khong phai vo tinh.
#
# KHAC voi shim 79 ten da go khoi approve_service (A2): moi ten duoi day deu co
# nguoi goi that (do bang `grep -o "cb\.[a-z_]*"` trong repo), khong phai keo
# ca module sang cho co.
__all__ = [
    "DRAFTS", "ROOT", "UA", "_anh_muc_xep_hang", "_brand_cua", "_cho_luot",
    "_doc_json", "_ghi_json", "_gom_va_tai_anh", "_hdr", "_luu_crop",
    "_mo_ta_thieu_anh", "_nhin_anh", "bang_anh", "cau_xep_hang", "chay",
    "chuan_bi", "dong_brief_xep_hang", "dung_manifest", "mo_ta_anh",
    "nap_meta", "nap_nguon", "workdir",
]

TEN_CT = {"dcgr": "dcgr", "donniechublog": "blog"}      # brand -> CT_BRAND


def chuan_bi(draft_id: str, meta: dict, state: Path, wd: Path, khong_browser=False) -> dict:
    """Engine anh cho MOT bai: nguon -> browser -> (xep hang) -> tai anh -> nhin
    -> tim rong neu thieu -> anh khai niem neu van thieu/khong co bia -> tu lieu -> manifest. Tach 07/09/2026 tu mot ham 231
    dong; doi chieu bang vet voi moi ham anh em thay bang ban gia (13 kich ban)."""
    import carousel
    title = meta.get("title", draft_id)
    # MOT phien Chromium cho ca bai (audit B4): truoc day nap_nguon (giai link
    # Google News), browser_pass va xep_hang moi cho tu launch mot tien trinh —
    # toi BON lan cho mot bai. Phien mo LUOI nen `--khong-browser` khong ton
    # tien trinh nao, va giu tien trinh RIENG cho moi bo tham so (xep_hang ep
    # srgb) de khong lang le doi cach xu ly mau anh chup.
    with PhienBrowser() as phien:
        nguon, nguon_path, link = nap_nguon(draft_id, meta, state, phien=phien)
        trang = nguon.get("trang", [])
        tom = _tom_tat_tu_img_json(draft_id)

        trang = _bo_sung_nguon(nguon, nguon_path, trang, link)
        bp = {"tieu_de_en": "", "chu": "", "cands": [], "trang_them": []}
        if not khong_browser:
            bp, trang = _lay_tu_browser(trang, wd, nguon, nguon_path, phien=phien)
        xhs, tin_xep_hang = _chup_xep_hang(title, nguon, tom, link, meta, bp, wd,
                                           khong_browser, phien=phien)
        anh = _gom_va_tai_anh(title, link, nguon_path, nguon, trang, bp, wd, xhs)
        anh, dung_duoc, chua_nhin = _nhin_anh(anh, nguon, title, wd)
        flagship = bool(carousel._FLAGSHIP_RE.search(title + " " + tom.get("summary", "")))
        # NGUONG DI THEO VAI (su co 10/09/2026). Truoc day dong nay la
        # `carousel.FLAGSHIP_MIN if flagship else carousel.MIN_SLIDE` — engine
        # chay chung cho ca ba vai dung anh nen Ethan (card.py, MOT anh la du)
        # cung bi doi 5 anh, roi ca day "thieu anh" ban cho Ethan cau hoi cua
        # carousel. `tom["vai_anh"]` da co san tu sidecar .img.json ngay tren
        # (`_tom_tat_tu_img_json`), chi la truoc gio khong ai dung toi.
        vai_anh = vai.slug_that(tom.get("vai_anh") or "")
        if vai_anh not in vai.VAI:
            # Chay tay, hoac sidecar mat/chua kip ghi. Khong im: nguong sai lam
            # lech ca `thieu_anh` o manifest lan cau bao gui Ong Chu.
            print(f"[chuan bi] khong biet vai cua {draft_id} "
                  f"(vai_anh={tom.get('vai_anh')!r}) -> dung nguong cua "
                  f"{vai.MAC_DINH_ANH}", file=sys.stderr)
            vai_anh = vai.MAC_DINH_ANH
        toi_thieu = vai.so_anh_toi_thieu(vai_anh, flagship)
        # HAI CAU HOI KHAC NHAU, dung lan nhau la hong ca hai chieu:
        #   `toi_thieu`             — nguong CHAN: duoi no thi bai bi coi la
        #                             thieu anh, Ong Chu bi hoi, bai co the bi
        #                             day sang Kite.
        #   `vai.du_nguyen_lieu()`  — CON PHAI DI TIM NUA KHONG.
        # Cau thu hai truoc LOW-12 do bang so cua carousel (5, hay 8 voi tin
        # flagship) cho CA BA vai. Ong Chu 10/09/2026: *"cach lam anh cua Ethan
        # dau phai la carousel? nhung gi thuoc ve carousel ma lien quan toi Ethan
        # la nhung thu ko dung"* va *"carousel la nhieu anh con Ethan lam single
        # image, nen 'so luong' ko the la thu ap vao duoc"*. Nay ban dang ky vai
        # tra loi: vai xep nhieu anh moi dem tam, vai mot anh chi hoi da co tam
        # nao dung lam anh chinh chua — tieu chi CHAT LUONG thi van dung chung o
        # `luat_anh` + `phan_loai` cho ca ba.
        tieu_de_nhin = nguon.get("tieu_de_en") or title
        if not vai.du_nguyen_lieu(vai_anh, dung_duoc, flagship) and not khong_browser:
            anh, dung_duoc, chua_nhin = _vong_tim_rong(anh, trang, tieu_de_nhin, toi_thieu,
                                                       dung_duoc, wd, phien=phien)
        # ANH CUA CHINH HANG trong tin (logo, chan dung founder/CEO, tru so,
        # campus): chay cho MOI tin nhac toi mot hang trong watchlist, KHONG doi
        # toi luc thieu anh. Ong Chu 10/09/2026, lan thu hai cua cung mot cau:
        # "Dre van ko chiu di tim cac hinh lien quan nhu logo, brand, founder,
        # tru so... cua chu de duoc nhac toi". Ban 09/09 treo vong nay sau dieu
        # kien thieu anh, nen tin nao bai goc du anh la khong bao gio hoi toi
        # Commons/Wikidata — ma vai bi cam tu tai them ("chi dung MA ANH"), nen bo
        # anh giao cho Dre trang tron du may moc da san. Tin khong nhac hang nao:
        # `hang_trong_tin` tra rong va vong thoat ngay, khong mot request nao.
        # Chi mang, chay ca khi --khong-browser; tran +4 anh nam trong vong.
        # So truyen vao chi dieu khien MOT thu trong vong do: nhanh mo browser di
        # chup bang xep hang lam boi canh. Voi vai mot anh no la 0 — mot cai chart
        # khong bao gio la nen hero duoc, di chup la tra tien browser lay mot tam
        # Ethan khong dung duoc.
        anh, dung_duoc, chua_nhin = _vong_thuong_hieu(anh, tieu_de_nhin, tom.get("summary", ""),
                                                      wd, vai.so_anh_muc_tieu_tim(vai_anh, flagship),
                                                      khong_browser, phien=phien)
        # Van thieu, hoac co anh ma khong tam nao lam anh chinh cua VAI NAY duoc
        # -> anh khai niem chung chung cua chu de, sau anh cua chinh hang (chi
        # mang, khong browser; chay ca khi --khong-browser).
        if not vai.du_nguyen_lieu(vai_anh, dung_duoc, flagship):
            anh, dung_duoc, chua_nhin = _vong_khai_niem(anh, tieu_de_nhin, tom.get("summary", ""), wd)
        tl = _tu_lieu_bai(title, link, nguon_path, wd, nguon, bp)
        m = dung_manifest(draft_id, meta, title, link, nguon, nguon_path, tom, wd, anh, xhs,
                          tin_xep_hang, bp, tl, flagship, toi_thieu, vai_anh=vai_anh)
    bang_anh(anh, wd / "bang_anh.png")     # ngoai phien: khong dung browser
    return m


# ---- chay + khoa + idempotent (dung chung cho moi vai) -----------------------
def workdir(state: Path, draft_id: str) -> Path:
    return state / "chuan_bi" / draft_id

def nap_meta(draft_id: str) -> dict:
    meta = _doc_json(DRAFTS / f"{draft_id}.meta.json")
    if not meta:
        sys.exit(f"Khong thay drafts/{draft_id}.meta.json — task nay khong do approve_service tao?")
    os.environ.setdefault("CT_BRAND", TEN_CT.get(_brand_cua(meta), "blog"))
    return meta


# Tran so engine chay CUNG LUC tren ca may (chung hai brand): moi engine mo mot
# Chromium 1600x1200 DPR2 + goi vision tung anh. Ong Chu chon 7 tin la 7 engine
# khoi chay cung luc (audit 05/09/2026). Het cho thi doi, khong bo.
SO_ENGINE_SONG_SONG = max(1, int(os.environ.get("CT_CHUAN_BI_SONG_SONG", "2") or 2))


@contextlib.contextmanager
def _cho_luot():
    """Giu mot trong N khoa tep state/chuan_bi.<i>.lock (flock) trong luc chuan bi.

    Thieu fcntl (Windows) thi CHAY KHONG KHOA kem mot dong canh bao — tran
    CT_CHUAN_BI_SONG_SONG khong con hieu luc, nhung may do chi mot nguoi chay
    tay/chay test, khong phai server hai brand. Truoc 09/09/2026 cho nay
    `import fcntl` tran nen `chay()` KHONG chay duoc tren Windows chut nao
    (audit C3); emoji_deck.py da co san mau nay tu lau."""
    if fcntl is None:
        print("[cho] khong co fcntl (khong phai POSIX) -> chay KHONG khoa, "
              f"tran {SO_ENGINE_SONG_SONG} engine song song khong duoc ap",
              file=sys.stderr)
        yield
        return
    thu_muc = ROOT / "state"
    thu_muc.mkdir(parents=True, exist_ok=True)
    da_bao = False
    while True:
        for i in range(SO_ENGINE_SONG_SONG):
            fh = open(thu_muc / f"chuan_bi.{i}.lock", "w")
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
        if not da_bao:
            print(f"[cho] da co {SO_ENGINE_SONG_SONG} engine dang chay, doi toi luot...", file=sys.stderr)
            da_bao = True
        time.sleep(5)


def _mo_ta_thieu_anh(m: dict) -> dict | None:
    """Bai nay co THIEU anh that khong, thieu bao nhieu — None neu du.

    Engine chi MO TA, khong quyet dinh (audit A1): hoi Ong Chu hay chuyen Kite
    la viec cua tang dieu phoi, xem `route_thieu_anh.sau_chuan_bi`."""
    so, tt = int(m.get("so_dung_duoc", 0)), int(m.get("toi_thieu", 5))
    return None if so >= tt else {"so": so, "toi_thieu": tt}


def chay(draft_id: str, lam_moi=False, khong_browser=False, cho=300,
         sau_chuan_bi=None) -> tuple:
    """Bao dam xong.json co san (chay neu chua, doi neu tien trinh khac dang chay).
    Tra ve (manifest, workdir, meta).

    `sau_chuan_bi(draft_id, m)`: moc cho tang GHEP NOI xu ly `m["thieu_anh"]`
    (hoi Ong Chu / chuyen Kite) — truyen `route_thieu_anh.sau_chuan_bi` vao.
    Engine khong tu import cai do: lam vay la lop CHUAN BI goi nguoc len lop
    dieu phoi (audit A1). Goi TRONG khoa va TRUOC khi ghi `xong.json`, nen moi
    nguoi doc `xong.json` deu thay quyet dinh da chot — day la ly do no la moc
    dong bo chu khong phai mot viec day sang vong poll khac."""
    meta = nap_meta(draft_id)
    state = env_load.state_dir()
    wd = workdir(state, draft_id)
    wd.mkdir(parents=True, exist_ok=True)
    xong, khoa = wd / "xong.json", wd / "dang_chay.pid"
    if not lam_moi and khoa.exists():
        try:
            pid = int(khoa.read_text().strip() or 0)
            os.kill(pid, 0)
            print(f"[cho] tien trinh {pid} dang chuan bi, doi toi da {cho}s...", file=sys.stderr)
            t0 = time.time()
            da_bao_giay = 0
            while khoa.exists() and time.time() - t0 < cho:
                time.sleep(3)
                troi = int(time.time() - t0)
                # Bao dinh ky: doi tron 300s trong im lang thi nguoi doc log
                # (va nguoi chay tay) khong phan biet duoc "dang doi binh thuong"
                # voi "treo han" — dung thu im lang ma ca hai dot vua roi di go.
                if troi - da_bao_giay >= 30:
                    da_bao_giay = troi
                    print(f"[cho] ...{troi}s/{cho}s, tien trinh {pid} van giu khoa",
                          file=sys.stderr)
            # HET GIO MA PID VAN SONG: KHONG duoc ghi de khoa. Truoc 06/09/2026
            # doan duoi ghi `dang_chay.pid` vo dieu kien, nen khi may ban that
            # (tran CT_CHUAN_BI_SONG_SONG=2, Ong Chu chon 7 tin mot luc, moi
            # engine ton browser 110s x2 + vision + Bing) thi engine thu hai
            # khoi dong tren CUNG mot draft: ca hai cung ghi xong.json, va
            # engine xong truoc unlink khoa cua engine sau.
            if khoa.exists():
                try:
                    con = int(khoa.read_text().strip() or 0)
                    os.kill(con, 0)
                except (ValueError, ProcessLookupError, PermissionError):
                    khoa.unlink(missing_ok=True)          # chet that -> don khoa
                else:
                    sys.exit(f"[LOI] tien trinh {con} van dang chuan bi {draft_id} "
                             f"sau {cho}s. KHONG chay engine thu hai tren cung mot "
                             "draft (hai ban se de len xong.json cua nhau). Doi "
                             "them roi chay lai, hoac `--lam-moi` neu chac tien "
                             "trinh kia treo.")
        except (ValueError, ProcessLookupError, PermissionError):
            khoa.unlink(missing_ok=True)
    if xong.exists() and not lam_moi:
        # doc_manifest bu khoa dan xuat cho ban cu (F2) — moi nguoi doc
        # thay cung mot so, khong ai phai tu doan nua.
        return schema.doc_manifest(xong), wd, meta
    khoa.write_text(str(os.getpid()))
    try:
        with _cho_luot():
            m = chuan_bi(draft_id, meta, state, wd, khong_browser=khong_browser)
        thieu = _mo_ta_thieu_anh(m)
        if thieu:
            m["thieu_anh"] = thieu
        if sau_chuan_bi is not None:
            t_route = time.time()
            try:
                sau_chuan_bi(draft_id, m)
            except (Exception, SystemExit) as e:             # noqa: BLE001
                # SystemExit cung phai bat: vai ham thu vien (gui_telegram, crop_ti_le)
                # bao loi bang sys.exit, lot qua thi mat luon xong.json (audit 05/09).
                print(f"[route] {type(e).__name__}: {e}", file=sys.stderr)
            giay = time.time() - t_route
            # Moc nay chay TRONG khoa draft: cham la moi tien trinh khac phai
            # doi theo. Noi ra de con truy, thay vi chi thay ben kia "doi lau".
            if giay > 10:
                print(f"[route] mat {giay:.0f}s — khoa draft bi giu suot thoi gian do",
                      file=sys.stderr)
        _ghi_json(xong, m)
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
    # noi — con than module `anh_chuan_bi` phai sach bong tang dieu phoi (audit
    # A1). Dat import nay len dau tep la keo duyet_giao_viec/duyet_bai vao lai
    # dung cai vua go ra.
    import route_thieu_anh
    m, wd, _ = chay(a.draft_id, a.lam_moi, a.khong_browser, a.cho,
                    sau_chuan_bi=route_thieu_anh.sau_chuan_bi)
    print(f"[xong] {len(m['anh'])} anh, {len(m.get('tu_lieu', {}).get('cau_co_so', []))} cau so lieu -> {wd}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
