#!/usr/bin/env python3
"""image_provenance.py — dấu vết xuất xứ PNG, THUẦN CƠ CHẾ, không có tiêu chí nào.

Tách khỏi `image_rules.py` khi bỏ file dùng chung đó (LOW-182, 16/09/2026): mọi
`check_*`/`kiem_*` (có ngưỡng, có phán đoán "ảnh này dùng được không") đi vào ba
module riêng của Ethan/Dre/Kite (`image_rules_<vai>.py`), CÒN mấy hàm ở đây thì
không — chúng chỉ đọc/ghi một dòng text vào metadata PNG ("ảnh này do công cụ
nào tạo ra"), không có ngưỡng nào để mà lệch giữa các vai. Bằng chứng: Gin và
Itachi vốn đã gọi `stamp_file` từ trước 16/09/2026 mà KHÔNG áp bộ luật ảnh nào
cả (`swap_image_text.py`/`gin_submit.py` chỉ sửa ảnh gốc, không tạo ảnh mới) —
tức bản thân hệ thống đã coi đây là hạ tầng đứng ngoài "luật", không phải một
phần của thứ vừa bị tách ba.

Mọi công cụ TẠO ảnh (`crop_ratio.py`, `capture_chart.py`, `arxiv_figures.py`,
`ranking.py`, `carousel.py` ghép dọc, `prepare/browser.py`, `prepare/fallback_rounds.py`)
và công cụ SỬA ảnh (`gin_submit.py`, `swap_image_text.py`) đều đóng dấu qua đây,
bất kể đang làm cho vai nào — ba module luật đọc dấu này qua `read_crop_trace`/
`allows_landscape_crop`/`is_ranking_image`/`is_stacked_composite`.
"""
from pathlib import Path

from PIL import Image

MARK_PNG = ("crop_ti_le", "nguon_dung")   # cac khoa metadata bao "do doi dung ra"


def stamp_provenance(xuat_xu, **them):
    """Tra ve PngInfo mang dau `nguon_dung=<xuat_xu>` (+ cac khoa phu neu co).

    Ten tham so la `xuat_xu` chu khong phai `nguon`: `nguon` la mot trong nhung
    khoa phu hay dung nhat (nguon=ARENA.AI), de trung ten thi vo TypeError.

    Moi cong cu trong doi sinh ra anh PHAI dong dau: crop_ratio.py, arxiv_cover.py,
    ghep doc cua carousel.py, capture_chart.py. Cong `kiem_xuat_xu` dua vao dau nay
    de phan biet "anh do doi dung ra" voi "anh cat tay bang cong cu ngoai".
    """
    from PIL.PngImagePlugin import PngInfo
    m = PngInfo()
    m.add_text("nguon_dung", str(xuat_xu))
    for k, v in them.items():
        if v is not None:
            m.add_text(str(k), str(v))
    return m


def stamp_file(duong_dan, xuat_xu, **them):
    """Mo lai mot tep PNG DA LUU va ghi dau `nguon_dung` (+ khoa phu) vao do.

    Cho cac cong cu khong luu bang PIL (playwright screenshot, cv2.imwrite,
    tai thang tu URL). Khong phai PNG thi bo qua, tra ve False — dong dau la
    viec phu, khong duoc lam hong buoc chinh.
    """
    q = Path(duong_dan)
    try:
        im = Image.open(q)
        if (im.format or "").upper() != "PNG":
            return False
        im.load()
        im.save(q, "PNG", pnginfo=stamp_provenance(xuat_xu, **them))
        return True
    except Exception:
        return False


def _text(img):
    return (getattr(img, "text", None) or img.info or {})


def read_crop_trace(img):
    """Dau vet crop_ratio.py -> (w_goc, h_goc), hoac None."""
    m = _text(img).get("crop_ti_le")
    if not m:
        return None
    try:
        goc = [k for k in m.split(";") if k.startswith("goc=")][0][4:]
        w, h = goc.lower().split("x")
        return int(w), int(h)
    except Exception:
        return None


def allows_landscape_crop(img):
    """crop_ratio.py co duoc phep cat BE NGANG tam nay khong (co --cat-ngang)?

    Day la mot UY QUYEN da ghi lai luc cat, tuong duong `crop_ok` khai trong
    spec — chi khac la no duoc dong dau ngay tai cho cat nen khong khai lai
    duoc. `check_crop_landscape` (moi module luat) nhan ca hai."""
    return _text(img).get("crop_ti_le", "").find("cat_ngang=1") >= 0


def is_ranking_image(img):
    """Anh do ranking.py dung: bang xep hang chup tu nguon (co khoanh model) hoac
    the du phong. Voi tin xep hang thi DAY LA CHU THE cua tin (Ong Chu 06/09/2026),
    nen no duoc mien hai cong von cam chart len bia/hero."""
    return _text(img).get("nguon_dung") in ("chup_xep_hang", "the_xep_hang")


def is_stacked_composite(img):
    """Anh nay co phai ban GHEP DOC do doi dung ra khong."""
    return _text(img).get("nguon_dung") == "ghep_doc"


# ---- So "anh da dung" — THUAN I/O, dung CHUNG ca ba vai theo thiet ke -------
#
# `state/<brand>/used_images.jsonl` la MOT tep dung chung co y: cung mot tin co
# the giao cho Dre roi Ethan ra HAI draft_id khac nhau (`story_key`), va ca hai
# phai thay duoc anh nhau da dung — tach tep nay theo vai se lam vai nop sau
# khong biet vai truoc da dung anh nao, dung cai bug 06/09/2026 tung xay ra
# (Ethan mat toan bo 5-6 ma Dre da dung, khong nop duoc). Khong co nguong/phan
# doan nao o day — ba module luat (`image_rules_<vai>.py`) tu tinh `dhash`/
# `is_near_duplicate` cua RIENG minh roi ghi/doc qua ba ham nay.
def _used_images_log():
    """state/<brand>/used_images.jsonl — moi dong mot anh da GUI DI (khong phai
    ung vien). Ghi o buoc gui album, doc o buoc nop."""
    import env_load
    import state_paths
    return env_load.state_dir() / state_paths.USED_IMAGES_FILE


def story_key(link: str) -> str:
    """Khoa on dinh cua MOT TIN (khong phai mot draft).

    Cung mot tin giao cho Dre roi giao cho Ethan ra HAI draft_id khac nhau
    (approve_pick._draft_id ghep them vai-brand) nhung van la MOT tin va dung
    CHUNG bo anh engine tai ve. So "anh da dung" khoa theo draft thi vai nop sau
    bi chan sach anh cua vai truoc — do 06/09/2026: Ethan mat toan bo 5-6 ma Dre
    da dung, khong nop duoc the nao."""
    import re as _re
    u = _re.sub(r"^https?://(www\.)?", "", (link or "").strip().lower()).rstrip("/")
    return _re.sub(r"[?#].*$", "", u)


def remove_used_for_draft(draft_id: str) -> int:
    """Go moi dong cua mot draft khoi so "anh da dung". Tra so dong da go.

    So duoc ghi o buoc GUI album, tuc TRUOC khi Ong Chu bam nut. Bam "Bo han
    tin" hay "Lam lai" thi bai chet / album bi thay, anh KHONG bao gio len
    kenh — nhung truoc 06/09/2026 chung van nam trong so va chan moi bai khac
    suot 14 ngay. Voi cac tin cung chu de (cung anh wire Reuters/AP, cung anh
    tru so hang) thi bai sau bi day sang anh kem hon, hoac tac han neu tam bi
    khoa la anh that duy nhat — ma thong bao chan chi noi ten bai va cham, KHONG
    noi bai do da bi bo.
    """
    import json
    so = _used_images_log()
    if not so.exists():
        return 0
    dong = so.read_text(encoding="utf-8").splitlines()
    giu = []
    for d in dong:
        try:
            giu.append(d) if json.loads(d).get("draft_id") != draft_id else None
        except Exception:                                    # noqa: BLE001
            giu.append(d)                                    # dong hong: giu nguyen
    if len(giu) == len(dong):
        return 0
    tmp = so.with_suffix(".jsonl.tmp")
    tmp.write_text(("\n".join(giu) + "\n") if giu else "", encoding="utf-8")
    tmp.replace(so)
    return len(dong) - len(giu)
