---
name: carousel
description: "Dựng carousel nhiều slide kiểu bảng tin cho Dre (donniechublog và dcgr.tech). Từ 04/09/2026 luồng là BA BƯỚC: dre_chuan_bi.py (script tìm/tải/đo/cắt ảnh, bóc tư liệu, in brief) → vai viết spec.json (chỉ chữ + mã ảnh) → dre_nop.py (cắt/ghép, cổng chặn, dựng, gửi album kèm nút duyệt, bàn giao Miles). Skill này giữ phần vai cần: khung kể chuyện, cách viết copy từng slide, slide quote, cú pháp spec, và cách đọc lỗi của dre_nop."
version: 2.0.0
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

Kiểu ảnh thứ hai của đội, bên cạnh hero image của Ethan. Ethan nén cả tin vào
**một thẻ**; Dre trải tin ra **5–10 slide** 4:5 nền đen, mỗi slide một ý, người
đọc lướt tới đâu hiểu tới đó, slide cuối để lại một câu hỏi hay một mốc.

## Luồng ba bước (04/09/2026) — phần cơ học không còn là việc của vai

Đo thật trước khi đổi: mỗi task Dre tốn 51–60 tool call, chủ yếu `curl` tải
ảnh, `ls`/`grep` dò file, ghi rồi đọc lại spec, mở từng ảnh. Giờ:

```bash
cd /home/donniechu/content-team && venv/bin/python dre_chuan_bi.py <id>   # 1
# 2. viết spec.json vào đường dẫn brief in ra
cd /home/donniechu/content-team && venv/bin/python dre_nop.py <id>        # 3
```

**Bước 1 — `dre_chuan_bi.py`** (đã chạy nền từ lúc Ông Chủ chọn tin; gọi lại
chỉ in):
- giải mã link Google News của Vera ra bài thật; đọc bộ nguồn Finn đã research;
- tìm ảnh thật: `anh_bai` (tĩnh) **và** mở browser thật lấy `<img>` lớn,
  chụp `figure`/`table`/`canvas` full bề ngang (bảng benchmark, chart);
- tải về, bỏ trùng (md5), bỏ ảnh nhỏ, bỏ logo/wordmark, bỏ cỡ ảnh AI sinh;
- đo từng ảnh bằng `luat_anh`: chart hay ảnh chụp, tỉ lệ, mặt người, đáy sáng;
  cắt sẵn ảnh chụp về 1:1/4:5 qua `crop_ti_le` (có dấu vết); chart giữ nguyên;
  tính sẵn các cặp ảnh ngang **ghép dọc được** (cùng tone, tỉ lệ sau ghép hợp lệ);
- bóc tư liệu (câu có số liệu, đoạn đầu bài) bằng `tu_lieu`;
- in **brief**: tư liệu, bảng ảnh có **mã A1, A2…** kèm nhãn "dùng được ở đâu",
  gợi ý bìa, cặp ghép, khung `spec.json`, và một tấm `bang_anh.png` gom mọi ảnh.

**Bước 2 — vai viết `spec.json`.** Chỉ chữ và mã ảnh. Cú pháp:

```json
{
  "tam_co": "flagship",
  "cover":  {"anh": "A2", "hook": "<câu giật, ≤ 90 ký tự>", "category": "MODEL RELEASE", "label": "GPT-6 ASTRA · OPENAI"},
  "slides": [
    {"anh": "A1", "text": "đoạn một.\n\nđoạn hai (tổng ≤ 240 ký tự)"},
    {"anh": "A3", "quote": "<câu đắt nhất, DỊCH tiếng Việt, ≤ 150 ký tự>", "attrib": "Hock Tan, CEO Broadcom (CRN)"},
    {"ghep": ["A4", "A5"], "text": "hai ảnh ngang cùng tone xếp dọc"},
    {"anh": "A6", "nhan_vat": "Greg Brockman", "quote": "…", "attrib": "…"},
    {"anh": "A7", "cat_ngang": true, "tam": [0.5, 0.4], "text": "ảnh NGANG là người/sản phẩm không chữ"}
  ]
}
```

- Mỗi slide **một** ảnh (`anh` hoặc `ghep`), **một** ý, `text` **hoặc**
  `quote`+`attrib`. Mỗi mã ảnh dùng đúng một lần.
- **Chart** (brief ghi CHART) chỉ ở slide thân — script tự thêm `"chart": true`,
  dán full bề ngang nguyên vẹn. Chart làm bìa → lỗi.
- **Ảnh NGANG** (brief ghi NGANG, không phải chart): `ghep` với một ảnh trong
  "cặp ghép được", hoặc `cat_ngang: true` **chỉ khi** là ảnh người/sản phẩm
  không có chữ (`tam` = tâm crop, tuỳ chọn).
- **Ảnh có mặt người**: phải khai `nhan_vat` là người **được nhắc trong bài**
  (CEO phát biểu, tác giả). Không gọi được tên thì không dùng.
- `tam_co`: brief đã suy sẵn (`flagship` khi tin nhắc họ model frontier);
  `"thuong"` chỉ khi Ông Chủ nói rõ tin nhỏ.

**Bước 3 — `dre_nop.py`.** Đổi mã → tệp, cắt/ghép theo spec, xoá slide cũ, chạy
`carousel.py` (mọi cổng chặn chữ/ảnh/bố cục ở đó), gửi album lên topic kèm nút
Duyệt/Làm lại/Bỏ, ghi `drafts/<id>.ban_giao.md` (approve_service dán vào task
của Miles khi Ông Chủ bấm Duyệt), ghi `da_dung.json`. In `[LOI]` thì sửa đúng
chỗ trong `spec.json` và chạy lại — script đã nói cách sửa ngay trong dòng lỗi.
Thành công thì in dòng **"Kết quả task"** để kết thúc task.

**Làm lại** (Ông Chủ bấm nút): brief in "LÀM LẠI — lần trước bìa Ax, hook …".
`dre_nop.py` từ chối nếu bìa hoặc hook trùng lần trước.

## Khung kể chuyện (không cứng, hầu hết tin AI hợp)

1. **Bìa — HOOK.** Một câu giật khiến người ta dừng lướt: **nghịch lý** hoặc
   **con số**. Không phải nhan đề trung tính. "OpenAI đang xây điện thoại AI.
   Một startup Trung Quốc vừa ship trước." Hook 2 dòng mạnh hơn 4 dòng.
2. **Cái gì vừa xảy ra.** Sản phẩm/mô hình gì, ai làm, điểm lạ là gì.
3. **Con số gây sốc.** Diễn giải cho dễ hình dung ("đếm tới một nghìn tỉ mất
   31.700 năm").
4. **Ý nghĩa thật / được mất.** Slide bẻ góc: tin này **thật ra** nói về cái gì.
   Đây là chỗ carousel hơn hẳn một dòng tin.
5. **Đối thủ / diễn biến.** Ai cạnh tranh, rào cản, ai sắp ra cái tương tự.
6. **Cái cần theo dõi.** Mốc thời gian, câu hỏi mở. Không chốt cụt.

**Tối thiểu 5 slide** kể cả bìa; tin **flagship** (model ra mắt của OpenAI,
Anthropic, Google, Meta, xAI, DeepSeek, Qwen, Kimi, GLM, MiniMax…) **tối thiểu
8**: ra mắt → bảng benchmark → chart thứ hai → giá/context/tốc độ → đối thủ →
phát biểu lãnh đạo → rủi ro/an toàn → cái cần theo dõi. Tối đa 10. Đừng kéo
dài cho đủ số: slide không có ý mới là slide thừa.

## Giọng và độ dài

- Câu ngắn, chủ động. Mỗi slide thân 1–2 đoạn, mỗi đoạn 2–4 dòng, cách nhau
  `\n\n`. Tổng ≤ 240 ký tự — dài hơn là cổng "vùng chữ 30%" chặn.
- Một ý một slide. Số nằm trong câu, không tách thành nhãn.
- **Tiếng Việt có dấu** (cổng chặn). Không em-dash. Chỉ dùng
  `dre_nop.py --bo-qua-dau` khi copy **thật sự** là tiếng Anh.
- `category` chip bìa (viết hoa): MODEL RELEASE / MODEL UPDATE / PRODUCT /
  RESEARCH / FUNDING / POLICY / OPINION / EARNINGS / M&A… `label` là tên
  model/hãng viết hoa.

## Slide quote — bắt buộc ≥ 2 mỗi bộ

Câu trích dẫn mạnh (phát biểu, con số, nhận định sắc, câu chốt) trong khung
ngoặc, dòng nguồn canh giữa — `carousel.py` tự vẽ, màu nét khung theo brand,
dấu " đổi màu theo hãng được nhắc.

- **Dịch sang tiếng Việt có dấu**, giữ tên riêng/thuật ngữ/số liệu. Không chép
  nguyên văn tiếng Anh.
- Ngắn: ≤ 150 ký tự. Chạm 7 dòng ở cỡ nhỏ nhất là cổng chặn báo cắt.
- `attrib`: "Ai nói, chức/hãng" nếu là lời thật; "Đọc bài “…” - nguồn" nếu là
  câu chốt/hook. Không gán câu tự viết thành lời một người cụ thể.
- Cân 2–3 quote + 3–4 slide kể; đừng ép cả bộ thành quote.

## Ảnh: nhãn là gợi ý, cột "ảnh là" và dấu ❌ mới là luật

Từ 05/09/2026 mỗi ảnh trong brief đã được **nhìn** (vision) và ghi `ảnh là: …`
kèm phán `LIÊN_QUAN`. Vì sao: bộ Broadcom/Gimlet dcgr có 4/8 ảnh là **widget
linh kiện, banner sàn crypto, logo placeholder, ảnh trang trắng** — engine gắn
nhãn CHART hết, vai đọc nhãn rồi dán lên slide. Không phép đo nào bắt được
"widget cơ khí trên bài Broadcom"; chỉ nhìn mới biết.

- Ảnh có **❌ KHÔNG LIÊN QUAN** → **không dùng**, dù nhãn/tỉ lệ đẹp đến đâu.
  `dre_nop.py` chặn thẳng.
- Đọc cột `ảnh là:` của **từng** mã trước khi ghép vào slide. Ảnh mô tả không
  khớp ý slide thì đừng dùng cho slide đó.
- **THIẾU ẢNH** (brief cảnh báo) → gộp ý để giảm slide, hoặc kết thúc task
  "Thiếu ảnh thật". **Không nhồi** ảnh không liên quan cho đủ số.
- **Mặt người KHÔNG RÕ AI** → bỏ. Không điền tên CEO trong bài vào `nhan_vat`
  để qua cổng — tên phải có trong chữ bài, `dre_nop.py` kiểm.
- `CHƯA AI NHÌN` (vision không chạy) → mở `bang_anh.png` trước khi dùng.

| Nhãn | Dùng thế nào |
|---|---|
| `bìa` | ảnh chụp liên quan, không chart, không mặt lạ, góc dưới-trái tối |
| `thân` | ảnh chụp đã cắt 1:1/4:5 — slide thân |
| `CHART` | slide thân, dán full bề ngang; **hình minh hoạ/AI art không phải chart** |
| `NGANG` | `ghep` với cặp gợi ý (đã lọc liên quan), hoặc `cat_ngang` nếu là người/sản phẩm không chữ |

## Nhìn lại trước khi nộp

1. Bìa có khiến muốn lướt tiếp không? Hook trung tính là bìa hỏng.
2. Mỗi slide có một ý mới không? Lặp ý là thừa, bỏ.
3. Slide cuối có để lại gì không?
4. Đủ tối thiểu slide (brief ghi) và ≥ 2 quote chưa?
5. Mã ảnh nào dùng hai lần, chart nào đặt làm bìa, ảnh NGANG nào chưa
   `ghep`/`cat_ngang`, ảnh có mặt nào chưa `nhan_vat`? — `dre_nop.py` sẽ chặn,
   nhưng tự soát trước là đỡ một vòng.

Spec đầy đủ của khổ, font và màu ở `carousel.py` (đầu tệp) và
`/home/donniechu/content-team/STYLE_TEXT_SPEC.md`.
