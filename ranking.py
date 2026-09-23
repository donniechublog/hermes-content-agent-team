#!/usr/bin/env python3
"""ranking.py — ẢNH CHO TIN XẾP HẠNG: chụp bảng xếp hạng thật, khoanh đúng model.

Luật Ông Chủ 06/09/2026: tin về thứ hạng thì ảnh phải là bảng/chart xếp hạng —
không có sẵn thì tự chụp màn hình, chụp phải khoanh đúng model đang nói tới,
không chụp được thì thẻ dữ liệu (tên model + #hạng + logo + site).

Vì sao là tệp riêng: engine chung chỉ chụp figure/table trên trang BÀI BÁO, còn
bảng xếp hạng nằm ở TRANG XẾP HẠNG và phải khoanh đúng hàng. Không có nó, ba thẻ
liền nhau (04–06/09) đã lấy bảng tỉ số giải golf và bảng câu cá trên băng vì
khớp chữ "leaderboard".

Dùng tay:
    venv/bin/python ranking.py --tieu-de "Kimi-K3 leo lên #1 Frontend Code Arena" --ra kimi.png
    venv/bin/python ranking.py --model "Claude Opus 4.6" --nguon arena-text --ra x.png
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import image_provenance                                           # noqa: E402
import env_load                                              # noqa: E402
import manifest_values                                       # noqa: E402
import model_name                                            # noqa: E402
import role                                                  # noqa: E402
import state_paths                                           # noqa: E402

DPR = 2
UA = env_load.UA_BROWSER        # mot ban duy nhat, xem env_load (A5)
# Khung MOBILE — thu TRUOC cho MOI nguon. Hang so nam o `browser_session` (dung
# chung voi capture_page.py tu 12/09/2026); o day chi giu PHEP DO rieng cua trang
# xep hang. Do 06/09: 12/18 nguon co layout mobile that (arena x6, aa-models,
# livebench, aider, livecodebench, hle, vellum); 6 nguon con lai (tbench,
# swebench, bfcl, gaia, opencompass, openrouter) giu bang rong 892-1878px trong
# khung cuon ngang nen tu dong lui ve desktop.
from browser_session import (MOBILE_DPR, MOBILE_UA,            # noqa: E402
                           MOBILE_VIEWPORT, got_block)
GOLD = (245, 197, 24)          # màu khoanh — cùng gam với đồ hoạ tham chiếu của arena.ai
TOP_DEFAULT = 10              # ít nhất top-N khi model nằm trong top
ON_MODEL = 2                 # model nằm sâu: giữ 2 hàng phía trên, kéo dài xuống dưới
HEIGHT_MAX_CSS = 1500          # trần chiều cao cửa sổ chụp (CSS px)
TIME_LIMIT = 150                  # trần thời gian đi hết các nguồn (giây)
# Anh coi la VUA KHO khi rong/cao <= muc nay. Cong hero chan o 1.6 (kiem_anh_thap:
# anh di mot minh phai chiem >=50% kho 4:5), de 1.5 cho co bien.
RATIO_FIT = 1.5

# ---- Registry nguồn xếp hạng --------------------------------------------------
# Thu tu trong danh sach = uu tien khi tin khong goi y gi; `suggest_sources` chi xep
# lai thu tu nay, khong them nguon la.
SOURCE: list[dict] = [
    {"id": "arena-text",     "site": "ARENA.AI",  "board": "Text Arena",
     "url": "https://arena.ai/leaderboard/text",          "domain_pattern": r"arena\.ai|lmarena",
     "board_pattern": r"\btext\b(?![- ]?to[- ]?)|văn bản|van ban|\bchat\b"},
    {"id": "arena-code",     "site": "ARENA.AI",  "board": "WebDev / Code Arena",
     "url": "https://arena.ai/leaderboard/code",          "domain_pattern": r"arena\.ai|lmarena",
     "board_pattern": r"\bcode\b|webdev|frontend|front-end|lập trình|lap trinh"},
    {"id": "arena-vision",   "site": "ARENA.AI",  "board": "Vision Arena",
     "url": "https://arena.ai/leaderboard/vision",        "domain_pattern": r"arena\.ai|lmarena",
     "board_pattern": r"\bvision\b|thị giác|thi giac"},
    # `independent` (09/09/2026): bang nay do NANG LUC RIENG, khong phai mot cach do
    # khac cua cung mot thu — model tao anh gioi va model sua anh gioi la HAI
    # bang xep hang khac han (Ong Chu: "một bảng là top model tạo sinh, một bảng
    # là top model chỉnh sửa, đâu có trùng lặp"). `find_and_capture_many` doc co nay
    # de KHONG dung lai sau khi da chup duoc mot bang `independent` khac — khac voi vi
    # du arena-code/swebench/aider/livecodebench duoi day: bon cai do la BON CACH
    # DO CUNG MOT NANG LUC (code), chup mot cai la du, chup them chi lap lai.
    {"id": "arena-t2i",      "site": "ARENA.AI",  "board": "Text-to-Image Arena",
     "url": "https://arena.ai/leaderboard/text-to-image", "domain_pattern": r"arena\.ai|lmarena",
     "board_pattern": r"text[- ]?to[- ]?image|tạo ảnh|tao anh|\bt2i\b",
     "independent": True},
    # Them 09/09/2026: bang RIENG voi text-to-image, do het truoc do — tin GPT
    # Image 2.5 #1&#2 Image Edit Arena khong co duong nao chup duoc (Ong Chu
    # gui anh chup 2 bang, hoi sao khong dua vao duoc). Da doc thu URL
    # (arena.ai/leaderboard/image-edit) truoc khi them, dung 55 model nhu chup.
    {"id": "arena-image-edit", "site": "ARENA.AI", "board": "Image Edit Arena",
     "url": "https://arena.ai/leaderboard/image-edit", "domain_pattern": r"arena\.ai|lmarena",
     "board_pattern": r"image[- ]?edit|sửa ảnh|sua anh|chỉnh sửa ảnh",
     "independent": True},
    # Them 09/09/2026 cung dot: tweet cong bo cua chinh @arena (status
    # 2097400515546255754) dan lai DUNG bang thu ba nay — "sua NHIEU anh cung
    # luc" khac han "sua MOT anh" (arena-image-edit), nen cung la nang luc rieng.
    # URL doc thang tu chu thich nguon in duoi tam anh trong tweet
    # ("ARENA.AI/LEADERBOARD/IMAGE-EDIT/MULTI-IMAGE-EDIT"), xac nhan lai bang
    # WebFetch: 42 model, gpt-image-2.5-sunburst #1 diem 1535 — khop anh.
    {"id": "arena-multi-image-edit", "site": "ARENA.AI", "board": "Multi-Image Edit Arena",
     "url": "https://arena.ai/leaderboard/image-edit/multi-image-edit", "domain_pattern": r"arena\.ai|lmarena",
     "board_pattern": r"multi[- ]?image|nhiều ảnh|nhieu anh",
     "independent": True},
    {"id": "arena-t2v",      "site": "ARENA.AI",  "board": "Text-to-Video Arena",
     "url": "https://arena.ai/leaderboard/text-to-video", "domain_pattern": r"arena\.ai|lmarena",
     "board_pattern": r"\bvideo\b|tạo video|tao video"},
    {"id": "arena-search",   "site": "ARENA.AI",  "board": "Search Arena",
     "url": "https://arena.ai/leaderboard/search",        "domain_pattern": r"arena\.ai|lmarena",
     "board_pattern": r"\bsearch\b|tìm kiếm|tim kiem"},
    {"id": "aa-models",      "site": "ARTIFICIALANALYSIS.AI", "board": "Intelligence Index",
     "url": "https://artificialanalysis.ai/leaderboards/models", "domain_pattern": r"artificialanalysis"},
    # mobile KHONG dung duoc (do 06/09/2026): bang rong 892px trong khung cuon ngang, khung 414 mat cot.
    {"id": "tbench",         "site": "TBENCH.AI", "board": "Terminal-Bench",
     "url": "https://www.tbench.ai/leaderboard",          "domain_pattern": r"tbench|terminal[-_ ]?bench",
     "viewport": "desktop"},
    # mobile KHONG dung duoc (do 06/09/2026): bang rong 990px trong khung cuon ngang, khung 414 mat cot.
    {"id": "swebench",       "site": "SWEBENCH.COM", "board": "SWE-bench",
     "url": "https://www.swebench.com/",                  "domain_pattern": r"swebench|swe[-_ ]?bench",
     "viewport": "desktop"},
    # mobile KHONG dung duoc (do 06/09/2026): khung hep chi bat duoc bieu do CHI PHI
    # chu khong phai bang xep hang, ten model lai bi cat cut ("Claude 4.7 Opu...").
    {"id": "livebench",      "site": "LIVEBENCH.AI", "board": "LiveBench",
     "url": "https://livebench.ai/",                      "domain_pattern": r"livebench",
     "viewport": "desktop"},
    {"id": "aider",          "site": "AIDER.CHAT", "board": "Aider Polyglot",
     "url": "https://aider.chat/docs/leaderboards/",      "domain_pattern": r"aider"},
    # Ông Chủ 06/09/2026: "phải sử dụng hình ảnh từ tất cả trang này, đừng tự giới
    # hạn nguồn ảnh". Bảy mục dưới đây đều ĐO THẬT (chụp ra ảnh có khoanh model)
    # trước khi thêm — không thêm nguồn chưa chụp được, vì mỗi nguồn hỏng ngốn
    # ~18s của trần 150s mà không bao giờ ra ảnh.
    # ĐÃ THỬ, CHƯA ĐƯỢC, nên KHÔNG có trong danh sách:
    #   bigcode-bench.github.io — có bảng 171 hàng nhưng hàng nằm dưới đáy khung
    #     nhìn mà `scrollIntoView` không kéo trang lên (khung cuộn lạ).
    #   designarena.ai / scale.com/leaderboard / vals.ai — không có <table> lẫn
    #     nhóm hàng lặp nào nhận ra được; mỗi trang cần một bộ bóc riêng.
    #   epoch.ai — bảng vẽ bằng <canvas>, không định vị được hàng để khoanh.
    #   mteb (HF Space) — benchmark embedding, không phải xếp hạng model kiểu tin.
    # openrouter khong render bang xep hang nao o khung <900px -> luon lui ve desktop.
    {"id": "openrouter",     "site": "OPENROUTER.AI", "board": "LLM Rankings (lượt dùng)",
     "url": "https://openrouter.ai/rankings",             "domain_pattern": r"openrouter",
     "viewport": "desktop"},
    # mobile KHONG dung duoc (do 06/09/2026): bang rong 556px, rong hon khung 414 nen mat cot.
    {"id": "livecodebench",  "site": "LIVECODEBENCH", "board": "LiveCodeBench",
     "url": "https://livecodebench.github.io/leaderboard.html", "domain_pattern": r"livecodebench",
     "viewport": "desktop"},
    {"id": "bfcl",           "site": "GORILLA (UC BERKELEY)", "board": "Function-Calling Leaderboard",
     "url": "https://gorilla.cs.berkeley.edu/leaderboard.html",
     "domain_pattern": r"\bbfcl\b|gorilla\.cs\.berkeley|berkeley function"},
    # mobile KHONG dung duoc (do 06/09/2026): bang cuon ngang 1788px, khung 414 mat cot.
    {"id": "gaia",           "site": "GAIA BENCHMARK", "board": "GAIA",
     "url": "https://gaia-benchmark-leaderboard.hf.space/", "domain_pattern": r"\bgaia\b",
     "viewport": "desktop"},
    {"id": "hle",            "site": "SAFE.AI", "board": "Humanity's Last Exam",
     "url": "https://agi.safe.ai/",                       "domain_pattern": r"agi\.safe\.ai|humanity'?s? last exam|\bHLE\b"},
    # mobile KHONG dung duoc (do 06/09/2026): bieu do cot mang ngu nghia bang: toa do hang khong trung cho hien, chup ra lech.
    {"id": "vellum",         "site": "VELLUM.AI", "board": "LLM Leaderboard",
     "url": "https://www.vellum.ai/llm-leaderboard",      "domain_pattern": r"vellum",
     "viewport": "desktop"},
    # mobile KHONG dung duoc (do 06/09/2026): bang rong 1417px trong khung cuon ngang, khung 414 mat cot.
    {"id": "opencompass",    "site": "OPENCOMPASS", "board": "OpenCompass LLM",
     "url": "https://rank.opencompass.org.cn/leaderboard/llm", "domain_pattern": r"opencompass|司南",
     "viewport": "desktop"},
]

# Từ khoá chọn bảng con của một site theo chủ đề tin (video → arena-t2v trước...).
# Mã trong CÙNG một mục là ALTERNATE — cùng đo một năng lực (vd arena-code/
# swebench/aider/livecodebench đều là "giỏi code cỡ nào"), chụp được cái đầu
# tiên là dừng: chụp thêm chỉ lặp lại cùng một bằng chứng. Nguồn nào đo NĂNG LỰC
# RIÊNG (không phải cách đo khác của cùng một thứ) thì đánh dấu `independent: True`
# ngay tại chỗ khai NGUON — xem chú thích ở đó (arena-t2i/arena-image-edit).
TOPIC = [
    # Bang TEXT (LOW-22, 12/09/2026): truoc day khong co mục nao cho no, nen mot
    # chu "code" trong 1500 ky tu dau bai goc du day arena-code (+200) len tren
    # arena-text cho mot tin noi ro "bang van ban" — anh chup #26 bang code di
    # kem tieu de #3 bang text. Tu khoa cua BANG trong tieu de phai co trong luong.
    # `text` khong duoc an "text-to-image"/"text-to-video" (link hai bang do).
    (r"\btext\b(?![- ]?to[- ]?)|văn bản|van ban|\bchat\b", ["arena-text"]),
    (r"\bvideo\b|text-to-video|tạo video", ["arena-t2v"]),
    # "sửa/chỉnh sửa ảnh" ưu tiên bảng EDIT; "image" trần (đa số tin tạo ảnh)
    # vẫn xét cả hai — một model tạo ảnh mạnh thường lên cả hai bảng (09/09/2026:
    # GPT-Image-2.5 #1&#2 CẢ Text-to-Image lẫn Image Edit Arena).
    (r"multi-image edit|nhiều ảnh|multi image", ["arena-multi-image-edit"]),
    (r"chỉnh sửa ảnh|sửa ảnh (bằng|với) ai|image edit(?:ing)?|photo edit(?:ing)?",
     ["arena-image-edit", "arena-multi-image-edit"]),
    (r"\bimage\b|text-to-image|tạo ảnh|hình ảnh",
     ["arena-t2i", "arena-image-edit", "arena-multi-image-edit"]),
    (r"\bvision\b|thị giác|multimodal|đa phương thức", ["arena-vision"]),
    (r"webdev|frontend|front-end|\bcode\b|coding|lập trình|swe[-_ ]?bench",
     ["arena-code", "swebench", "aider", "livecodebench"]),
    (r"terminal|agentic|\bagent\b", ["tbench", "gaia"]),
    (r"\bsearch\b|tìm kiếm", ["arena-search"]),
    (r"intelligence|trí tuệ|artificial ?analysis", ["aa-models"]),
    # Xep hang theo LUOT DUNG THAT, khong phai diem benchmark — khac han ve ban chat
    # nen phai co tu khoa rieng, dung de tin "top 10 OpenRouter" roi vao bang diem.
    (r"openrouter|\busage\b|lượt dùng|thị phần|market share|token/tuần", ["openrouter"]),
    (r"function[- ]?call|tool[- ]?use|gọi hàm|dùng công cụ", ["bfcl"]),
    (r"humanity'?s? last exam|\bhle\b|đề thi khó nhất", ["hle"]),
]

# ---- Nhận diện tin xếp hạng + tách model/hạng ---------------------------------
# CHI nhan khi co dau hieu BANG XEP HANG, khong nhan tu roi. Truoc 06/09/2026
# mau nay con bat "vượt", "dẫn đầu", "đứng đầu", "số 1", "top N" dung mot minh —
# nhung chu co trong hau het tom tat cua Finn/Nova/Vera. Do that: 6/6 tieu de
# goi von / doanh thu / gia chip deu bi dong dau TIN XEP HANG ("Reflection gọi
# vốn 2 tỷ USD, vòng seed do Nvidia dẫn đầu"), keo theo ca chuoi hong ben duoi.
# Gia tri `kind` ma find_and_capture / find_and_capture_many PHAT RA khi CHUP DUOC bang
# that (bang, hai bang ghep, danh sach hang-the, nhan SVG). Chi "the" la the du
# phong engine tu dung. LOW-21 (11/09/2026): manifest va submit_common tung doi
# `kieu == "chup"` — gia tri KHONG MOT nhanh nao o day phat ra — nen moi tin xep
# hang deu bi brief goi la "THE DU PHONG" va cong ep bia XH chua tung chay; test
# thi stub "chup" nen xanh gia. Nguoi doc hoi qua `is_capture`, khong so chuoi.
# Ma English tu LOW-230 (bang cu -> table, bang-ghep -> table-stitched, danh-sach -> list,
# danh-sach-ghep -> list-stitched, the -> card).
# "x_post": do hoa xep hang chinh chu tu tweet @arena (arena_x.py, LOW-337) — anh THAT cua nguon.
# "board-page": bang cua CHINH trang nguon bai, chup khi khong nguon nao khoanh duoc
# hang (LOW-385). VAN la anh THAT cua mot bang — chi khac la chua khoanh hang nao.
KIND_CAPTURE = frozenset({"table", "table-stitched", "list", "list-stitched", "svg",
                          "x_post", "board-page"})


def is_capture(kieu) -> bool:
    """Anh XH nay la CHUP THAT tu trang xep hang (True) hay the du phong (False)."""
    return kieu in KIND_CAPTURE


_XEP_HANG = re.compile(
    # (a) ten bang / khai niem xep hang — tu no da du nghia
    r"(xếp hạng|thứ hạng|bảng xếp hạng|leaderboard|ranking|ranked|\brank\b|"
    r"elo|arena|intelligence index|trí tuệ .{0,20}(artificial|analysis)|"
    r"soán ngôi|lọt top|"
    # (b) tu chi vi tri — CHI khi di kem ngu canh bang/benchmark trong 40 ky tu
    r"(?:đứng đầu|dẫn đầu|đứng thứ|vượt|áp sát|chen chân|số 1|number one|no\.\s?1|"
    r"first place|hạng \d|#\s?\d|top\s?\d|top-\d|leo \d|leo lên)"
    r".{0,40}(bảng|leaderboard|arena|benchmark|xếp hạng|bxh)|"
    r"(?:bảng|leaderboard|arena|benchmark|xếp hạng|bxh).{0,40}"
    r"(?:đứng đầu|dẫn đầu|đứng thứ|vượt|áp sát|số 1|hạng \d|#\s?\d|top\s?\d|leo lên))", re.I)

# Họ model + đuôi phiên bản. Bắt cả "GPT-6 Astra (max)", "Claude Fable 5.1", "Kimi-K3",
# "Grok Imagine Video 1.5 Agent", "Qwen3.8-27B", "GLM-5.2 (Max)", "Muse Spark 1.2".
# Ho model. Cac ho TRUNG TU THUONG tieng Anh/Viet (Seed, Solar, Granite, Phi,
# Command, Nova, Step, Yi) da tach rieng xuong _HO_CAN_SO: chung chi duoc nhan
# khi DI KEM so phien ban. Truoc 06/09/2026 chung nam chung o day, nen "vòng
# seed do Nvidia dẫn đầu" ra models=['seed'] va keo ca engine di luc 11 bang
# xep hang cho mot tin goi von.
_HO = (r"GPT|Claude|Gemini|Gemma|Grok|Kimi|Qwen|GLM|DeepSeek|Llama|Mistral|Mixtral|Muse Spark|"
       r"MiniMax|Nemotron|Jamba|Hunyuan|Doubao|MiMo|o\d")
# MiMo (Xiaomi, 22/09/2026): thieu ho nay thi tin "XiaomiMiMo/MiMo-V2.6-Pro-RL tha trong so" tach ra
# [] va khong bao gio hoi toi X @arena, du @arena vua dang "MiMo-V2.6-Pro just landed … top 10".
_HO_CAN_SO = r"Seed|Solar|Granite|Phi|Command|Nova|Step|Yi"
# Duoi cho phep: TU dat ten (khong phai dong tu/tu Viet) hoac so phien ban. So tran
# (khong cham) chi nhan khi KHONG di truoc mot tu thuong: "Opus 4 (Thinking)" co,
# "55 điểm" khong. Neu khong, "GPT-6 Astra (max) 55 điểm" se an ca "55".
_DUOI = (r"(?:Astra|Flash|Pro|Max|Mini|Nano|Ultra|Sol|Sonnet|Opus|Haiku|Fable|Thinking|Imagine|"
         r"Video|Image|Agent|Spark|Coder|Instruct|Turbo|Lite|Next|Plus|Preview|Chat|Reasoning|"
         r"High|Low|Medium|XHigh|Vision|Code|Omni|Deep|Research|Horizon|Build|Experimental|Exp|"
         # Ten ma cua CAC BIEN THE cung ho hien tren mot bang xep hang (09/09/2026:
         # GPT-Image-2.5 Sunburst #1 va GPT-Image-2.5 Flare #2, CUNG mot bang Image
         # Edit Arena). Thieu duoi nay thi extract_model dung o "GPT Image 2.5", khop
         # NHAP NHANG ca hai hang — khoanh dai dung hang nao tim thay truoc, sai
         # tin khi tin noi ve Flare ma engine khoanh Sunburst.
         r"Sunburst|Flare|"
         r"[KVRM]\d+(?:\.\d+)?[A-Za-z]*|\d+[bB]|\d+\.\d+(?:\.\d+)*[A-Za-z]*|"
         # So NGUYEN lam duoi phien ban: loai bang DANH SACH DON VI, khong bang
         # "chu thuong bat ky". Truoc 06/09/2026 lookahead cam moi chu thuong
         # dung sau so, ma tieu de tu nhien gan nhu luon co: "GPT-6 vượt...",
         # "Grok 5 takes first place" -> models=['GPT'], ['Grok'] — mat so phien
         # ban. Engine roi khoanh HANG DAU TIEN chua chu "gpt" tren bang (co the
         # la GPT-5.2 mini hang 23), dong dau model=GPT, va cong ep dung tam do
         # lam anh chinh. Bai ve GPT-6 #1 di kem anh khoanh model khac.
         r"\d{1,3}(?!\s*(?-i:(?:điểm|diem|point|elo|%|tỷ|ty|triệu|trieu|nghìn|nghin|"
         r"USD|đô|do|tokens?|token|lần|lan|bậc|bac|giây|giay|phút|phut|giờ|gio|"
         r"ngày|ngay|tháng|thang|năm|nam)\b)))")
_MODEL = re.compile(r"\b((?:(?:" + _HO + r")|(?:(?:" + _HO_CAN_SO + r")(?=[-\s]?\d)))"
                    r"(?:[-\s]?" + _DUOI + r")*"
                    r"(?:\s?\((?:max|high|thinking|xhigh|low|medium|pro|mini)\))?)", re.I)

_HANG = re.compile(r"(?:#|hạng |thứ |rank(?:ed)? |vị trí |top )\s?(\d{1,3})\b|\b(\d{1,3})\s?(?:st|nd|rd|th)\b", re.I)


def is_ranking_story(tieu_de: str, tom_tat: str) -> bool:
    return bool(_XEP_HANG.search(f"{tieu_de} {tom_tat}"))


def extract_model(tieu_de: str) -> list:
    """Danh sách tên model để thử khớp, DÀI trước NGẮN sau.
    "GPT-6 Astra (max) 55 điểm" -> ["GPT-6 Astra (max)", "GPT-6 Astra", "GPT-6"]."""
    # Tieu de trang HuggingFace la "org/Model · Hugging Face": "deepseek-ai/"
    # dung truoc nen _MODEL bat "deepseek" (khong so, khong duoi) roi dung —
    # _lock_model ra rong va trang cong bo chinh chu KHONG BAO GIO duoc hoi
    # (LOW-34, 12/09/2026: the DeepSeek-V4.1-Flash khong co anh tu deepseek.com).
    # Bo tien to repo truoc khi tim.
    tieu_de = re.sub(r"^\s*[\w.-]+/(?=[A-Za-z])", "", tieu_de or "")
    m = _MODEL.search(tieu_de)
    if not m:
        return []
    ten = m.group(1).strip(" -:")
    ra = [ten]
    khong_ngoac = re.sub(r"\s?\([^)]*\)$", "", ten).strip()
    if khong_ngoac != ten:
        ra.append(khong_ngoac)
    # Ten dang SLUG cua bang ("claude-opus-5-5-max-effort") la MOT tu: vong rut
    # gon theo tu ben duoi khong chay, nen truoc LOW-381 danh sach chi co dung
    # mot ung vien — va khong hang nao chua chuoi do, vi bang in "Claude Opus 5.5
    # (max with fallback)". Quy ve dang hien thi TRUOC roi moi rut gon tiep.
    display_form = model_name.display_name(khong_ngoac)
    if display_form and display_form.lower() != khong_ngoac.lower():
        ra.append(display_form)
        khong_ngoac = display_form
    ws = khong_ngoac.split()
    # bớt dần từ cuối, nhưng KHÔNG bớt tới dạng MỘT TỪ KHÔNG MANG SỐ — đó là TÊN
    # HÃNG TRẦN ("DeepSeek", "Gemini", "Claude"), nó khớp mọi hàng có chữ đó kể cả
    # hàng KHÔNG PHẢI model của bài: "DeepSeek" khoanh trúng "DeepSeek Harness" —
    # app của người khác, hạng 9 bảng Apps của openrouter — trong ba bài liền
    # 15/09/2026 (LOW-177). Giữ "GPT-6" (một từ nhưng có số nên vẫn định danh
    # được model) và "Muse Spark" (hai từ nên vẫn là tên model, không phải hãng).
    while len(ws) > 1:
        ws = ws[:-1]
        ngan = " ".join(ws)
        if len(ws) == 1 and not any(c.isdigit() for c in ngan):
            break
        ra.append(ngan)
    return list(dict.fromkeys(x for x in ra if len(x) >= 3))


# "top N" o dau tieu de hoac sau "lot/vao" la KICH CO DANH SACH, khong phai thu
# hang cua chu the: "Top 10 mô hình AI 2026: GPT-6 Astra dẫn đầu" -> hang 1 chu
# khong phai 10 (do 06/09/2026: so nay in TO tren the du phong va vao brief).
_TOP_LIET_KE = re.compile(r"(?:^|[:\-–—]\s*|\b(?:lọt|lot|vào|vao)\s+)top\s?\d{1,3}\b", re.I)
_DAN_DAU = re.compile(r"(dẫn đầu|dan dau|đứng đầu|dung dau|số 1|so 1|number one|"
                      r"no\.\s?1|first place|soán ngôi|soan ngoi|quán quân|quan quan)", re.I)


def extract_rank(tieu_de: str, model: str):
    """Thu hang cua CHU THE trong tieu de.

    Tieu de hay nhac HAI model ("GPT-6 ... ap sat #1 Claude Fable"): mot so hang
    di lien ngay truoc mot TEN MODEL KHAC thi thuoc ve model do. Ngoai ra khong
    lay match DAU TIEN nua ma xep uu tien: "#N / hạng N / thứ N" (tuong minh) >
    "top N" (co the chi la kich co danh sach). Va neu tieu de noi thang la dan
    dau thi hang = 1, ke ca khi phia truoc co "Top 10"."""
    t = tieu_de or ""
    ro, mo = None, None
    for m in _HANG.finditer(t):
        sau = t[m.end():m.end() + 40]
        mm = _MODEL.match(sau.lstrip())
        if mm and model and not mm.group(1).lower().startswith(model.split()[0].lower()):
            continue                                 # "#1 Claude ..." — hang cua Claude
        rank = int(m.group(1) or m.group(2))
        la_top = t[m.start():m.end()].lower().lstrip("#").strip().startswith("top")
        if la_top and _TOP_LIET_KE.search(t[max(0, m.start() - 12):m.end()]):
            mo = mo if mo is not None else rank        # kich co danh sach: chi dung khi khong con gi
            continue
        if ro is None:
            ro = rank
    if _DAN_DAU.search(t):
        return 1
    return ro if ro is not None else mo


def suggest_sources(tieu_de: str = "", link: str = "", via: str = "", chu: str = "") -> list:
    """Xếp registry: nguồn được NHẮC (tiêu đề/link/via/chữ bài) trước, rồi theo chủ
    đề tin, rồi phần còn lại. Hàm này KHÔNG loại nguồn nào — nó chỉ xếp thứ tự;
    việc loại nằm ở `source_proves_story`, xem đó.

    Mỗi mục trả về mang thêm hai khoá:
      `mentioned`  True khi CHÍNH TIN nhắc tới nguồn đó (đọc ở tiêu đề/link/via).
      `on_topic`   True khi tiêu đề/link/via khớp một mẫu TOPIC của nguồn đó — tin
                   "top 10 OpenRouter" với bảng lượt dùng. ĐỌC Ở TIÊU ĐỀ, không
                   đọc thân bài (LOW-22).

    Trước LOW-179, chụp được từ nguồn `mentioned=False` vẫn dùng được, chỉ kèm
    cảnh báo "đây là bảng khác" trong `describe_ranking_image`. Không còn: tin
    HuggingFace thả trọng số ra ảnh bảng lượt dùng openrouter (15/09/2026), mà
    cảnh báo đó thì hai bài cùng đợt không hề nổ vì tiêu đề có chữ "OpenRouter"
    nên `mentioned=True`. Luật Ông Chủ 16/09: không chụp đại chart rồi đưa vào
    minh hoạ.

    Mỗi mục còn giữ nguyên `independent` nếu có (spread từ NGUON) — `find_and_capture_many`
    đọc khoá này để biết nguồn nào đo NĂNG LỰC RIÊNG, không phải cách đo khác
    của cùng một thứ, nên cố lấy hết thay vì dừng ở thành công đầu tiên."""
    # Tieu de NAM TRONG chuoi do "nguon duoc nhac": tin hay goi thang ten trang
    # ("#1 LiveCodeBench", "leo top OpenCompass") ma khong co link toi trang do.
    goi = f"{tieu_de} {link} {via} {chu[:3000]}".lower()
    chu_de = f"{tieu_de} {chu[:1500]}".lower()
    # BANG nao duoc nhac thi doc o TIEU DE / LINK / VIA — KHONG doc o than bai
    # (LOW-22): than bai ve mot model text hau nhu luon co chu "code", ma bay bang
    # arena chung mot ten mien nen truoc 12/09/2026 `mentioned` = "co arena.ai
    # o dau do" — ca 7 bang deu True, canh bao "BANG KHAC" trong describe_ranking_image
    # khong bao gio no. Nguon co `board_pattern` thi phai KHOP bang moi la duoc nhac.
    nhac_bang = f"{tieu_de} {link} {via}".lower()
    diem, ra = {}, []
    for i, n in enumerate(SOURCE):
        d = 1000 - i
        nhac = bool(re.search(n["domain_pattern"], goi, re.I))
        if nhac and n.get("board_pattern"):
            nhac = bool(re.search(n["board_pattern"], nhac_bang, re.I))
        if nhac:
            d += 500
        on_topic = False
        for pat, mas in TOPIC:
            if n["id"] not in mas:
                continue
            if re.search(pat, chu_de, re.I):
                d += 200
            # `on_topic` doc o TIEU DE/LINK/VIA, KHONG doc than bai — cung ly do
            # voi `nhac_bang` (LOW-22: than bai lam moi nguon trong nhu duoc nhac).
            # Diem sap xep van doc ca than bai: doi no la doi THU TU nguon, khong
            # phai viec cua LOW-179.
            if re.search(pat, nhac_bang, re.I):
                on_topic = True
        # `in_title`: bang duoc goi ten ngay o TIEU DE, hep hon `mentioned` (doc
        # ca link/via/than bai). Chi THE DU PHONG dung khoa nay — xem `_card_source`.
        in_title = bool(re.search(n["domain_pattern"], (tieu_de or "").lower(), re.I))
        if in_title and n.get("board_pattern"):
            in_title = bool(re.search(n["board_pattern"], (tieu_de or "").lower(), re.I))
        diem[n["id"]] = d
        ra.append({**n, "mentioned": nhac, "on_topic": on_topic, "in_title": in_title})
    return sorted(ra, key=lambda n: -diem[n["id"]])


# ---- Chụp ----------------------------------------------------------------------
# Bảng xếp hạng hay nằm trong một KHUNG CUỘN RIÊNG (artificialanalysis: div
# overflow-auto cao 80vh chứa 300 hàng, tài liệu chỉ cao 4000px). Toạ độ "tài liệu"
# vô nghĩa ở đó: window.scrollTo không tới được hàng 125. Nên cách đo là: gọi
# scrollIntoView lên đúng phần tử cần thấy (nó cuộn cả cửa sổ lẫn khung), đợi,
# rồi đo lại theo VIEWPORT và clip ngay — không tính toạ độ trước rồi cuộn sau.
_JS_NORM = """
const norm = s => (s||'').toLowerCase().replace(/[\\s\\-_–—.]+/g,'');
// Khop ten model trong mot chuoi DA norm. `norm` xoa ca dau cham nen phien ban
// NGAN an duoc phien ban DAI: "deepseekv4" la substring cua "deepseekv41flash",
// nen bai ve V4 Pro khoanh nham hang V4.1 Flash (LOW-177). Chan bang mot dieu
// kien: ky tu ngay sau cho khop khong duoc la CHU SO. "Gemini 3" cung khong con
// an duoc "Gemini 3.8 Flash". (charCodeAt qua cuoi chuoi tra NaN -> moi so sanh
// la false -> tinh la khop, dung y: khop tan cung chuoi.)
const matchesModel = (hay, nm) => {
  for (let i = hay.indexOf(nm); i >= 0; i = hay.indexOf(nm, i + 1)) {
    const c = hay.charCodeAt(i + nm.length);
    if (!(c >= 48 && c <= 57)) return true;
  }
  return false; };
const rect = el => { const r = el.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; };
const khungCuon = el => { for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
  const cs = getComputedStyle(e); if (/(auto|scroll)/.test(cs.overflowY) && e.scrollHeight > e.clientHeight + 4) return e; }
  return null; };
const hangHien = t => Array.from(t.querySelectorAll('tr,[role=row]')).filter(r => { const b = r.getBoundingClientRect(); return b.width > 0 && b.height > 0; });
const vung = el => { const k = khungCuon(el); const vw = window.innerWidth, vh = window.innerHeight;
  if (!k) return {x: 0, y: 0, w: vw, h: vh};
  const r = k.getBoundingClientRect();
  return {x: Math.max(0, r.x), y: Math.max(0, r.y), w: Math.min(vw, r.right) - Math.max(0, r.x), h: Math.min(vh, r.bottom) - Math.max(0, r.y)}; };
"""

# Liệt kê MỌI bảng có hàng chứa model (không chỉ bảng lớn nhất — Ông Chủ 06/09:
# "trang ảnh rất ngang chắc chắn còn nhiều benchmark table khác"). Mỗi bảng kèm
# ước lượng tỉ lệ khi chụp đủ cao (rộng / min(cao đủ hàng, trần)), để chọn cái
# vừa khổ hero trước. Đánh dấu data-xh-bang="k" theo thứ tự.
_JS_TIM = _JS_NORM + """
([models, tranCao, tiLeMucTieu, vuaKhung]) => {
  const ra = [];
  const vw = window.innerWidth;
  // Nguong be ngang theo KHUNG NHIN, khong phai 500px cung: o khung mobile 414
  // moi bang deu hep hon 500 -> khoa cung thi khong bao gio chup duoc bang o mobile.
  const toiThieu = Math.min(500, vw * 0.6);
  const bangs = Array.from(document.querySelectorAll('table,[role=table],[role=grid]'))
    .map(t => ({t, rows: hangHien(t)}))
    .filter(b => b.rows.length >= 5 && b.t.getBoundingClientRect().width >= toiThieu)
    // `vuaKhung`: bo bang RONG HON khung nhin — no nam trong khung cuon ngang nen
    // chup ra chi duoc mot lat cat ben trai, mat cot phai (tbench/swebench/bfcl/
    // gaia/opencompass o khung mobile).
    .filter(b => !vuaKhung ||
                 Math.max(b.t.getBoundingClientRect().width, b.t.scrollWidth) <= vw * 1.05);
  let k = 0;
  for (const {t, rows} of bangs) {
    for (const model of models) {
      const nm = norm(model);
      // CHI khop theo innerText (chu THAT SU hien), khong lui ve textContent: mot
      // dai rong tren thanh nav van chua textContent cua con chau an -> khop nham,
      // ra anh khoanh vang mot o trong (thay tren vellum o khung mobile 06/09).
      const idx = rows.findIndex((r, i) => {
        const t = (r.innerText || '').trim();
        return i > 0 && t.length >= 3 && matchesModel(norm(t), nm);
      });
      if (idx < 0) continue;
      const r = rows[idx];
      const cells = Array.from(r.children).map(c => (c.innerText || '').trim().replace(/\\s+/g, ' '));
      // Cot HANG (neu co) luon nam trong hai o dau tien tinh tu trai — arena "Rank",
      // swebench cot checkbox+"#", tbench "RANK". artificialanalysis KHONG CO cot hang
      // (sap xep ngam theo Intelligence Index) nen KHONG duoc do o ca hang: truoc day
      // regex bat BAT KY o nao khop "so nguyen <=3 chu so" trong ca hang, va vo nham
      // chinh diem Intelligence (vd "55") lam thu hang — bao sai "hang #55" trong khi
      // do la diem so. Gioi han vung do ve HAI O DAU tien moi dung.
      const hang = (cells.slice(0, 2).find(c => /^#?\\d{1,3}$/.test(c)) || '').replace('#', '');
      const img = r.querySelector('img'); if (img) img.setAttribute('data-xh-logo', String(k));
      t.setAttribute('data-xh-bang', String(k));
      const w = t.getBoundingClientRect().width;
      const caoDu = rows.slice(0, Math.min(rows.length, 40)).reduce((a, x) => a + x.getBoundingClientRect().height, 0);
      const cao = Math.min(caoDu, tranCao);
      ra.push({k, model, idx, row_count: rows.length, rank: hang ? parseInt(hang, 10) : null,
               row: cells.join(' | ').slice(0, 160), logo: !!img,
               ratio: w / Math.max(1, cao), fits: w / Math.max(1, cao) <= tiLeMucTieu});
      k++; break;
    }
  }
  // vừa khổ trước; trong nhóm đó bảng nhiều hàng hơn trước; rồi tới bảng hẹp hơn
  ra.sort((a, b) => (b.fits - a.fits) || (b.row_count - a.row_count) || (a.ratio - b.ratio));
  return ra;
}"""

# Cuộn phần tử vào tầm nhìn rồi đo TẤT CẢ theo viewport.
_JS_CUON_DO = _JS_NORM + """
([cach, dau, k]) => {
  const t = document.querySelector('[data-xh-bang="' + k + '"]'); if (!t) return null;
  const rows = hangHien(t);
  const hdrH = rows[0].getBoundingClientRect().height;
  if (cach === 'top') { t.scrollIntoView({block: 'start', inline: 'nearest'}); window.scrollBy(0, -8); }
  else { rows[dau].scrollIntoView({block: 'start', inline: 'nearest'}); window.scrollBy(0, -(hdrH + 12)); }
  // Khung cuon con (khong go tran duoc): dat hang dau cua so ngay duoi header dinh.
  const kc = khungCuon(t);
  if (kc) { const kb = kc.getBoundingClientRect(); const muc = cach === 'top' ? t : rows[dau];
    const d = muc.getBoundingClientRect().y - kb.y - (cach === 'top' ? 0 : hdrH + 8);
    if (Math.abs(d) > 2) kc.scrollTop += d; }
  // VUNG DINH (sticky) THAT: header co the hai tang (artificialanalysis: 90px, rows[0]
  // chi 36px) — hang model trot xuong duoi tang hai, bi che. Do dinh/day cua moi phan
  // tu sticky dang nam o mep tren, roi cuon bu cho hang dau cua so nam duoi day do.
  const stickyDo = () => { let top = Infinity, bot = -Infinity;
    for (const e of t.querySelectorAll('thead, thead tr, tr, th, [role=columnheader], [role=rowgroup]')) {
      if (getComputedStyle(e).position !== 'sticky') continue;
      const b = e.getBoundingClientRect(); if (b.height <= 0) continue;
      top = Math.min(top, b.top); bot = Math.max(bot, b.bottom); }
    return isFinite(bot) ? {top, bot} : null; };
  let st = stickyDo();
  if (cach !== 'top' && st) {
    const y = rows[dau].getBoundingClientRect().y;
    if (y < st.bot + 4) { const d = y - (st.bot + 8);
      if (kc) kc.scrollTop += d; else window.scrollBy(0, d); }
    st = stickyDo();
  }
  return {region: vung(t), table_rect: rect(t), rows: rows.map(rect), sticky: st};
}"""

# `cuon=true`: tim nhan SVG mang ten model trong mot chart du lon roi cuon toi;
# `false`: do lai chinh nhan do sau khi cuon.
_JS_SVG = _JS_NORM + """
([models, cuon]) => {
  for (const model of models) {
    const nm = norm(model);
    for (const t of document.querySelectorAll('svg text, svg tspan')) {
      if (!matchesModel(norm(t.textContent), nm) || t.getBoundingClientRect().width <= 0) continue;
      const s = t.closest('svg'); if (!s) continue;
      const sb = s.getBoundingClientRect();
      if (sb.width < 500 || sb.height < 250) continue;
      if (cuon) { s.scrollIntoView({block: 'center'});
                  return {model, row: (t.textContent||'').trim().slice(0,80)}; }
      return {svg: rect(s), label_rect: rect(t), region: vung(s)};
    }
  }
  return null;
}"""


def _change_board(page, giay: int = 14):
    """Đợi trang render xong BẢNG (≥5 hàng) hoặc DANH SÁCH hàng-thẻ hoặc SVG lớn,
    tối đa `giay`, rồi thêm 1.2s cho font/logo. Chờ cố định 6s là đánh bạc: arena
    text-to-video có lúc chưa ra hàng nào ở giây thứ 6.

    Phải nhận cả danh sách chứ không chỉ bảng: trang chỉ có danh sách (arena, aa,
    livebench ở khung mobile) mà chỉ dò bảng thì lần nào cũng đợi hết `giay` vô ích."""
    page.wait_for_timeout(1200)
    t0 = time.time()
    while time.time() - t0 < giay:
        if page.evaluate(_JS_NORM_DS + """() => {
              for (const t of document.querySelectorAll('table,[role=table],[role=grid]'))
                if (Array.from(t.querySelectorAll('tr,[role=row]'))
                      .filter(r => r.getBoundingClientRect().height > 0).length >= 5) return true;
              if (timDanhSach(null)) return true;
              return Array.from(document.querySelectorAll('svg'))
                       .some(s => s.getBoundingClientRect().width >= 500); }"""):
            break
        page.wait_for_timeout(600)
    page.wait_for_timeout(1200)


def _hand(a: dict, b: dict) -> dict:
    x0, y0 = max(a["x"], b["x"]), max(a["y"], b["y"])
    x1, y1 = min(a["x"] + a["w"], b["x"] + b["w"]), min(a["y"] + a["h"], b["y"] + b["h"])
    return {"x": x0, "y": y0, "w": max(0, x1 - x0), "h": max(0, y1 - y0)}


def _capture(page, r: dict, out: Path, dem: int = 8):
    """Chụp `r` (viewport px), thêm `dem` px hai bên nếu còn chỗ — mép bảng sát
    mũi tên sort/ô cuối (thấy trên tbench thu hẹp: "COST ⇅" và "$6.2k" chạm cạnh)."""
    if r["w"] < 50 or r["h"] < 30:
        raise RuntimeError(f"vùng chụp rỗng {r}")
    vw = page.viewport_size["width"]
    x0 = max(0, r["x"] - dem)
    x1 = min(vw, r["x"] + r["w"] + dem)
    page.screenshot(path=str(out), clip={"x": x0, "y": r["y"], "width": x1 - x0, "height": r["h"]})


def _highlight(png: Path, x: float, y: float, w: float, h: float, dpr: int = DPR):
    im = Image.open(png).convert("RGB")
    d = ImageDraw.Draw(im)
    pad = 3 * dpr
    box = [max(0, x * dpr - pad), max(0, y * dpr - pad),
           min(im.width - 1, (x + w) * dpr + pad), min(im.height - 1, (y + h) * dpr + pad)]
    d.rounded_rectangle(box, radius=6 * dpr, outline=GOLD, width=2 * dpr)
    im.save(png, "PNG")


def _of_count(rows: list, idx: int, hdr_h: float) -> tuple:
    """[dau, cuoi] hàng đưa vào ảnh: trong top → từ hàng 1, sâu → từ idx-2, rồi
    kéo xuống hết HEIGHT_MAX_CSS. Ông Chủ 06/09/2026: "chụp full chiều dài cũng
    chả vấn đề" — càng nhiều hàng quanh model càng tốt, chỉ chặn ở trần vì thẻ
    cao bấy nhiêu, chụp thêm cũng bị cắt."""
    n = len(rows)
    dau = 1 if idx <= TOP_DEFAULT + 2 else max(1, idx - ON_MODEL)
    cuoi = min(n - 1, max(idx + 2, dau + TOP_DEFAULT - 1))
    cao = lambda k: rows[k]["y"] + rows[k]["h"] - rows[dau]["y"] + hdr_h
    while cuoi + 1 < n and cao(cuoi + 1) <= HEIGHT_MAX_CSS:
        cuoi += 1
    while cuoi > idx + 1 and cao(cuoi) > HEIGHT_MAX_CSS:
        cuoi -= 1
    return dau, cuoi


def _capture_one_board(page, tim: dict, out: Path, dpr: int = DPR):
    """Chụp cửa sổ top-N của MỘT bảng (đã đánh dấu k), khoanh hàng model."""
    idx, k = tim["idx"], tim["k"]
    out.parent.mkdir(parents=True, exist_ok=True)
    # Lượt 1: cuộn header lên đầu (trường hợp top) hoặc hàng model vào giữa (sâu), đo.
    trong_top = idx <= TOP_DEFAULT + 2
    do = page.evaluate(_JS_CUON_DO, ["top" if trong_top else "row", idx, k])
    page.wait_for_timeout(400)
    do = page.evaluate(_JS_CUON_DO, ["top" if trong_top else "row", idx, k])
    rows, vung, hdr = do["rows"], do["region"], do["rows"][0]
    st = do.get("sticky")
    hdr_h = max(hdr["h"], (st["bot"] - st["top"]) if st else 0)
    dau, cuoi = _of_count(rows, idx, hdr_h)
    x, w = do["table_rect"]["x"], do["table_rect"]["w"]
    # Hàng nào nằm dưới vùng DÍNH (header sticky, có thể nhiều tầng) hoặc ngoài
    # vùng nhìn thì bỏ khỏi band — không chụp cái không hiện.
    duoi_hdr = max(hdr["y"] + hdr["h"] if hdr["y"] >= vung["y"] - 1 else vung["y"],
                   st["bot"] if st else -1)
    hien = [k for k in range(dau, cuoi + 1)
            if rows[k]["y"] >= duoi_hdr - 1 and rows[k]["y"] + rows[k]["h"] <= vung["y"] + vung["h"] + 1]
    if idx not in hien:
        # Hang model bi che (header dinh cao / cuon lech): thu cach 'row' — hang dau
        # cua so len dau viewport, lui mot header.
        do = page.evaluate(_JS_CUON_DO, ["row", dau, k]); page.wait_for_timeout(300)
        do = page.evaluate(_JS_CUON_DO, ["row", dau, k])
        rows, vung, hdr = do["rows"], do["region"], do["rows"][0]
        st = do.get("sticky")
        duoi_hdr = max(hdr["y"] + hdr["h"] if hdr["y"] >= vung["y"] - 1 else vung["y"],
                       st["bot"] if st else -1)
        hien = [k for k in range(dau, cuoi + 1)
                if rows[k]["y"] >= duoi_hdr - 1 and rows[k]["y"] + rows[k]["h"] <= vung["y"] + vung["h"] + 1]
    if idx not in hien:
        return None, (f"thấy hàng {idx}/{tim['row_count']} nhưng không đưa vào tầm nhìn được "
                      f"(vùng {round(vung['y'])}..{round(vung['y']+vung['h'])}, hàng y={round(rows[idx]['y'])} "
                      f"h={round(rows[idx]['h'])}, header y={round(hdr['y'])} h={round(hdr['h'])}, {len(hien)} hàng hiện)")
    dau, cuoi = hien[0], hien[-1]
    band = {"x": x, "w": w, "y": rows[dau]["y"], "h": rows[cuoi]["y"] + rows[cuoi]["h"] - rows[dau]["y"]}
    # Header lien ke band: header thuong (rows[0]) ngay tren, HOAC vung sticky ket
    # thuc sat tren band -> mot clip lien tu dinh header/sticky xuong het band.
    dinh = None
    if vung["y"] - 1 <= hdr["y"] and hdr["y"] + hdr["h"] <= band["y"] + 2:
        dinh = hdr["y"]
    elif st and st["bot"] <= band["y"] + 12 and st["top"] >= vung["y"] - 1:
        dinh = st["top"]
    if dinh is not None:
        r = _hand({"x": x, "w": w, "y": dinh, "h": band["y"] + band["h"] - dinh}, vung)
        _capture(page, r, out)
        goc = (max(0, r["x"] - 8), r["y"]); do_hdr = 0
    else:
        # Header không liền band (model sâu, header không dính): chụp riêng rồi ghép.
        p1, p2 = out.with_suffix(".h.png"), out.with_suffix(".b.png")
        _capture(page, _hand(band, vung), p2)
        do2 = page.evaluate(_JS_CUON_DO, ["top", 0, k]); page.wait_for_timeout(300)
        do2 = page.evaluate(_JS_CUON_DO, ["top", 0, k])
        h2 = do2["rows"][0]
        _capture(page, _hand({"x": x, "w": w, "y": h2["y"], "h": h2["h"]}, do2["region"]), p1)
        a, b = Image.open(p1).convert("RGB"), Image.open(p2).convert("RGB")
        g = Image.new("RGB", (max(a.width, b.width), a.height + b.height), (255, 255, 255))
        g.paste(a, (0, 0)); g.paste(b, (0, a.height)); g.save(out, "PNG"); p1.unlink(); p2.unlink()
        goc = (max(0, max(band["x"], vung["x"]) - 8), max(band["y"], vung["y"])); do_hdr = a.height / dpr
    row = rows[idx]
    _highlight(out, row["x"] - goc[0], row["y"] - goc[1] + do_hdr, min(row["w"], w), row["h"], dpr)
    return {"kind": "table", "model": tim["model"], "rank": tim["rank"], "row": tim["row"],
            "has_logo": tim["logo"]}, ""


def capture_board(page, models: list, out: Path, dpr: int = DPR, vua_khung: bool = False):
    """Chụp bảng chứa model, chọn bảng VỪA KHỔ nhất trang. Thử tối đa 3 bảng theo
    thứ tự vừa khổ → nhiều hàng → hẹp, lấy bảng đầu ra rộng/cao ≤ RATIO_FIT.
    Vẫn quá ngang thì thu hẹp cửa sổ trình duyệt cho bảng tự dồn cột (tbench ra
    3.2 nếu không làm)."""
    ung = page.evaluate(_JS_TIM, [models, HEIGHT_MAX_CSS, RATIO_FIT, vua_khung])
    if not ung:
        return None, "không có bảng ≥5 hàng chứa tên model"
    da, ly_do = [], []
    for tim in ung[:3]:
        p = out if not da else out.with_suffix(f".b{len(da)}.png")
        try:
            kq, ld = _capture_one_board(page, tim, p, dpr)
        except Exception as e:                               # noqa: BLE001
            kq, ld = None, f"{type(e).__name__}: {str(e)[:60]}"
        if not kq:
            ly_do.append(f"bảng {tim['k']} ({tim['row_count']} hàng): {ld}")
            continue
        with Image.open(p) as im:
            r = im.width / im.height
        da.append((kq, p, r, tim))
        if r <= RATIO_FIT:
            break
    if not da:
        return None, "; ".join(ly_do)
    da.sort(key=lambda t: t[2])
    kq, p, r, tim = da[0]
    if r > RATIO_FIT and len(da) < 2:
        # Trang chi co MOT bang va no qua ngang (tbench: 15 hang trai 2319px o viewport
        # 2400): bang responsive tra rong theo cua so. Thu hep cua so — bang tu don
        # cot, van du noi dung, chi bo cuc hep lai. Lay ban dau tien vua kho.
        rong_cu = page.viewport_size["width"]
        for rong in (1500, 1200, 1000):
            page.set_viewport_size({"width": rong, "height": page.viewport_size["height"]})
            page.wait_for_timeout(700)
            p2 = out.with_suffix(f".w{rong}.png")
            try:
                kq2, _ = _capture_one_board(page, tim, p2, dpr)
            except Exception:                                # noqa: BLE001
                kq2 = None
            if not kq2:
                continue
            with Image.open(p2) as im2:
                r2 = im2.width / im2.height
            if r2 < r:
                if p != out:
                    p.unlink(missing_ok=True)     # ban hep hon truoc do, khong con dung toi
                da = [(kq2, p2, r2, tim)]
                kq, p, r = kq2, p2, r2
            else:
                p2.unlink(missing_ok=True)
            if r <= RATIO_FIT:
                break
        page.set_viewport_size({"width": rong_cu, "height": page.viewport_size["height"]})
    if r > RATIO_FIT and len(da) >= 2:
        kq2, p2, r2, tim2 = da[1]
        a, b = Image.open(p).convert("RGB"), Image.open(p2).convert("RGB")
        b = b.resize((a.width, round(b.height * a.width / b.width)), Image.Resampling.LANCZOS)
        g = Image.new("RGB", (a.width, a.height + b.height), (255, 255, 255))
        g.paste(a, (0, 0)); g.paste(b, (0, a.height))
        g.save(out, "PNG")
        kq = {**kq, "kind": "table-stitched", "row": kq["row"] + " ‖ " + kq2["row"][:60],
              "stitch_with": tim2["k"]}
    elif p != out:
        p.replace(out)
    for _, q, _, _ in da:
        if q != out and q.exists():
            q.unlink()
    return kq, ""


# ---- Chụp DANH SÁCH MOBILE (arena.ai: div-list, không phải <table>) -----------
# arena.ai có giao diện mobile riêng: danh sách <div> hàng-thẻ, mỗi hàng full-width
# 380px cho màn 414px. Ba site còn lại (tbench/swebench/aa) KHÔNG có — bảng của
# chúng giữ nguyên bề ngang trong khung cuộn ngang, vào viewport hẹp chỉ thấy lát
# cắt bên trái, nên chúng đi đường desktop.
#
# Hai cái khó riêng ở đây:
#   1. Danh sách chỉ hiện ~11-12 mục đầu và KHÔNG tải thêm khi cuộn — đã thử cả
#      `.scrollTop` lẫn `mouse.wheel()` thật, chờ tới 3.6s mỗi lần, nội dung không
#      đổi. (Có ô tìm kiếm riêng để nhảy tới model sâu, nhưng lái nó qua Playwright
#      không ổn định giữa các lần tải.) Nên: model không có trong danh sách đầu thì
#      trả None, `find_and_capture` rơi về bảng desktop — tìm được ở bất kỳ hạng nào.
#   2. Không có thẻ ngữ nghĩa (không <tr>, không role=row), chỉ là <div> + class
#      Tailwind. Nhận diện TỔNG QUÁT (nhóm anh em cùng cha cùng chuỗi class, >=5
#      phần tử, kích thước dạng một hàng) thay vì khoá cứng một chuỗi class — đo
#      đúng trên cả arena-code lẫn arena-text, hai giao diện hơi khác nhau.
_JS_NORM_DS = """
const norm = s => (s||'').toLowerCase().replace(/[\\s\\-_.]+/g,'');
// Cung dieu kien bien nhu `matchesModel` trong _JS_NORM — xem chu thich o do (LOW-177).
const matchesModel = (hay, nm) => {
  for (let i = hay.indexOf(nm); i >= 0; i = hay.indexOf(nm, i + 1)) {
    const c = hay.charCodeAt(i + nm.length);
    if (!(c >= 48 && c <= 57)) return true;
  }
  return false; };
const rect = el => { const r = el.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; };
const timDanhSach = (models) => {
  const chuaModel = els => {
    if (!models || !models.length) return false;
    const t = norm(els.map(e => e.textContent || '').join(' '));
    return models.some(m => matchesModel(t, norm(m)));
  };
  const groups = new Map();
  // div/li/a: openrouter dung <ol><li>, arena dung <div> — quet ca ba, dung khoa
  // cung mot loai the.
  document.querySelectorAll('div,li,a').forEach(el => {
    const p = el.parentElement; if (!p) return;
    if (!groups.has(p)) groups.set(p, new Map());
    const m = groups.get(p);
    const kk = el.tagName + '|' + (el.className||'').toString().trim();
    if (!m.has(kk)) m.set(kk, []);
    m.get(kk).push(el);
  });
  let best = null;
  for (const [, m] of groups) {
    for (const [, els] of m) {
      if (els.length < 5) continue;
      const r0 = els[0].getBoundingClientRect();
      if (r0.width < 200 || r0.width > 500 || r0.height < 25 || r0.height > 120) continue;
      // Hang phai CO CHU. openrouter co dung 10 <div class="flex flex-col"> rong
      // lam khung bo cuc, dung kich thuoc hang that -> khong loc thi vo nham
      // chung roi bao "khong thay model".
      if (els.filter(e => (e.textContent||'').trim().length > 2).length < 5) continue;
      // Nhom CHUA MODEL luon thang nhom dong hon: openrouter co thanh dieu huong
      // 12 muc dung dang mot hang, con cot xep hang that chi 5 hang.
      const diem = [chuaModel(els) ? 1 : 0, els.length];
      if (!best || diem[0] > best.diem[0] || (diem[0] === best.diem[0] && diem[1] > best.diem[1]))
        best = Object.assign(els, {diem});
    }
  }
  return best;
};
// Moi nhom CUNG DANG voi nhom tot nhat (cung tag+class, khac cha) — openrouter
// chia top-10 thanh hai <ol> canh nhau, moi cot 5 hang.
const nhomCungDang = (models) => {
  const best = timDanhSach(models); if (!best) return [];
  const dau = best[0];
  const chuKy = dau.tagName + '|' + (dau.className||'').toString().trim();
  const theoCha = new Map();
  for (const e of document.querySelectorAll(dau.tagName)) {
    if (e.tagName + '|' + (e.className||'').toString().trim() !== chuKy) continue;
    const r = e.getBoundingClientRect();
    if (r.height < 10) continue;
    const p = e.parentElement; if (!p) continue;
    if (!theoCha.has(p)) theoCha.set(p, []);
    theoCha.get(p).push(e);
  }
  return [...theoCha.values()].filter(v => v.length >= 3)
    .sort((a, b) => { const ra = a[0].getBoundingClientRect(), rb = b[0].getBoundingClientRect();
                      return (ra.y - rb.y) || (ra.x - rb.x); });
};
const khungCuonDs = el => { for (let e = el; e; e = e.parentElement) {
  const cs = getComputedStyle(e);
  if (/(auto|scroll)/.test(cs.overflowY) && e.scrollHeight > e.clientHeight + 4) return e; }
  return null; };
"""

# `cuon=true`: dua hang model vao giua khung nhin roi do; `false`: chi do lai.
# `cot`: -1 = nhom chua model; >=0 = nhom thu may trong cac nhom CUNG DANG (dung
# de lay not cac cot con lai roi ghep doc, xem `capture_list_clean`).
_JS_DS = _JS_NORM_DS + """
([models, cuon, cot]) => {
  const els = cot >= 0 ? (nhomCungDang(models)[cot] || null) : timDanhSach(models);
  if (!els) return null;
  let idx = -1, model = null;
  for (const m of models) {
    const nm = norm(m);
    idx = els.findIndex(e => matchesModel(norm(e.innerText || e.textContent), nm));
    if (idx >= 0) { model = m; break; }
  }
  // Cot duoc goi DICH DANH (cot >= 0) thi khong doi phai co model: do la cac cot
  // con lai cua cung mot bang, lay tron de ghep doc.
  if (idx < 0) { if (cot < 0) return null; idx = 0; }
  if (cuon) { els[idx].scrollIntoView({block: 'center'}); return {cuon_roi: true}; }
  const cells = (els[idx].innerText || '').trim().split('\\n').map(s => s.trim()).filter(Boolean);
  const hang = (cells.find(c => /^#?\\d{1,3}$/.test(c)) || '').replace('#', '');
  const kc = khungCuonDs(els[0]);
  const r = kc ? kc.getBoundingClientRect() : {x:0, y:0, width:window.innerWidth, height:window.innerHeight};
  return {idx, model, rank: hang ? parseInt(hang, 10) : null,
          row: cells.join(' | ').slice(0, 160), rows: els.map(rect),
          region: {x: Math.max(0,r.x), y: Math.max(0,r.y),
                 w: Math.min(window.innerWidth, r.x+r.width) - Math.max(0,r.x),
                 h: Math.min(window.innerHeight, r.y+r.height) - Math.max(0,r.y)}};
}
"""


def _capture_one_column(page, models: list, out: Path, dpr: int, cot: int = -1):
    """Chụp một cột danh sách: `cot=-1` là cột chứa model (và khoanh hàng model),
    `cot>=0` là cột thứ N trong các cột cùng dạng (chụp trọn, không khoanh).
    Trả về `(thong_tin, ly_do)`."""
    do = page.evaluate(_JS_DS, [models, False, cot])
    if not do:
        return None, "mất dấu danh sách"
    idx, rows, vung = do["idx"], do["rows"], do["region"]
    dau = 0 if idx <= TOP_DEFAULT else max(0, idx - ON_MODEL)
    cuoi = idx if cot < 0 else len(rows) - 1
    cao = lambda k: rows[k]["y"] + rows[k]["h"] - rows[dau]["y"]
    while cuoi + 1 < len(rows) and cao(cuoi + 1) <= HEIGHT_MAX_CSS:
        cuoi += 1
    hien = [k for k in range(dau, cuoi + 1)
            if rows[k]["y"] >= vung["y"] - 1 and rows[k]["y"] + rows[k]["h"] <= vung["y"] + vung["h"] + 1]
    if not hien or (cot < 0 and idx not in hien):
        return None, f"hàng model không nằm trong vùng nhìn ({len(hien)}/{cuoi-dau+1} hàng hiện)"
    dau, cuoi = hien[0], hien[-1]
    out.parent.mkdir(parents=True, exist_ok=True)
    r = _hand({"x": rows[dau]["x"], "w": rows[dau]["w"], "y": rows[dau]["y"],
               "h": rows[cuoi]["y"] + rows[cuoi]["h"] - rows[dau]["y"]}, vung)
    _capture(page, r, out)
    if cot < 0:
        row = rows[idx]
        _highlight(out, row["x"] - r["x"], row["y"] - r["y"], row["w"], row["h"], dpr)
    return {"model": do["model"], "rank": do["rank"], "row": do["row"]}, ""


def capture_list_clean(page, models: list, out: Path, dpr: int = DPR):
    """Danh sách hàng-thẻ (`<div>`/`<li>`) thay cho `<table>`: arena.ai ở khung
    mobile, openrouter.ai ở khung desktop.

    Chụp dải hàng quanh model, khoanh hàng model. Cột quá ngang mà trang còn cột
    CÙNG DẠNG (openrouter dàn top-10 thành hai `<ol>` 5 hàng cạnh nhau, một cột
    rộng/cao ~1.75) thì GHÉP DỌC các cột lại — cùng một cách `capture_board` ghép hai
    bảng, để ra khối dọc vừa khổ hero thay vì dải ngang."""
    # Trang KHONG co danh sach hang-the nao (tbench/swebench/gaia/opencompass chi
    # co <table>): ve NGAY. Khong bail som thi moi nguon nhu vay ngon tron 12s poll
    # cua tran 150s — do that: tbench mat 37s mot luot vi cho vo ich.
    if not page.evaluate(_JS_NORM_DS + "() => !!timDanhSach(null)"):
        return None, "trang không có danh sách hàng-thẻ nào"
    # Co danh sach roi thi doi CHU hien trong hang: openrouter dung hang ~3s moi co
    # chu (dung hang rong truoc do). Poll thay vi cho cung mot con so.
    t0 = time.time()
    while time.time() - t0 < 10:
        if page.evaluate(_JS_DS, [models, True, -1]):
            break
        page.wait_for_timeout(700)
    else:
        return None, "không có model nào trong danh sách đang hiển thị"
    page.wait_for_timeout(350)
    kq, ly_do = _capture_one_column(page, models, out, dpr)
    if not kq:
        return None, ly_do
    with Image.open(out) as im:
        r = im.width / im.height
    so_cot = page.evaluate(_JS_NORM_DS + "(models) => nhomCungDang(models).length", models)
    if r <= RATIO_FIT or so_cot < 2:
        return {"kind": "list", **kq, "has_logo": False}, ""
    # Qua ngang + con cot cung dang: ghep doc theo dung thu tu tren trang.
    cot_model = page.evaluate(_JS_NORM_DS + """
        (models) => { const b = timDanhSach(models);
                      return nhomCungDang(models).findIndex(g => g[0] === b[0]); }""", models)
    manh, tam = [], []
    for i in range(so_cot):
        if i == cot_model:
            manh.append(out)
            continue
        p = out.with_suffix(f".c{i}.png")
        k2, _ = _capture_one_column(page, models, p, dpr, cot=i)
        if k2:
            manh.append(p); tam.append(p)
    if len(manh) < 2:
        return {"kind": "list", **kq, "has_logo": False}, ""
    ims = [Image.open(p).convert("RGB") for p in manh]
    rong = max(i.width for i in ims)
    ims = [i if i.width == rong else i.resize((rong, round(i.height * rong / i.width)), Image.Resampling.LANCZOS)
           for i in ims]
    g = Image.new("RGB", (rong, sum(x.height for x in ims)), (255, 255, 255))
    y = 0
    for anh in ims:                     # `i` da la chi so o tren trong cung ham (LOW-308)
        g.paste(anh, (0, y)); y += anh.height
    for anh in ims:
        anh.close()
    g.save(out, "PNG")
    for p in tam:
        p.unlink(missing_ok=True)
    return {"kind": "list-stitched", **kq, "has_logo": False}, ""



def capture_svg(page, models: list, out: Path, dpr: int = DPR):
    tim = page.evaluate(_JS_SVG, [models, True])
    if not tim:
        return None, "không có nhãn SVG chứa tên model"
    page.wait_for_timeout(400)
    do = page.evaluate(_JS_SVG, [models, False])
    if not do:
        return None, "nhãn SVG mất sau khi cuộn"
    out.parent.mkdir(parents=True, exist_ok=True)
    s = do["svg"]
    r = _hand({"x": s["x"], "y": s["y"], "w": s["w"], "h": min(s["h"], HEIGHT_MAX_CSS)}, do["region"])
    _capture(page, r, out)
    n = do["label_rect"]
    _highlight(out, n["x"] - r["x"], n["y"] - r["y"], n["w"], n["h"], dpr)
    return {"kind": "svg", "model": tim["model"], "rank": None, "row": tim["row"], "has_logo": False}, ""


def capture_logo(page, out: Path):
    """Logo model từ chính hàng vừa khớp (đã đánh dấu data-xh-logo). Best-effort."""
    try:
        el = page.query_selector("[data-xh-logo]")
        if not el:
            return None
        el.scroll_into_view_if_needed()
        el.screenshot(path=str(out))
        return out if out.exists() and out.stat().st_size > 200 else None
    except Exception:                                        # noqa: BLE001
        return None


# ---- Nấc trước thẻ chữ: chụp bảng của CHÍNH trang nguồn bài --------------------
# Ông Chủ 23/09/2026 (LOW-385): *"sao chúng ta ko chụp luôn trang này mà lại dùng
# text nhỉ?"* — *"hình ảnh chart sẽ luôn được ưu tiên hơn text thuần chứ"*.
#
# Chỉ lấy phần tử THẬT SỰ là bảng/đồ thị. `capture_chart.PICK_DEFAULT` còn có
# `img`/`picture` và lui về chụp cả trang — ở đây thì không: chụp cả trang một
# bài bất kỳ rồi gọi nó là "ảnh xếp hạng" đúng là lỗi LOW-179 cấm.
BOARD_PICK = ["table", "figure", "svg", "canvas"]


def source_page_is_board(url: str) -> bool:
    """Hàm THUẦN: `link gốc` của bài có phải một trang BẢNG XẾP HẠNG không?

    Chỉ tính khi tên miền ĐÃ nằm trong registry `SOURCE` — không chụp đại chart
    của một bài bất kỳ (LOW-179). Đo 23/09/2026 trên 23 bài đã rơi về thẻ chữ:
    4 bài có link gốc là trang bảng, và cả 4 đều thuộc tên miền khai ở đây —
    artificialanalysis ×3 (`/leaderboards/models`, `/text-to-speech`,
    `/speech-to-text`), arena.ai ×1 (`/leaderboard/code/webdev`). Ba trong số đó
    là bảng KHÔNG có mục riêng trong registry, nên vòng đi nguồn không bao giờ
    chạm tới chúng dù bài lấy tin từ đúng trang ấy.
    """
    return bool(url) and any(re.search(n["domain_pattern"], url, re.I) for n in SOURCE)


def capture_source_board(br, url: str, out: Path, in_log=print) -> dict | None:
    """Chụp bảng/đồ thị của chính trang nguồn bài. None khi trang không có cái nào.

    KHÔNG khoanh hàng: nấc này chạy đúng lúc không nguồn nào khớp được tên model,
    nên ảnh ra là cả bảng. Vì vậy nó mang `kind` riêng (`board-page`) — `alt` phải
    nói "chưa khoanh hàng", không được đội lốt ảnh đã khoanh (bài học LOW-177).

    Dùng phép đo bề ngang của `capture_chart` (`MEASURE_JS` + `frame_can`): nới
    khung cho vừa chart rồi mới chụp, vì bề ngang của một bảng LÀ nội dung
    (luật Ông Chủ 04/09/2026). Không gọi `capture_chart.capture` vì hàm đó tự mở
    một phiên playwright riêng — lồng vào phiên đang mở ở đây thì nổ — và nó
    `sys.exit` khi chụp thiếu, tức giết cả engine thay vì lui về thẻ chữ.
    """
    import capture_chart
    ctx = None
    try:
        rong = capture_chart.EMPTY_MARK
        for _ in range(2):          # lượt 1 đo, lượt 2 (nếu cần) nới khung rồi chụp lại
            if ctx:
                ctx.close()
            ctx = br.new_context(viewport={"width": rong, "height": 1400},
                                 device_scale_factor=DPR, user_agent=UA)
            pg = ctx.new_page()
            # `domcontentloaded` chứ không `networkidle`: networkidle không bao giờ
            # đạt trên trang có quảng cáo + websocket (sự cố 0b395ad, TICKET_TEMPLATE).
            pg.goto(url, wait_until="domcontentloaded", timeout=40000)
            pg.wait_for_timeout(1500)                # font + animation của chart
            do = pg.evaluate(capture_chart.MEASURE_JS, BOARD_PICK)
            if not do["sel"]:
                in_log(f"[xep_hang] trang nguồn {url}: không có bảng/đồ thị nào đủ lớn")
                return None
            rong_moi = capture_chart.frame_can(do["w"], rong)
            if rong_moi <= rong:
                break
            in_log(f"[xep_hang] trang nguồn: nới khung {rong} -> {rong_moi}px cho vừa bảng")
            rong = rong_moi
        el = pg.query_selector(do["sel"])
        if not el:
            return None
        # CAT BOT CHIEU CAO, GIU NGUYEN BE NGANG. Do that 23/09/2026: bang cua
        # artificialanalysis chup tron ven ra 2796x29920 (ti le 1:10,7) — mot tam
        # khong vai nao dung duoc o kho 4:5, va nang vo ich. Be ngang thi KHONG
        # duoc cham (luat Ong Chu 04/09: be ngang cua bang LA noi dung); chieu cao
        # cat o `HEIGHT_MAX_CSS` nghia la giu phan DAU bang — dung thu can xem.
        el.evaluate("(e, h) => { e.style.maxHeight = h + 'px'; e.style.overflow = 'hidden'; }",
                    HEIGHT_MAX_CSS)
        try:
            el.scroll_into_view_if_needed(timeout=8000)
        except Exception:                                    # noqa: BLE001
            # artificialanalysis /text-to-speech: bang nam trong khung cuon rieng,
            # `scroll_into_view_if_needed` het 30s ma khong bao gio "on dinh".
            in_log("[xep_hang] trang nguồn: cuộn tới bảng hụt, thử scrollIntoView thẳng")
            el.evaluate("e => e.scrollIntoView({block: 'start'})")
        pg.wait_for_timeout(400)
        out.parent.mkdir(parents=True, exist_ok=True)
        el.screenshot(path=str(out))
        rong_that, mo_ta = role.active_rules().is_blank_image(Image.open(out).convert("RGB"))
        if rong_that:
            in_log(f"[xep_hang] trang nguồn: ảnh ra RỖNG ({mo_ta}) — bỏ")
            out.unlink(missing_ok=True)
            return None
        bang = (pg.title() or "").strip()[:60] or "trang nguồn của bài"
        image_provenance.stamp_file(out, "ranking_board_page", source="source-page",
                                    board=bang, url=url)
        im = Image.open(out)
        in_log(f"[xep_hang] chụp bảng của CHÍNH trang nguồn ({do['sel']}, {im.width}x{im.height}) "
               f"— chưa khoanh hàng: {bang}")
        return {"file_path": str(out), "kind": "board-page", "source": "source-page",
                "site": _domain_of(url), "board": bang, "rank": None, "url": url, "row": ""}
    except Exception as e:                                   # noqa: BLE001
        in_log(f"[xep_hang] trang nguồn {url}: {type(e).__name__}: {str(e)[:80]}")
        return None
    finally:
        if ctx:
            try:
                ctx.close()
            except Exception:                                # noqa: BLE001
                pass


def _domain_of(url: str) -> str:
    from urllib.parse import urlparse
    return (urlparse(url).netloc or url).replace("www.", "").upper()


# ---- Thẻ dự phòng: tên model + #hạng + logo + site ------------------------------
def fallback_card(model: str, hang, site: str, bang: str, out: Path, brand: str = "donniechublog",
                 logo: Path | None = None) -> Path:
    """Khi không nguồn nào chụp được. Không phải minh hoạ — là một THẺ DỮ LIỆU:
    đúng bốn thứ Ông Chủ chốt, không thêm gì. Nội dung dồn lên NỬA TRÊN có chủ ý:
    thẻ này là `--image` của card.py, hook sẽ đè lên nửa dưới qua màn tối."""
    import card
    w, h = 1200, 1500
    b = card.set_brand(brand)
    im = Image.new("RGB", (w, h), card.BG)
    d = ImageDraw.Draw(im)
    f_nho = card._f(card.F_MONO, 30)
    f_hang = card._f(card.F_HERO, 420, 700)
    f_ten = card._f(card.F_QUOTE, 84)
    f_phu = card._f(card.F_QUOTE_REG, 34)
    def center(txt, font, y, mau):
        """Ve chu can giua theo INK BBOX that (Oswald 420pt bao cao hon ink ~25%,
        cong theo font.size la de chu sau de len chu truoc — loi thay tren the
        thu 06/09). Tra ve y duoi cung cua ink."""
        l, t, r, bt = d.textbbox((0, 0), txt, font=font)
        d.text((w / 2 - (r + l) / 2, y - t), txt, font=font, fill=mau)
        return y + (bt - t)

    y = 140
    nhan = f"{site} · {bang}".upper()
    y = center(nhan, f_nho, y, card.CYAN) + 70
    if logo and Path(logo).exists():
        try:
            lg = Image.open(logo).convert("RGBA")
            lg.thumbnail((160, 160), Image.Resampling.LANCZOS)
            im.paste(lg, (w // 2 - lg.width // 2, y), lg)
            y += lg.height + 50
        except Exception:                                    # noqa: BLE001
            pass
    # Co hang: "#N" la nhan vat chinh, ten model duoi. Khong hang: ten model la
    # nhan vat chinh — khong bia mot chu "TOP" vo nghia.
    if hang:
        y = center(f"#{hang}", f_hang, y, card.FG) + 60
        f_ten_dung = f_ten
    else:
        f_ten_dung = card._f(card.F_QUOTE, 120)
        y += 120
    while d.textlength(model, font=f_ten_dung) > w - 160 and f_ten_dung.size > 44:
        f_ten_dung = card._f(card.F_QUOTE, f_ten_dung.size - 6)
    y = center(model, f_ten_dung, y, card.FG) + 44
    d.line([(w // 2 - 60, y), (w // 2 + 60, y)], fill=card.CYAN, width=4)
    y += 44
    center(f"trên bảng xếp hạng {bang}", f_phu, y, card.MUTED)
    handle = b["handle"]
    d.text((w // 2 - d.textlength(handle, font=f_nho) / 2, h - 110), handle, font=f_nho, fill=card.MUTED)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG")
    image_provenance.stamp_file(out, "ranking_card", model=model, rank=hang, source=site, board=bang)
    return out


def _card_fields(models: list, nguon_ds: list) -> tuple:
    """(tên model để IN, nguồn ghi trên thẻ) cho THẺ DỰ PHÒNG. Hàm THUẦN.

    Hai chỗ lệch trên thẻ 23/09 (LOW-381), cùng một tấm:

      - nguồn lấy `nguon_ds[0]`, tức bảng xếp ĐẦU theo điểm — thẻ ghi
        "ARTIFICIALANALYSIS.AI · Intelligence Index" cho một tin mà hook nói
        LiveBench (AA lọt vào vì LINK bài trỏ tới đó). Bảng được gọi tên ngay ở
        TIÊU ĐỀ mới là bảng bài đang nói, nên `in_title` đi trước.
      - tên model in nguyên slug `claude-opus-5-5-max` thay vì `Claude Opus 5.5`.
    """
    n = (next((x for x in nguon_ds if x.get("in_title")), None)
         or next((x for x in nguon_ds if x.get("mentioned")), None)
         or (nguon_ds[0] if nguon_ds else SOURCE[0]))
    return model_name.display_name(models[0]) or models[0], n


# ---- Điều phối --------------------------------------------------------------------
class SessionCapture:
    """Mot phien chromium cho ca luot di nguon: hai context (mobile thu truoc, desktop
    lui ve) tao LAZY va dung lai giua cac nguon. Viewport desktop cao san bang
    tran cua so chup: khong doi kich thuoc giua chung, doi la trang reflow, bbox
    do truoc do lech. Tach khoi find_and_capture 07/09/2026 (118 dong, ba closure)."""

    def __init__(self, br):
        self.br = br
        self._ctx = {}
        self._pg = {}

    def page(self, khung: str):
        if khung not in self._pg:
            if khung == "desktop":
                self._ctx[khung] = self.br.new_context(
                    viewport={"width": 2400, "height": HEIGHT_MAX_CSS + 250},
                    device_scale_factor=DPR, user_agent=UA)
            else:
                self._ctx[khung] = self.br.new_context(
                    viewport=MOBILE_VIEWPORT, device_scale_factor=MOBILE_DPR,
                    is_mobile=True, has_touch=True, user_agent=MOBILE_UA)
            self._pg[khung] = self._ctx[khung].new_page()
        return self._pg[khung]

    @staticmethod
    def attempt(pg, models, out, dpr, vua_khung, giay):
        """Mot luot tren MOT khung: danh sach hang-the -> bang -> chart SVG."""
        _change_board(pg, giay)
        # Danh sach truoc bang: trang co ca hai (arena, aa, livebench o khung
        # mobile) thi danh sach la ban da xep lai cho man doc, hon han bang.
        kq, ly_do = capture_list_clean(pg, models, out, dpr)
        if kq:
            return kq, ly_do
        kq2, ly_do2 = capture_board(pg, models, out, dpr, vua_khung)
        if kq2:
            return kq2, ly_do2
        kq3, ly_do3 = capture_svg(pg, models, out, dpr)
        return kq3, f"danh sách: {ly_do}; bảng: {ly_do2}; svg: {ly_do3}"


def _try_source(phien: SessionCapture, n: dict, models: list, out: Path, in_log):
    """Mot nguon: mo trang (mobile mac dinh, desktop neu nguon danh dau), bo qua
    khi bi chan, thu chup; mobile hut thi mo lai o desktop. Tra (kq, ly_do, pg);
    kq None + ly_do None nghia la bo qua (da in log)."""
    # Mobile la MAC DINH cho moi nguon; `viewport: desktop` chi danh dau nhung
    # nguon DA DO la mobile khong dung duoc (ly do ghi ngay tren muc trong
    # NGUON). Go co ra thi van chay dung, chi ton them mot luot mo trang.
    chi_desktop = n.get("viewport") == "desktop"
    pg = phien.page("desktop" if chi_desktop else "mobile")
    try:
        resp = pg.goto(n["url"], wait_until="domcontentloaded", timeout=40000)
        # Cloudflare challenge / 429: khong doi 14s vo ich, sang nguon khac ngay.
        # (arena.ai tra 429 "Just a moment..." sau ~25 luot thu tu mot IP trong
        # mot gio — may local luc dev; server moi bai goi mot lan.)
        pg.wait_for_timeout(800)
        # Phep thu nam o `browser_session.got_block` tu 12/09/2026: `capture_page` chup
        # khoi lead cung hoi dung cau nay, chep doi thi mot ben vá mà bên kia không.
        ly = got_block(pg.title() or "", resp.status if resp else None)
        if ly:
            in_log(f"[xep_hang] {n['id']}: nguồn chặn ({ly}), bỏ qua")
            return None, None, pg
        # KHUNG MOBILE TRUOC cho MOI nguon (Ong Chu 06/09/2026: "vào trang
        # nào chụp thì cũng hãy duyệt theo kích thước mobile, vì hình luôn
        # đăng ở ratio 4:5"). 414px x DPR3 = 1242px, gan khop kho the
        # 1200px nen chu gan nhu khong bi co; desktop 2400 x DPR2 = 4800px
        # phai co bon lan, chu be lai bay nhieu. `vua_khung=True`: o khung
        # hep phai BO bang rong hon khung — no nam trong khung cuon ngang,
        # chup ra chi duoc lat cat ben trai (tbench/swebench/bfcl/gaia/
        # opencompass). Hut thi mo lai chinh nguon do o khung desktop.
        if chi_desktop:
            kq, ly_do = phien.attempt(pg, models, out, DPR, False, 14)
        else:
            kq, ly_do = phien.attempt(pg, models, out, MOBILE_DPR, True, 8)
            if not kq:
                pg = phien.page("desktop")
                pg.goto(n["url"], wait_until="domcontentloaded", timeout=40000)
                pg.wait_for_timeout(800)
                kq, ly_do2 = phien.attempt(pg, models, out, DPR, False, 14)
                ly_do = f"mobile: {ly_do}; desktop: {ly_do2}"
    except Exception as e:                           # noqa: BLE001
        in_log(f"[xep_hang] {n['id']}: {type(e).__name__}: {str(e)[:80]}")
        return None, None, pg
    return kq, ly_do, pg


# Chup bang xep hang ep srgb de mau tat dinh giua cac lan chup — KHAC bo args
# cua browser_pass/gnews, nen `PhienBrowser` giu tien trinh rieng cho bo nay
# (xem browser_session.py). Gop lam mot phai co y chot srgb cho ca engine.
ARGS_CAPTURE = ("--no-sandbox", "--disable-dev-shm-usage", "--force-color-profile=srgb")


_VERSION_TOKEN = re.compile(r"\d+(?:\.\d+)*")


def row_carries_version(models: list, kq: dict) -> bool:
    """LOW-338: hàng khoanh được phải mang PHIÊN BẢN của bài.

    `extract_model("… Qwen Image 2.1")` -> ['Qwen Image 2.1', 'Qwen Image']. Ứng viên
    ngắn bỏ mất "2.1" nên khớp `qwen-image-edit`, `qwen-image-edit-2511`,
    `qwen-image-prompt-extend`: bìa nói 2.1 mà ảnh khoanh một bản khác. Bảng không có
    hàng của model đó thì không có ảnh khoanh, không được khoanh hàng cùng họ.

    Ứng viên khớp còn giữ đủ số phiên bản của tên đầy đủ thì hợp lệ. Ngược lại hàng
    phải chứa các số đó (chỉ xét ô có chữ, tránh ăn nhầm điểm/hạng), cho phép
    "2.1" / "2-1" / "2 1" / "21".
    """
    if not models or not kq:
        return True
    full_name = models[0]
    tokens = _VERSION_TOKEN.findall(full_name)
    if not tokens:
        return True
    candidate = kq.get("model") or ""
    if all(t in _VERSION_TOKEN.findall(candidate) for t in tokens):
        return True
    text_cells = " ".join(c for c in str(kq.get("row") or "").split("|") if re.search(r"[A-Za-z]", c))
    for t in tokens:
        parts = t.split(".")
        pat = r"(?<!\d)" + r"[.\-_ ]?".join(re.escape(p) for p in parts) + r"(?!\d)"
        if not re.search(pat, text_cells):
            return False
    return True


def _drop_row_without_version(models: list, kq, ly_do, out: Path):
    """Huỷ ảnh chụp nếu hàng khoanh không mang phiên bản của bài (LOW-338); trả
    (kq, ly_do) để nhánh "bỏ nguồn" sẵn có xử lý tiếp."""
    if kq and not row_carries_version(models, kq):
        out.unlink(missing_ok=True)
        return None, (f"hàng {str(kq.get('row'))[:60]!r} không mang phiên bản của bài "
                      f"({models[0]!r}); khớp lỏng {kq.get('model')!r}")
    return kq, ly_do


def arena_first(models: list, out_dir: Path, in_log, extra_urls=()) -> list:
    """LOW-337 (Ong Chu 21/09/2026): *"cu lay hinh tu tai khoan twitter cua arena.ai la chuan
    nhat, khi noi toi benchmark, ko tim duoc thi moi dung bang cua ben khac"*; 22/09/2026: *"mien
    la tin ve model release, cu lay tu arena.ai dau tien"* — nen `fallback_rounds._capture_ranking`
    goi ham nay cho MOI tin tach duoc ten model, khong can browser. Hong gi cung khong chan duong
    cu: tra [] va di chup cac trang bang nhu truoc."""
    try:
        import arena_x
        return arena_x.find_arena_images(models, out_dir, in_log, extra_urls=extra_urls)
    except Exception as e:                                   # noqa: BLE001
        in_log(f"[xep_hang] arena X hong ({type(e).__name__}), di chup trang bang")
        return []


def _board_page_result(phien, models: list, source_url: str, out_dir: Path, in_log) -> dict | None:
    """Nac LOW-385, dung chung cho hai ham dieu phoi: khong nguon nao khoanh duoc
    hang thi chup lay bang cua CHINH trang nguon bai truoc khi in the chu."""
    if not source_page_is_board(source_url):
        return None
    out = out_dir / f"{state_paths.RANKING_IMAGE_PREFIX}source_page.png"
    kq = capture_source_board(phien.br, source_url, out, in_log)
    if kq:
        kq["model"] = model_name.display_name(models[0]) or models[0]
        kq["mentioned"] = True          # chinh trang bai dang dan, khong the "bang khac"
    return kq


def find_and_capture(models: list, nguon_ds: list, out_dir: Path, brand: str = "donniechublog",
                hang_goi_y=None, in_log=print, phien_browser=None, source_url: str = "") -> dict:
    """Đi qua từng nguồn, nguồn nào ra ảnh khoanh được model thì dừng; không nguồn
    nào ra thì dựng thẻ dự phòng. Luôn trả về dict mô tả ảnh (file_path, kind, source,
    site, board, rank, model, url). `models` phải khác rỗng."""
    arena = arena_first(models, out_dir, in_log)
    if arena:
        return arena[0]
    from browser_session import session_or_new
    t0 = time.time()
    logo = None
    kq_cuoi = None
    # `closing(...)` chu khong phai `br.close()` o cuoi than: ban cu chi dong
    # browser tren duong THANH CONG, nen mot ngoai le giua chung (mot nguon doi
    # DOM, mot `page.evaluate` nem) de lai tien trinh chromium song. Chay 7 tin
    # mot sang la 7 lan nhu vay.
    nguon_ds = _sources_proving_story(nguon_ds, in_log)
    with session_or_new(phien_browser) as _ph:
        phien = SessionCapture(_ph.browser(ARGS_CAPTURE))
        for n in nguon_ds:
            if time.time() - t0 > TIME_LIMIT:
                in_log(f"[xep_hang] hết giờ ({TIME_LIMIT}s), dừng ở {n['id']}")
                break
            out = out_dir / f"{state_paths.RANKING_IMAGE_PREFIX}{n['id']}.png"
            kq, ly_do, pg = _try_source(phien, n, models, out, in_log)
            if kq is None and ly_do is None:
                continue
            kq, ly_do = _drop_row_without_version(models, kq, ly_do, out)
            if not kq:
                # Khop duoc hang nhung khong chup noi bang: van vot lay logo model
                # tu chinh hang do cho THE DU PHONG (duong duy nhat the do chay toi).
                if logo is None:
                    logo = capture_logo(pg, out_dir / f"{state_paths.RANKING_IMAGE_PREFIX}logo.png")
                in_log(f"[xep_hang] {n['id']}: bỏ — {ly_do}")
                continue
            image_provenance.stamp_file(out, "ranking_capture", model=kq["model"], source=n["id"],
                                  site=n["site"], board=n["board"], rank=kq.get("rank"), url=n["url"])
            im = Image.open(out)
            in_log(f"[xep_hang] {n['id']}: khớp {kq['model']!r} hàng #{kq.get('rank') or '?'} "
                   f"({manifest_values.ranking_kind_label(kq['kind'])}, {im.width}x{im.height}) — {kq['row'][:70]}")
            kq_cuoi = {"file_path": str(out), "kind": kq["kind"], "source": n["id"], "site": n["site"],
                       "board": n["board"], "rank": kq.get("rank") or hang_goi_y, "model": kq["model"],
                       "url": n["url"], "row": kq["row"], "logo": str(logo) if logo else None,
                       "mentioned": bool(n.get("mentioned", True))}
            break
        if not kq_cuoi:
            kq_cuoi = _board_page_result(phien, models, source_url, out_dir, in_log)
    if kq_cuoi:
        return kq_cuoi
    card_name, n = _card_fields(models, nguon_ds)
    out = out_dir / f"{state_paths.RANKING_IMAGE_PREFIX}card.png"
    fallback_card(card_name, hang_goi_y, n["site"], n["board"], out, brand, logo)
    in_log(f"[xep_hang] không nguồn nào chụp được → thẻ dự phòng {card_name} #{hang_goi_y or '?'}")
    return {"file_path": str(out), "kind": "card", "source": n["id"], "site": n["site"], "board": n["board"],
            "rank": hang_goi_y, "model": card_name, "url": n["url"], "logo": str(logo) if logo else None}


MAX_XH = 3      # tran so anh xep hang lay cho MOT tin (cac nguon `independent`)


def _rank_of(kq: dict, n: dict, hang_goi_y):
    """Hang ghi vao alt/manifest cho MOT anh bang xep hang.

    `hang_goi_y` la hang tach tu TIEU DE tin — hang tren MOT bang (bang chinh,
    duoc nhac). Truoc audit lượt 2 (R-r2-5) no lam fallback cho MOI bang: nguon
    kieu svg luon tra hang=None nen XH2/XH3 (bang doc lap, do nang luc khac)
    mang "#1" cua bang khac vao alt — dung loi "khoanh sai hang" ma chuoi commit
    nhieu bang muon tranh. Chi bang chinh moi duoc muon hang tu tieu de.

    Tu LOW-177: anh CHUP DUOC ma khong doc ra so hang o chinh hang da khoanh thi
    de TRONG, khong muon hang o tieu de nua. Truoc do alt ghi "DeepSeek #2" de
    len mot anh dang khoanh hang 9 ("hang #?" trong log nhung van nop) — con so
    o tieu de bien thanh loi khang dinh ve mot tam anh khong chung minh no. The
    du phong (`kind="card"`) thi van duoc: hang do la CHU engine tu in ra the,
    khong phai bang chung chup tu bang nao."""
    if kq.get("rank"):
        return kq["rank"]
    if is_capture(kq.get("kind")):
        return None
    return None if n.get("independent") else hang_goi_y


def source_proves_story(n: dict) -> bool:
    """Nguồn này có đủ tư cách làm ẢNH XẾP HẠNG cho bài không? Hàm THUẦN.

    Chỉ hai loại đủ: bảng bài NHẮC TÊN (`mentioned`) hoặc bảng ĐÚNG CHỦ ĐỀ bài
    (`on_topic` — tin "top 10 OpenRouter" với bảng lượt dùng).

    `independent` KHÔNG phải tư cách. Đo 16/09/2026: với tin HuggingFace thả trọng số,
    ba bảng arena ảnh (`independent: True`) là những nguồn DUY NHẤT lọt qua nếu tính
    `independent` — tức lấy bảng đấu model tạo ảnh minh hoạ cho tin thả trọng số một
    model văn bản. Mà ca `independent` sinh ra để phục vụ (GPT-Image-2.5 lên cả bảng
    tạo ảnh lẫn bảng chỉnh sửa ảnh) thì cả ba bảng đó đã `on_topic=True` rồi, nên
    không mất gì. Việc thật của `independent` nằm ở `_skip_source`: đừng dừng ở thành
    công đầu tiên — khác hẳn "nguồn này có tư cách làm ảnh của bài".

    Nguồn chỉ nằm trong registry theo thứ tự còn lại thì KHÔNG: chụp nó là lấy
    bảng đo THỨ KHÁC làm bằng chứng cho claim của bài. Đó chính là ba bài
    15/09/2026 — tin HuggingFace thả trọng số (325.712 lượt tải, trending 2327)
    ra ảnh bảng LLM Rankings theo lượt dùng của openrouter, một bảng không đo
    lượt tải cũng không đo trending (LOW-179).

    Hết nguồn đủ tư cách thì rơi về THẺ DỰ PHÒNG, không thay bằng bảng khác —
    thẻ là chữ engine tự in, `is_capture("card")` là False nên `needs_ranking_image`
    không ép vai dùng nó.
    """
    return bool(n.get("mentioned") or n.get("on_topic"))


def _sources_proving_story(nguon_ds: list, in_log) -> list:
    """Lọc `nguon_ds` qua `source_proves_story` và NÓI RA đã bỏ những gì — im lặng
    thì "vì sao bài xếp hạng này không có ảnh" lại phải đoán (INV-3)."""
    ok = [n for n in nguon_ds if source_proves_story(n)]
    if len(ok) < len(nguon_ds):
        in_log(f"[xep_hang] bỏ {len(nguon_ds) - len(ok)}/{len(nguon_ds)} nguồn không chứng minh "
               f"được bài (bài không nhắc, không đúng chủ đề, không đo năng lực riêng) — "
               f"còn: {', '.join(n['id'] for n in ok) or 'không nguồn nào, sẽ dựng thẻ dự phòng'}")
    return ok


def _skip_source(n: dict, da_chup_thuong: bool) -> bool:
    """Ham THUAN: co bo qua nguon `n` khong, khi DA co it nhat mot anh "thuong"?

    Tach rieng de test khong can Playwright — day la toan bo "luat chon" cua
    `find_and_capture_many` (tran so luong `toi_da` va het gio nam o vong lap goi
    ham nay, khong phai o day). Nguon `independent` khong bao gio bi luat nay chan —
    no do NANG LUC RIENG, thanh cong o nguon khac khong lam no "du roi".
    """
    return da_chup_thuong and not n.get("independent")


def find_and_capture_many(models: list, nguon_ds: list, out_dir: Path, brand: str = "donniechublog",
                      hang_goi_y=None, in_log=print, toi_da: int = MAX_XH, phien_browser=None,
                      source_url: str = "",
                      arena_checked: bool = False) -> list:
    """Nhu `find_and_capture`, nhung KHONG dung o thanh cong dau tien: nguon mang
    `independent: True` (xem chu thich tai NGUON) la NANG LUC RIENG cua model, cu gang
    lay CA nguon do lan mot nguon "thuong" khac, khong coi thanh cong o nguon nay
    la "du roi". Nguon thuong (khong `independent`) van dung o thanh cong dau tien nhu
    truoc — bon cai swebench/aider/livecodebench/arena-code deu la CACH DO KHAC
    cua CUNG mot nang luc (code), lay them chi lap lai bang chung.

    Ong Chu 09/09/2026, dap lai de xuat "chi lay mot anh xep hang moi tin" tung
    co trong ban dau cua module nay: *"đã làm social media thì làm gì có chuyện
    bị giới hạn ở nguồn tư liệu"* — va hai bang vi du (tao anh / sua anh) *"một
    bảng là top model tạo sinh, một bảng là top model chỉnh sửa, đâu có trùng
    lặp"*. Dung y: khong tu gioi han khi cac nguon KHONG trung nhau.

    Ham nay TACH KHOI `find_and_capture` (khong sua ham do) de khong doi hop dong tra
    ve dict don cua cac noi da goi no (`_ranking_context_edge`, CLI `main()`).

    Tra danh sach KHONG RONG — thẻ dự phòng (1 phan tu) khi khong nguon nao
    chup duoc.

    `arena_checked`: nguoi goi DA hoi @arena roi (khong ra) — khong doc lai X lan nua."""
    arena = [] if arena_checked else arena_first(models, out_dir, in_log)
    if arena:
        return arena[:toi_da]
    from browser_session import session_or_new
    t0 = time.time()
    logo = None
    ket_qua: list = []
    da_chup_thuong = False
    nguon_ds = _sources_proving_story(nguon_ds, in_log)
    with session_or_new(phien_browser) as _ph:
        phien = SessionCapture(_ph.browser(ARGS_CAPTURE))
        for n in nguon_ds:
            if len(ket_qua) >= toi_da:
                in_log(f"[xep_hang] đủ {toi_da} ảnh, dừng")
                break
            if time.time() - t0 > TIME_LIMIT:
                in_log(f"[xep_hang] hết giờ ({TIME_LIMIT}s), dừng ở {n['id']}")
                break
            if _skip_source(n, da_chup_thuong):
                continue                              # da co MOT anh "thuong", nguon khac chi lap lai
            out = out_dir / f"{state_paths.RANKING_IMAGE_PREFIX}{n['id']}.png"
            kq, ly_do, pg = _try_source(phien, n, models, out, in_log)
            if kq is None and ly_do is None:
                continue
            kq, ly_do = _drop_row_without_version(models, kq, ly_do, out)
            if not kq:
                if logo is None:
                    logo = capture_logo(pg, out_dir / f"{state_paths.RANKING_IMAGE_PREFIX}logo.png")
                in_log(f"[xep_hang] {n['id']}: bỏ — {ly_do}")
                continue
            image_provenance.stamp_file(out, "ranking_capture", model=kq["model"], source=n["id"],
                                  site=n["site"], board=n["board"], rank=kq.get("rank"), url=n["url"])
            im = Image.open(out)
            in_log(f"[xep_hang] {n['id']}: khớp {kq['model']!r} hàng #{kq.get('rank') or '?'} "
                   f"({manifest_values.ranking_kind_label(kq['kind'])}, {im.width}x{im.height}) — {kq['row'][:70]}")
            ket_qua.append({"file_path": str(out), "kind": kq["kind"], "source": n["id"], "site": n["site"],
                            "board": n["board"], "rank": _rank_of(kq, n, hang_goi_y), "model": kq["model"],
                            "url": n["url"], "row": kq["row"], "logo": str(logo) if logo else None,
                            "mentioned": bool(n.get("mentioned", True))})
            if not n.get("independent"):
                da_chup_thuong = True
        if not ket_qua:
            kq_trang = _board_page_result(phien, models, source_url, out_dir, in_log)
            if kq_trang:
                ket_qua.append(kq_trang)
    if ket_qua:
        return ket_qua
    card_name, n = _card_fields(models, nguon_ds)
    out = out_dir / f"{state_paths.RANKING_IMAGE_PREFIX}card.png"
    fallback_card(card_name, hang_goi_y, n["site"], n["board"], out, brand, logo)
    in_log(f"[xep_hang] không nguồn nào chụp được → thẻ dự phòng {card_name} #{hang_goi_y or '?'}")
    return [{"file_path": str(out), "kind": "card", "source": n["id"], "site": n["site"], "board": n["board"],
            "rank": hang_goi_y, "model": card_name, "url": n["url"], "logo": str(logo) if logo else None}]


def main() -> int:
    ap = argparse.ArgumentParser(description="Ảnh xếp hạng: chụp bảng đúng nguồn, khoanh đúng model")
    ap.add_argument("--tieu-de", default="", help="Tiêu đề tin (tự tách model + hạng + chủ đề)")
    ap.add_argument("--model", default="", help="Tên model (ghi đè tách từ tiêu đề)")
    ap.add_argument("--hang", type=int, default=None)
    ap.add_argument("--nguon", default="", help="Mã nguồn thử trước (arena-code, tbench, aa-models...)")
    ap.add_argument("--link", default="", help="Link bài, để gợi ý nguồn")
    ap.add_argument("--brand", default="donniechublog")
    ap.add_argument("--ra", required=True, help="Tệp PNG ra")
    a = ap.parse_args()
    models = [a.model] if a.model else extract_model(a.tieu_de)
    if not models:
        sys.exit("Không tách được tên model — truyền --model")
    ds = suggest_sources(a.tieu_de, a.link)
    if a.nguon:
        ds = [n for n in SOURCE if n["id"] == a.nguon] + [n for n in ds if n["id"] != a.nguon]
    ra = Path(a.ra)
    kq = find_and_capture(models, ds, ra.parent / ".xep_hang_tmp", a.brand,
                     a.hang if a.hang is not None else extract_rank(a.tieu_de, models[0]),
                     in_log=lambda s: print(s, file=sys.stderr))
    if not kq:
        sys.exit("Không ra ảnh")
    Path(kq["file_path"]).replace(ra)
    kq["file_path"] = str(ra)
    print(json.dumps(kq, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
