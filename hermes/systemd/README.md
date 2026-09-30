# Bản chụp cấu hình chạy thật (systemd user units)

Chụp từ máy chủ ngày 06/09/2026. Trước đó **chỉ có `journal-web.service`** nằm
trong git, còn unit template `hermes-approve@.service` — nơi đặt `CT_BRAND`,
`HERMES_HOME`, và các drop-in đặt `CT_BLACKBOARD_BRANDS` — thì không. Nghĩa là prompt và
hành vi thật của đội phụ thuộc vào những tệp không ai theo dõi được: cài lại máy
hay `hermes update` xong là phải dựng lại từ trí nhớ. Đúng cái sự cố
`moat_publish.py` ngày 22/08 mà `hermes/README.md` mở đầu bằng.

Đây là **bản chụp để đọc và tái tạo**, không phải nguồn tự động triển khai:
`sync_hermes.py` không ghi đè systemd (đổi unit là việc cần người xác nhận).
Sửa trên máy chủ xong thì chụp lại vào đây trong cùng một commit.

Để biết máy chủ có đang lệch bản chụp không (kể cả `hermes/gateway/<brand>/config.yaml`
và `~/.config/openssl/hermes-groups.cnf`), chạy chế độ **chỉ đọc**:
`venv/bin/python sync_hermes.py --compare-runtime` (`--chi <chuỗi>` để lọc). Nó in
`[KHAC]` / `[THIEU]` / `[CHI_CO_TREN_MAY]` cho từng tệp và thoát 1 nếu có lệch; token
dashboard được che ở cả hai bên trước khi so. Không ghi gì.

## Cài lại từ bản chụp

```bash
cp -r hermes/systemd/*.service hermes/systemd/*.service.d ~/.config/systemd/user/
mkdir -p ~/.config/openssl && cp hermes/systemd/openssl/hermes-groups.cnf ~/.config/openssl/
systemctl --user daemon-reload
systemctl --user enable --now hermes-approve@blog hermes-approve@dcgr
```

`worker-scope-sweep.timer` (LOW-126) cài riêng — xem chú thích đầu tệp timer.

## `OPENSSL_CONF` cho approve + gateway (LOW-133)

Từ 04:05 UTC ngày 14/09/2026, máy chủ bắt tay TLS tới `api.telegram.org` hỏng
khoảng một nửa số lần khi dùng danh sách nhóm khoá mặc định của OpenSSL 3.5
(runtime Python của hermes-agent). Đo A/B cùng lúc: mặc định 5/12 và 6/10,
nhóm cổ điển 12/12 và 10/10, curl hệ thống (OpenSSL 3.0) 12/12. Triệu chứng: nút
Telegram "không phản hồi" vì callback tới trễ, tin tiến độ và tin nút bị rơi.

- `hermes-approve@.service.d/openssl-groups.conf` và
  `hermes-gateway@.service.d/openssl-groups.conf` đặt
  `OPENSSL_CONF=%h/.config/openssl/hermes-groups.cnf` cho mọi instance.
- `openssl/hermes-groups.cnf` chỉ đặt `Groups = X25519:prime256v1:secp384r1`.
- Worker kanban là tiến trình con của gateway nên kế thừa env; worker sinh trước
  lần restart thì không.
- Tệp này thay `/etc/ssl/openssl.cnf` cho các tiến trình con dùng OpenSSL hệ
  thống. Bản Ubuntu 24.04 trên máy chủ chỉ có `providers = default` (vốn là mặc
  định) nên không mất gì; đã thử `openssl s_client` với tệp này: TLS 1.3, xác thực OK.
- Restart gateway không giết worker đang chạy (đo 14/09: 6/6 worker sống, task
  vẫn `running`).

Gỡ khi đường tới Telegram ổn lại: xoá hai drop-in, `daemon-reload`, restart
`hermes-approve@{blog,dcgr}` và `hermes-gateway@{blog,dcgr}`.

## Báo khi `hermes-approve@` chết hẳn (D17, 30/09/2026)

Trước đây unit chỉ có `Restart=always`, không `OnFailure=`: dịch vụ duyệt bài chết là
im lặng, Ông Chủ chỉ biết khi nút Telegram không phản hồi. Nay:

- `hermes-approve@.service` có `OnFailure=notify-fail@%n.service`.
- **Kèm** `StartLimitIntervalSec=900` / `StartLimitBurst=20`. Không có giới hạn này thì
  `OnFailure=` không bao giờ chạy: `Restart=always` + `RestartSec=5` chỉ ở trạng thái
  "auto-restart", không sang `failed` (mặc định 5 lần/10 giây, mà 1 lần/5 giây thì không
  chạm). Hệ quả: crash loop thật (20 lần trong 15 phút) sẽ khiến unit **dừng hẳn** thay
  vì quay vô hạn trong im lặng. Khởi động lại tay: `systemctl --user reset-failed
  hermes-approve@<brand> && systemctl --user start hermes-approve@<brand>`.
- `notify-fail@.service` + `notify-fail.sh` (unit mẫu, chỉ trong repo): ghi một dòng mức
  ERR vào journal (`journalctl --user -p err` thấy) và gửi Telegram vào topic `ada` của
  brand qua `publish.py --text ... --to-env TELEGRAM_GROUP_ID --thread-name ada`.
  Không có gì lạ cần cài ngoài `daemon-reload`. Lệnh `cp` ở trên đã chép được nó
  (`*.service`); script chạy thẳng từ `~/content-team/hermes/systemd/`.

Chưa cài lên máy nào. Khi cài: chép `hermes-approve@.service` mới + `notify-fail@.service`,
`daemon-reload`, rồi **restart** `hermes-approve@{blog,dcgr}` để unit nhận `OnFailure=`.
Thử: `systemctl --user start notify-fail@hermes-approve@blog.service` (chỉ gửi báo, không
đụng dịch vụ thật).

## Thứ KHÔNG nằm ở đây

- `HERMES_DASHBOARD_SESSION_TOKEN` trong hai unit dashboard đã được **che**.
  Token thật lấy từ máy chủ đang chạy, hoặc sinh mới rồi đặt lại vào unit.
- `secret.common.env` và `secret.<brand>.env` (bot token Telegram, khoá moat) —
  không bao giờ commit; unit chỉ trỏ tới đường dẫn.
