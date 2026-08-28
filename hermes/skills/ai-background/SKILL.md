---
name: ai-background
description: "Sinh nền AI cho carousel slide-thiết-kế bằng tao_nen_ai.py, tự động gửi vào topic Telegram của bạn (--gui), và sửa lại theo yêu cầu reply — dùng khi làm carousel GỐC của đội, không có ảnh thật nào để remake. Không khoá cứng vào một nhà cung cấp AI: codex-imagen là backend hiện có, đổi/thêm backend khác không đụng tới cách Gin/Itachi dùng công cụ. Cách viết prompt, ràng buộc không-chữ, cách xác định đúng ảnh cần sửa từ text reply, và ranh giới với doi_chu_anh.py / nền màu phẳng."
version: 1.1.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [ai-background, carousel, deck, gin, itachi, nen-ai, telegram]
---

# ai-background — nền sinh bằng AI cho carousel gốc

Nguồn nền thứ ba của `deck.py`, bên cạnh nền màu phẳng (`"bg": "cream"` mặc
định đen) và nền ảnh thật đã dọn chữ (`doi_chu_anh.py` của Gin). Dùng khi
carousel là **của chính đội, không remake ai** — không có ảnh thật nào tồn
tại để chọn hay để dọn, vì nội dung là gốc.

**Ai gọi:** cả **Gin** và **Itachi** đều dùng được tool này — không phân vai
cứng. Trong thực tế Itachi thường là người gọi trực tiếp (Itachi quyết định
layout và biết rõ từng slide cần nền kiểu gì, còn tool không đụng máy nặng
nên không cần qua Gin). Gin vẫn có thể gọi khi thuận tiện hơn cho luồng việc
của bạn — không có quy tắc nào cấm.

## Không khoá cứng vào một nhà cung cấp

`tao_nen_ai.py` có cờ `--provider`. Hiện chỉ có **`codex-imagen`** (qua router
`yihan-9router`, key trong `.secrets.env`) — đó là backend duy nhất đã đấu dây,
không phải backend duy nhất được phép tồn tại. Thêm provider khác là thêm một
hàm trong `PROVIDERS` của script, không đổi cách gọi, không đổi hợp đồng đầu
ra (luôn là một PNG). Đừng viết cứng "dùng codex-imagen" vào task hay bàn giao
— nói "sinh nền AI", để `--provider` (mặc định lấy từ env
`AI_BACKGROUND_PROVIDER`, hiện là `codex-imagen`) quyết định backend.

```bash
venv/bin/python tao_nen_ai.py --list-providers
```

## Cách dùng

```bash
cd /home/donniechu/content-team && venv/bin/python tao_nen_ai.py \
  --prompt "flat abstract geometric background, dark navy, minimal, editorial" \
  --out /tmp/nen_ai_<id>_<n>.png
```

Ra một PNG, đưa thẳng vào `"bg_anh"` của slide đó trong spec `deck.py`.
`_open_bg` trong `deck.py` tự cover-crop về đúng khung 1080×1350 dù ảnh ra
kích thước nào — backend hiện tại (router) hay bỏ qua `--size`, đừng cố ép,
`deck.py` lo phần khung.

Layout `statement`/`list_steps`/`checklist` nhận `bg_anh` bình thường.
`grid3` cần ảnh có sẵn grid ảnh thật bên trong (nhãn chữ đặt DƯỚI các ảnh nhỏ
có sẵn) nên **không hợp** với nền AI generate — dùng nền màu phẳng hoặc
`cover` cho các slide đó thay vì `grid3`.

## Gửi vào Telegram, và sửa lại khi có reply

Việc của bạn không dừng ở sinh file PNG — **luôn gửi kết quả vào topic của
chính bạn** để Ông Chủ xem ngay, không chờ được hỏi. Thêm `--gui <tên bạn>`
(`gin` hoặc `itachi`) và `--mo-ta` khi gọi `tao_nen_ai.py`:

```bash
venv/bin/python tao_nen_ai.py \
  --prompt "Doraemon and Conan shaking hands, Hidden Leaf Village backdrop" \
  --out /tmp/anh_<id>.png \
  --gui itachi --mo-ta "Doraemon bắt tay Conan, bối cảnh làng Lá"
```

Cờ này gọi `gui_telegram.py` ngay sau khi sinh xong, gửi PNG vào đúng topic
của bạn (tra `state/topics.json`: `gin`=289, `itachi`=291) và **ghi lại nhật
ký** ở `state/telegram_sent/<vai>.jsonl` — mỗi dòng là `{message_id, files,
mo_ta, ts}`. Nhật ký này là chỗ bạn tra lại khi cần, đừng chỉ dựa trí nhớ hội
thoại (phiên có thể bị tóm tắt/rớt ngữ cảnh qua nhiều lượt).

Sinh **nhiều ảnh cùng lúc** (vài phương án, hoặc nhiều slide) thì gọi
`tao_nen_ai.py` nhiều lần lấy nhiều file, rồi gửi chung một album bằng
`gui_telegram.py` trực tiếp (không qua `--gui` của `tao_nen_ai.py`, cờ đó chỉ
gửi một ảnh):

```bash
venv/bin/python gui_telegram.py --vai itachi \
  --anh /tmp/anh_1.png --anh /tmp/anh_2.png --anh /tmp/anh_3.png \
  --mo-ta "3 phương án nền cho carousel <id>"
```

### Khi Ông Chủ reply yêu cầu sửa

Ông Chủ reply vào đúng ảnh/album đó bằng **văn bản mô tả**, không phải số thứ
tự cứng nhắc — ví dụ "ảnh Doraemon đổi tư thế, thêm Naruto vào", "cái thứ 2
làm lại đậm màu hơn". Việc của bạn:

1. **Chưa chắc nhớ chính xác** đã gửi ảnh nào, prompt gì → tra lại:
   ```bash
   venv/bin/python gui_telegram.py --vai itachi --list
   ```
   In ra vài lần gửi gần nhất (mặc định 5) kèm `mo_ta` và đường dẫn file gốc
   — đối chiếu với text Ông Chủ vừa reply để xác định ĐÚNG ảnh nào đang được
   nhắc tới. Mô tả không khớp gì trong danh sách thì hỏi lại cho rõ, đừng đoán
   đại — sửa nhầm ảnh còn tốn công hơn hỏi lại một câu.

   **Hỏi lại bằng câu trả lời cuối cùng (text thường), KHÔNG gọi tool
   `clarify`.** Kênh Telegram này chạy one-shot (`chat_router.py`, không có
   người thật chờ trả lời tool) — gọi `clarify` ở đây sẽ tự chọn "Recommended"
   trong im lặng hoặc khiến bạn lặp lại việc đã kiểm tra cho tới khi hết 600
   giây timeout, Telegram không nhận được gì cả (đã xảy ra thật ở skill
   `inplace-translate`, cùng cơ chế). Viết câu hỏi thẳng vào text cuối rồi
   dừng lượt; Ông Chủ trả lời bằng tin nhắn mới, bạn xử lý tiếp ở lượt sau.
2. **Sinh lại bằng `tao_nen_ai.py`** với prompt đã chỉnh theo đúng yêu cầu
   (giữ nguyên phần Ông Chủ không yêu cầu đổi, chỉ sửa đúng phần được nhắc —
   đọc lại `mo_ta`/prompt cũ trong nhật ký để biết cái gì đang giữ nguyên).
3. **Gửi lại bằng `--gui`/`gui_telegram.py` như một tin MỚI**, không sửa đè
   lên tin cũ (Telegram Bot API không cho sửa ảnh đã gửi) — ghi rõ trong
   `--mo-ta` đây là bản sửa của ảnh nào, để lần reply sau còn tra lại được.

## Viết prompt

- **Tiếng Anh.** Model sinh ảnh không đọc tiếng Việt tốt cho mô tả bố cục.
- **Luôn nói rõ không có chữ/số nào trong ảnh.** `tao_nen_ai.py` tự thêm ràng
  buộc này vào cuối prompt, nhưng đề bài gốc bạn viết cũng nên né chủ đề dễ tự
  sinh ra chữ — bảng biểu, màn hình, sách, biển hiệu.
- **Mô tả bố cục và tâm trạng, không mô tả một sự kiện có thật.** Đây là nền
  trang trí cho carousel gốc, không phải minh hoạ tin tức — xem mục ngoại lệ
  bên dưới.
- Bảng màu editorial của đội: đen, kem, san hô, xanh (`INK`/`CREAM`/`CORAL`/
  `BLUE` trong `deck.py`). Không bắt buộc nhưng nên bám để nền hợp với chữ
  Việt vẽ đè lên.

## Ngoại lệ riêng của Gin/Itachi — đọc kỹ trước khi dùng

Luật cứng "không tự vẽ minh hoạ" của cả đội (Chad/Ethan/Heller/Dre — ảnh phải
là ảnh thật, đưa tin) **không** áp cho nền AI generate ở đây. Carousel
slide-thiết-kế vốn đã chấp nhận nền màu phẳng trừu tượng (`BG_DARK`/
`BG_CREAM`); nền AI generate là mở rộng tự nhiên của đúng ý đó — **trang trí,
không phải minh hoạ sự kiện thật**.

Hai ranh giới cứng đi kèm ngoại lệ này:

1. **Đừng suy rộng sang vai khác.** Chad/Ethan/Heller/Dre vẫn phải dùng ảnh
   thật, không có ngoại lệ nào cho họ.
2. **Đừng dùng AI generate khi đang REMAKE một carousel có ảnh thật sẵn.**
   Case đó vẫn của Gin/`doi_chu_anh.py` như cũ — xoá chữ khỏi ảnh thật, không
   thay ảnh thật bằng ảnh AI.

## Khi lỗi

`tao_nen_ai.py` tự thử lại và đổi model dự phòng khi backend trả lời bằng chữ
thay vì ảnh (lỗi hay gặp, không phải bug của bạn). Lỗi khác (mạng, thiếu key
trong `.secrets.env`) dừng ngay với thông báo rõ — đọc `stderr`, đừng thử lại
tay nhiều lần trước khi biết lý do.

`gui_telegram.py` dừng hẳn nếu thiếu `TELEGRAM_BOT_TOKEN`/`TELEGRAM_GROUP_ID`
trong `.secrets.env`, nếu vai không có topic trong `state/topics.json`, hoặc
nếu Telegram trả lỗi (token sai, bot bị kick khỏi group...) — không nuốt lỗi
âm thầm, vì mất một lần gửi mà không ai biết là mất niềm tin vào cả luồng.
