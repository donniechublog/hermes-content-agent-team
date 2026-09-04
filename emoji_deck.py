#!/usr/bin/env python3
"""Bo xoay vong emoji cho teaser — khong lap lai cho toi khi het mot vong.

Trang thai ben (state/emoji_deck.json) luu vi tri con tro. Moi lan goi
`next N` lay ra N emoji ke tiep trong bo bai, khong trung nhau, va TIEP TUC
tu cho da dung lan truoc — nghia la khong trung giua cac doan van trong
cung mot bai, VA khong trung giua bai nay voi bai sau, cho toi khi di het
ca bo moi quay vong.

Khong co emoji quoc ky nao trong bo bai (chi loai co quoc gia; co bao quat
chung nhu cham do, la co checkered van giu vi khong dai dien quoc gia nao).
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

try:
    import fcntl                 # POSIX (server) — khoa tep that
except ImportError:              # Windows (test local): khong co fcntl,
    fcntl = None                 # chay khong khoa — mot nguoi thao tac, chap nhan

import env_load

# Per-brand qua env_load.state_dir(), va theo vi tri ma nguon — truoc day
# hardcode ~/content-team/state: chay o may khac la lang le tao state sai cho.
STATE_PATH = env_load.state_dir() / "emoji_deck.json"

DECK = [
    "🔥", "✨", "🚀", "💡", "🎯", "🧠", "⚡", "🌱", "🔍", "📌",
    "🛠️", "🧩", "📊", "🔑", "🌟", "🧭", "🪄", "🎨", "🧵", "🔗",
    "📈", "🧱", "🔬", "🗺️", "🧰", "🪞", "🌊", "🔮", "🧪", "🎬",
    "📚", "🕹️", "🧊", "🌉", "🎲", "🧨", "🎁", "🧗", "🌀", "🪝",
    "🔦", "🧬", "🛰️", "🎛️", "🧷", "🥇", "🎼", "🧑‍🍳", "🖇️", "🪟",
    "🌈", "🧗‍♀️", "🎢", "🪁", "🔧", "🧫", "🎣", "🧮", "🕸️", "🌋",
    "🪴", "🧱", "🔩", "🎻", "🧯", "🌵", "🪃", "🧿", "🎏", "🧑‍🚀",
    "🪐", "🌌", "🧑‍🔬", "🎙️", "📡", "🪛", "🧑‍💻", "🖥️", "⌨️", "🖱️",
    "💾", "📀", "🧲", "🔋", "🪫", "🧵", "🪡", "🧶", "🪢", "🧸",
    "🎯", "🎪", "🎭", "🖼️", "🎞️", "📽️", "🎥", "📷", "📸", "🕯️",
    "🪔", "🏮", "🎐", "🧨", "✏️", "🖊️", "🖋️", "📝", "📋", "📎",
    "📐", "📏", "✂️", "🗂️", "🗃️", "🗄️", "🧾", "🧮", "🔭", "🔬",
    "🧫", "🧪", "🩺", "💊", "🚦", "🚧", "🧱", "🏗️", "🏭", "🏛️",
    "🗼", "🗽", "⛩️", "🕌", "🛤️", "🚂", "🚁", "🛶", "⛵", "🚤",
    "🛥️", "🚢", "✈️", "🛩️", "🚀", "🛸", "🪂", "🎈", "🪅", "🪆",
]

# Bo bai phai KHONG co phan tu trung, neu khong loi hua "khong lap lai cho toi
# khi het mot vong" bi vo: hai ban sao cach nhau 40 vi tri nghia la sau khoang
# sau bai teaser da gap lai cung mot emoji, thay vi sau ca vong 150.
# Loc ngay tai day thay vi sua tay danh sach — them emoji moi bi trung ve sau
# cung tu dong duoc loai.
DECK = list(dict.fromkeys(DECK))

# Loi hua trong docstring "khong co quoc ky" duoc THI HANH tai day, khong chi
# bang mat thuong: emoji them sau ma dinh ky tu regional-indicator / co se tu
# dong bi loai.
FLAG_HINTS = ("🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
              "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹",
              "🇺", "🇻", "🇼", "🇽", "🇾", "🇿", "🏳", "🏴", "🎌")
DECK = [e for e in DECK if not any(h in e for h in FLAG_HINTS)]


def _load():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"pos": 0, "laps": 0}


def _save(state):
    """Ghi nguyen tu: viet ra tep tam cung thu muc roi doi ten de len.

    write_text truc tiep co the de lai tep rong neu tien trinh chet giua chung,
    va con tro bi mat thi ca bo bai quay ve dau — moi bai sau do lai bat dau
    tu cung mot emoji.
    """
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tam = tempfile.mkstemp(dir=str(STATE_PATH.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tam, STATE_PATH)
    except BaseException:
        Path(tam).unlink(missing_ok=True)
        raise


def next_emoji(count: int) -> list:
    """Lay `count` emoji ke tiep, khong trung nhau, tiep tu lan goi truoc.

    Doc-sua-ghi duoi mot khoa tep: hai tien trinh cung goi (vi du hai task
    kanban chay song song) neu khong khoa se cung doc mot `pos`, cung lay mot
    day emoji, roi ghi de len nhau — hai bai khac nhau ra emoji y het.
    """
    if not DECK:
        raise ValueError("Bo bai rong")
    if count < 1:
        raise ValueError(f"Xin {count} emoji — phai it nhat 1")
    # Chan o TRONG ham, khong chi o CLI: teaser_assemble goi thang ham nay,
    # neu khong chan thi mot bai qua dai se lang le nhan emoji trung.
    if count > len(DECK):
        raise ValueError(
            f"Xin {count} emoji nhung bo bai chi co {len(DECK)} — "
            f"mot bai khong nen co qua {len(DECK)} doan.")

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    khoa = STATE_PATH.with_suffix(".lock")
    with open(khoa, "w") as lf:
        if fcntl:
            fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            state = _load()
            out = []
            pos = state.get("pos", 0)
            if pos < 0 or pos > len(DECK):       # trang thai cu / bo bai da doi kich thuoc
                pos = 0
            for _ in range(count):
                if pos >= len(DECK):
                    pos = 0
                    state["laps"] = state.get("laps", 0) + 1
                out.append(DECK[pos])
                pos += 1
            state["pos"] = pos
            _save(state)
            return out
        finally:
            if fcntl:
                fcntl.flock(lf, fcntl.LOCK_UN)


def main():
    ap = argparse.ArgumentParser(description="Lay N emoji ke tiep, khong trung, tu bo xoay vong")
    ap.add_argument("cmd", choices=["next", "peek", "reset"])
    ap.add_argument("count", nargs="?", type=int, default=1)
    a = ap.parse_args()

    if a.cmd == "reset":
        _save({"pos": 0, "laps": 0})
        print("da reset ve dau bo bai")
        return
    if a.cmd == "peek":
        state = _load()
        print("vi tri hien tai: {} / {} (da quay {} vong)".format(
            state["pos"], len(DECK), state.get("laps", 0)))
        return

    try:
        print(" ".join(next_emoji(a.count)))
    except ValueError as e:
        print(f"LOI: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
