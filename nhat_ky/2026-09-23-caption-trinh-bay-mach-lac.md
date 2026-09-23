# 23/09/2026 — Caption mất cách dòng sau khi đổi model

Ticket theo dõi: LOW-379 (khối văn xuôi dính liền), LOW-380 (bullet cho đoạn liệt kê).
PR: donniechublog/hermes-content-agent-team#239. Deploy: `fdab223 → 975164b`.

## Ông Chủ báo gì

Ảnh chụp bài trên trang Donnie Chu Blog: *"các đoạn hiện tại vẫn chưa được cách dòng"*,
*"những nội dung liệt kê chưa có emoji ở đầu dòng"*, kèm một câu quyết định hướng chẩn
đoán: *"việc này ko diễn ra ở mọi bài, một số bài làm rất tốt, ko bị những issue này"*.

Sau đó Ông Chủ gửi thêm một bài làm chuẩn và nói rõ chuẩn là gì: *"rất chuẩn mực, dù ko
có emoji nhưng các đoạn được cách dòng, và những chỗ nào liệt kê là có bullet point"*, rồi
chốt ưu tiên: *"quan trọng nhất là trình bày mạch lạc, bullet hay emoji thì cũng chỉ là
phần thêm"*.

## Chẩn đoán

Bài chê: `grok-4-7-kite-donniechublog` (Jika, 22/09) — hook, dòng trống, rồi **8 câu dính
liền**, dòng trống, câu kết. Chạy lại cổng chặn trên đúng caption đó: `LOI: []`,
`CANH: []`, `JIKA: []`. Bài đi qua cổng sạch sẽ.

Luật "mỗi đoạn cách một dòng trống" chỉ tồn tại ở **một chỗ duy nhất**: một mệnh đề phụ
trong brief của `miles_prepare.py`. Không SOUL nào nhắc, không cổng nào giữ, và bài mẫu
trong `jika.SOUL.md` lại là 9 dòng dính liền — mẫu dạy ngược lại brief.

Nó sống được bấy lâu là nhờ model cũ tình cờ nghe lời. Đo trên `caption.txt` thật của máy
chủ, tách theo mốc 4 profile vai viết đổi sang `ag/gemini-3.8-flash` (21/09 09:57,
LOW-326):

| writer | giai đoạn | n | khối ≤3 (đạt) | khối ≥5 (hỏng rõ) |
|---|---|---:|---:|---:|
| jika | trước (DeepSeek) | 46 | 84% | 10% |
| jika | sau 21/09 09:57 | 29 | 55% | **24%** |
| miles | trước (DeepSeek) | 47 | 97% | 0% |
| miles | sau 21/09 09:57 | 30 | 63% | **20%** |

Hỏng đều ở **cả hai vai**, không phải lỗi của Jika hay Miles. Cùng code, cùng brief, cùng
SOUL — chỉ đổi model.

Bài Ông Chủ khen do Miles viết **ngày 22/09, tức là sau mốc đổi model**: model mới làm
được, chỉ là không có gì bắt nó làm.

## Bài học: thước đo phải xin bài MẪU trước khi chốt

Lần đo đầu tiên tôi dùng "tỉ lệ dòng trống / số dòng" và ra 76% → 14%, nghe rất thuyết
phục. Rồi Ông Chủ gửi bài chuẩn mực — nó chấm **0,4** theo thước đó, tức là thước của tôi
**đánh trượt chính bài được khen**. Nếu cứ thế vá thì cổng mới sẽ chặn oan đúng thứ cần
noi theo.

Thước đúng là **khối văn xuôi dính liền dài nhất**, dòng bullet không tính:

| | khối dài nhất | dòng trống | bullet |
|---|---:|---:|---:|
| microchip (KHEN) | 2 | 4 | 3 |
| grok-4-7 (CHÊ) | 8 | 2 | 0 |

Hai bài gần bằng nhau về **số** dòng trống. Chỉ độ dài khối mới tách được chúng.

Luật rút ra: có **một bài KHEN và một bài CHÊ** rồi mới chốt ngưỡng. Đừng nghĩ ra ngưỡng
từ trực giác rồi đi tìm số liệu ủng hộ nó.

## Đã vá

- `caption_check.longest_prose_block()` + `MAX_PROSE_BLOCK = 4`: khối trên 4 dòng là
  **LỖI**, không phải `[nhac]` — vì `miles_submit` in thẳng cho vai đọc rằng `[nhac]`
  không cần sửa. Dòng bullet không tính vào khối.
- Ngưỡng cổng (5) rộng hơn ngưỡng SOUL dạy (1–3 câu), có chủ đích: dạy chặt, chặn lỏng.
  Vai chỉ được sửa 2 lần rồi task hỏng.
- `check_jika_voice` miễn dòng danh sách khỏi luật "emoji chỉ ở câu mở/kết" (LOW-380) —
  trước đây Jika viết đúng khuôn liệt kê cũng bị đá về. Miễn cả gạch `•` lẫn emoji làm
  gạch đầu dòng, **nhưng chỉ khi thân bài còn văn xuôi**: thiếu điều kiện đó thì kiểu
  emoji-đầu-mọi-câu (Ông Chủ bỏ 19/09, LOW-274) tự gọi mình là "một danh sách dài" rồi
  lọt. Ca này lọt thật ở bản đầu, `test_emoji_dau_moi_cau_van_bi_chan` bắt được.
- Luật vào **cả 4 SOUL**, sửa hai bài mẫu `jika.SOUL.md`, brief tách thành mục riêng.
- `tests/test_caption_spacing.py` chép **nguyên văn hai bài thật** — vì chính bài thật mới
  lộ ra chuyện thước đo sai.

Một test CŨ (`test_jika_bai_mau_trong_soul_dat_cong`) đỏ lên ngay khi cổng mới bật, và
chính nó chỉ ra bài mẫu trong SOUL đang dạy ngược. Cổng đó có từ trước, không phải tôi
phát hiện bằng mắt.

## Chạy thử và deploy

Máy chủ, bản sao `/tmp/ct-low379` clone `--shared` (không đụng production): nền
**192/192**, sau khi vá **193/193**. (Máy dev Windows có 35 tệp hỏng vì `fcntl` /
`time.tzset` — nền máy chủ chứng minh đó là chuyện môi trường.)

Deploy `fdab223 → 975164b`, máy chủ không có tệp dirty, chỉ PR #239 đi trong lượt này.

SOUL không tự tới runtime. Đẩy bằng bốn lệnh hẹp thay vì `cp` tay:

```bash
for s in blog/jika blog/miles dcgr/jika dcgr/miles; do
  venv/bin/python sync_hermes.py --ra-hermes --chi SOUL\ $s
done
```

`--chi` lọc theo TÊN MỤC (`SOUL <brand>/<vai>` và `MEMORY <brand>/<vai>`), nên mỗi lượt
chọn đúng 1 tệp. **`--ra-hermes` trần vẫn là bẫy**: lúc deploy vẫn còn `MEMORY dcgr/nova`
và `MEMORY dcgr/vera` lệch (vai tự ghi), chạy trần là mất. Sau khi chép, `sync_hermes.py`
chỉ còn báo đúng hai MEMORY đó — SOUL đã khớp.

Kiểm sau deploy trên production: `MAX_PROSE_BLOCK = 4` đã sống, `10 test DAT`, `38/38`;
bài KHEN `khoi 2 | QUA, 0 loi`, bài CHÊ `khoi 8 | BI CHAN`.

## Nhìn ở đâu những ngày tới

- Dòng `[LOI]` trong log nộp của `miles_submit.py` / `jika_submit.py` — dự kiến khoảng
  20% bài bị đá về lần đầu trong vài ngày tới, rồi giảm khi SOUL mới ngấm.
- Đo lại bằng script khối văn xuôi: kỳ vọng cột "khối ≥5" về gần 0 ở cả hai vai.
- Cột "bài có bullet" tách theo vai: **Jika đang 0/75 bài, chưa một bài nào**. Sau một
  tuần vẫn 0% thì mở ticket cho guardrail — cổng hiện chỉ chống chặn oan, không bắt buộc
  phải có bullet (code không phân biệt được "đáng ra phải liệt kê" với "không có gì để
  liệt kê").
