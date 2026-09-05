---
name: hero-image
description: "Dựng một thẻ ảnh (hero) bằng card.py cho Ethan (donniechublog và dcgr.tech). Từ 04/09/2026 luồng là BA BƯỚC: ethan_chuan_bi.py (script tìm/tải/đo ảnh, bóc tư liệu, in brief với mã ảnh) → vai viết spec.json (mã ảnh + hook/tagline/attrib) → ethan_nop.py (ghép/cắt, cổng chặn card.py, dựng, gửi kèm nút duyệt, bàn giao Miles). Skill này giữ phần vai cần: kiểu quote (thẻ HOOK, mặc định) và kiểu tràn, cách viết câu hook/tiêu đề, kicker, attrib, cú pháp spec, cách đọc lỗi."
version: 3.0.0
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

Ethan nén cả tin vào **một thẻ**: ảnh thật phủ kín khổ 4:5, một câu hook đè lên
qua màn tối liền mạch. Tin nhiều tầng không nén được vào một câu thì để Dre làm
carousel.

## Luồng ba bước (04/09/2026)

Đo trước khi đổi: mỗi task Ethan 19–43 tool call, chủ yếu `curl` tải ảnh,
`anh_bai` chạy lại, mở từng ảnh, `card.py` chạy nhiều vòng vì cổng chặn.

```bash
cd /home/donniechu/content-team && venv/bin/python ethan_chuan_bi.py <id>   # 1
# 2. viết spec.json vào đường dẫn brief in ra
cd /home/donniechu/content-team && venv/bin/python ethan_nop.py <id>        # 3
```

**Bước 1 — `ethan_chuan_bi.py`** (engine `anh_chuan_bi.py` đã chạy nền từ lúc
Ông Chủ chọn tin; lệnh này thường chỉ in): giải mã link Google News, tìm ảnh
(link gốc, báo khác qua Bing, browser thật lấy img/bảng, Commons khi thiếu),
bỏ trùng/logo/ảnh AI, đo bằng `luat_anh` (chart, tỉ lệ, mặt người, nửa dưới
sáng/tối), tính cặp ghép cùng tone, bóc tư liệu; in bảng ảnh **A1, A2…** với
nhãn theo luật `card.py` và khung spec.

**Bước 2 — spec.json.** Kiểu quote (mặc định):

```json
{"anh": "A2", "kieu": "quote",
 "hook": "Nvidia mua Hugging Face 12,9 tỷ USD: kho model mở lớn nhất đổi chủ.",
 "tagline": "M&A", "attrib": "via CNBC",
 "anh2": "A5", "nhan_vat": "Jensen Huang"}
```

Kiểu tràn (đổi không khí): `{"anh": "A?", "kieu": "tran", "title": "<MỘT câu
hoàn chỉnh bao quát tin, có số nếu tin có số>", "kicker": "MODEL RELEASE"}`.
`anh2` và `nhan_vat` tuỳ chọn, cả hai kiểu.

**Bước 3 — `ethan_nop.py`.** Đổi mã → tệp, `anh2` → `--image2` (ghép dọc),
`nhan_vat` → `--nhan-vat`, chạy `card.py` với brand từ sidecar, gửi ảnh lên
topic `designer` kèm nút Duyệt/Làm lại/Bỏ, ghi `drafts/<id>.ban_giao.md` (dán
vào task Miles khi Ông Chủ bấm Duyệt), ghi `da_dung.json`. Báo `[LOI]` thì sửa
đúng chỗ trong `spec.json` và chạy lại. **Làm lại**: ảnh và hook phải khác lần
trước, script từ chối nếu trùng.

## Ảnh: đọc nhãn trong brief là đủ

| Nhãn | Nghĩa |
|---|---|
| `nền hero (một mình)` | ảnh chụp tỉ lệ ≤ 1.6, dùng được ngay |
| `CHỈ ghép dọc (anh2)` | chart/bảng, hoặc ảnh ngang quá 1.6: `card.py` chặn một mình (mất nửa dưới dưới màn tối, hoặc khổ 4:5 trống quá nửa). Chọn `anh2` trong "cặp ghép được" |
| `CÓ n MẶT NGƯỜI` | chỉ dùng khi `nhan_vat` là người **được nhắc trong bài** |
| `nửa dưới sáng` | vẫn dùng được, hook hơi nhạt; có ảnh tối hơn thì ưu tiên |

Luật ảnh chung của đội (không tự vẽ, chart nguyên vẹn full bề ngang, chỉ crop
qua `crop_ti_le`, ghép cùng tone, mặt người, không hai vùng) ở
[`LUAT_ANH.md`](/home/donniechu/content-team/LUAT_ANH.md), đã code hoá trong
engine và `card.py`. Vai không cần nhớ.

## Kiểu quote — thẻ HOOK (mặc định)

Một câu lớn trong khung dấu `"`, phải **đập vào mắt trong 3 giây**:

- **Câu hook không nhất thiết là lời ai nói.** Mạnh nhất là chính tiêu đề/góc
  giật của tin **có con số sốc**; hoặc một câu nói **có thật** của người trong
  bài nếu đủ đắt. Một câu, không hai; giữ hoa/thường tự nhiên; ≤ 120 ký tự để
  đọc lớn (script thu nhỏ dần rồi cắt "…" khi quá 7 dòng).
- **`attrib`**: hook do bạn soạn → `via <báo>` hoặc `<Chủ đề>, via <báo>`; lời
  có thật → `Phát biểu của <tên>, <chức/hãng>`. **Không** gán câu tự soạn thành
  lời một người: bịa lời là sai.
- **`tagline`**: chip category tiếng Anh ngắn: MODEL RELEASE / MODEL UPDATE /
  FUNDING / M&A / EARNINGS / ROBOTICS / CYBERSECURITY / APPS / OPEN SOURCE /
  RESEARCH / POLICY / INFRA / IN BRIEF. Không để "daily AI update".
- Bố cục script tự vẽ: khung 2 góc ngoặc, chip tagline (trắng) trên-trái, chip
  tên kênh (CYAN nhận diện; dcgr trắng) trên-phải, dòng nguồn canh giữa, dấu `"`
  đổi màu theo hãng được nhắc.

## Kiểu tràn — kicker + một câu tiêu đề

Không phụ đề, không via trên thẻ; chỉ ảnh, kicker, tiêu đề, tên kênh. **Tiêu
đề là một câu hoàn chỉnh bao quát tin**, không giới hạn dòng (script tự chọn cỡ
chữ), có số nếu tin có số. **Kicker** tiếng Anh tối đa hai từ (BREAKING, MODEL
RELEASE, AGENT, FUNDING, BENCHMARK, OPEN SOURCE, M&A, RESEARCH, INFRA, POLICY).

## Tô tên hãng, ghi nguồn

Tên hãng trong câu được tô tự động (donniechublog: CYAN nhận diện; dcgr: màu
riêng của hãng, hãng lạ ra hổ phách). Gặp hãng không được tô thì báo lại để thêm
vào `card.py`, đừng đánh dấu tay. Thẻ không in via; nguồn ảnh đi theo
`ban_giao.md` sang Miles để vào chú thích bài, script lo.

## Nhìn lại trước khi nộp (đọc spec, không cần mở ảnh)

1. Hook có khiến người ta dừng lướt không, có số chưa, một câu chưa?
2. `attrib` đúng loại chưa (via vs. Phát biểu)?
3. Ảnh chọn có bị nhãn "CHỈ ghép" hay "CÓ MẶT" mà chưa xử lý không?
4. Tiếng Việt có dấu, không em-dash?
