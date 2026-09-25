# Đổi máy chủ, cron trôi 7 tiếng: Finn/Nova/Vera không quét sáng — 22/09/2026

Ticket theo dõi: LOW-353.

Ông Chủ, nguyên văn: *"researcher hôm nay ko làm việc"*. Sáng 22/09 không có task quét
nào của Finn (blog), Nova và Vera (dcgr). Qinn vẫn chạy nhưng lúc 10:00.

Ba lớp chồng lên nhau:

1. **Giờ máy đổi, lịch không đổi.** `donniechu-01` chạy `Etc/UTC`, `dc-group` chạy
   `Asia/Bangkok` (+07). Hermes để `timezone: ''` nên đọc biểu thức cron theo giờ máy.
   Mọi expr viết theo UTC (`0 22 * * *` = 05:00 VN) thành 22:00 VN.
2. **Hermes chỉ đuổi kịp MỘT lượt.** `timezone_migration_catchups.jsonl` ghi lượt 05:00
   ngày 21/09 được chuẩn hoá và chạy đúng; từ đó `next_run_at` tính theo +07, lượt kế là
   22:00 VN ngày 21/09.
3. **Lượt 22:00 im lặng.** Khoá chống trùng theo ngày VN (`finn-daily-20260921`) trùng
   lượt 05:00 cùng ngày; kanban trả task cũ; cổng "task mới" trong `daily_scan.sh` so
   TIÊU ĐỀ — task cũ cùng ngày có đúng tiêu đề đó → exit 0, output rỗng, cron "ok".

Sửa:

- `timezone: Asia/Ho_Chi_Minh` trong `~/.hermes-{blog,dcgr}/config.yaml` — đổi máy lần
  sau không trôi nữa. Lịch viết lại theo giờ VN: quét 06:00 (Ông Chủ chốt 22/09), Qinn
  06:00 + 18:00, daily-log 06:00, audit-cron 07:00/07:10, model-watch giữ khung cũ
  (`*/30 0-7,11,12,17-23`).
- Cổng "task mới" so `created_at` (quá 600s = task cũ → exit 1), không so tiêu đề.
- Mốc lượt Qinn: `scan_prepare.FRAME_START = 6`, cùng số trong công thức `LUOT` của
  `daily_scan.sh` (test `test_qinn_turn_matches_scan_prepare` giữ hai chỗ khớp nhau).
- Chạy tay lượt quét 22/09 cho Finn/Nova/Vera lúc 10:21.

Bài học: đổi máy chủ phải so `timedatectl` hai máy. Lịch cron là trạng thái của máy,
không nằm trong mã — test xanh, bản chụp repo khớp máy chủ, mà lịch vẫn sai 7 tiếng.
