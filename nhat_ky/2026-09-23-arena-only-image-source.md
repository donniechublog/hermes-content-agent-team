# Ảnh xếp hạng chỉ còn lấy từ arena.ai — 23/09/2026

Ticket theo dõi: LOW-389.

Ông Chủ, sau khi xem mấy tấm bảng dựng từ LOW-385: *"vì ảnh ko đẹp nên chúng ta mới chỉ dùng
source arena.ai, còn AA chỉ dùng để tăng tính confirm"* — *"Openrouter ko còn nằm trong danh
sách nguồn từ lâu rồi. Chúng ta quét arena.ai thôi, các benchmark site còn lại là nguồn sự
thật"*.

Phân vai từ nay:

| | Vai trò |
|---|---|
| **arena.ai** (@arena trên X + 8 bảng) | nguồn **ẢNH** |
| artificialanalysis, tbench, livebench, swebench, aider, bfcl, gaia, opencompass, livecodebench, hle, vellum | nguồn **SỰ THẬT** — số liệu, link cho mục BẮT BUỘC; không làm ảnh |
| openrouter | không còn là nguồn gì |

## Con số đứng sau quyết định

Đếm `[xep_hang] … khớp` trên toàn bộ `prepare.log` còn trong `state`:

| Nguồn | Số lần ra ảnh |
|---|---|
| arena (X + 7 bảng) | **40** |
| openrouter | 3 |
| tbench | 1 |
| livebench | 1 |
| **aa-models** | **0** |

Bỏ AA khỏi đường ảnh không mất gì — nó chưa từng ra một tấm nào. Cái mất là **4 bài**: ba bài
openrouter và tin *"Grok 4.7 vào top 6 Terminal-Bench"*. Bài cuối là tin **về chính bảng đó**,
từ nay ra thẻ chữ nếu model không có trên arena. Ông Chủ biết và vẫn chốt.

## Luật cũ mới chỉ được gỡ một nửa

OpenRouter bị Ông Chủ bỏ từ **LOW-185 (16/09/2026)**: *"tiêu chí research chỉ còn benchmark uy
tín + HuggingFace, không đưa số liệu usage/gateway vào làm tín hiệu"*. Nhưng hôm đó nó chỉ
được gỡ ở `scan_models.py`. Ở `ranking.py` nó vẫn nằm trong registry ảnh (`SOURCE`) và bảng
`TOPIC` — và trong tuần sau đó vẫn đẻ ra **3 tấm ảnh** từ bảng LƯỢT DÙNG.

Bài học: một nguồn nằm ở nhiều bảng đăng ký khác nhau. Bỏ nguồn thì phải `grep` tên nó trên cả
repo, đừng chỉ sửa chỗ vừa đọc. `tests/test_ranking_arena_only.py` giờ khoá cả hai mặt: không
còn tên nó trong `SOURCE`/`TOPIC`, và `source_page_is_board` không mở cho tên miền đó.

## Cửa vừa mở hôm nay cũng phải hẹp theo

`ranking.source_page_is_board` (LOW-385, merge sáng cùng ngày) nhận **mọi tên miền có trong
registry**. Nó đọc `SOURCE` nên tự hẹp lại theo — nhưng đó là may, không phải thiết kế; test
khoá lại để lần sau ai mở rộng registry thì không vô tình mở lại đường ảnh cho nhà khác.
