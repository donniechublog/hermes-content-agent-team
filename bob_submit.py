#!/usr/bin/env python3
"""bob_submit.py — NOP cua Bob: mot lenh lam het phan co hoc cua viec dong khung anh.

    lay anh goc (URL hoac tep co san) -> dong khung + mascot -> gui topic bob

Vi sao co tep nay (06/09/2026): Bob ra doi 28/08, TRUOC dot "kien truc 3 lop cho
moi vai" ngay 04/09 (a757f61 + 26b4d9a). Hai commit do gom 10 vai chay theo day
chuyen tin (co draft_id, co manifest.json) va bo sot dung Bob — vai duy nhat nhan
mot URL roi le. Hau qua: viec don gian nhat doi lai co SOUL DAI NHAT (91 dong,
chep hai ban cho hai brand, lech dung 3 dong handle), vi moi thu tuc phai nam
trong van xuoi cho LLM nho: duong dan hai script, thu tu tham so cua lenh dang
(phai khop command_allowlist tung ky tu), --document chu khong --photo, chuoi
handle cua brand. Gio ba buoc do la code; SOUL chi con: nhin anh, chon mood.

Dung:
    venv/bin/python bob_submit.py "<url>"                     # URL bat ky
    venv/bin/python bob_submit.py /duong/dan/anh.jpg          # anh da tai san
    venv/bin/python bob_submit.py "<url>" --emoji "🤔"        # chon mood khac
    venv/bin/python bob_submit.py "<url>" --khong-gui --out /tmp/x.png   # thu

LINK TWEET di duong rieng (23/09/2026): thay vi lay anh TRONG tweet, dung ca
THE tweet voi chu da dich sang tieng Viet (tweet_translate.py) roi moi dong
khung + mascot nhu thuong. Hai luot:

    venv/bin/python bob_submit.py "<link tweet>"              # in nguyen van de dich
    venv/bin/python bob_submit.py "<link tweet>" --vi-file vi.txt --khong-gui --out /tmp/x.png

`--tweet-image` keo link tweet ve duong CU (dong khung chinh tam anh trong tweet).
"""
import argparse
import atexit
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import image_frame                                             # noqa: E402
import capture_page                                            # noqa: E402
import env_load                                              # noqa: E402
import tweet_translate                                        # noqa: E402

# Skill nam trong repo (profile tro vao qua skills.external_dirs), khong phai
# trong ~/.hermes — nen duong dan tinh tu ROOT, khong doan theo HERMES_HOME.
SKILL = ROOT / "hermes" / "skills" / "url-mascot-frame"
GET_SOURCE = SKILL / "scripts" / "get_source.py"
# frame.js / screenshot.js da bo 09/09/2026 (audit A6): ca hai viet lai bang
# PIL + Playwright cua Python (image_frame.py, capture_page.py), server het can Node.
# Skill van giu assets (avatar, font, mood-palette) va SKILL.md.

# Ong Chu 06/09/2026: eyeroll la mood AN TOAN NHAT — no hop voi moi tinh huong,
# nen khi khong dinh vi duoc mood trong anh thi dung no. Truoc day mac dinh la
# 😂 (cuoi), nhung cuoi la mot phan doan CU THE: dat nham vao anh khong buon
# cuoi thi lech han, con eyeroll thi khong bao gio lech.
EMOJI_DEFAULT = "🙄"
RC_NO_HAS_IMAGE = 3            # get_source.py thoat 3 khi trang khong co anh don


def handle_channel(brand: str) -> str:
    """@handle hien thi cua brand — mot ban o env_load.handle_channel (ADF-r2-9).

    Su co 06/09/2026 giu lai lam ly do ham nay LUON co "@": CT_BRAND='blog'
    khong co trong card.BRAND nen tung roi ve chuoi 'blog' — watermark tren
    MOI anh Bob dong khung in dung chu "blog"."""
    return env_load.handle_channel(brand, co_a_cong=True)


def board_mood() -> dict:
    """{emoji: mood} doc tu assets/mood-palette.json cua chinh skill — MOT nguon
    su that, khong chep tay lai vao day."""
    import json
    try:
        ds = json.loads((SKILL / "assets" / "mood-palette.json").read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return {}
    return {m["emoji"]: m.get("mood", "") for m in ds if m.get("emoji")}


def mood_from_vision(txt: str) -> str:
    """Emoji dau tien trong `txt` co nam trong bang mood cua skill. "" neu khong.

    Chi nhan emoji THUOC BANG: vision tra ve chu tu do, ma image_frame chi doi
    emoji sang mascot cho nhung mood da co anh."""
    bang = board_mood()
    for ky_tu in txt or "":
        if ky_tu in bang:
            return ky_tu
    # emoji ghep (vd 😵‍💫, 😮‍💨) khong duyet duoc theo tung ky tu
    for e in bang:
        if len(e) > 1 and e in (txt or ""):
            return e
    return ""


def is_url(s: str) -> bool:
    return urlparse(s).scheme in ("http", "https")


def is_tweet(s: str) -> bool:
    """Link tới MỘT tweet cụ thể. Trang hồ sơ (`x.com/arena`) không tính —
    không có bài nào để dịch."""
    return bool(is_url(s) and tweet_translate._STATUS.search(s))


def take_tweet_card(nguon: str, out_path: Path, a) -> str:
    """Link tweet -> thẻ tweet chữ TIẾNG VIỆT ra `out_path` (tweet_translate).

    Không đưa bản dịch thì MÁY DỊCH bằng Grok (`env_load.TRANSLATE_MODEL`) — Bob
    chỉ cần một lượt. Bản dịch máy in ra stderr; không ưng thì chạy lại kèm
    `--vi "<bản của mình>"`, nó thắng tuyệt đối.
    """
    tu_dich = None if (a.vi or a.vi_file) else (a.model or True)
    vi = (tweet_translate.read_vi(a.vi, a.vi_file, a.bo_qua_dau, "tweet chính")
          if (a.vi or a.vi_file) else None)
    quote_vi = (tweet_translate.read_vi(a.quote_vi, a.quote_vi_file, a.bo_qua_dau, "quote")
                if (a.quote_vi or a.quote_vi_file) else None)
    source = tweet_translate.render(nguon, vi, out_path, theme=a.theme, lang=a.lang,
                                    clean=a.clean, quote_vi=quote_vi,
                                    hide_quote=a.hide_quote, hl_color=a.hl_color,
                                    auto=tu_dich)
    # Chỉ còn cho trường hợp NGƯỜI đưa bản dịch: tweet có quote mà không dịch,
    # không ẩn thì ảnh lẫn nguyên một khối tiếng Anh — và ở đây nó đi thẳng qua
    # bước đóng khung rồi lên Telegram. Máy dịch thì quote đã được dịch.
    if len(source) > 1 and quote_vi is None and not a.hide_quote and not tu_dich:
        out_path.unlink(missing_ok=True)
        sys.exit("[LOI] tweet có QUOTE lồng bên trong, chữ tiếng Anh của nó sẽ nằm "
                 f"trong ảnh:\n  {source[1][:160]!r}\n"
                 "  Dịch bằng --quote-vi, hoặc bỏ hẳn bằng --hide-quote.")
    return "thẻ tweet dịch tiếng Việt (tweet_translate.py)"


def take_image(nguon: str, out_path: Path) -> str:
    """Dua anh goc ve `out_path`. Tra ve mot dong mo ta cach lay duoc (de in ra).

    Thu tu la LUAT, khong phai lua chon cua vai: ban CDN goc truoc, chup man
    hinh chi khi trang khong co anh don nao."""
    if not is_url(nguon):
        p = Path(nguon).expanduser()
        if not p.exists():
            sys.exit(f"[LOI] khong thay tep: {p}")
        shutil.copyfile(p, out_path)
        return f"tep co san: {p}"

    r = subprocess.run([sys.executable, str(GET_SOURCE), nguon, str(out_path)],
                       capture_output=True, text=True, timeout=180)
    if r.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
        return "anh goc tu CDN (get_source.py)"
    if r.returncode != RC_NO_HAS_IMAGE:
        cuoi = [d for d in (r.stderr or "").strip().splitlines() if d.strip()]
        sys.exit(f"[LOI] get_source.py rc={r.returncode}: "
                 + (cuoi[-1][:200] if cuoi else "khong co stderr"))

    # Trang khong co anh don (tweet toan chu, bai bao) -> chup man hinh DPR cao.
    if not capture_page.capture(nguon, out_path):
        sys.exit("[LOI] khong lay duoc anh lan chup man hinh (xem stderr o tren)")
    return "chup man hinh (trang khong co anh don)"


def line_frame(src: Path, out_path: Path, emoji: str, handle: str) -> None:
    """Goi thang image_frame trong CUNG tien trinh, thay vi shell ra node frame.js.

    Het mot lop subprocess nghia la loi hien nguyen van (traceback that) chu
    khong con phai doan tu vai dong stderr cuoi cua Node."""
    try:
        image_frame.line_frame(src, out_path, emoji=emoji, handle=handle)
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] khong dong duoc khung: {type(e).__name__}: {e}")
    if not Path(out_path).exists():
        sys.exit("[LOI] dong khung xong ma khong thay tep ra")


def _env_clean() -> dict:
    """Env cho tien trinh con, da bo cac bien RONG.

    Shell cua profile bob dat `TELEGRAM_BOT_TOKEN=` RONG co y (de tat Telegram
    cua gateway). env_load.nap() dung `setdefault`, ma bien RONG van la bien DA
    CO — nen token that trong secret.common.env khong bao gio duoc nap va
    publish.py bao "Thieu TELEGRAM_BOT_TOKEN". Truoc day Bob phai tu nho meo
    `env -u TELEGRAM_BOT_TOKEN ...` (nam trong MEMORY.md, khong ai kiem). Gio
    la code: bien rong thi coi nhu chua dat."""
    return {k: v for k, v in os.environ.items() if v != ""}


def send(anh: Path, chu_thich: str) -> None:
    """Gui len topic `bob` bang publish.py --document (KHONG --photo: Telegram
    nen anh xuong ~1280px, khung mem hong). Truoc day thu tu tham so nay nam
    trong SOUL vi command_allowlist khop theo chuoi; gio la code."""
    r = subprocess.run([str(ROOT / "venv/bin/python"), str(ROOT / "publish.py"),
                        "--to-env", "TELEGRAM_GROUP_ID", "--thread-name", "bob",
                        "--document", str(anh), "--caption", chu_thich[:1000]],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120,
                       env=_env_clean())
    if r.returncode != 0:
        cuoi = [d for d in ((r.stderr or "") + "\n" + (r.stdout or "")).splitlines() if d.strip()]
        sys.exit("[LOI] publish.py: " + (cuoi[-1][:300] if cuoi else "khong ro"))
    print((r.stdout or "").strip()[-300:])


def main() -> int:
    ap = argparse.ArgumentParser(description="Dong khung mot anh cho Bob (tat dinh)")
    ap.add_argument("nguon", help="URL bat ky, hoac duong dan anh da tai ve")
    ap.add_argument("--emoji", default=None,
                    help="mood mascot, GHI DE ket qua nhin anh; khong truyen thi "
                         f"lay tu luot vision, khong nhan ra thi {EMOJI_DEFAULT}. "
                         "Bang mood o SKILL.md cua url-mascot-frame")
    ap.add_argument("--chu-thich", default="", help="Mot dong ve anh, gui kem")
    ap.add_argument("--khong-nhin", action="store_true",
                    help="Bo qua buoc vision mo ta anh (nhanh hon, tu chon mood)")
    ap.add_argument("--khong-gui", action="store_true", help="Thu: khong gui Telegram")
    ap.add_argument("--out", help="Duong dan anh ra (mac dinh tep tam)")
    # --- link tweet: dựng thẻ chữ tiếng Việt rồi mới đóng khung (23/09/2026) ---
    ap.add_argument("--vi", help="Bản dịch tiếng Việt của tweet (<hl>…</hl> = nhấn màu)")
    ap.add_argument("--vi-file", help="Tệp chứa bản dịch — dùng khi có nhiều dòng")
    ap.add_argument("--quote-vi", help="Bản dịch cho tweet được QUOTE bên trong")
    ap.add_argument("--quote-vi-file", help="Tệp chứa bản dịch của quote")
    ap.add_argument("--hide-quote", action="store_true", help="Ẩn hẳn khối quote")
    ap.add_argument("--hl-color",
                    help="Màu cụm <hl>: mã #rrggbb hoặc tên "
                         f"({', '.join(tweet_translate.HL_DARK)}). "
                         "Không đặt thì chọn theo id tweet.")
    ap.add_argument("--theme", default="dark", choices=("dark", "light"))
    ap.add_argument("--lang", default="vi", help="Ngôn ngữ chữ UI của thẻ tweet")
    ap.add_argument("--clean", action="store_true",
                    help="Thẻ tweet sạch hơn: bỏ nút Theo dõi và icon ⓘ")
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="Bỏ qua cổng chặn chữ Việt mất dấu")
    ap.add_argument("--model", help="Model dịch tweet (mặc định "
                                    f"{tweet_translate.env_load.TRANSLATE_MODEL})")
    ap.add_argument("--tweet-image", action="store_true",
                    help="Link tweet: lấy ẢNH TRONG tweet như trước, không dịch thẻ")
    a = ap.parse_args()

    # Kiem ASSETS cua skill (avatar/font/palette) — phan .js da bo, nhung khung
    # van doc avatar tu day nen thieu thu muc la hong ngay.
    if not (SKILL / "assets" / "avatars").is_dir():
        sys.exit(f"[LOI] khong thay assets cua skill url-mascot-frame o {SKILL}")

    env_load.load()
    # Bob DI THEO ORG GOI NO, khong co brand mac dinh nao (Ong Chu 23/09/2026).
    #
    # Truoc day cho nay mac dinh "donniechublog" CHO RIENG handle, con
    # `env_load.topics_path()` khong mac dinh gi ca -> roi ve `state/topics.json`
    # che do don cu (khong co topic `bob`): anh dong khung ra @donniechublog ma
    # buoc GUI thi chet "Topic 'bob' khong co". Hai cho doan khac nhau, va ca hai
    # deu doan.
    #
    # Gio MOT nguon duy nhat (`env_load.current_brand`: CT_BRAND, roi HERMES_HOME),
    # va DAT LAI vao moi truong de publish.py (tien trinh con) tra dung
    # `state/topics.<brand>.json`. Khong xac dinh duoc thi DUNG — dang nham brand
    # la loi khong ai thay cho toi khi da dang.
    brand = env_load.current_brand()
    if not brand:
        sys.exit("[LOI] khong biet dang chay cho org nao (thieu ca CT_BRAND lan "
                 "HERMES_HOME). Chay qua profile hermes thi gateway dat san; chay tay "
                 "thi neu ro, vd:\n"
                 "  CT_BRAND=dcgr venv/bin/python bob_submit.py \"<link>\"")
    os.environ["CT_BRAND"] = brand
    handle = handle_channel(brand)

    tam = Path(tempfile.mkdtemp(prefix="bob_"))   # mkdtemp-ok: don co dieu kien ngay duoi
    src = tam / "original.png"
    ra = Path(a.out) if a.out else tam / "framed.png"
    ra.parent.mkdir(parents=True, exist_ok=True)
    # Don thu muc tam CHI KHI anh ra khong nam trong no (LOW-390). Khong co
    # `--out` thi `ra` chinh la `tam/framed.png` — xoa la xoa mat san pham, nen
    # truong hop do phai giu. Truoc 23/09/2026 khong don bao gio, va 265 thu muc
    # `bob_*` nam lai tren may chu (/tmp o do la tmpfs, tuc an RAM).
    if ra.parent != tam:
        atexit.register(shutil.rmtree, tam, ignore_errors=True)

    # Link tweet đi đường vietsub; mọi URL khác giữ nguyên đường cũ (ảnh CDN,
    # chụp trang). `--tweet-image` kéo link tweet về đường cũ khi Bob muốn đóng
    # khung chính tấm ảnh TRONG tweet thay vì cả thẻ.
    if is_tweet(a.nguon) and not a.tweet_image:
        cach = take_tweet_card(a.nguon, src, a)
    else:
        cach = take_image(a.nguon, src)
    print(f"[nguon] {cach}  ({src.stat().st_size // 1024} KB)")

    # NHIN anh giup Bob. Tren profile bob, toolset `vision_analyze` khong dung
    # duoc (model chinh khong nhan anh), nen truoc day Bob phai tu go mot lenh
    # HTTP toi router vision — meo do nam trong MEMORY.md, khong ai kiem, va
    # mau thuan voi luat "ngoai lenh nay khong chay gi khac". Gio engine nhin
    # ho: cung ham `description_image` ma Dre/Ethan/Kite dung. Hong thi bao va di tiep,
    # vi Bob van co the tu nhin neu model cua no doc duoc anh.
    emoji, vi_sao = a.emoji, "Ông Chủ chỉ định"
    if not a.khong_nhin:
        try:
            import image_prepare as cb
            mo_ta, _, mood = cb.description_image(
                src, "anh gui cho kenh de dong khung",
                hoi_them="<DUNG MOT emoji trong bang: " + " ".join(board_mood()) + ">",
                nhan_them="MOOD")
        except Exception as e:                               # noqa: BLE001
            mo_ta, mood = "", ""
            print(f"[nhin] khong goi duoc vision: {type(e).__name__}", file=sys.stderr)
        if mo_ta:
            print(f"[nhin] ảnh này là: {mo_ta}")
        else:
            print("[nhin] chưa nhìn được ảnh")
        if emoji is None:
            tim = mood_from_vision(mood) or mood_from_vision(mo_ta)
            if tim:
                emoji, vi_sao = tim, f"vision chọn ({board_mood().get(tim, '')})"
    if emoji is None:
        emoji, vi_sao = EMOJI_DEFAULT, "mặc định an toàn — chưa định vị được mood"
    line_frame(src, ra, emoji, handle)
    print(f"[khung] {ra}  ({ra.stat().st_size // 1024} KB, handle {handle}, "
          f"mood {emoji} — {vi_sao})")

    if a.khong_gui:
        print(f"[thu] khong gui. Anh o: {ra}")
    else:
        send(ra, a.chu_thich or f"<b>Bob</b> — {handle}")
        print(f"[xong] da gui topic bob ({handle})")

    print(f"Ket qua task (dung dong nay de ket thuc task): Bob đã đóng khung ảnh "
          f"từ {'URL' if is_url(a.nguon) else 'tệp'} và {'lưu tại ' + str(ra) if a.khong_gui else 'gửi lên topic'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
