---
name: inplace-translate
description: "Khi nào dịch tại chỗ, khi nào thiết kế lại bằng deck, và bẫy màu đo được, cho Gin và Itachi khi remake carousel có chữ tiếng Anh sang tiếng Việt. Lệnh, danh sách vùng chữ, khung spec và cách sửa lỗi nằm trong brief mà gin_chuan_bi.py / itachi_chuan_bi.py in mỗi lần và trong báo [LOI] của nop; skill này chỉ giữ phần vai phải nghĩ."
version: 3.0.0
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

Gin xoá chữ khỏi ảnh nền (OCR định vị + LaMa), trả nền sạch và vị trí, màu chữ
gốc; Itachi viết chữ Việt lên: **tại chỗ** đúng box gốc, hoặc **deck** thiết kế
lại. `<id>` là message_id trong dòng `[Ảnh đính kèm đã tải về: …/<id>.jpg]`.

```bash
cd /home/donniechu/content-team && venv/bin/python gin_chuan_bi.py <id>              # Gin 1
cd /home/donniechu/content-team && venv/bin/python gin_nop.py <id>                   # Gin 3 (bước 2 chỉ khi có logo cần giữ)
cd /home/donniechu/content-team && venv/bin/python itachi_chuan_bi.py <id> [<id2>…]  # Itachi 1
cd /home/donniechu/content-team && venv/bin/python itachi_nop.py <id>                # Itachi 3 (bước 2: spec.json)
```

## Khi nào dịch tại chỗ, khi nào deck

- **Tại chỗ**: nhãn, badge, tiêu đề một dòng, slide ít vùng. Chữ Việt vẽ đúng box
  gốc, cỡ chữ lớn nhất còn vừa, font theo chiều cao, màu đo được từ ảnh gốc.
- **Đoạn văn nhiều dòng**: OCR trả một box mỗi dòng, câu Việt hiếm khi ngắt
  giống bản Anh. Dùng `gop` để gộp dải vùng thành một khối (script wrap trong
  khối đó), hoặc chuyển slide đó sang deck với `statement`/`list_steps`.
- **Deck**: thiết kế lại; `bg_anh: true` để lấy nền sạch của slide đó, bỏ thì
  nền phẳng. `null` ở một vùng = bỏ vùng (logo, nhiễu OCR), nền sạch để trống.

## Bẫy màu đo được

Màu chữ lấy bằng trung vị pixel phía chữ sau khi tách Otsu trong box; vùng nhỏ
hoặc chữ có gradient có thể lệch. Dấu hiệu: hai dòng cùng khối mà một dòng
`[20,55,134]`, dòng kia `[237,248,249]` → dòng sáng gần chắc sai, ghi
`color_rgb` theo dòng đúng. Ảnh BodyMist 28/08 mất trắng 3 dòng vì bỏ qua.

## Ranh giới

Logo và hình khối thương hiệu gốc: giữ và báo Ông Chủ, không tự thay. Không vẽ
minh hoạ, không nền AI (retouch/blend chờ GPU). Tiếng Việt mất dấu ở bất kỳ
vùng nào thì nop dừng; `--bo-qua-dau` chỉ khi bản dịch thật sự là tiếng Anh.
