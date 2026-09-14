#!/usr/bin/env python3
"""check_env.py -- chan dau truoc khi cho engine chay: co du cv2, model
YuNet, Playwright/Chromium, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN hay khong.

Vi sao (audit C1 diem 4): thieu tung thu nay khong lam engine crash NGAY o
dau, ma chet cam lang o GIUA chung, rat xa cho thieu that su:
- Thieu cv2               -> image_rules._load_yunet() tra ve None, dem_mat()/
                             kiem_mat_nguoi() lang le bao "khong kiem duoc",
                             cong mat nguoi (LUAT_ANH SS6) tu tat ma khong ai
                             biet.
- Thieu file model .onnx  -> giong het thieu cv2 (_yunet() cung tra None),
                             nhung ly do khac (thieu file, khong phai thieu
                             goi cv2).
- Thieu Chromium          -> moi buoc dung playwright (browser_pass trong
                             image_prepare.py, cac buoc trong ranking.py,
                             capture_chart.py...) nem exception giua chung,
                             thuong sau khi da ton thoi gian/LLM cho cac buoc
                             truoc do roi.
- Thieu OPENAI_API_KEY    -> vision (prepare.vision._seen_image) tu tat, brief
                             ghi "CHUA AI NHIN" ma khong dung engine lai.
- Thieu TELEGRAM_BOT_TOKEN -> gui/duyet qua Telegram im lang khong gui duoc
                             (tru profile Bob, noi bien nay RONG la CO Y --
                             xem bob_submit.py / docstring env_load.nap).

Chay TRUOC khi bat engine, de biet ro thieu gi ma sua, thay vi doi engine
chay nua chung roi moi phat hien:

    python check_env.py

In moi muc kiem + tong ket; MOT muc loi khong duoc lam mat kha nang bao cac
muc con lai (dung quy uoc C1 dang rai khap repo) nen moi ham kiem_* tu boc
try/except rieng va khong bao gio raise ra ngoai. Exit 0 khi tat ca OK, 1 khi
co it nhat mot muc THIEU.
"""
import argparse
import os
import sys
from pathlib import Path

import env_load

# Ten model YuNet phai KHOP CHINH XAC voi cai image_rules._load_yunet() dung. Duong
# dan thuc te lay tu image_rules.__file__ trong check_yunet() (khong hardcode lai
# ROOT o day) de khong bao gio lech neu image_rules.py doi vi tri.
NAME_MODEL_YUNET = "face_detection_yunet_2023mar.onnx"


def check_cv2() -> tuple:
    """`import cv2` co thanh cong khong -- image_rules.count_faces/kiem_mat_nguoi can no."""
    try:
        import cv2
    except Exception as e:
        return False, f"import cv2 loi: {type(e).__name__}: {e} (can: pip install opencv-python)"
    # In luon phien ban: vua la thong tin huu ich khi doi chieu su co, vua de
    # `cv2` duoc DUNG that -- pyflakes khong hieu `# noqa` (flake8 moi hieu) nen
    # mot import chi de thu se thanh canh bao, ma C4 muon CI chan tren pyflakes.
    return True, f"ban {getattr(cv2, '__version__', '?')}"


def check_yunet() -> tuple:
    """Model YuNet ma image_rules._load_yunet() dung co nap duoc khong.

    Goi THANG image_rules._load_yunet() -- ham co gach duoi nhung Python khong chan
    goi tu ngoai, va day la duong CHINH XAC ma dem_mat()/kiem_mat_nguoi() di
    qua (khong mo phong lai logic, tranh lech nhau ve sau). Kiem file .onnx
    truoc de tach ro ly do: thieu FILE khac voi thieu cv2 (da co muc rieng o
    tren) -- ca hai deu lam _yunet() tra ve None nhu nhau nen tu no khong noi
    duoc ly do gi.
    """
    try:
        import image_rules
    except Exception as e:
        return False, f"khong import duoc image_rules: {type(e).__name__}: {e}"

    model = Path(image_rules.__file__).resolve().parent / "assets" / NAME_MODEL_YUNET
    if not model.exists():
        return False, f"khong thay file model: {model}"

    try:
        det = image_rules._load_yunet()
    except Exception as e:
        return False, f"loi khi goi image_rules._load_yunet(): {type(e).__name__}: {e}"
    if det is None:
        return False, ("image_rules._load_yunet() tra ve None du file model co ton tai "
                        "-- xem muc cv2 o tren")
    return True, ""


def check_chromium() -> tuple:
    """Playwright import duoc va Chromium co THAT SU launch duoc khong.

    Launch that roi dong ngay thay vi doan qua `playwright install --dry-run`:
    da thu tren may nay, dry-run luon in ra thong tin ban se TAI VE bat ke da
    cai hay chua -- khong dung de biet may nay san sang hay khong. Launch that
    la cach chac chan duy nhat, va khi thieu no bao loi ngay (khong treo cho),
    nen khong can them timeout rieng.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return False, f"import playwright loi: {type(e).__name__}: {e} (can: pip install playwright)"

    try:
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                b.close()
            except Exception:
                pass          # dong loi khong tinh la launch loi, bo qua
    except Exception as e:
        return False, (f"chromium khong launch duoc: {type(e).__name__}: {e} "
                        "(can: playwright install chromium)")
    return True, ""


def check_variable_environment(ten: str, ghi_chu: str = "") -> tuple:
    """Bien moi truong `ten` co duoc dat va KHONG rong khong.

    Goi SAU env_load.nap() de bat duoc gia tri tu secret.common.env /
    secret.<brand>.env, khong chi os.environ goc cua shell.
    """
    if os.environ.get(ten):
        return True, ""
    ly_do = "chua dat (rong hoac thieu)"
    if ghi_chu:
        ly_do += f" -- {ghi_chu}"
    return False, ly_do


def check_openai_key() -> tuple:
    """OPENAI_API_KEY -- vision trong image_prepare.py can bien nay."""
    return check_variable_environment("OPENAI_API_KEY")


def check_telegram_token() -> tuple:
    """TELEGRAM_BOT_TOKEN -- gui tin/duyet qua Telegram can bien nay.

    RONG co the la CO Y (profile Bob tat Telegram, xem bob_submit.py) nen THIEU
    o day khong luon dong nghia sai cau hinh -- ghi chu vao ly do de nguoi
    doc tu quyet, khong tu suy doan thay ho.
    """
    return check_variable_environment(
        "TELEGRAM_BOT_TOKEN",
        "co the RONG CO Y tren profile Bob, xem bob_submit.py")


ITEM_CHECK = [
    ("cv2 (opencv)", check_cv2),
    ("model YuNet (image_rules)", check_yunet),
    ("Playwright + Chromium", check_chromium),
    ("OPENAI_API_KEY", check_openai_key),
    ("TELEGRAM_BOT_TOKEN", check_telegram_token),
]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Chan dau truoc khi chay engine: kiem cv2, model YuNet, "
                     "Playwright/Chromium, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN.")
    ap.parse_args()

    # Console Windows mac dinh hay dung codepage cu (vd cp1252), khong phai
    # UTF-8. Da thu that: khi thieu Chromium, loi that cua Playwright chua ky
    # tu ve khung Unicode, va print() chuoi loi do len mot console cp1252 nem
    # UnicodeEncodeError -- tuc DUNG mot muc kiem lai lam chet ca script, thu
    # ta dang chan. errors="replace" doi ky tu khong in duoc thanh "?" thay vi
    # crash.
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(errors="replace")
        except Exception:
            pass

    env_load.load()

    so_ok = 0
    for ten_muc, ham in ITEM_CHECK:
        try:
            ok, ly_do = ham()
        except Exception as e:               # mot ham kiem tu no khong duoc lam chet main()
            ok, ly_do = False, f"ham kiem tu crash: {type(e).__name__}: {e}"
        trang_thai = "OK   " if ok else "THIEU"     # cung do rong 5 ky tu -> ten_muc thang cot
        print(f"{trang_thai}  {ten_muc}" + (f": {ly_do}" if ly_do else ""))
        if ok:
            so_ok += 1

    tong = len(ITEM_CHECK)
    print(f"\n{so_ok}/{tong} muc OK")
    if so_ok < tong:
        print(f"[THIEU] {tong - so_ok} muc chua san sang -- xem chi tiet o tren "
              "truoc khi chay engine.")
        return 1
    print("[OK] moi truong day du, an tam chay engine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
