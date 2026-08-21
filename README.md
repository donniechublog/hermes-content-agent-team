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
- `assets/` — font (JetBrains Mono, Inter), icon SVG, mascot

## Dịch vụ systemd

- `hermes-gateway` — gateway hermes, chứa dispatcher kanban
- `hermes-approve` — dịch vụ duyệt bài (tệp này)
- `hermes-dashboard` — bảng điều khiển web, cổng 9119

## Suy luận (reasoning)

Quinn và Jean chạy `ds/deepseek-v4-pro` với `agent.reasoning_effort: none`.

Lý do: bản mặc định đốt hết ngân sách token vào suy luận rồi trả về **rỗng** —
đo thật 3/24 lần (2/8 ở `max_tokens=800`, 1/8 ở 1200, 0/8 ở 2000). Lỗi phụ thuộc
ngân sách nên im lặng và ngắt quãng. Tắt suy luận: 0/24 lần rỗng, nhanh gấp 3,
rẻ hơn 26%, chữ vẫn đủ dấu.

Việc của cả hai vai không cần suy luận — Jean chỉ viết tiêu đề + đoạn văn thuần,
phần trình bày đã do `teaser_assemble.py` lo bằng code.

Đã thử model rẻ hơn cho Jean (`ds/deepseek-chat`, `ds/deepseek-v4-flash`): chữ
vẫn tốt nhưng **lệch giọng** — viết kiểu tường thuật "bài viết nói rằng..." thay
vì giọng mời đọc. Chênh lệch giá chỉ 0,0026 USD/teaser nên không đáng đổi.

Kimi K3 đậu audition nhưng **đắt gấp 14 lần** v4-pro và mọi tuyến Kimi đều báo
`thinkingCanDisable: false` — không tắt suy luận được. Không dùng.

## Lưu ý

`.secrets.env` chứa bot token và khoá fal.ai — **không bao giờ commit**.
Chỉ một tiến trình được long-poll một bot token; `approve_service.py` giữ vai trò đó.
