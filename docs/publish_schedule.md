# Xếp lịch đăng bài — 2 bài liên tiếp cách nhau 1 tiếng

Chốt 18/09/2026 với Ông Chủ. Áp cho **cả hai brand** (`donniechublog`, `dcgr`).

## Vấn đề

Bấm "✅ Duyệt & đăng" là bài lên Telegram channel **ngay lập tức**, rồi đẩy thẳng
sang moat. Duyệt 5 bài trong 3 phút thì channel ra 5 bài trong 3 phút, và
extension cũng nhả 5 bài lên Facebook/Instagram gần như cùng lúc.

## Cách làm

Nút Duyệt không còn đăng bài. Nó **chiếm một slot** rồi trả thẻ về ngay:

    slot = max(now, last_slot + 1 tiếng)

`last_slot` là một con trỏ duy nhất trong `state/<brand>/publish_schedule.json`.
Hàng vắng (bài trước đã quá 1 tiếng) thì `slot == now`, tức bấm là đăng — giãn
cách chỉ xuất hiện khi thật sự có dồn bài.

Việc đăng chuyển cho cron `publish-due` (mỗi phút, mỗi home một job): quét
`drafts/*.json`, lấy bài `status == "scheduled"` và `publish_at <= now` của
đúng brand mình, đăng lần lượt qua `publish_one()` — cùng một hàm mà nút
"⚡ Đăng ngay" gọi. **Một đường code duy nhất**, không có nhánh "đăng nhanh"
riêng để lệch dần theo thời gian.

## Vì sao cron chứ không phải `threading.Timer`

Lịch phải sống sót `systemctl restart`, OOM và mất điện. Con trỏ + `publish_at`
nằm trên đĩa, nên máy tắt 3 tiếng rồi bật lại thì tick đầu tiên đăng bù hết bài
quá giờ. Timer trong tiến trình thì mất sạch, không để lại dấu vết nào.

## Trạng thái trên đĩa

| Chỗ | Khoá | Ý nghĩa |
|---|---|---|
| `state/<brand>/publish_schedule.json` | `last_slot` | epoch của slot vừa phát ra |
| `drafts/<id>.json` | `publish_at` | epoch tới giờ đăng |
| `drafts/<id>.json` | `status` | thêm `scheduled`, `cancelled` |

Hai khoá `flock` **riêng**, không gộp:

- `state/<brand>/publish_slot.lock` — chia slot, giữ vài micro-giây. Hai thread
  nền của approve_service bấm cùng lúc vẫn ra hai giờ khác nhau.
- `state/<brand>/publish_due.lock` — đăng một bài, giữ tới vài **phút** (upload
  carousel trên uplink ~50 KB/s). Chặn hai tick cron chồng nhau, và chặn luôn
  nút "Đăng ngay" đâm vào giữa một bài cron đang đăng.

Gộp làm một thì bấm Duyệt bài mới bị treo mấy phút chờ cron đăng xong bài
trước — thẻ không trả về, Ông Chủ bấm lại.

## Luật đã chốt

- **Teaser đăng ngay**, không chiếm slot: `publish_at = now`, con trỏ đứng im.
  Teaser chỉ lên Telegram (`moat_publish.intake` vốn đã từ chối nó), nên nó
  không giành chỗ với bài social.
- **Huỷ lịch không dồn hàng lên.** Bỏ một bài giữa chừng thì slot đó để trống.
  Dồn lên nghĩa là bài sau bị đăng sớm hơn giờ đã báo cho Ông Chủ — đổi giờ sau
  lưng người ta tệ hơn là phí một chỗ.
- **Khoảng cách 1 tiếng là hằng số** `GAP_SECONDS` trong code, không phải biến
  môi trường. Đổi nhịp là một quyết định có chủ đích, đi qua commit.
- **"Đăng ngay" không kéo con trỏ về.** Ép một bài lên sớm thì slot đã phát cho
  nó vẫn tính, nên bài duyệt tiếp theo vẫn cách slot đó một tiếng chứ không
  cách lúc đăng thật một tiếng. Đây là escape hatch, không phải đường chính —
  nếu dùng nhiều tới mức thấy vướng thì sửa `reserve()` đọc `max(publish_at)`
  thay cho con trỏ.

## Nút trên thẻ

Sau khi bấm Duyệt, bàn phím đổi thành:

- `⚡ Đăng ngay` (`pnow:<id>`) — đặt `publish_at = now` rồi gọi thẳng
  `publish_one` ở thread nền. Cùng `flock` với cron nên không đăng đôi.
- `🗑 Huỷ lịch` (`pcancel:<id>`) — `status = "cancelled"`, gỡ nút.

Cron báo kết quả bằng `moat_publish.report_card()` (reply đúng thẻ) rồi gỡ bàn
phím trên chính thẻ đó.

## Kẹt giữa chừng

Bài đang đăng vẫn mang `status = "scheduled"` cho tới khi Telegram trả lời,
chứ không chuyển sang `publishing`. Nên một cú `kill -9` giữa lúc upload để lại
bài ở đúng trạng thái chờ, và tick sau đăng lại (an toàn nhờ mục dưới) — khác
đường cũ, vốn để bài kẹt vĩnh viễn ở `publishing` và phải có
`_rescue_article_end_publishing` gỡ lúc khởi động.

## Vì sao đăng đôi không xảy ra

`approve_post.publish()` vốn đã ghi `channel_album_mid` / `channel_photo_mid`
ngay khi Telegram nhận, và bỏ qua bước gửi album nếu khoá đó đã có. Nên cron
chạy bù, bấm "Đăng ngay" trùng lúc cron chạy, hay tick sau một lần crash giữa
chừng — đều không ra hai bài trên channel.

## Bất biến không được phá

Telegram lỗi thì **tuyệt đối không** gọi `moat_publish.intake`: bài chưa lên
channel là bài chưa duyệt xong. `tests/test_form_article.py` giữ luật này từ
trước khi tách hàm; `tests/test_publish_schedule.py` giữ lại sau khi tách.

## Cron

`hermes/scripts/publish_due.sh` (brand-aware, nằm trong danh sách `SCRIPT` của
`sync_hermes.py` nên có lịch sử git), job `publish-due` `* * * * *` ở cả
`~/.hermes-blog` lẫn `~/.hermes-dcgr`.
