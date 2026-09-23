"""Vung an toan cua khung 4:5 khi bi cat vuong 1:1 luc dang (LOW-364).

Ong Chu 22/09/2026, bai dcgr Grok 4.7 (the Ethan 1200x1500, dung 4:5) len Instagram/Threads
van bi cat: *"lý do đã làm hình ratio 4:5 nhưng đăng ig vẫn bị crop"*. Do tren tep that: bai
dang khop dung phep cat VUONG GIUA — mat 150px tren (hang tieu de bang + hang 1-2) va 150px
duoi (dong tua cuoi + name kenh). Khau dang (moat, team khac) co the de mac dinh 1:1. Ong Chu
chot: *"đưa những thứ quan trọng nhất vào safezone, như vậy ko còn lệ thuộc vào hình lúc
publish nữa"*.

Luat: moi thu QUAN TRONG (khung chu, tua/hook/quote, chip label, dong nguon quote, dinh anh
chup trang) nam trong O VUONG GIUA [band, H - band], band = (H - W) / 2, cong them
SAFE_PAD. Dai cat tren/duoi chi chua thu phu: nen, phan anh keo dai, name kenh.

Khong phu thuoc renderer nao: ca `card.py` (Ethan), `carousel.py` (Dre) cung goi day.
"""

SAFE_PAD = 12          # px ho giua noi dung va mep cat — chu khong cham sat mep sau khi cat


def band(w: int, h: int) -> int:
    """Chieu cao dai bi cat MOI DAU khi cat khung w x h ve vuong giua (4:5 -> 10% chieu cao)."""
    return max(0, (h - w) // 2)


def top(w: int, h: int) -> int:
    """y nho nhat noi dung quan trong duoc cham toi."""
    return band(w, h) + SAFE_PAD


def bottom(w: int, h: int) -> int:
    """y lon nhat noi dung quan trong duoc cham toi."""
    return h - band(w, h) - SAFE_PAD


def violations(boxes: dict, w: int, h: int) -> list:
    """`boxes`: {name: (y0, y1)} cua noi dung quan trong. Tra ve danh sach errors (rong = dat)."""
    lo, hi = top(w, h), bottom(w, h)
    errors = []
    for name, (y0, y1) in boxes.items():
        if y0 < lo or y1 > hi:
            errors.append(f"{name} y={int(y0)}..{int(y1)} ra ngoai vung an toan {lo}..{hi}")
    return errors


def gate(label: str, boxes: dict, w: int, h: int) -> None:
    """Cong chan (LOW-364): noi dung quan trong lot ra dai bi cat 1:1 thi DUNG — errors code bo
    cuc, khong phai errors spec (cau qua dai thi cac cong co chu da ha co truoc day roi)."""
    errors = violations(boxes, w, h)
    if errors:
        raise SystemExit(f"[LOW-364] {label}: " + "; ".join(errors)
                         + " — bi cat mat khi dang 1:1 (Instagram/Threads)")
