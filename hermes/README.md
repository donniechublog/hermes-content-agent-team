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
  trong `dist/index.js` là dấu hiệu bản vá đã mất.
- **Nhãn profile to lên**: lane header từ `0.65rem` lên `0.82rem` kèm viền trái
  màu nhấn; huy hiệu `@profile` trên thẻ có nền và cỡ `0.8rem`. Trước đó chữ quá
  nhỏ và chìm vào đám xám nên phải mở từng thẻ mới biết bot nào.
- **Chia lane ở mọi cột**: trước chỉ cột `running` mới tách theo profile.
- **Hiện tên người thay slug**: `/board` trả thêm `display_names` đọc từ
  `profile.yaml` (cache 30s trong `plugin_api.py`); mọi nhãn assignee trong
  `dist/index.js` đi qua `tenVai()` nên bảng hiện `Finn`, `Dre`… thay vì
  `scout`, `writer`. Giá trị gửi lên API và giá trị filter **vẫn là slug**, chỉ
  phần chữ nhìn thấy đổi.

### Bản vá sống ở đâu (đổi 06/09/2026)

Trước đây bản vá nằm **trong bản cài hermes** (`~/hermes-agent/plugins/kanban/dashboard/`),
tức đúng chỗ `hermes update` ghi đè, rồi `dong_bo_hermes.py` chép qua chép lại để
"khôi phục". Mất bản vá ba lần là hệ quả tất yếu của việc đặt sai chỗ, không phải
của cổng chặn yếu.

Hermes có sẵn cách đúng: dashboard quét `<HERMES_HOME>/plugins/<tên>/dashboard/`
**trước** plugin đi kèm và khử trùng **theo tên** (`_discover_dashboard_plugins`,
`seen_names`). Một plugin tên `kanban` ở thư mục người dùng che hoàn toàn bản đi
kèm, cả `dist/` lẫn `plugin_api.py`, và `hermes update` không bao giờ đụng vào
`<HERMES_HOME>/plugins/`. Nên từ 06/09/2026:

    hermes/plugins/kanban/dashboard/   <->   ~/.hermes-<brand>/plugins/kanban/dashboard/

cho cả hai home, gồm `manifest.json`, `plugin_api.py`, `dist/index.js`,
`dist/style.css` (bố cục y hệt upstream, không còn tên phẳng `dist.index.js`).
`~/hermes-agent` chỉ còn là nơi **soi upstream đổi gì**, không còn là điểm đồng bộ.

Chuyển một lần trên server, mỗi home:

    venv/bin/python dong_bo_hermes.py --ra-hermes          # tạo plugins/kanban/ ở cả hai home
    HERMES_HOME=~/.hermes-blog ~/hermes-agent/venv/bin/python -m hermes_cli.main plugins enable kanban
    HERMES_HOME=~/.hermes-dcgr ~/hermes-agent/venv/bin/python -m hermes_cli.main plugins enable kanban
    git -C ~/hermes-agent checkout -- plugins/kanban/dashboard   # bản đi kèm về nguyên bản
    systemctl --user restart hermes-dashboard@blog hermes-dashboard@dcgr   # unit thật của anh

Bước `plugins enable` là bắt buộc: hermes chỉ mount API của plugin **người dùng**
khi tên nó có trong `plugins.enabled` của `config.yaml` (GHSA-mcfc-hp25-cjv7).
Thiếu thì tab kanban vẫn hiện mà mọi `/api/plugins/kanban/*` đều 404.
`dong_bo_hermes.py` đọc `config.yaml` từng home và nhắc đúng lệnh khi thiếu.

Sau đó `hermes update` không còn liên quan gì tới bản vá. Sửa bản vá thì sửa trong
git rồi `--ra-hermes` và restart dashboard.

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

Cái giá của việc che plugin đi kèm: upstream đổi gì ở dashboard kanban, đội
**không tự nhận được** nữa. Đổi mất-im-lặng lấy port-có-chủ-ý, và port là việc
làm khi rảnh tay, không phải mỗi lần `hermes update`.

`hermes/plugins/kanban/UPSTREAM` ghi hash commit hermes-agent mà bản vá đang
đứng trên. Quy trình port:

    venv/bin/python dong_bo_hermes.py --kiem-upstream   # upstream đổi gì kể từ hash đó
    # vá lại bốn bản vá lên bản mới trong hermes/plugins/kanban/dashboard/
    venv/bin/python dong_bo_hermes.py --ra-hermes       # đẩy lên hai home, restart dashboard
    venv/bin/python dong_bo_hermes.py --chot-upstream   # ghi HEAD mới vào UPSTREAM

Bản trong repo hiện **đứng sau upstream** (theo bản audit, chưa kiểm được trên
máy Mac vì không có `~/hermes-agent`): thiếu endpoint export/import board và
phần giữ connection WS trong `stream_events` của `plugin_api.py`. Chạy
`--kiem-upstream` trên server để thấy đúng diff.
