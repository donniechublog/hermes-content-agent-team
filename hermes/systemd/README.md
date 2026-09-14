# Bản chụp cấu hình chạy thật (systemd user units)

Chụp từ máy chủ ngày 06/09/2026. Trước đó **chỉ có `journal-web.service`** nằm
trong git, còn unit template `hermes-approve@.service` — nơi đặt `CT_BRAND`,
`HERMES_HOME`, và các drop-in đặt `CT_BANG_DEN` — thì không. Nghĩa là prompt và
hành vi thật của đội phụ thuộc vào những tệp không ai theo dõi được: cài lại máy
hay `hermes update` xong là phải dựng lại từ trí nhớ. Đúng cái sự cố
`moat_publish.py` ngày 22/08 mà `hermes/README.md` mở đầu bằng.

Đây là **bản chụp để đọc và tái tạo**, không phải nguồn tự động triển khai:
`sync_hermes.py` không ghi đè systemd (đổi unit là việc cần người xác nhận).
Sửa trên máy chủ xong thì chụp lại vào đây trong cùng một commit.

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

## Thứ KHÔNG nằm ở đây

- `HERMES_DASHBOARD_SESSION_TOKEN` trong hai unit dashboard đã được **che**.
  Token thật lấy từ máy chủ đang chạy, hoặc sinh mới rồi đặt lại vào unit.
- `secret.common.env` và `secret.<brand>.env` (bot token Telegram, khoá moat) —
  không bao giờ commit; unit chỉ trỏ tới đường dẫn.
