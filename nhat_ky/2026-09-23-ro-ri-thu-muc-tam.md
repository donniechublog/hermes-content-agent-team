# 23/09/2026 — Rò rỉ thư mục tạm: 2,6 GB RAM trong /tmp

Ticket theo dõi: LOW-390. PR: donniechublog/hermes-content-agent-team#… (điền khi mở).
Liên quan: LOW-382 (`241aa6b`) — cùng vấn đề, làm song song, xem mục "Hai phiên giẫm chân nhau".

## Sao lộ ra

Không ai báo. Nó lộ ra lúc dọn dẹp sau LOW-379/380: Ông Chủ bảo "dọn dẹp đi", tôi đi
xem `/tmp` trên máy chủ thì thấy gần 3 GB rác, rồi Ông Chủ bảo *"trace xem từ qua tới
giờ cái gì sinh ra .tmp"*.

`/tmp` ở đó là **tmpfs — ăn RAM, không phải đĩa**.

## Truy nguồn

| bước | thấy gì |
|---|---|
| Tách tên | `tmp.XXXX` (shell `mktemp -d`) chỉ 54; `tmpXXXX` (Python `tempfile`) 3.185 |
| Theo ngày | 1.617 hôm trước / 1.568 hôm sau — rò đều, không phải sự cố một lần |
| Nội dung | `boxed.png`, `mau.png`, `chup.png`, `roi.png` — grep cả repo: **chỉ có trong `tests/`** |
| Thư mục nặng | 20–33 MB, chứa `entity/ original/ ready/ prepare/ blog/ dcgr/` = `CT_STATE_DIR` giả của test |
| Theo phút | cụm 17–33 thư mục/phút kéo ~12 phút = đúng nhịp một lượt 184 tệp test |
| Giữa các cụm | rình `/tmp` 100 giây: 0 lần tạo mới → không phải cron/service |

Kết luận: **bộ test chạy trên chính máy production**, bởi các phiên agent (`TICKET_TEMPLATE.md`
mục 3 bắt mọi ticket chạy `bash tests/run.sh`).

## Cơ chế

40 chỗ `tempfile.mkdtemp()` trong 18 tệp test. `mkdtemp()` **không bao giờ tự dọn**, khác
hẳn 601 chỗ dùng `TemporaryDirectory()`. Cộng chính dòng `mktemp -d` của `tests/run.sh`.

## Hai phiên giẫm chân nhau — chuyện đáng ghi nhất

Giữa lúc tôi làm, **LOW-382 merge vào `main` với cùng chẩn đoán** (con số của họ: ~1800
thư mục/ngày, 2,2 GB, "19 tệp, 41 chỗ gọi"). Rebase đâm xung đột ngay ở `tests/run.sh`.

Suýt hỏng: lệnh `git checkout --theirs tests/run.sh` trong lúc rebase lấy bản **của tôi**
(trong rebase, "theirs" là commit đang được áp), xoá sạch phần LOW-382. Phải dựng lại
`run.sh` từ `github/main` rồi chồng phần của mình lên.

Hai bản **không** trùng nhau về mục đích:

- LOW-382 = **dọn**: một `TMPDIR` cho cả lượt `run.sh`, xoá khi thoát, `CT_KEEP_TMP=1` để
  giữ lại khi mổ xác. Họ **cố ý** không sửa 41 chỗ gọi.
- LOW-390 = **ngăn**: ba chỗ lớp 1 không với tới —
  1. chạy **ngoài** `run.sh` (vai tự gõ `venv/bin/python tests/test_x.py`),
  2. `bob_submit.py` rò trong **mã production**,
  3. không có gì chặn `mkdtemp()` thêm vào ngày mai.

Ông Chủ chốt: giữ cả hai lớp cạnh nhau.

## Cơ chế đã dựng

- **Cổng động** (`run.sh`): mỗi tệp test một `TMPDIR` riêng → đếm được **ai** bỏ lại bao
  nhiêu, in ra, và chặn. Đo bằng thư mục thật nên bắt được cả rò rỉ của thư viện.
- **Cổng tĩnh** (`tests/test_temp_cleanup.py`): quét AST bắt `mkdtemp(` mới; bắt `.sh`
  gọi `mktemp -d` thiếu `trap`; và giữ cho **cả hai lớp** không bị gỡ âm thầm khỏi
  `run.sh`. Lối thoát là chú thích `# mkdtemp-ok: <lý do>` cạnh mã, không dùng tệp
  baseline rời.
- `tam.temp_dir()` — mkdtemp có `atexit` dọn, đổi một dòng mỗi chỗ thay vì thụt lại 40 hàm.

## Ba thứ chỉ cổng mới tìm ra, đọc mã không thấy

1. `ignore_errors=True` **nuốt lỗi câm**: `rmtree` gặp tệp chỉ-đọc trong `.git` là bỏ
   cuộc im lặng, để lại 15 thư mục của `test_kanban_plugin_patch`. Phải có handler
   chmod-rồi-thử-lại.
2. `test_report_one_attempt.py` đặt `CT_STATE_DIR` rồi không trả lại. Thư mục bị xoá,
   biến vẫn trỏ tới đó, và `env_load.state_dir()` *luôn tạo sẵn thư mục* nên nó **dựng
   lại**. Không một chữ `mkdtemp` nào trong tệp đó.
3. `.org.chromium.Chromium.*` của Chromium, 1/3 lần chạy. Không sửa được → đếm và in,
   **không chặn**. Chặn cứng vì nó thì cổng đỏ thất thường, mà đỏ thất thường thì người
   ta học cách bỏ qua cổng.

## Số đo (máy chủ dc-group)

Qua `run.sh`: **204/204 tệp test qua, 0 rác**, cổng tĩnh 4/4.

Chạy **ngoài** `run.sh` — đây là phần LOW-390 thêm được sau khi đã có LOW-382:

| tệp | main (đã có LOW-382) | thêm LOW-390 |
|---|---:|---:|
| `test_replay_model_watch` | 32 | 0 |
| `test_low339_contain_fit` | 21 | 0 |
| `test_kanban_plugin_patch` | 15 | 0 |
| `test_scan_seen` | 13 | 0 |
| `test_low347_hairline_trim` | 10 | 0 |
| `test_line_gate_fail_open` | 1 | 0 |
| `test_report_one_attempt` | 1 | 0 |
| **tổng** | **93** | **0** |

Một chỗ tôi nói sai giữa chừng rồi sửa: "160 → 0" chỉ đúng với `main` **trước** LOW-382.
Với `main` hôm nay nền đã là 0 cho đường qua `run.sh`; bảng trên mới là phần thêm thật.

## Nhìn ở đâu sau khi deploy

- `df -h /tmp` những ngày tới — con số phải đứng yên thay vì tăng ~1.600 thư mục/ngày.
- Dòng `[RAC TAM]` trong log `tests/run.sh` của các phiên.
- 2,6 GB đang tồn: dọn riêng sau khi cổng xanh (lệnh an toàn chỉ đụng thứ cũ hơn 24h,
  chừa `discard-*`/`deploy-*`). LOW-382 đã hạ tuổi quét `/etc/tmpfiles.d/tmp.conf` từ 10
  ngày xuống 3 ngày nên phần cũ sẽ tự rụng.

## Để sau (Ông Chủ 23/09: "tạm thời cứ để đó, fix sau")

1. Đổi tên tiếng Việt trong `tests/test_caption_spacing.py` (tệp mới của LOW-379, đã merge).
2. Mở rộng cổng `test_name_english.py` sang `tests/` — hiện `docs/tu_dien_ten/tudien.py:15`
   loại hẳn `tests` khỏi tầm quét. Chính phiên này chứng minh là thiếu: 7 tên mới tiếng
   Việt của tôi lọt vào `tests/tam.py` mà cổng vẫn xanh, phải Ông Chủ hỏi "tam.py là Eng
   hay Vi" mới lộ.
