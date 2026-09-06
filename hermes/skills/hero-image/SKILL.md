---
name: hero-image
description: "Cách viết câu hook, chọn kiểu quote hay tràn, ghi tagline và attrib cho thẻ ảnh hero của Ethan (donniechublog và dcgr.tech). Lệnh, nhãn ảnh, cú pháp spec và cách sửa lỗi nằm trong brief mà ethan_chuan_bi.py in mỗi task và trong báo [LOI] của ethan_nop.py; skill này chỉ giữ phần vai phải nghĩ."
version: 4.0.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [hero-image, card, designer, ethan, donniechublog, dcgr]
---

# hero-image — một thẻ ảnh, mặc định kiểu quote (thẻ HOOK)

Ethan nén cả tin vào **một thẻ**: ảnh thật phủ kín khổ 4:5, một câu hook đè
thẳng lên ảnh. Kiểu quote (mặc định, 06/09/2026) không còn màn tối — chỉ làm
mờ cục bộ đúng vùng chữ đè lên, phần ảnh còn lại giữ nguyên sắc nét; màu chữ tự
đổi theo độ sáng vùng đã mờ đó. Tin nhiều tầng không nén được vào một câu thì
để Dre.

## Luồng

```bash
cd /home/donniechu/content-team && venv/bin/python ethan_chuan_bi.py <id>   # 1. brief
# 2. viết spec.json vào đường dẫn brief in ra
cd /home/donniechu/content-team && venv/bin/python ethan_nop.py <id>        # 3. nộp
```

Brief in ảnh đã tải với mã A1, A2…, nhãn theo luật của renderer (nền hero một
mình, chỉ ghép dọc, có mặt người), cặp ghép, tư liệu và khung spec; nop in
`[LOI]` kèm cách sửa. Làm lại thì ảnh và hook phải khác lần trước.

## Kiểu quote — thẻ HOOK (mặc định)

Một câu lớn trong khung dấu `"`, phải **đập vào mắt trong 3 giây**:

- **Hook không nhất thiết là lời ai nói.** Mạnh nhất là chính tiêu đề hoặc góc
  giật của tin **có con số sốc**; hoặc một câu nói **có thật** của người trong
  bài nếu đủ đắt. Một câu, không hai; giữ hoa thường tự nhiên; ngắn để đọc lớn.
- **`attrib`**: hook do bạn soạn → `via <báo>`; lời có thật → `Phát biểu của
  <tên>, <chức/hãng>`. Không gán câu tự soạn thành lời một người: bịa lời là sai.
- **`tagline`**: chip category tiếng Anh ngắn: MODEL RELEASE / MODEL UPDATE /
  FUNDING / M&A / EARNINGS / ROBOTICS / CYBERSECURITY / APPS / OPEN SOURCE /
  RESEARCH / POLICY / INFRA / IN BRIEF. Không để "daily AI update".
- dcgr.tech: hook nói về tiền, thị phần, quy mô, hệ quả; donniechublog: benchmark,
  tham số, tốc độ.

## Kiểu tràn — kicker + một câu tiêu đề

Chỉ khi muốn đổi không khí. Không phụ đề, không via trên thẻ; chỉ ảnh, kicker,
tiêu đề, tên kênh. **Tiêu đề là một câu hoàn chỉnh bao quát tin**, có số nếu tin
có số. **Kicker** tiếng Anh tối đa hai từ (BREAKING, MODEL RELEASE, AGENT,
FUNDING, BENCHMARK, OPEN SOURCE, M&A, RESEARCH, INFRA, POLICY).

Tên hãng trong câu được tô màu tự động (donniechublog: cyan nhận diện; dcgr: màu
riêng của hãng). Gặp hãng không được tô thì báo lại để thêm vào `card.py`, đừng
đánh dấu tay. Nguồn ảnh đi theo bàn giao sang Miles, script lo.

## Nhìn lại trước khi nộp (đọc spec, không cần mở ảnh)

1. Hook có khiến người ta dừng lướt không, có số chưa, một câu chưa?
2. `attrib` đúng loại chưa (via hay Phát biểu)?
3. Ảnh chọn có nhãn "chỉ ghép" hay "có mặt" mà chưa xử lý không?
4. Tiếng Việt có dấu, không em-dash?
