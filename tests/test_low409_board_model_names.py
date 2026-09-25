#!/usr/bin/env python3
"""LOW-409 (25/09/2026) — tin leo hang bang Tao anh / Tao video cua arena phai
tach duoc ten model, de engine chup va khoanh dung hang tren arena.ai.

Hai bai that Ethan dung (blocked) cung ngay:
  "Reve-2.1 leo một bậc tiến sát top đầu với vị trí thứ năm Bảng Tạo ảnh Arena"
  "Dreamina Seedance 2.0 720p tăng một bậc vươn lên vị trí thứ tư bảng Tạo video"
`extract_model` ra [] cho ca hai vi `_HO` chi co ho model van ban -> khong chup
bang nao -> khong co anh XH -> ethan_submit chan toan bo A1-A31. Ca hai model
nam ngay tren bang arena.ai (`reve-2.1` #5 text-to-image, `dreamina-seedance-
2.0-720p` #5 text-to-video, doc 25/09).

Chay:  python tests/test_low409_board_model_names.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import env_load  # noqa: E402
import ranking  # noqa: E402
import state_paths  # noqa: E402

REVE = "Reve-2.1 leo một bậc tiến sát top đầu với vị trí thứ năm Bảng Tạo ảnh Arena"
SEEDANCE = "Dreamina Seedance 2.0 720p tăng một bậc vươn lên vị trí thứ tư bảng Tạo video"

# Ten THAT doc tu arena.ai 25/09/2026 (mot phan top 40 moi bang).
BOARDS = {
    "image": {"gpt-image-2.5-sunburst": 1, "gpt-image-2 (medium)": 3, "mai-image-2.6": 4,
              "reve-2.1": 5, "reve-2.0": 8, "muse-image": 7, "seedream-5.0-pro": 10,
              "gemini-3.1-flash-image (nano-banana-2) [web-search]": 9, "flux-2-max": 27},
    "video": {"gemini-omni-flash": 2, "flux-3-video": 3, "dreamina-seedance-2.0-720p": 5,
              "dreamina-seedance-2.5-720p": 7, "wan3.0": 6, "veo-3.1-audio": 12, "sora-2": 17},
    "text": {"gpt-5.5": 28, "gpt-5.5-high": 20, "claude-opus-5-max": 14, "muse-spark": 13,
             "muse-spark-1.3-max": 8},
}
NAMES = sorted({n for rows in BOARDS.values() for n in rows})


def test_reve_title_finds_its_board_row():
    names = ranking.extract_model(REVE, known_names=NAMES)
    assert names and names[0] == "reve-2.1", f"ra {names}"
    assert "reve-2.0" not in names, "khong duoc truot sang hang reve-2.0"


def test_seedance_title_keeps_the_full_variant():
    names = ranking.extract_model(SEEDANCE, known_names=NAMES)
    assert names and names[0] == "dreamina-seedance-2.0-720p", f"ra {names}"
    # Khong rut gon: "Dreamina Seedance" khoanh trung ca hang 2.5-720p.
    assert all("2.0" in n or "2 0" in n for n in names), f"co ten bi rut gon: {names}"


def test_old_code_had_no_name_for_either_title():
    """Dung dieu ticket bao: khong co ten bang thi van [] nhu truoc — vi vay test
    tren fail o code cu (extract_model khong nhan known_names)."""
    assert ranking.extract_model(REVE, known_names=[]) == []
    assert ranking.extract_model(SEEDANCE, known_names=[]) == []


def test_token_match_does_not_eat_a_longer_version():
    """Khop theo token, khong theo chuoi con: ten ngan `gpt-5` khong duoc an vao
    "GPT-5.5"."""
    pos, name = ranking._board_name_in_title("GPT-5.5 vượt mặt", ["gpt-5"])
    assert name is None, "gpt-5 khop nham GPT-5.5"
    pos, name = ranking._board_name_in_title("muse leo hạng", ["muse"])
    assert name is None, "ten mot tu khong so trung tu thuong"


def test_qualifier_in_brackets_is_optional():
    pos, name = ranking._board_name_in_title(
        "Gemini 3.1 Flash Image lên #9 bảng Tạo ảnh", NAMES)
    assert name == "gemini-3.1-flash-image (nano-banana-2) [web-search]"
    assert pos == 0


def test_text_models_keep_their_old_result():
    """Regex bat tu dau tieu de thi giu nguyen — khong doi ket qua cho model van ban."""
    for title in ("GPT-6 Astra (max) 55 điểm dẫn đầu", "Claude Fable 5.1 lên #1 Text Arena",
                  "Kimi-K3 leo lên #1", "Muse Spark 1.3 vào top 10 Arena"):
        assert ranking.extract_model(title, known_names=NAMES) == \
            ranking.extract_model(title, known_names=[]), title


def test_subject_is_the_first_model_named():
    """Tieu de nhac hai model: chu the la ten dung truoc. Truoc LOW-409 regex bo qua
    "reve-2.1" va bat "GPT Image 2" dung sau -> khoanh hang cua model khac."""
    names = ranking.extract_model("Reve-2.1 áp sát GPT Image 2 trên bảng Tạo ảnh", known_names=NAMES)
    assert names[0] == "reve-2.1", f"ra {names}"


def test_default_names_come_from_nova_state():
    """Khong truyen known_names -> doc `models_seen.json` cua Nova (brand hien tai)."""
    saved = {k: os.environ.get(k) for k in ("CT_STATE_DIR",)}
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CT_STATE_DIR"] = tmp
        try:
            assert ranking.extract_model(REVE) == [], "chua co tep -> nhu cu"
            path = env_load.state_dir() / state_paths.MODELS_SEEN_FILE
            path.write_text(json.dumps({"ids": ["x"], "rankings": BOARDS}), encoding="utf-8")
            assert ranking.extract_model(REVE)[0] == "reve-2.1"
            assert ranking.extract_model(SEEDANCE)[0] == "dreamina-seedance-2.0-720p"
            path.write_text("{hong", encoding="utf-8")
            assert ranking.board_names() == [], "tep hong khong duoc lam chet engine"
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
