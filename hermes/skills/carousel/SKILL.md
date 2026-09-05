---
name: carousel
description: "Khung kể chuyện, giọng copy và slide quote cho carousel nhiều slide của Dre (một vai cho cả donniechublog và dcgr.tech, khác handle và người đọc). Lệnh, luật ảnh, cú pháp spec và cách sửa lỗi nằm trong brief mà dre_chuan_bi.py in mỗi task và trong báo [LOI] của dre_nop.py; skill này chỉ giữ phần vai phải nghĩ."
version: 3.0.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [carousel, slide, dre, bang-tin, album, donniechublog, dcgr]
---

# carousel — bộ nhiều slide kể một tin

Ethan nén cả tin vào **một thẻ**; Dre trải tin ra **5–10 slide** 4:5, mỗi slide
một ý, người đọc lướt tới đâu hiểu tới đó, slide cuối để lại một câu hỏi hay
một mốc. Nền không cố định một màu: nền phục vụ ảnh, miễn ảnh và chữ nổi; đen
và trắng là hai màu ưu tiên. Engine hiện dựng biến thể tối (ảnh phủ kín, màn
tối liền mạch); màu nền không phải trường trong spec.

## Luồng

```bash
cd /home/donniechu/content-team && venv/bin/python dre_chuan_bi.py <id>   # 1. brief
# 2. viết spec.json vào đường dẫn brief in ra
cd /home/donniechu/content-team && venv/bin/python dre_nop.py <id>        # 3. nộp
```

Brief in ảnh đã tải với mã A1, A2…, cột "ảnh là", nhãn dùng được ở đâu, cặp ghép,
tư liệu, số slide tối thiểu và khung spec; nop in `[LOI]` kèm cách sửa. Không
cần nhớ cú pháp hay luật ảnh, đọc brief là đủ.

## Khung kể chuyện (không cứng, hầu hết tin AI hợp)

1. **Bìa — HOOK.** Một câu giật khiến người ta dừng lướt: **nghịch lý** hoặc
   **con số**, không phải nhan đề trung tính. "OpenAI đang xây điện thoại AI.
   Một startup Trung Quốc vừa ship trước." Hook 2 dòng mạnh hơn 4 dòng.
2. **Cái gì vừa xảy ra.** Sản phẩm/mô hình gì, ai làm, điểm lạ là gì.
3. **Con số gây sốc.** Diễn giải cho dễ hình dung ("đếm tới một nghìn tỉ mất
   31.700 năm").
4. **Ý nghĩa thật / được mất.** Slide bẻ góc: tin này **thật ra** nói về cái gì.
   Đây là chỗ carousel hơn hẳn một dòng tin.
5. **Đối thủ / diễn biến.** Ai cạnh tranh, rào cản, ai sắp ra cái tương tự.
6. **Cái cần theo dõi.** Mốc thời gian, câu hỏi mở. Không chốt cụt.

Tin **flagship** (model ra mắt của hãng frontier) cần nhiều tầng hơn: ra mắt →
bảng benchmark → chart thứ hai → giá/context/tốc độ → đối thủ → phát biểu lãnh
đạo → rủi ro → cái cần theo dõi. Đừng kéo dài cho đủ số: slide không có ý mới
là slide thừa.

## Giọng và độ dài

- Câu ngắn, chủ động. Mỗi slide thân 1–2 đoạn, mỗi đoạn 2–4 dòng. Một ý một
  slide. Số nằm trong câu, không tách thành nhãn.
- Tiếng Việt có dấu, không em-dash. Chỉ `--bo-qua-dau` khi copy thật sự là
  tiếng Anh.
- `category` chip bìa viết hoa (MODEL RELEASE / PRODUCT / RESEARCH / FUNDING /
  POLICY / EARNINGS / M&A…); `label` là tên model hoặc hãng viết hoa.

## Slide quote

Câu trích dẫn mạnh (phát biểu, con số, nhận định sắc, câu chốt) trong khung
ngoặc, dòng nguồn canh giữa; script tự vẽ.

- **Dịch sang tiếng Việt có dấu**, giữ tên riêng, thuật ngữ, số liệu. Không chép
  nguyên văn tiếng Anh.
- Ngắn, một câu; `attrib` là "Ai nói, chức/hãng" nếu là lời thật, "Đọc bài “…” -
  nguồn" nếu là câu chốt. Không gán câu tự viết thành lời một người.
- Cân 2–3 quote với 3–4 slide kể; đừng ép cả bộ thành quote.

## Ảnh: cột "ảnh là" và dấu ❌ là luật

Mỗi ảnh trong brief đã được nhìn. Ảnh ❌ không dùng dù nhãn đẹp. Đọc cột "ảnh
là" của từng mã trước khi ghép vào slide; mô tả không khớp ý slide thì đổi. Thiếu
ảnh thì gộp ý để giảm slide hoặc kết thúc task "Thiếu ảnh thật", không nhồi. Mặt
người không rõ ai thì bỏ; không điền tên CEO cho qua cổng.

## Nhìn lại trước khi nộp

1. Bìa có khiến muốn lướt tiếp không? Hook trung tính là bìa hỏng.
2. Mỗi slide có một ý mới không? Lặp ý là thừa, bỏ.
3. Slide cuối có để lại gì không?
4. Đủ tối thiểu slide brief ghi và ít nhất 2 quote chưa?
