#!/usr/bin/env python3
"""bo_fallback_chat.py — bỏ `ds/deepseek-chat` khỏi `fallback_providers` của MỌI
config Hermes (2 gốc + profiles, cả hai brand).

Vì sao (05/09/2026): Ông Chủ đã tắt deepseek-chat trên 9router và combo
DS-v4Flash chỉ còn v4-flash, nhưng 19 config Hermes vẫn giữ:

    fallback_providers:
    - provider: main
      model: ds/deepseek-chat

Đây là chuỗi dự phòng CỦA HERMES, độc lập với combo: combo trả lỗi 2 lần liên
tiếp (route xKiro chết 404) là Hermes tự nhảy sang deepseek-chat, 9router
không can được. Mặc định THAY bằng `ds/deepseek-v4-flash` (route trực tiếp,
cùng model, còn một tuyến khi combo lỗi); `--xoa` thì bỏ hẳn mục đó.

Chỉ đụng mục có model đúng bằng `ds/deepseek-chat`; mục khác (analyst dùng
v4-pro) giữ nguyên. Backup `.bak-truoc-bo-fallback-chat-0905` một lần.

Chạy trên server:
    venv/bin/python bo_fallback_chat.py --thu        # chỉ in
    venv/bin/python bo_fallback_chat.py              # thay bằng ds/deepseek-v4-flash
    venv/bin/python bo_fallback_chat.py --xoa        # bỏ hẳn mục deepseek-chat
Lưu ý: vai chat chỉ nhận config mới sau khi gateway khởi động lại; task kanban
đọc config mỗi lần chạy.
"""
import argparse
import os
import re
import shutil
import sys

try:
    import yaml
except ImportError:                                          # pragma: no cover
    yaml = None

from doi_model_combo import tep_config

CHAT = "ds/deepseek-chat"
BAK = ".bak-truoc-bo-fallback-chat-0905"


def sua(s: str, thay: str | None) -> tuple:
    """Trong khối `fallback_providers:` tìm mục list có `model: ds/deepseek-chat`.
    thay=None → xoá cả mục; thay=<tên> → đổi dòng model."""
    m = re.search(r"^fallback_providers:\n((?:(?:- |  ).*\n)+)", s, re.M)
    if not m:
        return s, "không có fallback_providers"
    khoi = m.group(1)
    # tách thành từng mục: mỗi mục bắt đầu bằng "- "
    muc = re.findall(r"^- .*\n(?:  .*\n)*", khoi, re.M)
    if "".join(muc) != khoi:
        return s, "khối fallback_providers lạ, không đụng"
    ra, trang_thai = [], None
    for x in muc:
        dong = re.search(rf"^(?:- |  )model: {re.escape(CHAT)}\s*$", x, re.M)
        if not dong:
            ra.append(x)
            continue
        if thay is None:
            trang_thai = f"xoá mục {CHAT}"
            continue
        ra.append(x[:dong.start()] + dong.group(0).replace(CHAT, thay) + x[dong.end():])
        trang_thai = f"{CHAT} -> {thay}"
    if trang_thai is None:
        return s, f"không có {CHAT}"
    khoi_moi = "".join(ra)
    if not khoi_moi:                                         # xoá hết → bỏ luôn khoá, tránh `fallback_providers:` rỗng = null
        return s[:m.start()] + s[m.end():], trang_thai + " (bỏ cả khoá)"
    return s[:m.start(1)] + khoi_moi + s[m.end(1):], trang_thai


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--thay", default="ds/deepseek-v4-flash", help="model thay vào; dùng --xoa để bỏ hẳn")
    ap.add_argument("--xoa", action="store_true")
    ap.add_argument("--thu", action="store_true", help="chỉ in, không ghi")
    a = ap.parse_args()
    thay = None if a.xoa else a.thay
    loi = 0
    for f in tep_config():
        s = open(f, encoding="utf-8").read()
        moi, trang_thai = sua(s, thay)
        ok = True
        if yaml is not None and moi != s:
            try:
                fb = (yaml.safe_load(moi) or {}).get("fallback_providers") or []
                ok = all((x or {}).get("model") != CHAT for x in fb) and (thay is None or any((x or {}).get("model") == thay for x in fb))
            except Exception:                                # noqa: BLE001
                ok = False
        if not ok:
            loi += 1
        if not a.thu and moi != s and ok:
            if not os.path.exists(f + BAK):
                shutil.copy2(f, f + BAK)
            open(f, "w", encoding="utf-8").write(moi)
        print(f"{'OK ' if ok else 'LOI'} {trang_thai:44s} {f.replace(os.path.expanduser('~'), '~')}"
              + (" (thử)" if a.thu else ""))
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main())
