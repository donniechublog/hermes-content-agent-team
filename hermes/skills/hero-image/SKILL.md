---
name: hero-image
description: "Cách viết câu tiêu đề và kicker cho thẻ ảnh hero của Ethan (kiểu khung chữ nhật full_bleed — kiểu duy nhất của Ethan) (donniechublog và dcgr.tech). Lệnh, nhãn ảnh, cú pháp spec và cách sửa lỗi nằm trong brief mà ethan_prepare.py in mỗi task và trong báo [LOI] của ethan_submit.py; skill này chỉ giữ phần vai phải nghĩ."
version: 5.0.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [hero-image, card, designer, ethan, donniechublog, dcgr]
---

# hero-image — một thẻ ảnh, kiểu khung chữ nhật (full_bleed)

Ethan nén cả tin vào **một thẻ**: ảnh thật phủ kín khổ, kicker + một câu tiêu đề
trong khung chữ nhật đè lên ảnh; màu chữ tự đổi theo độ sáng vùng chữ. Tin nhiều
tầng không nén được vào một câu thì để Dre.

**Kiểu `quote` (ngoặc kép, chip tagline, dòng "via") là phong cách của Dre, không
phải của Ethan** (Ông Chủ 21/09/2026, LOW-343): `ethan_submit` từ chối spec có
`"card_style": "quote"`.

## Luồng

```bash
cd /home/dc-group/content-team && venv/bin/python ethan_prepare.py <id>   # 1. brief
# 2. viết spec.json vào đường dẫn brief in ra
cd /home/dc-group/content-team && venv/bin/python ethan_submit.py <id>        # 3. nộp
```

Brief in ảnh đã tải với mã A1, A2…, nhãn theo luật của renderer (nền hero một
mình, chỉ ghép dọc, có mặt người), cặp ghép, tư liệu và khung spec; nop in
`[LOI]` kèm cách sửa. Làm lại thì ảnh và tiêu đề phải khác lần trước.

## Kicker + một câu tiêu đề

- **Tiêu đề** (`title`) là MỘT câu hoàn chỉnh bao quát tin, phải **đập vào mắt
  trong 3 giây**: chính góc giật của tin, có con số nếu tin có số. Một câu, không
  hai; tiếng Việt có dấu, không em-dash. Không phụ đề, không "via" trên thẻ.
- **Kicker** (`kicker`) tiếng Anh ngắn: MODEL RELEASE / MODEL UPDATE / FUNDING /
  M&A / EARNINGS / ROBOTICS / CYBERSECURITY / APPS / OPEN SOURCE / RESEARCH /
  POLICY / INFRA / BREAKING / BENCHMARK.
- dcgr.tech: tiêu đề nói về tiền, thị phần, quy mô, hệ quả; donniechublog:
  benchmark, tham số, tốc độ.

Tên hãng trong câu được tô màu tự động (donniechublog: cyan nhận diện; dcgr: màu
riêng của hãng), mã model chữ lẫn số (NEEDLE3, H100, XING4.0-29B-A4B) cũng tự tô.
Cụm KEY khác cần nổi bật (tên hãng/sản phẩm chưa có trong danh sách, vd "Cactus
Compute") thì ghi vào `"highlight": ["Cactus Compute"]` — 1-3 cụm, chép ĐÚNG từ
trong title, script chặn cụm không có trong title. Nguồn ảnh đi theo bàn giao sang Miles, script lo.

## Chọn ảnh: ảnh tốt là chữ rõ mà không cần che

Brief ghi cho mỗi ảnh hero "✅ vùng khung chữ SẠCH" hoặc "⚠️ vùng khung chữ RỐI" / "⚠️ phủ
kín thẻ sẽ CẮT MẤT chi tiết ở mép" — đo trên đúng bố cục thẻ sẽ dựng. Ưu tiên ảnh SẠCH và
không mất mép (dòng "Gợi ý nền hero" đã xếp sẵn); chỉ dùng ảnh ⚠️ khi không còn ảnh nào khác.

## Nhìn lại trước khi nộp (đọc spec, không cần mở ảnh)

1. Tiêu đề có khiến người ta dừng lướt không, có số chưa, một câu chưa?
2. `card_style` là `full_bleed`, có `kicker` chưa?
3. Ảnh chọn có nhãn "chỉ ghép" hay "có mặt" mà chưa xử lý không?
4. Tiếng Việt có dấu, không em-dash?
