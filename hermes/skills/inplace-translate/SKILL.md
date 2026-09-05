---
name: inplace-translate
description: "Remake carousel/ảnh có chữ tiếng Anh sang tiếng Việt cho Gin và Itachi. Từ 04/09/2026 luồng là BA BƯỚC: gin_chuan_bi.py (OCR định vị + đo màu, đánh số vùng) → gin_nop.py (LaMa xoá, nen_sach.png + vung.json) và itachi_chuan_bi.py (chữ gốc từng vùng, nền sạch, khung spec) → spec.json → itachi_nop.py (vẽ tại chỗ đúng vị trí/màu/cỡ hoặc deck.py). Phần vẽ tại chỗ nằm trong itachi_nop.py; retouch/blend/nền AI chờ GPU (đợt tới). Skill này giữ phần vai cần: khi nào dịch tại chỗ, khi nào deck, cú pháp spec, bẫy màu."
version: 2.0.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [remake, translate, gin, itachi, deck, lama, ocr]
---

# inplace-translate — dịch ảnh có chữ sang tiếng Việt

Hai vai, một chuỗi script:

| Bước | Lệnh | Ra |
|---|---|---|
| Gin 1 | `gin_chuan_bi.py <id>` | danh sách vùng chữ đánh số (text OCR, x,y,w,h, màu), `vung_preview.png` |
| Gin 2 (tuỳ chọn) | `spec.json` `{"giu": [stt], "xoa_them": [[x,y,w,h]], "ghi_chu": "…"}` | chỉ khi có logo cần giữ |
| Gin 3 | `gin_nop.py <id>` | `nen_sach.png`, `mask_debug.png`, `vung.json`; gửi trả lời tin nhắn |
| Itachi 1 | `itachi_chuan_bi.py <id> [<id2>…]` | chữ Anh từng vùng, nền sạch (tự làm phần Gin nếu chưa), gợi ý đường, khung spec |
| Itachi 2 | `spec.json` | chữ Việt cho từng slide |
| Itachi 3 | `itachi_nop.py <id>` | slide tiếng Việt, gửi album trả lời tin nhắn |

`<id>` là message_id trong dòng `[Ảnh đính kèm đã tải về: …/telegram_incoming/<id>.jpg]`.
Workdir: `state/<brand>/chuan_bi/gin_<id>/` và `itachi_<id>/`.

## Khi nào dịch tại chỗ, khi nào deck

- **Tại chỗ** (`"cach": "tai_cho"`): nhãn, badge, tiêu đề một dòng, slide ít
  vùng. Chữ Việt vẽ đúng box gốc, cỡ chữ lớn nhất còn vừa, font theo chiều cao
  (≥4,5% ảnh → bold, không thì regular; ghi `font` để đổi: bold/regular/serif/
  condensed/mono), màu đo được từ ảnh gốc.
- **Đoạn văn nhiều dòng**: OCR trả một box mỗi dòng, câu Việt hiếm khi ngắt
  giống bản Anh. Dùng `"gop": [[stt_đầu, stt_cuối, "bản dịch cả đoạn"]]` để
  gộp dải vùng thành một khối (script wrap trong khối đó), hoặc chuyển slide đó
  sang `"cach": "deck"` với `statement`/`list_steps`.
- **Deck** (`"cach": "deck"`): thiết kế lại, `bg_anh: true` để lấy nền sạch của
  slide đó, bỏ thì nền phẳng. Trường theo layout in trong brief.

## Cú pháp spec (Itachi)

```json
{"slides": [
  {"nguon": "338", "cach": "tai_cho",
   "vung": {"1": "Xin chào thế giới", "2": null,
            "3": {"text": "Đoạn thân bài", "font": "regular", "align": "center", "color_rgb": [230, 230, 230]}},
   "gop": [[4, 6, "Ba dòng gốc gộp thành một đoạn tiếng Việt, script tự xuống dòng."]]},
  {"nguon": "340", "cach": "deck", "layout": "statement", "bg_anh": true,
   "heading": "Câu tuyên bố lớn", "subs": [{"text": "dòng phụ", "col": "cream"}]}
]}
```

`null` = bỏ vùng (logo, nhiễu OCR): nền sạch để trống chỗ đó.

## Bẫy màu đo được

Màu chữ lấy bằng trung vị pixel phía chữ sau khi tách Otsu trong box; vùng nhỏ
hoặc chữ có gradient có thể lệch. Dấu hiệu: hai dòng cùng khối mà một dòng
`[20,55,134]`, dòng kia `[237,248,249]` → dòng sáng gần chắc sai, ghi
`color_rgb` theo dòng đúng. Ảnh BodyMist 28/08 mất trắng 3 dòng vì bỏ qua.

## Cổng chặn

Tiếng Việt mất dấu ở bất kỳ vùng nào → dừng, in rõ vùng. `--bo-qua-dau` chỉ khi
bản dịch thật sự là tiếng Anh. Logo/hình khối thương hiệu gốc: giữ và báo Ông
Chủ, không tự thay. Không vẽ minh hoạ, không nền AI (`tao_nen_ai.py` và
retouch/blend chờ GPU, đợt tới mới bật).
