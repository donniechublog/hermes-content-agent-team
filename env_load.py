#!/usr/bin/env python3
"""Mot cho duy nhat nap bien moi truong tu cac tep .env cua du an.

Vi sao gom lai: truoc day nhieu tep tu viet lai doan nay, va chung KHONG giong
nhau — ai sua mot cho thi nam cho kia lech.

Nguy hiem hon: `~/.hermes/.env` co dong `TELEGRAM_BOT_TOKEN=` DE RONG CO Y — de
tat Telegram cua gateway. Neu doc nham thu tu, token that bi gia tri rong che
mat va canh bao chet CAM. Nen nap nay BO QUA GIA TRI RONG: mot bien dat rong o
tep nay khong bao gio de len gia tri that o tep kia, va ket qua khong phu thuoc
thu tu.

KIEN TRUC CONTAINER (nhieu brand tren 1 ma nguon):
- Moi brand mot tep `secret.<key>.env` (key = bien moi truong `CT_BRAND`, vd
  'dcgr' | 'blog'), dung chung `secret.common.env`.
- Systemd/cron dat san `CT_BRAND` + `HERMES_HOME` cho tung container; cac gia tri
  do da nam trong os.environ nen `setdefault` o day khong de len chung.
- STATE per-brand: `state/<CT_BRAND>/` (offset, topics, dedup, manifest...) — xem
  `state_dir()`. Khong co `CT_BRAND` -> roi ve che do don cu (`.secrets.env`,
  `state/`), nen ma cu van chay binh thuong truoc khi cutover.
"""
import json
import os
from pathlib import Path

_BASE = Path(__file__).resolve().parent
# Goc du an = thu muc chua tep nay. Truoc day 16 tep tu tinh `Path.home() /
# "content-team"` — dung tren server, sai o moi may khac (audit 05/09/2026).
ROOT = _BASE
HERMES_DIR = Path.home() / "hermes-agent"
HERMES_PY = HERMES_DIR / "venv" / "bin" / "python"

# LOW-159: OpenSSL 3.5 mac dinh bat nhom khoa lai ML-KEM, ~50% handshake tu may
# chu toi api.telegram.org bi treo (LOW-133/134). Ban va o do dung Environment=
# systemd cho hermes-approve@/hermes-gateway@ — nhung KHONG toi duoc kanban
# worker: hermes dung lai worker vao mot moi truong xay lai tu dau, khong ke
# thua os.environ cua tien trinh gateway cha (do truc tiep /proc/<pid>/environ
# cua mot worker dang chay: 13 bien, khong co OPENSSL_CONF). Moi vai chay that
# publish.py/send_telegram.py o day, nen phai va o CHINH tien trinh do.
#
# Phai set TRUOC `import httpx` trong tung tep goi Telegram — set SAU khong co
# tac dung (do truc tiep: OpenSSL da nap cau hinh ngay luc thu vien SSL khoi
# tao khi import). Vi vay ca 5 tep goi Telegram (send_telegram.py, publish.py,
# approve_service.py, route_missing_images.py, approve_base.py) dua `import
# env_load` len TRUOC `import httpx`. `setdefault` de khong de neu ai da tu
# dat OPENSSL_CONF khac; kiem ton tai de khong vo may khac chua co tep nay.
_OPENSSL_CONF = _BASE / "hermes" / "systemd" / "openssl" / "hermes-groups.cnf"
if _OPENSSL_CONF.exists():
    os.environ.setdefault("OPENSSL_CONF", str(_OPENSSL_CONF))

ROUTER_URL = "http://127.0.0.1:20128/v1/chat/completions"   # 9router cuc bo, chung hai brand
VISION_MODEL = "ds/deepseek-v4-flash-vision-exp"            # con mat cua engine anh (image_prepare)

# User-Agent RIENG cho moi thu goi Wikimedia (API commons + tai anh tu
# upload.wikimedia.org). Robot policy cua Wikimedia doi UA co TEN cong cu va
# DUONG LIEN HE trong ngoac; UA kieu "Mozilla/5.0 (compatible; donniechu-dre/1.0)"
# bi tra 403 kem mot dong chu, khong phai JSON — ma ca ba cho goi Commons deu
# `except Exception -> []`, nen ca duong Wikimedia CHET CAM LANG (do 09/09/2026:
# 403 o ca API lan tai anh; doi UA nay thi 200). Khong nhet email vao day.
UA_WIKI = "donniechu-content-team/1.0 (https://dcgr.tech)"

# UA GIA TRINH DUYET, dung cho trang CHAN BOT (bang xep hang, arxiv). Truoc
# 09/09/2026 chuoi nay duoc chep tay o BA cho — ranking.py, arxiv_cover.py va
# prepare/browser.py — chi khac cho xuong dong; nang phien ban Chrome thi phai
# sua ba noi (audit A5).
#
# KHONG gop cac UA khac vao day, chung khac nhau CO CHU DICH:
#   scan_common.UA        "donniechu-scout/1.0"        — bot thanh that khi di quet
#   prepare/common.UA    "donniechu-dre/1.0"          — engine anh, danh rieng de
#                                                       doc log ben kia biet ai goi
#   article_extract.UA   "donniechu-content-bot/1.0"  — boc bai
#   UA_WIKI              — Wikimedia DOI ten cong cu + duong lien he (xem tren)
# Doi mot trong so do sang UA gia trinh duyet la mat tinh thanh that voi trang
# minh quet; doi UA_WIKI la an 403 (da do).
UA_BROWSER = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def hermes_home() -> Path:
    """HERMES_HOME cua container hien tai (~/.hermes-<brand>, systemd/cron dat san);
    khong co bien thi roi ve ~/.hermes (che do don cu).

    LOW-217: trong kanban worker, hermes dat HERMES_HOME = home cua PROFILE
    (`~/.hermes-blog/profiles/dre`), khong phai home cua brand. Moi nguoi goi ham
    nay deu can home brand (`profiles/<vai>`, `kanban.db`, `cron/`), nen doc tho
    thi `standard_assignee("kite")` tim `.../profiles/dre/profiles/kite`, khong
    thay, va engine anh bao sai "brand nay chua co Kite" (17/09/2026). Quy
    `<goc>/profiles/<ten>` ve `<goc>` — cung quy tac hermes dung cho kanban."""
    home = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
    return home.parent.parent if home.parent.name == "profiles" else home


def hermes_homes() -> dict:
    """Anh xa brand -> HERMES_HOME cua brand do, cho MOI brand chay tren may nay.

    Vi sao o day chu khong o sync_hermes: tu 07/09/2026 co hai nguoi dung —
    `sync_hermes` (dong bo SOUL/script) va `audit_cron` (soat cron ca hai home
    moi sang). Hai ban sao cua cung mot dict thi them mot brand la sua hai cho,
    va cho nao quen thi im lang bo sot ca mot brand — dung kieu loi tep nay sinh
    ra de chan. Them brand = them MOT dong o day."""
    return {"blog": Path.home() / ".hermes-blog",
            "dcgr": Path.home() / ".hermes-dcgr"}


def topics(brand: str = None) -> dict:
    """Anh xa ten vai -> thread_id cua brand; rong neu tep thieu hoac hong.
    `brand`: xem `state_dir`."""
    try:
        return json.loads(topics_path(brand).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _brand() -> str:
    """Khoa brand cua container hien tai ('dcgr' | 'blog'), rong neu che do don."""
    return os.environ.get("CT_BRAND", "").strip()


# CT_BRAND ('dcgr'|'blog', tren) la ten NGAN dung cho thu muc state — KHAC voi
# slug thuong hieu DAI ('dcgr'|'donniechublog') ma card.py/image_brand.py
# doi ("dcgr" trung ca hai nen an; "blog" != "donniechublog" thi lo ra ngay).
# image_prepare.NAME_CT giu chieu nguoc (dai -> ngan); giu them ban nay o day
# (khong import duoc image_prepare vi vong lap) de moi noi doi slug dai deu goi
# CUNG mot ham, khong tu viet lai phep tra nguoc roi quen mot cho (bat
# 09/09/2026: image_brand.py co HAI cho lam sai giong het nhau).
_BRAND_DAI = {"dcgr": "dcgr", "blog": "donniechublog"}
# Cong khai (audit lượt 2, ADF-r2-10): bang nay tung chep o 3 tep nua
# (moat_publish/approve_base/bob_submit `_TEN_BRAND`) — mot brand moi la sua 4 cho.
BRAND_LONG = _BRAND_DAI


def brand_long(mac_dinh: str = "donniechublog") -> str:
    """Slug thuong hieu DAI ('donniechublog'/'dcgr') tu CT_BRAND hien tai —
    dung cho moi loi goi card.set_brand (goi tu card.py va image_brand.py)."""
    return _BRAND_DAI.get(_brand(), mac_dinh)


def quantity(mac_dinh: int) -> int:
    """So worker cho mot ThreadPoolExecutor: min(mac dinh cua cho goi, CT_WORKERS).

    7 cho gõ cứng 4/6/8 (audit lượt 2, B-r2-6) — tren server 2 vCPU hay khi
    router vision gioi han, khong chinh duoc ma khong sua ma. CT_WORKERS chi ha
    xuong, khong nang len: moi cho da chon tran theo tinh chat I/O cua no."""
    try:
        tran = int(os.environ.get("CT_WORKERS", "0") or 0)
    except ValueError:
        tran = 0
    return max(1, min(mac_dinh, tran)) if tran > 0 else mac_dinh


def handle_channel(brand: str, co_a_cong: bool = True) -> str:
    """Handle hien thi cua brand ("@donniechublog" / "@dcgr.tech"), nhan CA khoa
    container ('blog') lan slug dai ('donniechublog').

    MOT ban (audit lượt 2, ADF-r2-9): truoc day bob_submit.handle_channel luon them "@"
    va doi 'blog', con kite_prepare.handle_channel tra nguyen 'donniechublog'
    khong "@" va khong doi 'blog' — cung ten ham, hai ket qua. Nguon su that
    van la card.BRAND (import tai cho de tranh vong: card import env_load).
    `co_a_cong=False` cho cho tu ghep "@" vao chu (slide cuoi cua Kite)."""
    import card
    b = (brand or "").strip()
    b = _BRAND_DAI.get(b, b)
    h = (getattr(card, "BRAND", {}).get(b) or {}).get("handle") or b
    h = h.lstrip("@")
    return ("@" + h) if co_a_cong else h


def _file_env() -> tuple:
    """Danh sach tep .env theo thu tu uu tien (tep truoc thang qua setdefault)."""
    files = [_BASE / "secret.common.env"]
    key = _brand()
    if key:
        files.append(_BASE / f"secret.{key}.env")
    # Tuong thich nguoc: che do don truoc cutover van doc tep cu.
    files.append(_BASE / ".secrets.env")
    files.append(Path.home() / ".hermes" / ".env")
    return tuple(files)


def state_dir(brand: str = None) -> Path:
    """Thu muc STATE RUNTIME cua brand (offset, dedup, manifest, drafts tam...).
    `state/<CT_BRAND>/` khi co CT_BRAND, nguoc lai `state/` (che do don cu).
    CT_STATE_DIR env var ghi de duong dan co ban. Bi gitignore (du lieu chay). Luon tao san thu muc.

    `brand` (LOW-283, 19/09/2026): state cua MOT brand KHAC container dang chay.
    Duy nhat mot cho can: Vera (dcgr) ghi phan tin du sang blog."""
    state_base = os.environ.get("CT_STATE_DIR")
    if state_base:
        d = Path(state_base)
    else:
        d = _BASE / "state"
    key = brand or _brand()
    if key:
        d = d / key
    d.mkdir(parents=True, exist_ok=True)
    return d


def topics_path(brand: str = None) -> Path:
    """Duong dan tep anh xa topic cua brand. KHONG phai runtime — day la CAU HINH
    khong tai tao duoc (topic id trong group), NEN commit vao git: `state/
    topics.<CT_BRAND>.json` (da un-ignore). Che do don cu: `state/topics.json`.
    `brand`: xem `state_dir`."""
    base = _BASE / "state"
    key = brand or _brand()
    return base / f"topics.{key}.json" if key else base / "topics.json"


def _env_keys(p: Path) -> set:
    """Ten bien khai trong mot tep .env (khong doc gia tri ra ngoai)."""
    try:
        dong = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {d.split("=", 1)[0].strip() for d in dong
            if "=" in d and not d.strip().startswith("#")}


def env_for_brand(brand: str) -> dict:
    """Moi truong cho tien trinh con chay nhu container `brand` (LOW-283).

    Vi sao khong chi doi CT_BRAND: `load` dung `setdefault`, nen bien tien trinh
    cha da nap tu `secret.<brand cha>.env` (token bot, id group) THANG tep cua
    brand dich — con dcgr goi publish.py voi CT_BRAND=blog van gui bang bot
    dcgr vao group dcgr. Bo moi bien khai trong tep secret cua HAI brand, va
    moi TELEGRAM_* (worker hermes con nap them .env cua HERMES_HOME), roi de
    tien trinh con tu nap lai tu tep cua brand dich."""
    bo = _env_keys(_BASE / f"secret.{_brand()}.env") | _env_keys(_BASE / f"secret.{brand}.env")
    env = {k: v for k, v in os.environ.items()
           if k not in bo and not k.startswith("TELEGRAM_")}
    env["CT_BRAND"] = brand
    home = hermes_homes().get(brand)
    if home:
        env["HERMES_HOME"] = str(home)
    return env


def load(*them: Path) -> None:
    """Nap cac tep .env vao os.environ.

    Khong ghi de bien da co san trong moi truong, va khong bao gio dat mot bien
    thanh chuoi rong.
    """
    for p in _file_env() + tuple(them):
        if not p or not p.exists():
            continue
        for dong in p.read_text(encoding="utf-8").splitlines():
            dong = dong.strip()
            if not dong or dong.startswith("#") or "=" not in dong:
                continue
            k, v = dong.split("=", 1)
            k, v = k.strip(), v.strip()
            if not k or not v:            # gia tri rong: bo qua, xem muc dich o docstring
                continue
            os.environ.setdefault(k, v)


def album_secondary(draft_id: str, thu_muc: Path = None) -> list:
    """Danh sach anh phu <draft_id>_2.png, _3.png... _10.png... sap dung so,
    khong theo thu tu chuoi.

    Truoc day 3 noi (draft_write, dre_submit, kite_submit) tu glob rieng bang mau
    `_[0-9].png` — chi khop MOT chu so nen bo sot slide thu 10 tro len. Bug
    that: Ong Chu duyet du 10 slide tren Telegram nhung album dang kenh chi
    con 9, vi draft_write doc thieu slide cuoi (audit 06/09/2026). Gom mot cho
    de sua mot lan, dung o ca ba noi."""
    d = thu_muc or (ROOT / "drafts")
    ung_vien = set(d.glob(f"{draft_id}_[0-9].png")) | set(d.glob(f"{draft_id}_[0-9][0-9].png"))

    def so(p: Path) -> int:
        try:
            return int(p.stem.rsplit("_", 1)[-1])
        except ValueError:
            return 0

    return sorted(ung_vien, key=so)


def required(ten: str) -> str:
    """Nap roi lay mot bien bat buoc; thieu thi dung han voi loi ro rang."""
    load()
    gt = os.environ.get(ten)
    if not gt:
        raise SystemExit(
            f"Thieu {ten} — kiem tra secret.common.env / secret.<brand>.env "
            f"(hoac .secrets.env che do don)")
    return gt

def write_json(p, d, indent: int = 2) -> None:
    """Ghi mot tep JSON state NGUYEN TU: tmp cung thu muc + os.replace.

    Dat o day vi gan nhu moi script deu da import env_load. `write_text` CAT
    NGAN tep cu truoc khi ghi noi dung moi — chet dung giua hai buoc do (restart
    dich vu, het cho dia) de lai mot sidecar cut, va moi nguoi doc sau do nem
    ValueError: bai ket vinh vien ma khong ai biet.

    Quan trong nhat voi cac tep NHIEU TIEN TRINH cung ghi: `drafts/<id>.meta.json`
    duoc ghi tu approve_service, tu engine chay nen, VA tu tien trinh hermes cua
    bang den — ba tien trinh khac nhau, khong khoa chung.

    Ten tmp mang pid de hai tien trinh khong ghi lan vao cung mot tep tam.
    """
    import json as _j
    import os as _os
    import threading as _th
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    # pid + thread id (ADF-r2-11, lay tu approve_base._write_json): approve_service
    # ghi cung mot tep state tu nhieu thread (nut chay nen, vong poll) — chung
    # mot ten tmp thi hai ban ghi lan vao nhau roi ban lai lan moi la cai replace.
    tmp = p.with_name(f"{p.name}.tmp.{_os.getpid()}.{_th.get_ident()}")
    try:
        tmp.write_text(_j.dumps(d, ensure_ascii=False, indent=indent, default=str),
                       encoding="utf-8")
        _os.replace(tmp, p)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
