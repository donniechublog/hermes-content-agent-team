# Bản chụp cấu hình gateway dcgr (bot mode chuẩn Hermes, thí điểm từ 05/09/2026)

Blog vẫn chat qua `chat_router.py` của approve_service; dcgr chat qua gateway Hermes
với bot riêng @hermesdcgr_bot. Khác biệt nằm hoàn toàn ở cấu hình dưới đây, code
chung một nhánh. Thư mục này là **bản chụp để tái tạo**, không được `dong_bo_hermes.py`
tự đẩy: sửa trên server rồi chép lại vào đây (`hermes/gateway/dcgr/`), tránh ghi đè
config đang chạy bằng bản cũ.

| Tệp trong repo | Đích trên server | Ghi chú |
|---|---|---|
| `config.yaml` | `~/.hermes-dcgr/config.yaml` | phần quan trọng: `gateway.multiplex_profiles: true`, 8 `gateway.profile_routes` (thread_id lấy từ `state/topics.dcgr.json`), `gateway.platforms.telegram.channel_overrides["-1003763882779"].system_prompt` thay cho chat_hint; `auxiliary.title_generation.enabled: false`; `model.default: DS-v4Flash` |
| `hermes-approve@dcgr.override.conf` | `~/.config/systemd/user/hermes-approve@dcgr.service.d/override.conf` | bật `CT_CHAT_QUA_GATEWAY=1` chỉ cho instance dcgr; unit template `hermes-approve@.service` dùng chung, blog không có cờ |
| `profile.env.mau` | `~/.hermes-dcgr/profiles/<vai>/.env` × 8 | chỉ `OPENAI_API_KEY` + `TELEGRAM_ALLOWED_USERS`, **không** token bot |
| (không chụp) | `~/.hermes-dcgr/.env` | `TELEGRAM_BOT_TOKEN` của @hermesdcgr_bot, `TELEGRAM_ALLOWED_USERS`, `OPENAI_API_KEY`, `TELEGRAM_HOME_CHANNEL` |

## Tái tạo từ đầu

1. Chép `config.yaml` sang `~/.hermes-dcgr/config.yaml` (backup bản cũ trước).
2. Tạo 8 `.env` profile theo `profile.env.mau` (hoặc `backfill_profile_envs()` của
   Hermes rồi **xoá** dòng `TELEGRAM_BOT_TOKEN`/`TELEGRAM_HOME_CHANNEL` trong từng tệp).
3. `systemctl --user restart hermes-gateway@dcgr`; kiểm `~/.hermes-dcgr/logs/gateway.log`
   (INFO không vào journal): "Connected to Telegram", "Cron scheduler will tick 9
   profile(s) under multiplex", không có "same credential" / `UnscopedSecretError`.
4. Chép `hermes-approve@dcgr.override.conf` vào drop-in, `daemon-reload`, restart
   `hermes-approve@dcgr`; journal approve phải ghi `chat -> nhuong gateway`.
5. Nhắn thử một topic: chỉ @hermesdcgr_bot trả lời chat; chọn số/Duyệt vẫn qua
   @hermesmodebot (approve).

## Quay về chat_router (bỏ thí điểm)

Xoá drop-in + `daemon-reload` + restart approve dcgr là chat quay về approve ngay; gateway
có thể giữ nguyên (chỉ trả lời đôi nếu còn poll), muốn tắt hẳn thì đặt
`multiplex_profiles: false` và bỏ `profile_routes`.
