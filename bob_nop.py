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
import card                                                  # noqa: E402
import env_load                                              # noqa: E402

# Skill nam trong repo (profile tro vao qua skills.external_dirs), khong phai
# trong ~/.hermes — nen duong dan tinh tu ROOT, khong doan theo HERMES_HOME.
SKILL = ROOT / "hermes" / "skills" / "url-mascot-frame"
GET_SOURCE = SKILL / "scripts" / "get_source.py"
SCREENSHOT = SKILL / "scripts" / "screenshot.js"
FRAME = SKILL / "scripts" / "frame.js"

# Ong Chu 06/09/2026: eyeroll la mood AN TOAN NHAT — no hop voi moi tinh huong,
# nen khi khong dinh vi duoc mood trong anh thi dung no. Truoc day mac dinh la
# 😂 (cuoi), nhung cuoi la mot phan doan CU THE: dat nham vao anh khong buon
# cuoi thi lech han, con eyeroll thi khong bao gio lech.
EMOJI_MAC_DINH = "🙄"
RC_KHONG_CO_ANH = 3            # get_source.py thoat 3 khi trang khong co anh don


def handle_kenh(brand: str) -> str:
    """@handle hien thi cua brand. MOT nguon su that: bang brand cua card.py —
    truoc day chuoi nay go tay trong SOUL nen phai chep SOUL thanh hai ban."""
    return (getattr(card, "THUONG_HIEU", {}).get(brand) or {}).get("handle") or brand


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
    if not shutil.which("node"):
        sys.exit("[LOI] trang khong co anh don va may khong co node de chup man hinh")
    r2 = subprocess.run(["node", str(SCREENSHOT), nguon, str(ra)],
                        capture_output=True, text=True, timeout=180, cwd=str(SKILL))
    if r2.returncode != 0 or not ra.exists():
        cuoi = [d for d in (r2.stderr or "").strip().splitlines() if d.strip()]
        sys.exit(f"[LOI] khong lay duoc anh lan chup man hinh: "
                 + (cuoi[-1][:200] if cuoi else "khong ro"))
    return "chup man hinh (trang khong co anh don)"


def dong_khung(src: Path, ra: Path, emoji: str, handle: str) -> None:
    if not shutil.which("node"):
        sys.exit("[LOI] thieu node de chay frame.js")
    r = subprocess.run(["node", str(FRAME), "--image", str(src), "--emoji", emoji,
                        "--handle", handle, "--out", str(ra)],
                       capture_output=True, text=True, timeout=180, cwd=str(SKILL))
    if r.returncode != 0 or not ra.exists():
        # In MAY dong cuoi, khong phai mot: loi cua frame.js thuong la nhieu
        # dong (thieu sharp / thieu node_modules) ma dong cuoi chi la goi y.
        cuoi = [d for d in ((r.stderr or "") + "\n" + (r.stdout or "")).splitlines() if d.strip()]
        for d in cuoi[-4:]:
            print(f"[LOI] frame.js: {d[:200]}", file=sys.stderr)
        sys.exit("[LOI] khong dong duoc khung. Thieu node_modules thi chay: "
                 f"cd {SKILL} && npm ci")


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
    ap.add_argument("--emoji", default=EMOJI_MAC_DINH,
                    help=f"mood mascot khop voi anh (mac dinh {EMOJI_MAC_DINH}); "
                         "bang mood o SKILL.md cua url-mascot-frame")
    ap.add_argument("--chu-thich", default="", help="Mot dong ve anh, gui kem")
    ap.add_argument("--khong-nhin", action="store_true",
                    help="Bo qua buoc vision mo ta anh (nhanh hon, tu chon mood)")
    ap.add_argument("--khong-gui", action="store_true", help="Thu: khong gui Telegram")
    ap.add_argument("--out", help="Duong dan anh ra (mac dinh tep tam)")
    a = ap.parse_args()

    if not FRAME.exists():
        sys.exit(f"[LOI] khong thay skill url-mascot-frame o {SKILL}")

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
    if not a.khong_nhin:
        try:
            import anh_chuan_bi as cb
            mo_ta, _ = cb.mo_ta_anh(src, "anh gui cho kenh de dong khung")
        except Exception as e:                               # noqa: BLE001
            mo_ta = ""
            print(f"[nhin] khong goi duoc vision: {type(e).__name__}", file=sys.stderr)
        if mo_ta:
            print(f"[nhin] ảnh này là: {mo_ta}")
        else:
            print("[nhin] chưa nhìn được ảnh — chọn mood theo ngữ cảnh Ông Chủ đưa, "
                  f"không chắc thì để {EMOJI_MAC_DINH}")
    dong_khung(src, ra, a.emoji, handle)
    print(f"[khung] {ra}  ({ra.stat().st_size // 1024} KB, handle {handle}, mood {a.emoji})")

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
