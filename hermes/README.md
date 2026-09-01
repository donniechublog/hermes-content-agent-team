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

Đã **tách container theo brand**: mỗi brand một HERMES_HOME riêng
(`~/.hermes-blog`, `~/.hermes-dcgr`). Profile trong git tổ chức theo container,
slug generic khớp thư mục thật trong home:

    hermes/profiles/blog/<slug>.SOUL.md    -> ~/.hermes-blog/profiles/<slug>/
    hermes/profiles/dcgr/<slug>.SOUL.md    -> ~/.hermes-dcgr/profiles/<slug>/
    hermes/profiles/shared/<slug>.SOUL.md  -> CẢ HAI home

Map slug ↔ nhân vật: blog `carousel`=Dre, `designer`=Ethan, `writer`=Miles,
`nova`; dcgr `carousel`=Dre, `designer`=Ethan, `writer`=Miles, `market`=Vera;
shared: `scout`=Finn, `teaser`=Jean, `itachi`, `gin`, `analyst`=Ada, `bob`.
`carousel-edu`=Kite (blog) đã có SOUL trong git nhưng CHƯA deploy (thiếu
config.yaml) → `dong_bo` sẽ báo `[thieu]`, không tạo.

Sửa ở home rồi chép vào git trước khi commit:

    venv/bin/python dong_bo_hermes.py --vao-repo

Hoặc chiều ngược lại (đẩy git → cả hai home), sau `hermes update`:

    venv/bin/python dong_bo_hermes.py --ra-hermes

Không cờ = chỉ so sánh. Script quét `profiles/{blog,dcgr,shared}/`, sync SOUL +
MEMORY + cron (brand-aware) sang home tương ứng; profile/script home không có
thì báo `[thieu]`, KHÔNG tạo (tôn trọng phân chia per-brand).

## Plugin kanban

`hermes/plugins/kanban/` giữ bản vá cho bảng kanban trong dashboard. Ba thay đổi:

- **Thứ tự cột**: `running, ready, blocked, todo, done` rồi mới tới `review,
  scheduled, triage`. Sắp theo mức độ cần nhìn, không theo vòng đời. Ba cột cuối
  gần như luôn rỗng trong dây chuyền nội dung.
- **Nhãn profile to lên**: lane header từ `0.65rem` lên `0.82rem` kèm viền trái
  màu nhấn; huy hiệu `@profile` trên thẻ có nền và cỡ `0.8rem`. Trước đó chữ quá
  nhỏ và chìm vào đám xám nên phải mở từng thẻ mới biết bot nào.
- **Chia lane ở mọi cột**: trước chỉ cột `running` mới tách theo profile.

Đây là tệp trong bản cài hermes nên **`hermes update` sẽ ghi đè**. Quy trình sau
khi cập nhật hermes:

    venv/bin/python dong_bo_hermes.py              # xem lệch những gì
    venv/bin/python dong_bo_hermes.py --ra-hermes  # khôi phục bản vá
    systemctl --user restart hermes-dashboard

Script **tự từ chối ghi đè** khi tệp plugin lệch quá 15% kích thước, vì đó là dấu
hiệu hermes đã đổi cấu trúc bên trong chứ không chỉ đổi vài dòng. Đè bản cũ lên
lúc đó là làm hỏng bảng. Gặp trường hợp này thì vá lại từ bản mới, đừng đè. Chỉ
dùng `--ep` khi đã xem bằng tay và chắc chắn.
