# Lớp gộp tin cùng chuyện tắt im lặng 10 ngày — 03/10/2026

Ticket theo dõi: LOW-457 (phát hiện khi chẩn đoán LOW-456).

`env_load.SAME_STORY_MODEL = "ds/deepseek-v4.1-flash"` trả 404 `No active credentials for
provider: deepseek` từ 23/09: cả hai connection deepseek trên 9router thật đều `isActive=0`
(`9RH` hết tiền, 402). Tool output của các vai cho thấy 20–21/09 có 172 lần gọi OK; từ
23/09 trở đi 0 lần OK, số lần 404 mỗi ngày từ 2 tới 148.

Hai đường bị ảnh hưởng:
- `article_sources.same_story_many`: LLM hỏng thì mọi ca lưng chừng tính là CÙNG tin. Đo
  trên bộ vàng 180 cặp, cách này nhận nhầm 34/38 cặp khác tin, nên báo khác sự kiện lọt
  vào làm nguồn ảnh.
- Vera (`scan_business`): bỏ hẳn bước chặn tin đã báo quay lại dưới cách diễn đạt khác.
  Lượt quét thật 03/10 có 7/80 tin như vậy lọt qua (Tencent–Oracle 7 tỷ báo 02/10, Samsung
  foundry hạng 2 báo 01/10, NODES báo 02/10…), và Dre làm carousel cho vài tin trong số đó.

Vá: chuyển sang `ag/gemini-3.8-flash`, route text duy nhất còn sống. Trên bộ vàng, Gemini
giữ 132/142 cặp cùng tin và nhận nhầm 1–2/38 — tốt hơn DeepSeek lúc còn sống (127–128/142,
5–6/38), đổi lại chậm hơn (~6 s mỗi lần hỏi).

Hệ quả cần biết: `find_more_images` đi qua Bing với từ khoá (không phải tiêu đề tin) giờ bị
LLM lọc chặt như trước 23/09. Thử thật với "Samsung Foundry": LLM nhận 0/8 ca lưng chừng,
nên ảnh từ báo Bing ít hơn. Các nguồn khác (web, Commons, Openverse, ảnh báo về thực thể)
không qua bộ lọc này.

Bài học: lần thứ hai một lớp LLM tắt mà không ai hay (lần trước là `ds/deepseek-v4-pro`,
23/09). Lỗi chỉ in ra stderr, không cổng nào báo lên Telegram — xem backlog trong ticket.
