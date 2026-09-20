#!/usr/bin/env python3
"""Dong bo SOUL/MEMORY/cron/plugin kanban giua cac HERMES_HOME dang chay va ban trong git.

Vi sao can: phan lon HANH VI cua doi nam trong SOUL va script cron, ma hai thu
do lai o ngoai git. Ngay 22/08 script don em-dash lam hong 21 tep Python: 20 tep
khoi phuc tu git trong mot lenh, con moat_publish.py khong nam trong git nen
phai va tay tung khoi. Sang 23/08 lai phat hien ba script cron dung sai mui gio
ma khong co lich su de doi chieu da doi gi.

Da TACH CONTAINER theo brand: moi brand mot HERMES_HOME rieng
(`~/.hermes-blog`, `~/.hermes-dcgr`). Ban CHAY THAT nam trong cac home do; thu
muc hermes/ trong repo la ban chep co lich su, to chuc theo container:

    hermes/profiles/blog/<slug>.SOUL.md    -> ~/.hermes-blog/profiles/<slug>/
    hermes/profiles/dcgr/<slug>.SOUL.md    -> ~/.hermes-dcgr/profiles/<slug>/
    hermes/profiles/shared/<slug>.SOUL.md  -> CA HAI home
    ban goc hermes-agent + hermes/plugins/kanban/patches/*.patch
                                           -> <home>/plugins/kanban/dashboard/*  (ca hai)

Slug la ten thu muc THAT trong home (generic: carousel, designer, writer...),
khong phai ten nhan vat cu (heller/dre...). Profile co trong git ma home khong
co (vd carousel-edu chua deploy) se bao [thieu], KHONG bi tao ra.

Dung:
    venv/bin/python sync_hermes.py                  # chi so sanh, khong ghi
    venv/bin/python sync_hermes.py --vao-repo       # home -> repo (truoc khi commit)
    venv/bin/python sync_hermes.py --ra-hermes      # repo -> home (sau khi sua trong git)
    venv/bin/python sync_hermes.py --kiem-upstream  # hermes-agent doi gi o kanban ke tu UPSTREAM
    venv/bin/python sync_hermes.py --chot-upstream  # da port xong: ghi HEAD hermes-agent vao UPSTREAM
    venv/bin/python sync_hermes.py --refresh-patches  # sua plugin trong home xong: lam lai ban va tu home
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

import env_load
import kanban_plugin_build

ROOT = env_load.ROOT
REPO = ROOT / "hermes"
# Moi brand mot home rieng. Khai bao o env_load (audit_cron.py cung doc bang do
# — hai ban sao thi them brand la sua hai cho, quen mot cho la bo sot ca brand).
HOMES = env_load.hermes_homes()

# ---- Plugin kanban: PLUGIN NGUOI DUNG, khong con va vao ban cai hermes -------
# Truoc 06/09/2026 ban va nam TRONG ~/hermes-agent/plugins/kanban/dashboard —
# tuc trong ban cai hermes — nen `hermes update` reset no ve upstream, roi mot
# lan --vao-repo keo ban da bi reset vao git va xoa mat ba ban va (a1f9387).
# Cong lech-kich-thuoc 15% khong bat duoc, cong dau vet (06/09 sang) bat duoc
# nhung van la vo dau: goc re la de ban va o cho hermes update se ghi de.
#
# Hermes co san cach dung: dashboard quet <HERMES_HOME>/plugins/<ten>/dashboard/
# TRUOC plugins di kem, va khu trung THEO TEN (web_server._discover_dashboard_
# plugins, `seen_names`). Mot plugin ten `kanban` o thu muc nguoi dung che
# hoan toan ban di kem — ca dist/ lan plugin_api.py — va `hermes update` khong
# bao gio dung vao <HERMES_HOME>/plugins/. Nen tu 06/09/2026 chieu:
#
#     hermes/plugins/kanban/dashboard/  <->  <home>/plugins/kanban/dashboard/
#
# cho CA HAI home. ~/hermes-agent chi con la NGUON DE SOI upstream doi gi
# (--kiem-upstream), khong con la diem dong bo. Dieu kien de API cua plugin
# nguoi dung duoc mount: `plugins.enabled` trong config.yaml cua home phai co
# "kanban" (hermes gate theo GHSA-mcfc-hp25-cjv7) — script kiem va nhac.
#
# Tu 20/09/2026 (LOW-313) repo KHONG con chep ca tep: ben "repo" cua moi muc plugin
# la ban DUNG = ban goc trong git cua hermes-agent + ban va `plugins/kanban/patches/`
# (kanban_plugin_build.py). Ban va khong ap duoc thi khong ghi gi va thoat khac 0.
HERMES_AGENT = kanban_plugin_build.HERMES_AGENT
PLUGIN_FILE = kanban_plugin_build.PLUGIN_FILES
PLUGIN_REPO = REPO / "plugins" / "kanban" / "dashboard"     # chi con la TEN muc, khong co tep
# Ghi lai ban va dang dung tren commit upstream nao, de lan sau con rebase 3
# chieu duoc thay vi doan. Xem chu thich trong chinh tep UPSTREAM.
FILE_UPSTREAM = REPO / "plugins" / "kanban" / "UPSTREAM"
# Cron scripts brand-aware (mot ban, doc CT_BRAND). Dong bo sang scripts/ cua
# CA HAI home; home nao khong chay job do thi khong co tep -> bao [thieu],
# KHONG tao (ton trong phan chia job per-brand trong jobs.json). "moat_publish_
# watch" tung nam ngoai danh sach du la job chay DAY NHAT (moi phut) co ca
# find -delete — mot script hong ngoai git la dung kich ban 22/08.
SCRIPT = ["daily_scan",                              # than chung cua ba vai quet
          "finn_daily_scan", "nova_daily_scan", "vera_daily_scan",   # vo mong, giu ten cho cron
          "qinn_scan",                                    # chi blog (LOW-156: thieu tu truoc, phat hien 14/09)
          "model_watch", "journal_daily", "moat_publish_watch",
          "publish_due",                                  # ca hai home, moi phut (18/09/2026)
          "audit_cron",                                   # chay o CA HAI home
          "skill_lesson_filter",                          # both homes (LOW-119)
          "skill_lesson_commit"]                          # both homes (LOW-120)
# `usage_audit` da bo khoi danh sach 06/09/2026: job cron da go khoi ca hai home,
# va tep chi con la mot stub echo mot dong ("da gop vao daily-log"). Giu mot stub
# trong git de dong bo ra server chi de nhac nguoi ta xoa no la mot vong lap kin.
# Skill KHONG dong bo: ban that da o thang trong repo (hermes/skills/), profile
# tro vao qua skills.external_dirs nen `hermes update` khong xoa duoc.


def _slug(soul_path: Path) -> str:
    return soul_path.name[: -len(".SOUL.md")]


def plugin_home(H: Path) -> Path:
    return H / "plugins" / "kanban" / "dashboard"


# ---- Cong cu bi TAT theo profile (agent.disabled_toolsets) ------------------
# Vi sao phai co co che RIENG, khong nhet vao cap_file(): cap_file chep NGUYEN
# TEP, ma config.yaml cua profile co api_key nen khong duoc vao git. Nhung
# `agent.disabled_toolsets` lai dung la CHINH SACH — no quyet dinh vai con
# execute_code/delegate_task hay khong — nen de no chi song tren server la dinh
# dung cai bay da gap nhieu lan trong repo nay: dung lai home la mat im lang,
# khong ai biet da tung tat gi. Nen dong bo DUNG MOT KHOA do, qua mot tep chinh
# sach nho: {slug: [ten toolset]}. Slug nao khong co trong tep thi KHONG dung
# toi (khong tu y xoa khoa dang co tren server).
ALL_GATE_OLD = REPO / "profiles" / "disabled_toolsets.json"


def _config_profile(H, slug):
    return H / "profiles" / slug / "config.yaml"


def _read_all(p):
    """Gia tri agent.disabled_toolsets trong config.yaml, hoac None neu khong doc duoc."""
    import yaml                                            # noqa: WPS433 — chi can khi dung toi
    try:
        c = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    return ((c.get("agent") or {}).get("disabled_toolsets")) or []


def _write_all(p, gia_tri):
    """Dat agent.disabled_toolsets = gia_tri, GIU NGUYEN phan con lai cua tep.

    Khong dump lai bang yaml: config.yaml day chu thich va thu tu khoa co y
    nghia voi nguoi doc, dump lai la mat sach. Nen sua theo DONG, nhung chi
    trong dung khoi `agent:`.

    Bay da dinh that 06/09/2026: chen thang sau dong `agent:` ma khong nhin
    xem khoa DA CO trong khoi hay chua -> hai khoa trung trong cung mot
    mapping, YAML lay khoa cuoi, thay doi thanh vo tac dung. Nen sau khi sua
    phai NAP LAI va doi chieu; khong khop thi KHONG ghi."""
    import yaml                                            # noqa: WPS433
    dong = p.read_text(encoding="utf-8").splitlines(keepends=True)
    moi = "  disabled_toolsets: [" + ", ".join(gia_tri) + "]\n"
    ra, i, xong = [], 0, False
    while i < len(dong):
        d = dong[i]
        ra.append(d)
        i += 1
        if xong or d.rstrip("\n") != "agent:":
            continue
        # Trong khoi `agent:`: moi dong thut dau (hoac trong) deu thuoc khoi.
        khoi = []
        while i < len(dong) and (not dong[i].strip() or dong[i][:1] in (" ", "\t")):
            khoi.append(dong[i])
            i += 1
        thay = False
        for k, dk in enumerate(khoi):
            if dk.strip().startswith("disabled_toolsets:"):
                khoi[k], thay = moi, True
                break
        if not thay:
            khoi.insert(0, moi)
        ra.extend(khoi)
        xong = True
    if not xong:
        return False, "khong tim thay khoi 'agent:'"
    chu = "".join(ra)
    try:                                    # cong doi chieu: sua xong phai DUNG
        c = yaml.safe_load(chu) or {}
    except yaml.YAMLError as e:
        return False, f"sua xong YAML hong: {e}"
    if ((c.get("agent") or {}).get("disabled_toolsets") or []) != list(gia_tri):
        return False, "sua xong doc lai khong ra dung gia tri (khoa trung?)"
    p.write_text(chu, encoding="utf-8")
    return True, ""


def sync_all_gate_old(vao_repo, ra_hermes, chi=None):
    """So sanh/dong bo agent.disabled_toolsets. Tra (so_khac, so_chep)."""
    import json                                            # noqa: WPS433
    chinh_sach = {}
    if ALL_GATE_OLD.exists():
        try:
            chinh_sach = json.loads(ALL_GATE_OLD.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"  [thieu] doc {ALL_GATE_OLD.name} loi: {e}", file=sys.stderr)
            return 0, 0
    khac = chep = 0
    gom = {}                                  # --vao-repo: gom lai tu cac home
    for hk, H in HOMES.items():
        if not H.exists():
            continue
        for slug_dir in sorted((H / "profiles").glob("*")):
            slug = slug_dir.name
            ten = f"tat-cong-cu {hk}/{slug}"
            if chi and chi not in ten:
                continue
            p = _config_profile(H, slug)
            if not p.exists():
                continue
            hien = _read_all(p)
            if hien is None:
                print(f"  [thieu] {ten}: khong doc duoc config.yaml", file=sys.stderr)
                continue
            if vao_repo:
                if hien:
                    gom[slug] = sorted(hien)
                continue
            muon = chinh_sach.get(slug)
            if muon is None:                  # khong khai trong chinh sach -> khong dung toi
                continue
            if sorted(hien) == sorted(muon):
                continue
            khac += 1
            print(f"  KHAC  {ten}: home={hien or '[]'} repo={muon}"
                  + (" -> home" if ra_hermes else ""))
            if ra_hermes:
                ok, ly_do = _write_all(p, muon)
                if ok:
                    chep += 1
                else:
                    print(f"  [BO QUA] {ten}: {ly_do}", file=sys.stderr)
    if vao_repo:
        cu = chinh_sach
        if gom != cu:
            ALL_GATE_OLD.parent.mkdir(parents=True, exist_ok=True)
            ALL_GATE_OLD.write_text(json.dumps(gom, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
            print(f"  KHAC  tat-cong-cu -> repo ({len(gom)} profile)")
            khac, chep = 1, 1
    return khac, chep


def cap_file():
    """[(ten hien thi, duong that trong home, duong trong repo)]"""
    ra = []

    def them_profile(slug, repo_soul, home_keys):
        for hk in home_keys:
            H = HOMES[hk]
            ra.append((f"SOUL {hk}/{slug}",
                       H / "profiles" / slug / "SOUL.md", repo_soul))
            # MEMORY.md mang HANH VI (vd quy uoc tag fact_store), can lich su
            # nhu SOUL. USER.md rieng tung profile KHONG dong bo (co the co du
            # lieu ca nhan) — chi USER.md base cua home moi chep.
            # SOUL dung chung (shared/) van co the co MEMORY rieng tung brand
            # (profiles/<brand>/<slug>.MEMORY.md, vd carousel/designer/writer
            # tu 05/09/2026): uu tien ban rieng, khong co thi lay ban canh SOUL.
            rieng = REPO / "profiles" / hk / f"{slug}.MEMORY.md"
            repo_mem = rieng if rieng.exists() else repo_soul.with_name(f"{slug}.MEMORY.md")
            if repo_mem.exists():
                ra.append((f"MEMORY {hk}/{slug}",
                           H / "profiles" / slug / "memories" / "MEMORY.md",
                           repo_mem))

    for brand in ("blog", "dcgr"):
        d = REPO / "profiles" / brand
        for soul in sorted(d.glob("*.SOUL.md")):
            them_profile(_slug(soul), soul, [brand])
    for soul in sorted((REPO / "profiles" / "shared").glob("*.SOUL.md")):
        them_profile(_slug(soul), soul, ["blog", "dcgr"])

    for hk, H in HOMES.items():
        ra.append((f"MEMORY base {hk}", H / "memories" / "MEMORY.md",
                   REPO / "memories" / "MEMORY.md"))
        ra.append((f"USER base {hk}", H / "memories" / "USER.md",
                   REPO / "memories" / "USER.md"))
    for s in SCRIPT:
        for hk, H in HOMES.items():
            ra.append((f"cron {hk}/{s}", H / "scripts" / f"{s}.sh",
                       REPO / "scripts" / f"{s}.sh"))
    # Ten muc: "kanban <home> <tep>" — missing_trace tach tep bang split(" ", 2).
    for f in PLUGIN_FILE:
        for hk, H in HOMES.items():
            ra.append((f"kanban {hk} {f}", plugin_home(H) / f, PLUGIN_REPO / f))
    return ra


IS_PLUGIN = "kanban "

_PLUGIN_BUILD = {}            # {"built": {tep: {...}}} hoac {"error": str} — dung MOT lan moi lan chay


def plugin_build() -> dict:
    """Ban dung cua ca bo plugin (xem kanban_plugin_build.build), nho lai trong
    tien trinh. Hong thi tra {"error": ly do} — nguoi goi quyet dinh bao va dung."""
    if not _PLUGIN_BUILD:
        try:
            _PLUGIN_BUILD["built"] = kanban_plugin_build.build(HERMES_AGENT)
        except kanban_plugin_build.PluginPatchError as e:
            _PLUGIN_BUILD["error"] = str(e)
    return _PLUGIN_BUILD


def read_repo_side(ten: str, repo: Path):
    """Ben "repo" cua mot muc: tep trong git, rieng plugin kanban la ban DUNG.
    Plugin khong dung duoc -> None (muc do bi bo qua, loi bao mot lan o main)."""
    tep = _file_plugin(ten)
    if not tep:
        return read(repo)
    built = plugin_build().get("built")
    return built[tep]["data"] if built else None

# Dau vet cua tung ban va doi tu sua trong plugin kanban. Van giu du ban va da
# ra khoi ban cai hermes: no la cong "khong thut lui" — mot lan --vao-repo keo
# tu mot home vua bi ai do chep nham ban upstream vao van bi chan, thay vi lang
# le xoa ban va nhu a1f9387. Ap cho CA HAI CHIEU.
TRACE = {
    "dist/index.js": [
        ("nhan ten vai", "tenVai("),
        ("chia lane moi cot", "if (!props.laneByProfile) return null;"),
        ("thu tu cot", '["running", "ready", "blocked"'),
    ],
    "dist/style.css": [
        # Khong dung "font-size: 0.82rem;" lam dau vet: chuoi do con nam o
        # .hermes-kanban-md h4 va mot rule khac, co ca o ban CHUA va, nen
        # khong phan biet duoc. Lay cau chu thich rieng cua ban va.
        ("co chu lane", "0.65rem qua nho"),
        ("vien trai lane", "border-left: 3px solid var(--color-ring"),
        ("nen huy hieu profile", "color-mix(in srgb, var(--color-ring) 16%"),
    ],
    "plugin_api.py": [
        ("ten vai tu profile.yaml", "display_names"),
    ],
}


def _file_plugin(ten: str) -> str | None:
    """'kanban blog dist/index.js' -> 'dist/index.js'; None neu khong phai muc plugin."""
    if not ten.startswith(IS_PLUGIN):
        return None
    phan = ten.split(" ", 2)
    return phan[2] if len(phan) == 3 else None


def missing_trace(ten: str, nguon: bytes, dich: bytes) -> str | None:
    """Ly do KHONG nen ghi `nguon` de len `dich`, hoac None neu an toan.

    Chi chan khi ben DICH dang co dau vet ma ben NGUON thieu — do dung la kich
    ban ghi de lam mat ban va. Chieu nguoc lai (nguon co, dich thieu) chinh la
    dang mang ban va sang, phai cho chay. Khong bat Exception o day: ca hai ban
    byte da doc xong truoc khi goi, fail-open kieu cu la thu da giau loi.
    """
    tep = _file_plugin(ten)
    dau = TRACE.get(tep) if tep else None
    if not dau or nguon is None or dich is None:
        return None
    mat = [nhan for nhan, chuoi in dau
           if chuoi.encode() in dich and chuoi.encode() not in nguon]
    if not mat:
        return None
    return ("ben nguon thieu ban va ma ben dich dang co: " + ", ".join(mat)
            + " — ghi de la mat ban va")


def two_home_offset(tep: str, doc_fn=None) -> str | None:
    """--vao-repo: hai home phai giong nhau o tep plugin nay, khong thi tu choi
    — chep 'home nao doc sau thang' la im lang nuot ban cua home kia. Tra ve ly
    do, hoac None neu chi mot home co tep / ca hai giong nhau."""
    doc_fn = doc_fn or read
    ban = {hk: standard(doc_fn(plugin_home(H) / tep)) for hk, H in HOMES.items()}
    ban = {hk: b for hk, b in ban.items() if b is not None}
    if len({b for b in ban.values()}) <= 1:
        return None
    return ("hai home co hai ban KHAC NHAU (" + ", ".join(sorted(ban)) + ") — "
            "xem diff bang tay, chon mot ban, chay lai voi --chi kanban <home>")


COLOR_UPSTREAM = """\
# Xuất xứ bản vá plugin kanban trong repo này. TỆP DO MÁY GHI, đừng sửa tay.
#
# Repo KHÔNG còn chép cả plugin (LOW-313). `hermes/plugins/kanban/patches/` chỉ giữ
# BẢN VÁ của đội; plugin người dùng trong <home>/plugins/kanban/dashboard/ được
# DỰNG = bản gốc trong git của ~/hermes-agent + bản vá (kanban_plugin_build.py).
# Bản vá không áp được thì sync_hermes/check_hermes báo HỎNG, không im lặng.
#
#   venv/bin/python sync_hermes.py --kiem-upstream     # upstream đổi gì kể từ hash dưới
#   venv/bin/python sync_hermes.py --ra-hermes         # dựng lại + ghi vào hai home
#   # bản vá hết áp được: port tay trong home, restart dashboard, kiểm, rồi:
#   venv/bin/python sync_hermes.py --refresh-patches   # làm lại bản vá + ghi hash dưới
#
# `commit:` là HEAD của ~/hermes-agent mà bản vá được làm ra trên đó.

commit: {hash}
ghi_luc: {ngay}
"""


def hash_upstream() -> str | None:
    """HEAD cua ban cai hermes-agent, hoac None neu no khong phai repo git."""
    try:
        r = subprocess.run(["git", "-C", str(HERMES_AGENT), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def read_upstream() -> str | None:
    try:
        for d in FILE_UPSTREAM.read_text(encoding="utf-8").splitlines():
            if d.startswith("commit:"):
                return d.split(":", 1)[1].strip() or None
    except OSError:
        pass
    return None


def write_upstream() -> str | None:
    """Ghi HEAD hermes-agent hien tai vao UPSTREAM (sau khi da port). Tra ve hash."""
    h = hash_upstream()
    if not h:
        return None
    FILE_UPSTREAM.parent.mkdir(parents=True, exist_ok=True)
    FILE_UPSTREAM.write_text(
        COLOR_UPSTREAM.format(hash=h, ngay=time.strftime("%d/%m/%Y")),
        encoding="utf-8")
    return h


def report_plugin_build(chi=None) -> int:
    """In ket qua dung plugin; tra ma thoat (1 = ban va khong ap duoc). Khong im
    lang: day la cho LOW-313 sinh ra de bao."""
    if chi and not any(chi in f"kanban {hk} {f}" for hk in HOMES for f in PLUGIN_FILE):
        return 0                                    # lan chay nay khong dung toi plugin
    st = plugin_build()
    if "error" in st:
        print("\n[!] PLUGIN KANBAN KHONG DUNG DUOC — khong ghi tep plugin nao vao home:",
              file=sys.stderr)
        print("    " + st["error"].replace("\n", "\n    "), file=sys.stderr)
        return 1
    doi = sorted(f for f, v in st["built"].items() if v["drifted"])
    if doi:
        print("\n[i] Ban goc hermes-agent DA DOI o " + ", ".join(doi) + " ke tu lan lam ban va; "
              "ban va van ap sach. Mo dashboard kiem roi chay --refresh-patches de chot.")
    return 0


def refresh_patches(chi=None) -> int:
    """Home -> ban va. Doc plugin dang chay trong home, so voi ban goc, ghi lai
    patches/ + MANIFEST.json + UPSTREAM."""
    ket_qua = {}
    for f in PLUGIN_FILE:
        ly_do = None if chi else two_home_offset(f)
        if ly_do:
            print(f"[!] {f}: {ly_do}", file=sys.stderr)
            return 1
        for hk, H in HOMES.items():
            if chi and chi not in f"kanban {hk} {f}":
                continue
            b = read(plugin_home(H) / f)
            if b is not None:
                ket_qua[f] = standard(b)
                break
    if not ket_qua:
        print("[!] Khong home nao co plugin kanban de lam ban va.", file=sys.stderr)
        return 1
    try:
        da_ghi = kanban_plugin_build.refresh(ket_qua, HERMES_AGENT)
    except kanban_plugin_build.PluginPatchError as e:
        print(f"[!] {e}", file=sys.stderr)
        return 1
    write_upstream()
    print("Da lam lai ban va: " + (", ".join(p.name for p in da_ghi) or "(khong con khac biet nao)"))
    return 0


def check_upstream() -> int:
    """In diff cua hermes-agent o plugins/kanban/dashboard ke tu hash trong UPSTREAM."""
    goc = read_upstream()
    if not goc:
        print(f"[!] Khong doc duoc hash trong {FILE_UPSTREAM}", file=sys.stderr)
        return 1
    if not (HERMES_AGENT / ".git").exists():
        print(f"[!] {HERMES_AGENT} khong phai repo git (dat HERMES_AGENT_DIR neu o cho khac)",
              file=sys.stderr)
        return 1
    r = subprocess.run(["git", "-C", str(HERMES_AGENT), "diff", "--stat",
                        f"{goc}..HEAD", "--", "plugins/kanban/dashboard"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"[!] git diff loi: {r.stderr.strip()[:300]}", file=sys.stderr)
        return 1
    head = hash_upstream()
    print(f"UPSTREAM da port: {goc[:12]}   HEAD hermes-agent: {(head or '?')[:12]}")
    if not r.stdout.strip():
        print("Upstream KHONG doi gi o plugins/kanban/dashboard ke tu lan port cuoi.")
        return 0
    print("Upstream DA DOI (chua co trong plugin cua doi):\n" + r.stdout)
    print("Xem chi tiet:  git -C", HERMES_AGENT, f"diff {goc[:12]}..HEAD -- plugins/kanban/dashboard")
    return 0


def kanban_already_catch(H: Path) -> bool | None:
    """config.yaml cua home co `plugins.enabled` chua "kanban" khong.
    None = khong doc duoc (thieu tep / thieu pyyaml)."""
    p = H / "config.yaml"
    try:
        import yaml
        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:                                        # noqa: BLE001
        return None
    pl = cfg.get("plugins") if isinstance(cfg, dict) else None
    en = pl.get("enabled") if isinstance(pl, dict) else None
    return isinstance(en, list) and "kanban" in en


def mention_catch_plugin() -> None:
    """Plugin nguoi dung chi duoc mount API khi co trong plugins.enabled — thieu
    thi tab kanban van hien ma moi request /api/plugins/kanban/* deu 404."""
    hermes_py = HERMES_AGENT / "venv" / "bin" / "python"
    for hk, H in HOMES.items():
        if not plugin_home(H).exists():
            continue
        ok = kanban_already_catch(H)
        if ok:
            continue
        ly = "chua co 'kanban' trong plugins.enabled" if ok is False else "khong doc duoc config.yaml"
        print(f"\n[!] {hk}: {ly} — API cua plugin se KHONG duoc mount. Bat mot lan:")
        print(f"    HERMES_HOME={H} {hermes_py} -m hermes_cli.main plugins enable kanban")
        print(f"    systemctl --user restart hermes-dashboard@{hk}   # hoac unit dashboard cua home nay")


def mention_single_copy_item() -> None:
    """Ban cai hermes-agent con giu ban va cu (di san truoc 06/09) thi la ban thu
    ba gay nhieu: ke tu nay ban di kem phai LA upstream nguyen ban."""
    d = HERMES_AGENT / "plugins" / "kanban" / "dashboard"
    if not (HERMES_AGENT / ".git").exists() or not d.exists():
        return
    # --untracked-files=no: chi tinh tep git THEO DOI bi sua. Sau tep .bak cu
    # (untracked) tung lam canh bao nay keu nham ngay 07/09 du ban cai da sach.
    r = subprocess.run(["git", "-C", str(HERMES_AGENT), "status", "--porcelain",
                        "--untracked-files=no", "--", str(d)],
                       capture_output=True, text=True, timeout=10)
    if r.returncode == 0 and r.stdout.strip():
        print(f"\n[!] {d} dang lech so voi upstream (ban va cu con nam trong ban cai).")
        print("    Ke tu 06/09/2026 ban va song o <home>/plugins/kanban/, ban cai phai nguyen ban:")
        print(f"    git -C {HERMES_AGENT} checkout -- plugins/kanban/dashboard")


def read(p: Path):
    try:
        return p.read_bytes()
    except Exception:                                        # noqa: BLE001
        return None


def standard(b):
    """Chuan hoa xuong dong ve LF. Dev tren Windows (CRLF), home tren Unix (LF)
    — so sanh/ghi theo byte tho se bao KHAC het du noi dung y het. So sanh va
    ghi deu qua ham nay: dong bo dung noi dung, khong lam ban xuong dong."""
    if b is None:
        return None
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


# ---- Chup CAU HINH quyet dinh PROMPT ------------------------------------------
# Prompt that cua mot vai = SOUL + MEMORY + SKILL (deu trong git) + config.yaml
# cua profile (KHONG trong git). Nghia la sau `hermes update` hay khi dung may
# moi, ba phan dau tai lap duoc con phan thu tu thi phai nho — ma chinh phan do
# quyet dinh vai duoc dung skill nao, chay lenh nao, model nao (audit 06/09/2026:
# ban chup gateway dcgr ghi `external_dirs: []` trong khi README noi SKILL song
# qua chinh khoa do).
#
# KHONG chup ca tep: moi config.yaml ~495 dong ma phan lon la mac dinh cua hermes,
# se troi theo tung ban cap nhat va lam nhieu moi ban diff. Chi chup nhung khoa
# THUC SU doi hanh vi cua vai.
LOCK_PROMPT = [
    ("model", "default"),
    ("model", "provider"),
    ("model", "base_url"),
    ("fallback_providers",),
    ("agent", "reasoning_effort"),
    ("skills", "external_dirs"),
    ("skills", "enabled"),
    ("skills", "write_approval"),
    ("terminal", "command_allowlist"),
    ("kanban", "max_in_progress"),
    ("auxiliary", "title_generation", "enabled"),
    ("toolsets",),
    ("disabled_toolsets",),
]

# Khoa con mang bi mat — bo truoc khi ghi ra git. `fallback_providers` la mot
# danh sach dict co `api_key`, va no la khoa THAT chu khong phai bien moi truong
# o mot so profile.
LOCK_SECRET = ("api_key", "token", "secret", "password")


def _filter_secret(v):
    if isinstance(v, dict):
        return {k: ("<da bo>" if any(b in k.lower() for b in LOCK_SECRET) else _filter_secret(x))
                for k, x in v.items()}
    if isinstance(v, list):
        return [_filter_secret(x) for x in v]
    return v
FILE_CONFIG = REPO / "profiles" / "live_config_snapshot.yaml"


def _take(d, duong):
    for k in duong:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def capture_config() -> int:
    """Ghi cac khoa quyet dinh prompt cua MOI profile o CA hai home vao git."""
    try:
        import yaml
    except ImportError:
        print("[LOI] can pyyaml: venv/bin/pip install -r requirements.txt")
        return 1
    ra = {}
    for hk, H in HOMES.items():
        thu_muc = H / "profiles"
        if not thu_muc.is_dir():
            continue
        for pd in sorted(thu_muc.iterdir()):
            cf = pd / "config.yaml"
            if not cf.is_file():
                continue
            try:
                d = yaml.safe_load(cf.read_text(encoding="utf-8")) or {}
            except Exception as e:                           # noqa: BLE001
                ra[f"{hk}/{pd.name}"] = {"READ_ERROR": f"{type(e).__name__}: {e}"}
                continue
            muc = {}
            for duong in LOCK_PROMPT:
                v = _take(d, duong)
                if v not in (None, [], {}, ""):
                    muc["/".join(duong)] = _filter_secret(v)
            ra[f"{hk}/{pd.name}"] = muc
    FILE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    dau = ("# CAC KHOA CAU HINH QUYET DINH PROMPT — ban chup, TEP DO MAY GHI.\n"
           "# Sinh bang: venv/bin/python sync_hermes.py --chup-cau-hinh\n"
           "# Doc de biet vai dang chay model nao, thay duoc skill nao, chay duoc\n"
           "# lenh nao. KHONG dung de trien khai nguoc: doi cau hinh that thi sua\n"
           "# tren may chu roi chup lai trong cung mot commit.\n\n")
    FILE_CONFIG.write_text(dau + yaml.safe_dump(ra, allow_unicode=True, sort_keys=True),
                            encoding="utf-8")
    print(f"Da chup {len(ra)} profile -> {FILE_CONFIG}")
    return 0


def _sync_pair(a) -> tuple:
    """Vong dong bo chinh: duyet tung cap (ban that o home, ban trong repo).

    Tra ve `(khac, thieu, bo_qua, da_chep)`. Chieu `--vao-repo` la chieu TUNG LAM
    MAT hai ban va hom 04/09/2026 nen no co cong `missing_trace` rieng — dung gop
    hai chieu lam mot. Tach khoi `main` o LOW-309.
    """
    khac, thieu, bo_qua, da_chep = [], [], [], 0
    plugin_da_chep = set()      # --vao-repo: moi tep plugin chep MOT lan du hai home
    for ten, that, repo in cap_file():
        if a.chi and a.chi not in ten:
            continue
        a_b, b_b = read(that), read_repo_side(ten, repo)
        if _file_plugin(ten) and b_b is None:
            continue                    # plugin khong dung duoc: bao mot lan o cuoi, khong ghi gi
        if a_b is None:
            thieu.append(f"{ten}: khong co ban that ({that})")
            continue
        if standard(a_b) == standard(b_b):     # so sanh theo noi dung (bo qua CRLF)
            continue
        khac.append((ten, that, repo, b_b is None))

        if a.vao_repo:
            tep = _file_plugin(ten)
            if tep:
                # LOW-313: repo khong con giu ca tep plugin de ma chep vao. Home
                # khac ban dung = ai do sua truc tiep trong home -> lam lai BAN VA.
                if tep not in plugin_da_chep:
                    plugin_da_chep.add(tep)
                    bo_qua.append((ten, "plugin kanban khong chep vao repo nua — neu ban trong "
                                        "home la ban DUNG thi chay --refresh-patches"))
                continue
            # Chieu nay truoc day khong co cong nao — chinh no lam mat hai ban
            # va hom 04/09/2026. Nguon = ban that, dich = ban repo.
            ly_do = missing_trace(ten, a_b, b_b)
            if ly_do and not a.ep:
                bo_qua.append((ten, ly_do))
                continue
            repo.parent.mkdir(parents=True, exist_ok=True)
            repo.write_bytes(standard(a_b))          # ghi LF vao repo
            da_chep += 1
        elif a.ra_hermes:
            if b_b is None:
                continue                # khong co ban repo thi khong ghi de
            # Nguon = ban repo, dich = ban that. Chan khi ban that co dau vet
            # ma ban repo thieu (repo thut lui).
            ly_do = missing_trace(ten, b_b, a_b)
            if ly_do and not a.ep:
                bo_qua.append((ten, ly_do))
                continue
            that.parent.mkdir(parents=True, exist_ok=True)
            that.write_bytes(standard(b_b))          # ghi LF vao home
            da_chep += 1
    return khac, thieu, bo_qua, da_chep


def _make_plugin_home(a) -> int:
    """Plugin nguoi dung: home CHUA co thi `--ra-hermes` TAO no.

    Khac profile: day la thu duy nhat repo la NGUON GOC, khong phai ban chep cua
    home. Tra so tep da tao. Tach khoi `main` o LOW-309.
    """
    if not a.ra_hermes:
        return 0
    da_chep = 0
    for hk, H in HOMES.items():
        if not H.exists():
            continue
        for f in PLUGIN_FILE:
            dich, nguon = plugin_home(H) / f, read_repo_side(f"kanban {hk} {f}", PLUGIN_REPO / f)
            if not dich.exists() and nguon is not None and (not a.chi or a.chi in f"kanban {hk} {f}"):
                dich.parent.mkdir(parents=True, exist_ok=True)
                dich.write_bytes(standard(nguon))
                da_chep += 1
                print(f"  TAO   kanban {hk} {f} -> home")
    return da_chep


def _report(a, khac: list, bo_qua: list, da_chep: int, tat_khac: int, ma: int) -> int:
    """In ket qua mot luot dong bo, tra ma thoat.

    Cong `tat_khac` (muc tat-cong-cu) vao dong tong ket: thieu no thi vua in mot
    dong KHAC xong lai tong ket "0 tep lech" ngay duoi — nhat ky tu mau thuan.
    Tach khoi `main` o LOW-309.
    """
    if not khac and not da_chep and not tat_khac:
        print("Hai ben khop nhau, khong co gi de dong bo." if not ma else
              "Phan con lai khop nhau; plugin kanban KHONG kiem duoc (xem [!] o tren).")
        mention_catch_plugin()
        return ma

    huong = "-> repo" if a.vao_repo else ("-> home" if a.ra_hermes else "")
    for ten, _, _, moi in khac:
        print(f"  {'MOI  ' if moi else 'KHAC '} {ten} {huong}")
    if bo_qua:
        print()
        for ten, ly_do in bo_qua:
            print(f"  [BO QUA] {ten}")
            print(f"           {ly_do}")
        print("  Xem lai bang tay roi va lai tu ban moi, hoac chay --ep neu chac chan.")
    if a.vao_repo or a.ra_hermes:
        print(f"\nDa chep {da_chep} tep.")
    else:
        print(f"\n{len(khac) + tat_khac} tep lech. Chay voi --vao-repo hoac --ra-hermes de dong bo.")
    mention_catch_plugin()
    mention_single_copy_item()
    return ma


def main():
    ap = argparse.ArgumentParser(description="Dong bo SOUL/cron/plugin kanban voi git (multi-home)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--vao-repo", action="store_true", help="home -> repo")
    g.add_argument("--ra-hermes", action="store_true", help="repo -> home")
    g.add_argument("--kiem-upstream", action="store_true",
                   help="hermes-agent doi gi o plugins/kanban/dashboard ke tu hash trong UPSTREAM")
    g.add_argument("--chup-cau-hinh", action="store_true",
                   help="chup cac khoa cau hinh quyet dinh prompt cua moi profile vao git")
    g.add_argument("--chot-upstream", action="store_true",
                   help="Da port xong upstream: ghi HEAD hermes-agent vao UPSTREAM")
    g.add_argument("--refresh-patches", action="store_true",
                   help="Lam lai hermes/plugins/kanban/patches/ tu plugin dang o home "
                        "(hai home phai giong nhau, hoac chon mot bang --chi 'kanban <home>')")
    ap.add_argument("--ep", action="store_true",
                    help="Ghi de ke ca khi ben nguon thieu ban va cua tep plugin "
                         "(dung sau khi da xem bang tay va chac chan)")
    ap.add_argument("--chi", metavar="CHUOI",
                    help="Chi dong bo cac muc co ten chua CHUOI (vd --chi carousel, "
                         "--chi 'kanban blog'). Dung khi drift hai chieu: day/keo tung phan.")
    a = ap.parse_args()

    if a.kiem_upstream:
        return check_upstream()
    if a.chup_cau_hinh:
        return capture_config()
    if a.chot_upstream:
        h = write_upstream()
        print(f"UPSTREAM = {h}" if h else f"[!] Khong doc duoc HEAD cua {HERMES_AGENT}")
        return 0 if h else 1

    if a.refresh_patches:
        return refresh_patches(a.chi)

    khac, thieu, bo_qua, da_chep = _sync_pair(a)

    for t in thieu:
        print(f"  [thieu] {t}", file=sys.stderr)
    da_chep += _make_plugin_home(a)

    # agent.disabled_toolsets: khoa chinh sach nam trong config.yaml (khong chep
    # ca tep duoc vi co api_key) — dong bo rieng, xem sync_all_gate_old.
    tat_khac, tat_chep = sync_all_gate_old(a.vao_repo, a.ra_hermes, a.chi)
    da_chep += tat_chep

    return _report(a, khac, bo_qua, da_chep, tat_khac, report_plugin_build(a.chi))


if __name__ == "__main__":
    sys.exit(main())
