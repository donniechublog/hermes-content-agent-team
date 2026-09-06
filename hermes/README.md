# Cấu hình hermes (bản trong git)

SOUL và script cron của đội **thật sự chạy** từ `~/.hermes-<brand>/` (mỗi brand một
home: `~/.hermes-blog`, `~/.hermes-dcgr`), không phải từ đây.
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

Map slug ↔ nhân vật. shared (một SOUL cho cả hai home, script tự lấy brand từ
sidecar, chỉ khác handle và người đọc): `designer`=Ethan, `carousel`=Dre,
`writer`=Miles, `carousel-edu`=Kite, `itachi`, `gin`, `analyst`=Ada (từ 05/09/2026,
trước đó designer/carousel/writer mỗi brand một bản), `bob` (từ 06/09/2026: một
SOUL 32 dòng thay hai bản 91 dòng, handle do `bob_nop.py` đọc từ bảng brand của
`card.py` chứ không gõ trong SOUL). Chỉ ở blog: `scout`=Finn,
`teaser`=Jean (đọc donniechu.com), `nova`. Chỉ ở dcgr: `market`=Vera.
(từ 03/09/2026: dcgr chỉ có Vera đi tìm tin, Finn không có cron ở dcgr nên bỏ).
`carousel-edu`=Kite (blog) đã deploy live từ 01/09/2026 (full pipeline:
render_edu.py + profile + approve).

Sửa ở home rồi chép vào git trước khi commit:

    venv/bin/python dong_bo_hermes.py --vao-repo

Hoặc chiều ngược lại (đẩy git → cả hai home), sau `hermes update`:

    venv/bin/python dong_bo_hermes.py --ra-hermes

Không cờ = chỉ so sánh. Script quét `profiles/{blog,dcgr,shared}/`, sync SOUL +
MEMORY + cron (brand-aware) sang home tương ứng; profile/script home không có
thì báo `[thieu]`, KHÔNG tạo (tôn trọng phân chia per-brand).

## Plugin kanban

`hermes/plugins/kanban/` giữ bản vá cho bảng kanban trong dashboard. **Bốn** thay
đổi (trước đây mục này chỉ ghi ba, thiếu mục cuối):

- **Thứ tự cột**: `running, ready, blocked, todo, done` rồi mới tới `review,
  scheduled, triage`. Sắp theo mức độ cần nhìn, không theo vòng đời. Ba cột cuối
  gần như luôn rỗng trong dây chuyền nội dung. Thứ tự gốc của hermes là
  `triage, todo, ready, running, blocked, review, done` — thấy `triage` đứng đầu
  trong `dist.index.js` là dấu hiệu bản vá đã mất.
- **Nhãn profile to lên**: lane header từ `0.65rem` lên `0.82rem` kèm viền trái
  màu nhấn; huy hiệu `@profile` trên thẻ có nền và cỡ `0.8rem`. Trước đó chữ quá
  nhỏ và chìm vào đám xám nên phải mở từng thẻ mới biết bot nào.
- **Chia lane ở mọi cột**: trước chỉ cột `running` mới tách theo profile.
- **Hiện tên người thay slug**: `/board` trả thêm `display_names` đọc từ
  `profile.yaml` (cache 30s trong `plugin_api.py`); mọi nhãn assignee trong
  `dist.index.js` đi qua `tenVai()` nên bảng hiện `Finn`, `Dre`… thay vì
  `scout`, `writer`. Giá trị gửi lên API và giá trị filter **vẫn là slug**, chỉ
  phần chữ nhìn thấy đổi.

Đây là tệp trong bản cài hermes nên **`hermes update` sẽ ghi đè**. Quy trình sau
khi cập nhật hermes:

    venv/bin/python dong_bo_hermes.py              # xem lệch những gì
    venv/bin/python dong_bo_hermes.py --ra-hermes  # khôi phục bản vá
    systemctl --user restart hermes-dashboard

### Cổng chặn mất bản vá

Trước 06/09/2026 cổng bảo vệ so **lệch kích thước 15%** và chỉ chạy ở chiều
`--ra-hermes`. Nó hỏng cả hai đầu, và đã mất bản vá thật:

- Chiều `--vao-repo` **không có cổng nào**. Ngày 04/09/2026 một bản `~/.hermes`
  vừa bị `hermes update` reset về gốc đã đi ngược vào git (commit `a1f9387`,
  message ghi là "chép bản vá vào git" nhưng diff thực tế **xoá** bản vá) và
  thổi bay hai bản vá *thứ tự cột* và *chia lane ở mọi cột*. Khôi phục 06/09.
- Kích thước không nói lên bản vá còn hay mất. Một bản hermes mới thêm ~130
  dòng vào `plugin_api.py` chỉ lệch ~2,4% — lọt dưới ngưỡng, và `--ra-hermes`
  vẫn đè mất tính năng upstream.

Nay `dong_bo_hermes.py` kiểm **theo dấu vết** (`DAU_VET`), áp cho **cả hai
chiều**: mỗi bản vá có một chuỗi đặc trưng (`tenVai(`, chuỗi lane-check, thứ tự
cột, các thuộc tính CSS, `display_names`). Trước khi ghi, script so bên nguồn và
bên đích — **bên đích đang có dấu vết mà bên nguồn thiếu thì từ chối ghi**, vì
đó đúng là kịch bản ghi đè làm mất bản vá. Chiều ngược lại (nguồn có, đích
thiếu) chính là đang mang bản vá sang nên vẫn chạy bình thường.

Gặp `[BO QUA]` thì **vá lại từ bản mới, đừng đè**. `--ep` chỉ dùng khi đã xem
bằng tay và chắc chắn.

### Bám theo upstream

`hermes/plugins/kanban/UPSTREAM` ghi hash commit hermes-agent mà bản vá đang
đứng trên (`dong_bo_hermes.py --vao-repo` tự cập nhật). Có hash mới rebase 3
chiều được thay vì đoán:

    git -C ~/hermes-agent diff <hash trong UPSTREAM>..HEAD -- plugins/kanban/dashboard

Bản chép trong repo hiện **đứng sau upstream**: thiếu endpoint export/import
board và phần giữ connection WS trong `stream_events` của `plugin_api.py`. Chưa
rebase — cần làm khi rảnh tay, theo đúng lệnh `diff` ở trên.
