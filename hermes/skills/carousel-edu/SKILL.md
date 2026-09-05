---
name: carousel-edu
description: "Ranh giới ngoại lệ 'không tự vẽ', bảng tone và hero, nhịp feature cho carousel EDU tech × magazine của Kite (role carousel.edu, cả hai brand). Lệnh, khung spec bảy kind kèm giới hạn chữ, hình thật đã chụp và cách sửa lỗi nằm trong brief mà kite_chuan_bi.py in mỗi task và trong báo [LOI] của kite_nop.py; skill này chỉ giữ phần vai phải nghĩ."
version: 3.0.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [carousel, edu, kite, magazine, vector, render_edu]
---

# carousel-edu — carousel kiến thức & nghiên cứu (tech × magazine)

Kite diễn đạt lại paper/nghiên cứu bằng **art vector gốc** trong bộ khung tạp
chí: masthead, eyebrow chuyên mục, tiêu đề lớn, standfirst in nghiêng, folio,
hero art trên bìa. Renderer vẽ hết; vai **chia slide, chọn hình diễn đạt và
viết chữ**. Chữ thuần là đường cuối: ý nào có hình nói nhanh hơn thì dùng hình.

| Ý muốn nói | Kind | Hình renderer vẽ |
|---|---|---|
| Quy trình, thứ tự | `steps` | dãy bước đánh số |
| Vòng lặp, cơ chế quay lại | `loop` | chip nối mũi tên khép vòng |
| So sánh vài con số | `bars` | biểu đồ cột ngang, số thật trong bài, caption via |
| Biểu đồ, bảng, ảnh có sẵn | `figure` | bản thật trải hết bề ngang |
| Bối cảnh, nhận định | `statement` | tiêu đề lớn + thẻ đánh số |
| Áp dụng | `cta` | checklist + đọc thêm |

## Luồng

```bash
cd /home/donniechu/content-team && venv/bin/python kite_chuan_bi.py <id>   # 1. brief
# 2. viết spec.json vào đường dẫn brief in ra
cd /home/donniechu/content-team && venv/bin/python kite_nop.py <id>        # 3. nộp
```

Brief in tư liệu, hình thật đã nhìn và liên quan (mã A?), theme/hero gợi ý
chưa dùng gần đây, khung spec bảy kind với giới hạn độ dài từng trường; nop in
`[LOI]` kèm cách sửa. Làm lại thì phải đổi theme hoặc hero.

## Ranh giới của ngoại lệ (đọc trước tiên)

Luật "không tự vẽ" tồn tại để **không bịa hiện thực**. Kite được nới đúng phần
không đụng hiện thực:

| ĐƯỢC vẽ | CẤM |
|---|---|
| Mô-típ hình học, quỹ đạo, node, glow | Ảnh giả trông như ảnh thật |
| Sơ đồ khái niệm: vòng lặp, các bước, luồng | Screenshot / UI sản phẩm giả |
| Đồ hoạ chữ, khối màu, hairline, badge | **Logo/nhận diện hãng thật** |
| Chèn **bản thật** của biểu đồ/bảng/ảnh chụp (caption "via") | Biểu đồ với số liệu bịa; ảnh AI; quote bịa |

Gọi tên sản phẩm bằng **chữ** thì được; tái tạo logo thì không. Nghi ngờ một
mảng art bị đọc thành "bằng chứng thật" thì nó thuộc cột CẤM.

## Tone & hero — mỗi bộ một tone, không lặp bộ trước

| theme | tone | hợp với |
|---|---|---|
| `orbit` | cyan × tím | agent, hệ thống |
| `ember` | cam hổ phách × đỏ san hô | hiệu năng, tốc độ, cảnh báo |
| `moss` | xanh lá × vàng chanh | dữ liệu mở, tăng trưởng, sinh học |
| `ink` | navy × vàng | benchmark, học thuật, paper nghiêm |
| `rose` | hồng × oải hương | sinh ảnh, sáng tạo, multimodal |

| hero | hình | hợp với |
|---|---|---|
| `orbit` | lõi sáng + node quỹ đạo | subagent, phân việc |
| `grid` | lưới toạ độ + ô sáng | benchmark, bảng số |
| `wave` | dải sóng + điểm nối | xu hướng, theo thời gian |
| `rings` | vòng đồng tâm + kim | mục tiêu, độ chính xác |
| `graph` | mạng node-cạnh | quan hệ, so sánh nhiều bên |

Chọn theo nội dung, không hỏi Ông Chủ. Bìa dùng hình thật thì bộ không vẽ hero.

## Hình thật

Brief liệt kê **mọi hình thật đã được nhìn và liên quan**: biểu đồ, bảng chụp
full bề ngang **và ảnh chụp**. Có hình thật trong brief thì **bắt buộc dùng ít
nhất một**: chart hoặc bảng vào `figure`, ảnh chụp làm bìa `image` hoặc `figure`.
Bộ toàn chữ và card khi có ảnh thật là thiếu. Mọi hình thật có `caption` "… ·
via <ai>"; ảnh có mặt người thì caption ghi đúng tên trong bài.

## Nhịp feature (tham chiếu, không cứng)

Bìa hook → bối cảnh/vấn đề → cách vận hành (`steps`) → số liệu (`figure` nếu có
hình thật, không thì `bars` từ số trong bài, không có số thì bỏ) → cơ chế/hệ quả
(`loop`) → áp dụng + CTA. Mỗi slide một
ý mới; bìa giật, slide cuối để lại câu hỏi hay mốc. Tiếng Việt có dấu, câu ngắn
chủ động, không em-dash, không số ngoài tư liệu, dẫn nguồn ghi "via".

## Nhìn lại trước khi nộp (đọc spec)

1. Bìa có hook giật và art (hoặc hình thật + caption) không?
2. Đủ slide brief ghi, mỗi slide một ý mới, slide 1 là cover?
3. Có mảng nào bị đọc thành ảnh, logo hay số liệu thật không? Có thì bỏ.
4. Theme/hero khác bộ gần đây chưa? Chữ trong giới hạn brief ghi chưa?
