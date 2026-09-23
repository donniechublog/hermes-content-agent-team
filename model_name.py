#!/usr/bin/env python3
"""Ten model tu BANG XEP HANG: slug -> dang hien thi, de khop hang va de in ra.

Vi sao mot tep rieng (LOW-381, 23/09/2026): hai trang bang lon dat ten KHAC HE
cho CUNG mot model —

    arena.ai            `claude-opus-5-max`, `gpt-6-astra-max`, `qwen3.8-max-0902`
    artificialanalysis  `Claude Opus 5.5 (max with fallback)`, `GPT-6 Astra`

Tieu de tin lay tu trang nao thi mang ten he do. Bai 23/09 lay tu AA nhung tieu
de viet dang slug (`claude-opus-5-5-max-effort`): `ranking.extract_model` rut gon
ten theo TU cach nhau bang dau cach, ma slug la MOT tu, nen danh sach ung vien
chi co dung mot cai va khong bang nao khop -> tin ra THE CHU thay vi anh bang.

Do 23/09 tren may chu: khop tho thay 1/20 ten trung giua hai phia; qua phep quy
ve o day la 16/20. `scan_models` (LOW-383) dung chung tep nay de biet mot model
da quet duoc ben arena hay chua.

Tep nay KHONG import gi cua du an — thuan, test duoc bang so, khong can mang.
"""
import re

# Hau to MUC NO LUC / che do chay, khong phai mot phan cua ten model. Bang in
# chung trong ngoac ("(max with fallback)", "(xhigh)") hoac dinh vao slug
# ("-max-effort", "-high").
#
# `max` cung la mot phan ten THAT cua vai model (Qwen3-Max). Khong sao: ham nay
# sinh ten NGAN HON de thu them, con ban dai nhat van duoc thu truoc — xem
# `ranking.extract_model` (dai truoc, ngan sau).
EFFORT = {"max", "xhigh", "high", "medium", "low", "minimal", "effort"}

_PAREN = re.compile(r"\s*\([^)]*\)")
_SEP = re.compile(r"[-_]+")
_DATE = re.compile(r"^\d{4}$")          # duoi ngay cua arena: `qwen3.8-max-0902`
# Chu viet tat luon in HOA — `.capitalize()` cua Python ra "Gpt", "Glm".
_UPPER = {"gpt", "glm", "llm", "ai", "tts", "stt", "bfcl"}


def _merge_version(tokens: list) -> list:
    """['claude','opus','5','5'] -> ['claude','opus','5.5'].

    Slug tach phien ban bang gach noi (`claude-opus-5-5`), con bang in dau cham
    (`Claude Opus 5.5`). Chi noi hai nhom CHU SO lien nhau va ngan (<=2 chu so)
    de khong nuot duoi ngay hay so tham so."""
    out = []
    for t in tokens:
        if (out and t.isdigit() and len(t) <= 2
                and re.fullmatch(r"\d{1,2}(\.\d{1,2})*", out[-1])):
            out[-1] = f"{out[-1]}.{t}"
        else:
            out.append(t)
    return out


def _case(t: str) -> str:
    if any(c.isdigit() for c in t):      # "qwen3.8", "5.5", "v2.6"
        return t
    if t.lower() in _UPPER:
        return t.upper()
    return t[:1].upper() + t[1:] if t.islower() else t


def display_name(name: str) -> str:
    """'claude-opus-5-5-max-effort' -> 'Claude Opus 5.5'; 'GPT-6 Astra (high)' -> 'GPT-6 Astra'.

    Ten da o dang hien thi thi chi bo phan trong ngoac va hau to muc no luc —
    KHONG doi hoa/thuong cua no, vi do la ten hang tu viet."""
    t = _PAREN.sub(" ", str(name or "")).strip()
    t = re.sub(r"\s+", " ", t)
    if not t:
        return ""
    # Slug = mot tu, co gach noi, TOAN CHU THUONG (arena.ai viet vay:
    # `claude-opus-5-max`). Ten hien thi thi hoac co dau cach ("GPT-6 Astra"),
    # hoac co chu hoa ("Kimi-K3", "MiMo-V2.6-Pro") — o do gach noi la MOT PHAN
    # cua ten, be ra la bia mot ten khac.
    slug = " " not in t and "-" in t and t == t.lower()
    tokens = _SEP.split(t) if slug else t.split()
    while len(tokens) > 1 and (tokens[-1].lower() in EFFORT or _DATE.match(tokens[-1])):
        tokens.pop()
    if slug:
        tokens = [_case(x) for x in _merge_version(tokens)]
    return " ".join(tokens)


def key(name: str) -> str:
    """Khoa de so ten giua HAI nha cung cap: 'claude-opus-5-5-max' va
    'Claude Opus 5.5 (max with fallback)' ra cung mot khoa.

    `display_name` con giu gach noi trong ten co chu hoa (`GLM-5.3`) vi do la
    cach hang viet; so ten thi phai bo het dau tach di. Cung phep chuan hoa voi
    `norm` trong `ranking._JS_NORM`, co y: hai cho deu dang tra loi cau "hai ten
    nay co phai mot model khong".

    Chu so KHONG bi nuot: 'claude opus 5' -> 'claudeopus5' khac
    'claude opus 5.5' -> 'claudeopus55'.
    """
    return re.sub(r"[\s\-_–—.]+", "", display_name(name).lower())
