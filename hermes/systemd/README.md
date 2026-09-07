# Bản chụp cấu hình chạy thật (systemd user units)

Chụp từ máy chủ ngày 06/09/2026. Trước đó **chỉ có `nhat-ky-web.service`** nằm
trong git, còn unit template `hermes-approve@.service` — nơi đặt `CT_BRAND`,
`HERMES_HOME`, và các drop-in đặt `CT_BANG_DEN` — thì không. Nghĩa là prompt và
hành vi thật của đội phụ thuộc vào những tệp không ai theo dõi được: cài lại máy
hay `hermes update` xong là phải dựng lại từ trí nhớ. Đúng cái sự cố
`moat_publish.py` ngày 22/08 mà `hermes/README.md` mở đầu bằng.

Đây là **bản chụp để đọc và tái tạo**, không phải nguồn tự động triển khai:
`dong_bo_hermes.py` không ghi đè systemd (đổi unit là việc cần người xác nhận).
Sửa trên máy chủ xong thì chụp lại vào đây trong cùng một commit.

## Cài lại từ bản chụp

```bash
cp -r hermes/systemd/*.service hermes/systemd/*.service.d ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hermes-approve@blog hermes-approve@dcgr
```

## Thứ KHÔNG nằm ở đây

- `HERMES_DASHBOARD_SESSION_TOKEN` trong hai unit dashboard đã được **che**.
  Token thật lấy từ máy chủ đang chạy, hoặc sinh mới rồi đặt lại vào unit.
- `secret.common.env` và `secret.<brand>.env` (bot token Telegram, khoá moat) —
  không bao giờ commit; unit chỉ trỏ tới đường dẫn.
