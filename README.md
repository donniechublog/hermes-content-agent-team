# content-team

Dây chuyền nội dung tự động cho kênh Telegram AI, chạy trên hermes-agent.

## Đội hình

| Vai | Profile hermes | Việc |
|---|---|---|
| Finn | `scout` | Quét HN/Reddit/arXiv, chấm điểm, gửi danh sách đánh số |
| Iris | `illustrator` | Dựng thẻ ảnh — dùng ảnh gốc hoặc tự vẽ SVG |
| Quinn | `writer` | Viết caption tiếng Việt, đẩy vào hàng duyệt |
| Ada | `analyst` | Đo phản hồi, đối chiếu điểm chấm với lựa chọn thực tế |
| Jean | `teaser` | Ghép teaser từ bài đã duyệt |

## Luồng

```
cron 07:00 VN → task kanban cho Finn → Finn quét, ghi manifest, gửi báo cáo
                                              ↓
        Ông Chủ trả lời số thứ tự trong topic Finn
                                              ↓
        approve_service tạo cặp task Iris → Quinn (Quinn chờ Iris xong)
                                              ↓
        Bản nháp + thẻ ảnh vào topic Quinn kèm nút ✅ / ❌
                                              ↓
                     ✅ → đăng lên channel      ❌ → đánh dấu bỏ
```

## Tệp

- `card.py` — dựng thẻ ảnh. Ảnh giữ nguyên tỉ lệ, textbox co giãn bù phần thiếu
- `publish.py` — gửi text/ảnh lên Telegram, hỗ trợ topic
- `approve_service.py` — dịch vụ nền: nghe nút duyệt và lệnh chọn số
- `model_audition.py` — thử model: tiếng Việt đủ dấu, gọi tool thật, có prompt caching không
- `model_watch.py` — dò sức khoẻ model đang dùng, báo Telegram khi trạng thái đổi
- `usage_audit.py` — soi usage thật từ 9router: bắt fallback âm thầm và model tụt cache
- `cost_squeeze.py` — chạy lặp trên việc thật, tìm model rẻ nhất mà vẫn ổn định
- `assets/` — font (JetBrains Mono, Inter), icon SVG, mascot

## Dịch vụ systemd

- `hermes-gateway` — gateway hermes, chứa dispatcher kanban
- `hermes-approve` — dịch vụ duyệt bài (tệp này)
- `hermes-dashboard` — bảng điều khiển web, cổng 9119

## Model từng vai

| Vai | Model chính | Suy luận | Dự phòng |
|---|---|---|---|
| Finn (scout) | `ds/deepseek-v4-flash` | tắt | deepseek-chat → qwen3.8-max |
| Iris (illustrator) | `ds/deepseek-v4-flash` | tắt | deepseek-chat → mimo-v2.5-pro |
| Quinn (writer) | `ds/deepseek-chat` | tắt | v4-pro → v4-flash |
| Jean (teaser) | `ds/deepseek-chat` | tắt | v4-pro → v4-flash |
| Ada (analyst) | `ds/deepseek-reasoner` | **bật** | v4-pro → deepseek-chat |

Ada là vai duy nhất giữ suy luận: việc của Ada là đối chiếu điểm chấm với tin
được chọn — đúng loại việc cần suy luận thật.

Đo bằng `cost_squeeze.py`, chạy lặp trên việc thật, chấm bằng code:

| Vai | Model | Trượt | USD/1000 lần |
|---|---|---|---|
| teaser | **deepseek-chat** | **0/5** | **0,77** |
| teaser | mimo-v2.5-pro | 1/5 (lan man 2417 từ) | 0,83 |
| teaser | v4-flash | 1/5 (rỗng) | 1,11 |
| teaser | v4-pro | 2/5 (rỗng, mất dấu) | 3,83 |
| writer | deepseek-chat | 0/6 | 0,06 |
| writer | v4-pro | 0/6 | 0,14 |

Gemini đã gỡ khỏi mọi chuỗi: trên số liệu usage thật nó tốn 1,72 USD/1M input
còn v4-flash chỉ 0,04 — **đắt gấp 44 lần**, vì cột cached của gemini trống rỗng,
không cache nổi một token. Kimi K3 đắt gấp 14 lần v4-pro và mọi tuyến Kimi đều
báo `thinkingCanDisable: false` — không tắt suy luận được.

## Hai nguyên tắc bắt buộc khi dùng nhiều model

**1. Bắt buộc phải có giám sát model.** Hermes fallback im lặng hoàn toàn — đặt
model chính thành model chết, agent vẫn trả lời bình thường, không một dòng báo.
Cần cả hai lớp: `model_watch.py` (model còn sống không) và `usage_audit.py`
(model nào **thật sự** được gọi).

**2. Ghim mỗi hội thoại vào một model. Chuyển tầng thì chuyển ở ranh giới task.**
`try_activate_fallback` đổi model ngay giữa lượt, `restore_primary_runtime` lật
về model chính ở lượt sau — một hội thoại có thể chạy qua 2–3 model mà không ai
biết. Cache là per-model, mỗi lần lật là mất sạch prefix đã cache và cả ngữ cảnh
bị tính lại giá gốc. Cột `cache%` trong `usage_audit.py` chính là thước đo
nguyên tắc này: tụt cache nghĩa là đang lật model.

## Suy luận (reasoning)

Bốn trong năm vai đặt `agent.reasoning_effort: none`.

Lý do: model deepseek đốt hết ngân sách token vào suy luận rồi trả về **rỗng**.
Đo thật trên v4-pro: 3/24 lần (2/8 ở `max_tokens=800`, 1/8 ở 1200, 0/8 ở 2000).
Tái hiện y hệt trên v4-flash. Lỗi phụ thuộc ngân sách nên im lặng và ngắt quãng —
loại tệ nhất. Tắt suy luận: 0/24 lần rỗng, nhanh gấp 3, rẻ hơn, chữ vẫn đủ dấu.

Đã thử model rẻ hơn cho Jean (`ds/deepseek-chat`, `ds/deepseek-v4-flash`): chữ
vẫn tốt nhưng **lệch giọng** — viết kiểu tường thuật "bài viết nói rằng..." thay
vì giọng mời đọc. Chênh lệch giá chỉ 0,0026 USD/teaser nên không đáng đổi.

Kimi K3 đậu audition nhưng **đắt gấp 14 lần** v4-pro và mọi tuyến Kimi đều báo
`thinkingCanDisable: false` — không tắt suy luận được. Không dùng.

## Lưu ý

`.secrets.env` chứa bot token và khoá fal.ai — **không bao giờ commit**.
Chỉ một tiến trình được long-poll một bot token; `approve_service.py` giữ vai trò đó.
