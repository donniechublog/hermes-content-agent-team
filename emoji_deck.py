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
import sys
from pathlib import Path

STATE_PATH = Path.home() / "content-team" / "state" / "emoji_deck.json"

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

FLAG_HINTS = ("🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
              "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹",
              "🇺", "🇻", "🇼", "🇽", "🇾", "🇿", "🏳", "🏴", "🎌")


def _load():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"pos": 0, "laps": 0}


def _save(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def next_emoji(count: int) -> list:
    assert all(e[0] not in FLAG_HINTS for e in DECK), "co quoc ky lot vao DECK"
    state = _load()
    out = []
    pos = state["pos"]
    for _ in range(count):
        if pos >= len(DECK):
            pos = 0
            state["laps"] = state.get("laps", 0) + 1
        out.append(DECK[pos])
        pos += 1
    state["pos"] = pos
    _save(state)
    return out


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

    if a.count > len(DECK):
        print("LOI: xin {} emoji nhung bo bai chi co {} — mot bai khong nen "
              "co qua {} doan.".format(a.count, len(DECK), len(DECK)), file=sys.stderr)
        sys.exit(1)
    print(" ".join(next_emoji(a.count)))


if __name__ == "__main__":
    main()
