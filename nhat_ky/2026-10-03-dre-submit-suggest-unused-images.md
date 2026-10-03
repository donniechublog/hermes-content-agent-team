# Dre đi tìm ảnh mới khi bài vẫn còn ảnh qua cổng — 03/10/2026

Ticket theo dõi: LOW-458 (tách từ LOW-456).

Đo 7 ngày trên dc-group (`profiles/dre/state.db`): 299/381 lần Dre gọi `find_more_images.py`
(78%) là lúc brief đã báo đủ ảnh. Lần gọi thừa hay đứng ngay sau một lỗi `dre_submit` kiểu
"A# gần như TRỐNG" hoặc "<chủ thể> của A# không đặt vừa khung 4:5 phía TRÊN vùng chữ…
Dùng ảnh khác". Lỗi không nói tấm nào thay được, nên Dre hiểu là phải đi tìm ảnh mới.

Vá: `dre_submit` ghi lại các lỗi "cần ảnh khác" kèm vùng chữ của loại slide (bìa 40%, quote
45%, thân 30%). Giải xong cả spec thì gắn vào chính lỗi đó các tấm CHƯA DÙNG qua được đúng
những cổng ấy (`submit_common.unused_fitting_images`), kèm câu "KHÔNG cần find_more_images".
Không còn tấm nào thì không gắn gì — lúc đó tìm thêm là đúng.

Phát lại 494 lỗi thật (bộ ảnh lấy theo brief gần nhất, tấm đã dùng lấy theo spec Dre vừa
ghi): 363 lỗi (73%) có tấm thay thế, trong đó 231 lần thực tế Dre đã đi tìm thêm.

Bài học khi đo: lần đầu tôi dùng tiêu chí "ảnh chụp sạch, không mặt người" (lấy lại từ
`_fits_frame_with_subject`). Tiêu chí đó chỉ thấy tấm thay thế ở 10% lỗi, vì nó chặt hơn
chính các cổng của `dre_submit` (ảnh chưa đo hộp chủ thể vẫn qua; mặt người có tên vẫn qua).
Gợi ý phải theo đúng cổng thật, không theo một luật chặt hơn nghĩ ra cho an toàn.

Còn mở: số "Slide dựng được: X / tối thiểu Y" trong brief đếm lạc quan hơn cổng nộp — nó
không xét vùng chữ theo loại slide.
