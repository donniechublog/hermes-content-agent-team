#!/usr/bin/env python3
"""bob_nop.py — NOP cua Bob: mot lenh lam het phan co hoc cua viec dong khung anh.

    lay anh goc (URL hoac tep co san) -> dong khung + mascot -> gui topic bob

Vi sao co tep nay (06/09/2026): Bob ra doi 28/08, TRUOC dot "kien truc 3 lop cho
moi vai" ngay 04/09 (a757f61 + 26b4d9a). Hai commit do gom 10 vai chay theo day
chuyen tin (co draft_id, co xong.json) va bo sot dung Bob — vai duy nhat nhan
mot URL roi le. Hau qua: viec don gian nhat doi lai co SOUL DAI NHAT (91 dong,
chep hai ban cho hai brand, lech dung 3 dong handle), vi moi thu tuc phai nam
trong van xuoi cho LLM nho: duong dan hai script, thu tu tham so cua lenh dang
(phai khop command_allowlist tung ky tu), --document chu khong --photo, chuoi
handle cua brand. Gio ba buoc do la code; SOUL chi con: nhin anh, chon mood.

Dung:
    venv/bin/python bob_nop.py "<url>"                     # URL bat ky
    venv/bin/python bob_nop.py /duong/dan/anh.jpg          # anh da tai san
    venv/bin/python bob_nop.py "<url>" --emoji "🤔"        # chon mood khac
    venv/bin/python bob_nop.py "<url>" --khong-gui --out /tmp/x.png   # thu
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import khung_anh                                             # noqa: E402
import chup_trang                                            # noqa: E402
import env_load                                              # noqa: E402

# Skill nam trong repo (profile tro vao qua skills.external_dirs), khong phai
# trong ~/.hermes — nen duong dan tinh tu ROOT, khong doan theo HERMES_HOME.
SKILL = ROOT / "hermes" / "skills" / "url-mascot-frame"
GET_SOURCE = SKILL / "scripts" / "get_source.py"
# frame.js / screenshot.js da bo 09/09/2026 (audit A6): ca hai viet lai bang
# PIL + Playwright cua Python (khung_anh.py, chup_trang.py), server het can Node.
# Skill van giu assets (avatar, font, mood-palette) va SKILL.md.

# Ong Chu 06/09/2026: eyeroll la mood AN TOAN NHAT — no hop voi moi tinh huong,
# nen khi khong dinh vi duoc mood trong anh thi dung no. Truoc day mac dinh la
# 😂 (cuoi), nhung cuoi la mot phan doan CU THE: dat nham vao anh khong buon
# cuoi thi lech han, con eyeroll thi khong bao gio lech.
EMOJI_MAC_DINH = "🙄"
RC_KHONG_CO_ANH = 3            # get_source.py thoat 3 khi trang khong co anh don


def handle_kenh(brand: str) -> str:
    """@handle hien thi cua brand — mot ban o env_load.handle_kenh (ADF-r2-9).

    Su co 06/09/2026 giu lai lam ly do ham nay LUON co "@": CT_BRAND='blog'
    khong co trong card.THUONG_HIEU nen tung roi ve chuoi 'blog' — watermark tren
    MOI anh Bob dong khung in dung chu "blog"."""
    return env_load.handle_kenh(brand, co_a_cong=True)


def bang_mood() -> dict:
    """{emoji: mood} doc tu assets/mood-palette.json cua chinh skill — MOT nguon
    su that, khong chep tay lai vao day."""
    import json
    try:
        ds = json.loads((SKILL / "assets" / "mood-palette.json").read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return {}
    return {m["emoji"]: m.get("mood", "") for m in ds if m.get("emoji")}


def mood_tu_vision(txt: str) -> str:
    """Emoji dau tien trong `txt` co nam trong bang mood cua skill. "" neu khong.

    Chi nhan emoji THUOC BANG: vision tra ve chu tu do, ma khung_anh chi doi
    emoji sang mascot cho nhung mood da co anh."""
    bang = bang_mood()
    for ky_tu in txt or "":
        if ky_tu in bang:
            return ky_tu
    # emoji ghep (vd 😵‍💫, 😮‍💨) khong duyet duoc theo tung ky tu
    for e in bang:
        if len(e) > 1 and e in (txt or ""):
            return e
    return ""


def la_url(s: str) -> bool:
    return urlparse(s).scheme in ("http", "https")


def lay_anh(nguon: str, ra: Path) -> str:
    """Dua anh goc ve `ra`. Tra ve mot dong mo ta cach lay duoc (de in ra).

    Thu tu la LUAT, khong phai lua chon cua vai: ban CDN goc truoc, chup man
    hinh chi khi trang khong co anh don nao."""
    if not la_url(nguon):
        p = Path(nguon).expanduser()
        if not p.exists():
            sys.exit(f"[LOI] khong thay tep: {p}")
        shutil.copyfile(p, ra)
        return f"tep co san: {p}"

    r = subprocess.run([sys.executable, str(GET_SOURCE), nguon, str(ra)],
                       capture_output=True, text=True, timeout=180)
    if r.returncode == 0 and ra.exists() and ra.stat().st_size > 0:
        return "anh goc tu CDN (get_source.py)"
    if r.returncode != RC_KHONG_CO_ANH:
        cuoi = [d for d in (r.stderr or "").strip().splitlines() if d.strip()]
        sys.exit(f"[LOI] get_source.py rc={r.returncode}: "
                 + (cuoi[-1][:200] if cuoi else "khong co stderr"))

    # Trang khong co anh don (tweet toan chu, bai bao) -> chup man hinh DPR cao.
    if not chup_trang.chup(nguon, ra):
        sys.exit("[LOI] khong lay duoc anh lan chup man hinh (xem stderr o tren)")
    return "chup man hinh (trang khong co anh don)"


def dong_khung(src: Path, ra: Path, emoji: str, handle: str) -> None:
    """Goi thang khung_anh trong CUNG tien trinh, thay vi shell ra node frame.js.

    Het mot lop subprocess nghia la loi hien nguyen van (traceback that) chu
    khong con phai doan tu vai dong stderr cuoi cua Node."""
    try:
        khung_anh.dong_khung(src, ra, emoji=emoji, handle=handle)
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] khong dong duoc khung: {type(e).__name__}: {e}")
    if not Path(ra).exists():
        sys.exit("[LOI] dong khung xong ma khong thay tep ra")


def _env_sach() -> dict:
    """Env cho tien trinh con, da bo cac bien RONG.

    Shell cua profile bob dat `TELEGRAM_BOT_TOKEN=` RONG co y (de tat Telegram
    cua gateway). env_load.nap() dung `setdefault`, ma bien RONG van la bien DA
    CO — nen token that trong secret.common.env khong bao gio duoc nap va
    publish.py bao "Thieu TELEGRAM_BOT_TOKEN". Truoc day Bob phai tu nho meo
    `env -u TELEGRAM_BOT_TOKEN ...` (nam trong MEMORY.md, khong ai kiem). Gio
    la code: bien rong thi coi nhu chua dat."""
    return {k: v for k, v in os.environ.items() if v != ""}


def gui(anh: Path, chu_thich: str) -> None:
    """Gui len topic `bob` bang publish.py --document (KHONG --photo: Telegram
    nen anh xuong ~1280px, khung mem hong). Truoc day thu tu tham so nay nam
    trong SOUL vi command_allowlist khop theo chuoi; gio la code."""
    r = subprocess.run([str(ROOT / "venv/bin/python"), str(ROOT / "publish.py"),
                        "--to-env", "TELEGRAM_GROUP_ID", "--thread-name", "bob",
                        "--document", str(anh), "--caption", chu_thich[:1000]],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120,
                       env=_env_sach())
    if r.returncode != 0:
        cuoi = [d for d in ((r.stderr or "") + "\n" + (r.stdout or "")).splitlines() if d.strip()]
        sys.exit("[LOI] publish.py: " + (cuoi[-1][:300] if cuoi else "khong ro"))
    print((r.stdout or "").strip()[-300:])


def main() -> int:
    ap = argparse.ArgumentParser(description="Dong khung mot anh cho Bob (tat dinh)")
    ap.add_argument("nguon", help="URL bat ky, hoac duong dan anh da tai ve")
    ap.add_argument("--emoji", default=None,
                    help="mood mascot, GHI DE ket qua nhin anh; khong truyen thi "
                         f"lay tu luot vision, khong nhan ra thi {EMOJI_MAC_DINH}. "
                         "Bang mood o SKILL.md cua url-mascot-frame")
    ap.add_argument("--chu-thich", default="", help="Mot dong ve anh, gui kem")
    ap.add_argument("--khong-nhin", action="store_true",
                    help="Bo qua buoc vision mo ta anh (nhanh hon, tu chon mood)")
    ap.add_argument("--khong-gui", action="store_true", help="Thu: khong gui Telegram")
    ap.add_argument("--out", help="Duong dan anh ra (mac dinh tep tam)")
    a = ap.parse_args()

    # Kiem ASSETS cua skill (avatar/font/palette) — phan .js da bo, nhung khung
    # van doc avatar tu day nen thieu thu muc la hong ngay.
    if not (SKILL / "assets" / "avatars").is_dir():
        sys.exit(f"[LOI] khong thay assets cua skill url-mascot-frame o {SKILL}")

    env_load.nap()
    brand = os.environ.get("CT_BRAND", "").strip() or "donniechublog"
    handle = handle_kenh(brand)

    tam = Path(tempfile.mkdtemp(prefix="bob_"))
    src = tam / "goc.png"
    ra = Path(a.out) if a.out else tam / "khung.png"
    ra.parent.mkdir(parents=True, exist_ok=True)

    cach = lay_anh(a.nguon, src)
    print(f"[nguon] {cach}  ({src.stat().st_size // 1024} KB)")

    # NHIN anh giup Bob. Tren profile bob, toolset `vision_analyze` khong dung
    # duoc (model chinh khong nhan anh), nen truoc day Bob phai tu go mot lenh
    # HTTP toi router vision — meo do nam trong MEMORY.md, khong ai kiem, va
    # mau thuan voi luat "ngoai lenh nay khong chay gi khac". Gio engine nhin
    # ho: cung ham `mo_ta_anh` ma Dre/Ethan/Kite dung. Hong thi bao va di tiep,
    # vi Bob van co the tu nhin neu model cua no doc duoc anh.
    emoji, vi_sao = a.emoji, "Ông Chủ chỉ định"
    if not a.khong_nhin:
        try:
            import anh_chuan_bi as cb
            mo_ta, _, mood = cb.mo_ta_anh(
                src, "anh gui cho kenh de dong khung",
                hoi_them="<DUNG MOT emoji trong bang: " + " ".join(bang_mood()) + ">",
                nhan_them="MOOD")
        except Exception as e:                               # noqa: BLE001
            mo_ta, mood = "", ""
            print(f"[nhin] khong goi duoc vision: {type(e).__name__}", file=sys.stderr)
        if mo_ta:
            print(f"[nhin] ảnh này là: {mo_ta}")
        else:
            print("[nhin] chưa nhìn được ảnh")
        if emoji is None:
            tim = mood_tu_vision(mood) or mood_tu_vision(mo_ta)
            if tim:
                emoji, vi_sao = tim, f"vision chọn ({bang_mood().get(tim, '')})"
    if emoji is None:
        emoji, vi_sao = EMOJI_MAC_DINH, "mặc định an toàn — chưa định vị được mood"
    dong_khung(src, ra, emoji, handle)
    print(f"[khung] {ra}  ({ra.stat().st_size // 1024} KB, handle {handle}, "
          f"mood {emoji} — {vi_sao})")

    if a.khong_gui:
        print(f"[thu] khong gui. Anh o: {ra}")
    else:
        gui(ra, a.chu_thich or f"<b>Bob</b> — {handle}")
        print(f"[xong] da gui topic bob ({handle})")

    print(f"Ket qua task (dung dong nay de ket thuc task): Bob đã đóng khung ảnh "
          f"từ {'URL' if la_url(a.nguon) else 'tệp'} và {'lưu tại ' + str(ra) if a.khong_gui else 'gửi lên topic'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
