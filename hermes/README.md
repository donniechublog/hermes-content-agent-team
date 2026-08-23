# Cấu hình hermes (bản trong git)

SOUL và script cron của đội **thật sự chạy** từ `~/.hermes/`, không phải từ đây.
Thư mục này là bản chép để có lịch sử thay đổi.

Vì sao cần: ngày 22/08 script dọn em-dash của tôi làm hỏng 21 tệp Python. Hai
mươi tệp khôi phục được từ git trong một lệnh; `moat_publish.py` không nằm trong
git nên phải vá tay từng khối. Sang 23/08 lại phát hiện ba script cron dùng sai
múi giờ, và cũng không có lịch sử để đối chiếu xem đã đổi gì.

SOUL và script cron là nơi chứa phần lớn hành vi của đội. Chúng đáng được theo
dõi ngang với mã nguồn.

## Đồng bộ

Sửa ở `~/.hermes/` rồi chép vào đây trước khi commit:

    venv/bin/python dong_bo_hermes.py --vao-repo

Hoặc chiều ngược lại, khi khôi phục sau `hermes update`:

    venv/bin/python dong_bo_hermes.py --ra-hermes

Script so nội dung và chỉ báo tệp thật sự khác nhau.
