---
name: carousel-edu
description: "Carousel EDU tech × magazine cho Kite (role carousel.edu) bằng render_edu.py: art vector gốc, không ảnh thật trừ biểu đồ/bảng có thật (figure). Từ 04/09/2026 luồng là BA BƯỚC: kite_chuan_bi.py (tư liệu, hình thật đã chụp, theme/hero gợi ý, khung spec kèm giới hạn chữ) → vai viết spec.json → kite_nop.py (kiểm, render Chromium, gửi album kèm nút duyệt, bàn giao Miles). Skill này giữ phần vai cần: ranh giới ngoại lệ 'không tự vẽ', hệ thiết kế, tone/hero, 6 kind, nhịp feature, cách đọc lỗi."
version: 2.0.0
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
hero art trên bìa. `render_edu.py` vẽ hết; vai chỉ **chia slide và viết chữ**.

## Luồng ba bước (04/09/2026)

Đo trước khi đổi: mỗi task Kite 32 tool call (skill_view 13, read_file 19,
vision_analyze 13, ls 18) vì phải tự đọc skill, đọc reference, mở từng slide.

```bash
cd /home/donniechu/content-team && venv/bin/python kite_chuan_bi.py <id>   # 1
# 2. viết spec.json vào đường dẫn brief in ra
cd /home/donniechu/content-team && venv/bin/python kite_nop.py <id>        # 3
```

**Bước 1** in: tư liệu (câu có số liệu, đoạn đầu bài), **hình thật** đã chụp/tải
sẵn là biểu đồ/bảng ≥ 800px (mã A?), theme/hero gợi ý không trùng bộ gần đây,
và khung spec 6 kind với **giới hạn độ dài từng trường** (đo theo cỡ chữ của
renderer). **Bước 3** kiểm spec (6..10 slide, slide 1 cover, kind/trường bắt
buộc, mã hình thật, caption "via", theme/hero hợp lệ, làm lại phải đổi tone),
render, gửi topic `carousel-edu` kèm nút Duyệt, ghi `ban_giao.md` cho Miles,
`da_dung.json`. Báo `[LOI]` thì sửa `spec.json` và chạy lại.

## Ranh giới của ngoại lệ (đọc trước tiên)

Luật "không tự vẽ" tồn tại để **không bịa hiện thực**. Kite được nới đúng phần
không đụng hiện thực:

| ĐƯỢC vẽ | CẤM |
|---|---|
| Mô-típ hình học, quỹ đạo, node, glow | Ảnh giả trông như ảnh thật |
| Sơ đồ khái niệm: vòng lặp, các bước, luồng | Screenshot / UI sản phẩm giả |
| Đồ hoạ chữ, khối màu, hairline, badge | **Logo/nhận diện hãng thật** |
| Chèn **bản thật** của biểu đồ/bảng (`figure`, caption "via") | Biểu đồ với số liệu bịa; ảnh AI; quote bịa |

Gọi tên sản phẩm bằng **chữ** thì được; tái tạo logo thì không. Nghi ngờ một
mảng art bị đọc thành "bằng chứng thật" thì nó thuộc cột CẤM.

## Sáu kind và trường bắt buộc

| kind | bắt buộc | tuỳ chọn |
|---|---|---|
| `cover` | eyebrow, title, standfirst | accent, byline `[brand, "Phân tích", "N phút đọc"]`, image (mã hình thật) + caption |
| `statement` | eyebrow, title, standfirst | accent, cards `[{num, text}]` (≤ 3) |
| `steps` | eyebrow, title, steps `[{title, desc}]` (3–4) | accent |
| `loop` | eyebrow, title, chips (3, ≤ 3 từ), standfirst | accent, callout |
| `figure` | eyebrow, title, image (mã hình thật), caption "… · via <ai>" | accent, standfirst, cards |
| `cta` | eyebrow, title, checks (3) | readmore `{label, text}`, follow "Theo dõi @brand" |

Giới hạn để không tràn: title ≤ 60 (slide có ảnh: tối đa 2 dòng), standfirst
≤ 200–220, card ≤ 90, step desc ≤ 80, callout ≤ 110, check ≤ 70, eyebrow ≤ 28
viết hoa. `accent` là cụm nằm trong title cần nhấn màu. Dẫn nguồn ghi "via",
không ghi "nguồn".

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

Brief in gợi ý chưa dùng gần đây; chọn theo nội dung, không hỏi Ông Chủ. Renderer
in `CANH BAO` nếu trùng bộ ngay trước; "làm lại" thì `kite_nop.py` từ chối nếu
giữ nguyên cả theme lẫn hero. Bìa dùng hình thật thì bộ không vẽ hero.

## Hình thật (`figure`, hoặc `cover.image`)

Khi nguồn **có sẵn** biểu đồ/bảng thì chèn bản thật thay vì vẽ lại: engine đã
chụp `table`/`figure`/`canvas` full bề ngang và tải ảnh chart trong bài; brief
chỉ liệt kê tấm rộng ≥ 800px. Renderer trải ảnh hết bề ngang (không bao giờ cắt
hai bên), chữ chìm vào ảnh một mặt phẳng liền, nền phẳng thì kéo màu nền của
chính nó; tiêu đề tối đa 2 dòng. Bắt buộc `caption` "… · via <ai>".

## Nhịp feature (tham chiếu, không cứng)

1. **Bìa**: hook + hero art + byline. 2. **Bối cảnh/vấn đề**. 3. **Cách vận
hành** (`steps`). 4. **Số liệu** (`figure` nếu có hình thật, không thì bỏ).
5. **Cơ chế/hệ quả** (`loop`). 6. **Áp dụng + CTA**. Tối thiểu 6, tối đa 10,
mỗi slide một ý mới; bìa giật, slide cuối để lại câu hỏi/mốc. Tiếng Việt có
dấu, câu ngắn chủ động, không em-dash, không số ngoài tư liệu.

## Hệ thiết kế (renderer lo, để hiểu vì sao)

Nền tối có độ sáng nhẹ ở đỉnh, chữ sáng; hairline, glow radial; font Be Vietnam
Pro (display/body), Noto Serif (standfirst), JetBrains Mono (nhãn/số), nhúng
base64 nên server không cần font hệ thống. Khổ 1080×1350, `--scale 2`. Bản canvas
tham chiếu (bộ /boost) ở `reference/`; không cần đọc để làm task.

## Nhìn lại trước khi nộp (đọc spec)

1. Bìa có hook giật và art (hoặc hình thật + caption) không?
2. Đủ 6 slide, mỗi slide một ý mới, slide 1 là cover?
3. Có mảng nào bị đọc thành ảnh/logo/số liệu thật không? Có thì bỏ.
4. Theme/hero khác bộ gần đây chưa? Chữ trong giới hạn chưa?
