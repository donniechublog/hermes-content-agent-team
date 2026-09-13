#!/usr/bin/env python3
"""gen.py — sinh lại TU_DIEN_TEN_v0.md từ 5 tệp JSON bên cạnh + repo. KHÔNG đụng
mã nguồn, chỉ đọc + in ra .md. Logic tách tên/quét repo nằm ở `tudien.py` —
`rename.py` (thực thi) dùng đúng cùng một bộ, nên bảng in ra = cái sẽ đổi.

Dùng:
    cd docs/tu_dien_ten
    python3 gen.py .                      # quét repo chứa thư mục này
    python3 gen.py . /duong/dan/repo-khac # quét một checkout khác

Tiêu chí (Ông Chủ 12/09/2026): "ngữ nghĩa là gì không quan trọng, thích gán nó
là gì cũng được, không bị lẫn lộn hàm là được" — chỉ cấm HAI HÀM/LỚP top-level
cùng module trùng tên sau dịch (mục F). Thoát mã 1 khi còn va chạm.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tudien import TuDien, quet, va_cham, va_cham_module     # noqa: E402

S = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent).resolve()
ROOT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else S.parent.parent

td = TuDien(S)
mods, defs, consts, top, where, _files = quet(ROOT)
unmapped = collections.Counter()


def _cờ(fl):
    return ("⚠️ " + " ".join(sorted(fl))) if fl else ""


def _ghi_thieu(en: str):
    for p in en.split("_"):
        if p.startswith("?"):
            unmapped[p[1:].lower()] += 1


L = [
    "# TỪ ĐIỂN TÊN — v0 (chưa đụng mã)", "",
    f"Sinh tự động bởi `gen.py` từ repo hiện tại: {len(mods)} module, {len(defs)} def/class "
    f"({len({d[1] for d in defs})} tên khác nhau), {len(consts)} hằng số. "
    "`?token` = chưa có trong bảng; ⚠️ = token mơ hồ, phải chọn tay theo nghĩa tại chỗ.", "",
    "**Tiêu chí (Ông Chủ 12/09/2026):** nghĩa dịch không cần đúng từng chữ — chỉ cần "
    "KHÔNG hai hàm/lớp top-level nào trong cùng module trùng tên sau khi dịch. Xem mục F.", "",
    "Luật: rename 1-1 giữ cấu trúc cụm; khoá JSON trên đĩa KHÔNG đổi; tên vai "
    "(ethan/dre/kite…) giữ nguyên; token đã là English giữ nguyên. Sửa `cum.json` / "
    "`don.json` / `moho.json` / `them.json` / `overrides.json` rồi chạy lại "
    "`python3 gen.py .` để bảng dưới cập nhật.",
    "", "## A. Từ gốc — CỤM (khớp trước)", "", "| Việt | English |", "|---|---|",
]
L += [f"| `{k}` | `{v}` |" for k, v in sorted(td.cum.items()) if "_" in k]
L += ["", "## A2. Từ gốc — TỪ ĐƠN", "", "| Việt | English | Mơ hồ |", "|---|---|---|"]
L += [f"| `{k}` | `{v}` | {('⚠️ ' + td.moho[k]) if k in td.moho else ''} |" for k, v in sorted(td.don.items())]
L += ["", "## B. Module", "", "| Hiện tại | Đề xuất | Cờ |", "|---|---|---|"]
for m in mods:
    en, fl = td.dich_module(m)
    L.append(f"| `{m}` | `{en}` | {_cờ(fl)} |")
L += ["", "## C. Hàm/lớp theo module", ""]
by = collections.defaultdict(list)
for mod, name, kind, ln in defs:
    by[mod].append((name, kind, ln))
for mod in mods:
    if not by.get(mod):
        continue
    L += [f"### `{mod}`", "", "| Hiện tại | Đề xuất | Cờ |", "|---|---|---|"]
    seen = set()
    for name, kind, ln in sorted(by[mod], key=lambda x: x[2]):
        if name in seen or name.startswith("__") or name == "main":
            continue
        seen.add(name)
        en, fl = td.dich_ten(mod, name, kind)
        _ghi_thieu(en)
        L.append(f"| `{name}` | `{en}` | {_cờ(fl)} |")
    L.append("")
L += ["## D. Hằng số module", "", "| Module | Hiện tại | Đề xuất | Cờ |", "|---|---|---|---|"]
for mod, c in sorted(consts):
    en, fl = td.dich_ten(mod, c, "const")
    _ghi_thieu(en)
    L.append(f"| `{mod}` | `{c}` | `{en}` | {_cờ(fl)} |")
L += ["", "## E. Token chưa có trong bảng", "", "| token | lần | ví dụ module |", "|---|---|---|"]
for t, n in unmapped.most_common():
    L.append(f"| `{t}` | {n} | {', '.join(sorted(where.get(t, []))[:3])} |")

vc = va_cham(td, top)
L += ["", "## F. Va chạm tên — PHẢI SỬA trước khi rename", "",
      "Hai hàm/lớp top-level khác nhau trong CÙNG module mà dịch ra CÙNG một tên "
      "— rename thẳng sẽ ghi đè, gây lỗi gọi thật. Sửa bằng `overrides.json` "
      "(`\"module.ten_goc\": \"ten_moi\"`), không cần đụng bảng từ điển chung.", ""]
if vc:
    L += ["| Module | Tên đề xuất trùng | Các hàm gốc bị trùng |", "|---|---|---|"]
    for mod, dup in vc.items():
        for en, origs in dup.items():
            L.append(f"| `{mod}` | `{en}` | {', '.join(f'`{o}`' for o in origs)} |")
else:
    L.append(f"**Không còn va chạm nào** — đo trên {len(mods)} module / "
             f"{sum(len(v) for v in top.values())} hàm-lớp top-level.")

vcm = va_cham_module(td, ROOT, mods)
L += ["", "## F2. Tên module mới đè lên tên đã dùng — PHẢI SỬA trước khi đổi tên tệp", "",
      "Tên tệp mới trùng một biến/tham số/def/alias đang có ở tệp khác (kể cả tests): "
      "sau rename tên đó SHADOW module → `UnboundLocalError`/pyflakes đỏ. Sửa: đổi tên "
      "module trong `cum.json` (khoá = tên tệp cũ), hoặc đổi biến cục bộ đó.", ""]
if vcm:
    L += ["| Tên mới | Module cũ | Trùng ở | Loại |", "|---|---|---|---|"]
    for ten, ds in sorted(vcm.items()):
        for rel, ln, loai, goc in ds[:12]:
            L.append(f"| `{ten}` | `{goc}` | `{rel}:{ln}` | {loai} |")
        if len(ds) > 12:
            L.append(f"| `{ten}` | | … +{len(ds) - 12} chỗ nữa | |")
else:
    L.append("**Không có.**")

out = S / "TU_DIEN_TEN_v0.md"
out.write_text("\n".join(L), encoding="utf-8")
so_vc = sum(len(v) for v in vc.values())
so_vcm = sum(len(v) for v in vcm.values())
print(f"đã ghi {out} — {len(L)} dòng, {len(unmapped)} token chưa map ({sum(unmapped.values())} lượt), "
      f"{so_vc} va chạm tên trong {len(vc)} module, {so_vcm} chỗ tên module mới bị shadow ({len(vcm)} tên)")
if so_vc or so_vcm:
    sys.exit(1)
