# Dre phản hồi chậm vì lệnh tìm thêm ảnh — 03/10/2026

Ticket theo dõi: LOW-456.

Ông Chủ hỏi "Dre hôm nay phản hồi lâu vậy?" kèm ảnh topic Dre dcgr: ba tin liền "⏳ Dre vẫn
đang làm, đã 20 phút" và "còn 4 việc xếp hàng sau việc này".

Đo trên dc-group (`profiles/dre/state.db`, `kanban.db`): một bài Dre dcgr p50 21.7 phút, chờ
model chỉ 4.0 phút, còn 16.4 phút là chạy tool — gần hết trong `find_more_images.py`
(58 lần / 8 bài, p50 124 s/lần). Model không chậm đi; hôm nay cũng không tệ hơn 25–29/09.
Sáng nay 12 bài đến trong 6 phút, 6 suất song song, nên bài cuối chờ ≥ 30 phút mới bắt đầu.

Hai nguyên nhân trong lệnh tìm thêm:

1. Mỗi từ khoá chạy **tuần tự** qua 5 nguồn (Yandex qua Chromium, Bing + bóc báo, Commons,
   Openverse, ảnh báo về thực thể), ~45 s/từ khoá. 3–4 từ khoá cộng vision là chạm
   `terminal.timeout: 180` của hermes: 45 lần bị giết trong 9 ngày, mất trắng (manifest
   chưa ghi). Vá: từ khoá chạy song song (mỗi luồng một Chromium riêng — Playwright sync
   không dùng chung qua luồng), chung ngân sách 75 s; hết giờ thì lấy phần đã tìm, vẫn tải
   / lọc / ghi manifest, in rõ từ khoá nào chưa chạy hết.
2. `schema._count_stackable_pairs_real` duyệt tập con để đếm cặp ghép — ổn với "vài tấm",
   nhưng tìm thêm nhiều lượt đẩy số tấm chỉ-ghép lên 20–33. Bài Tencent (33 tấm) **không
   bao giờ đếm xong**: treo cả `find_more_images` lẫn `dre_prepare`/`dre_submit` của bài đó.
   Vá: dừng khi đạt trần n//2 và bỏ trước các tấm không ghép được với tấm nào. Kết quả
   trùng 100% bản cũ trên 577 manifest thật; chậm nhất < 0.05 s.

Bài học: "duyệt tập con, số tấm chỉ vài tấm" là một giả định về dữ liệu, và một tính năng
khác (tìm thêm nhiều lượt) đã lặng lẽ phá nó. Giả định kiểu này phải khoá bằng test cỡ
thật (40 tấm), không chỉ ghi trong docstring.

Bẫy khi thử: `git diff github/main` giữa phiên kéo theo chiều ngược của commit phiên khác
vừa vào main — tạo patch bằng `git diff HEAD`.
