# content-team

Dây chuyền nội dung tự động cho kênh Telegram AI, chạy trên hermes-agent.

Tệp này chỉ mô tả **hiện trạng**. Chi tiết nằm ở tài liệu riêng:

| Cần gì | Đọc |
|---|---|
| Sơ đồ kiến trúc (C4/Mermaid) | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Sự cố, số đo, bài học | [INCIDENT_LOG.md](INCIDENT_LOG.md) |
| Luật ảnh từng vai | [IMAGE_RULES_ETHAN.md](IMAGE_RULES_ETHAN.md) · [IMAGE_RULES_DRE.md](IMAGE_RULES_DRE.md) · [IMAGE_RULES_KITE.md](IMAGE_RULES_KITE.md) |
| Spec chữ trên thẻ | [STYLE_TEXT_SPEC.md](STYLE_TEXT_SPEC.md) |
| Khuôn ticket Linear | [TICKET_TEMPLATE.md](TICKET_TEMPLATE.md) |
| Quy tắc worktree, push, đặt tên | [CLAUDE.md](CLAUDE.md) |

Nguồn sự thật của cấu hình là máy chủ, không phải tệp này:

```bash
grep -h "^  model:" ~/.hermes-*/profiles/*/config.yaml | sort | uniq -c
```

## Đội hình

Hai brand là hai container riêng (`~/.hermes-blog`, `~/.hermes-dcgr`). Profile chỉ
có **Tên** và **role**. Brand đi theo sidecar của bài (`drafts/<id>.*.json`), vai
không truyền cờ `--brand`; cùng một script phục vụ cả hai.

Mỗi brand có **hai người viết** (Miles, Jika) chia việc theo hàng chờ: lúc chọn tin,
`role.writer_for` ghi người viết tạm; lúc Ông Chủ duyệt ảnh, `approve_post` giao
cho người đang ít việc hơn. Vai **ảnh** do Ông Chủ chọn theo từng tin.

| Tên | Profile hermes | Role | Việc |
|---|---|---|---|
| Finn | `finn` | scout | Quét HN/Reddit/arXiv, chấm điểm, gửi danh sách đánh số — **chỉ donniechublog** |
| Qinn | `qinn` | scout.x | Đọc tin kỹ thuật trên X, 2 lượt/ngày (06:00, 18:00 VN) — **chỉ donniechublog**, tin đi sang Jika |
| Nova | `nova` | model | Quét 22 bảng xếp hạng model — **chỉ dcgr.tech** |
| Vera | `vera` | market | Quét tin kinh doanh/đầu tư quanh AI |
| Ethan | `ethan` | designer | Ảnh hero, mặc định thẻ **quote**; `--kieu full_bleed` cho ảnh phủ kín |
| Dre | `dre` | carousel | Carousel nhiều slide, ảnh thật, chữ chìm vào ảnh |
| Kite | `kite` | carousel.edu | Carousel EDU bằng **art vector gốc** (paper/nghiên cứu), tối thiểu 6 slide |
| Hiro | `hiro` | carousel.digest | Gom cả danh sách một researcher vừa nộp thành MỘT carousel bản tin vắn (mỗi headline một slide: ảnh + tiêu đề + tóm tắt). Gọi bằng reply `Hiro`, `Hiro 1-10` hoặc `Hiro /3,5` (bỏ tin 3 và 5) vào báo cáo; tối đa 10 slide |
| Gin | `gin` | clean | Thay chữ Anh bằng chữ Việt trên thẻ/dải nền phẳng |
| Itachi | `itachi` | carousel.rep | Thay chữ ở mọi chỗ trên ảnh (OCR + LaMa), hoặc dựng lại kiểu editorial-deck |
| Miles | `miles` | writer | Viết caption tiếng Việt, chia việc với Jika |
| Jika | `jika` | writer | Viết caption tiếng Việt, giọng khác Miles |
| Ada | `ada` | analyst | Đo phản hồi, đối chiếu điểm chấm với lựa chọn thực tế |
| Cape | `cape` | teaser | Ghép teaser từ bài đã duyệt — blog only |
| Bob | `bob` | — | Đóng khung một ảnh từ URL, gắn mascot hợp tâm trạng |

## Luồng

```
cron 06:00 VN → task cho vai quét → quét, ghi manifest, gửi báo cáo
                        ↓
        Ông Chủ trả lời số thứ tự trong topic của vai quét
                        ↓
   approve_service tạo cặp task: vai ảnh → vai viết (viết chờ ảnh xong)
                        ↓
      Bản nháp + thẻ ảnh vào topic Miles/Jika kèm nút ✅ / ❌
                        ↓
   ✅ → đăng lên channel + đẩy sang moat      ❌ → đánh dấu bỏ
```

**Phần của ta dừng ở moat.** `moat_publish.py` đẩy bài sang moat (`facebook_post`,
`instagram_carousel`), cron `moat-publish-watch` hỏi trạng thái mỗi 5 phút. Moat
hỏng không làm hỏng khâu duyệt. Từ moat trở đi là hệ thống của người khác.

## Kiến trúc 3 lớp

Mỗi vai theo một khuôn: **CHUẨN BỊ (script) → VIẾT (LLM, một tệp) → NỘP (script)**.

- `image_prepare.py` — engine ảnh dùng chung, chạy nền ngay khi Ông Chủ chọn số.
  Tìm ảnh (bài gốc, báo khác, Commons, ảnh thương hiệu, ảnh khái niệm), bỏ trùng,
  phân loại, cắt 1:1 / 4:5, ghi `state/<brand>/prepare/<id>/manifest.json`.
- Mỗi vai một cặp `<vai>_prepare.py` / `<vai>_submit.py` đọc chung manifest; nộp chạy
  cổng chặn của renderer, gửi kèm nút duyệt, ghi `drafts/<id>.handoff.md`.
- Vai quét dùng `scan_prepare.py` + `scan_submit.py`. Một lần quét = một báo cáo.
- Vai theo chat (`gin_*`, `itachi_*`, `cape_*`, `ada_*`, `bob_submit.py`) cùng mẫu.

**Thêm vai mới:** một dòng `Vai(...)` trong `role.py` (các bảng khác tự dẫn xuất),
một cặp `<vai>_prepare/submit.py`, một SOUL trong `hermes/profiles/`, một topic trong
`state/topics.<brand>.json`, rồi `sync_hermes.py --ra-hermes`. `tests/test_role.py`
giữ các bảng khớp nhau.

## Tệp chính

**Dựng ảnh**: `card.py` (thẻ đơn), `carousel.py` (Dre), `deck.py` và
`swap_image_text.py` (Itachi), `about_text.py` (vẽ chữ Việt, dùng chung Gin/Itachi),
`crop_ratio.py`, `capture_chart.py`, `ranking.py`, `arxiv_figures.py`,
`image_brand.py`, `image_concept.py`.

`render_edu.py` là renderer của Kite: HTML/CSS/SVG chụp bằng Chromium, spec JSON có
**7 kind**: `cover`, `statement`, `steps`, `loop`, `figure`, `bars`, `cta`.

**Tìm tin**: `scan_sources.py`, `article_sources.py`, `scan_models.py` (bảng đăng ký
ở `model_boards.py`), `manifest_write.py` / `manifest_build.py` /
`manifest_common.py`, `required.py`, `material.py`.

**Duyệt và đăng**: `approve_service.py` (mặt tiền; thân ở `approve_*.py`),
`chat_router.py`, `draft_write.py`, `publish.py`, `moat_publish.py`,
`blackboard.py`, `write_log.py`, `env_load.py`.

**Đo đạc**: `monitor_9router.py`, `journal.py` + `journal_web.py` (cổng 9130),
`model_watch.py`, `model_audition.py`, `cost_squeeze.py`.

**Khác**
- `assets/` — font và model YuNet, nguồn/giấy phép ở `assets/README.md`.
- `hermes/skills/` — skill dùng chung; `hermes/profiles/` — SOUL/MEMORY, đồng bộ bằng `sync_hermes.py`.
- `setup.sh` — dựng máy mới (chạy lại được), kết thúc bằng `check_env.py`.
- `requirements.txt` / `requirements.lock` — lock làm mới bằng `lock_requirements.py`.
- `tests/` — chạy `tests/run.sh` (offline).

## Dịch vụ systemd

User unit (`systemctl --user`), mỗi brand một instance:

- `hermes-gateway@<brand>` — gateway hermes, chứa dispatcher kanban.
- `hermes-approve@<brand>` — dịch vụ duyệt bài.
- `hermes-dashboard-blog` (cổng 9120), `hermes-dashboard-dcgr` (9121) — bind 127.0.0.1.
- `journal-web` — cổng 9130.

## Cron

Mỗi brand một tệp `~/.hermes-<brand>/cron/jobs.json`. Tệp `hermes/cron/jobs.*.json`
trong repo chỉ là **bản chụp**, sửa nó không tạo được job.

| Job | Lịch | Việc |
|---|---|---|
| `finn-daily-scan` / `nova-daily-scan` / `vera-daily-scan` | 06:00 VN | Quét tin; cùng gọi `hermes/scripts/daily_scan.sh <vai>` |
| `daily-log` | 06:00 VN | Nhật ký ngày + chốt nhật ký 9router → topic `ada` |
| `audit-cron` | 07:00 (blog) / 07:10 (dcgr) | Soát job hỏng của cả hai home |
| `model-watch` | `*/30` trừ 08–10h và 13–16h VN | Dò sức khoẻ model |
| `moat-publish-watch` | 5 phút | Hỏi moat bài đã lên social chưa |
| `skill-lesson-filter` | mỗi giờ | Chấm bài học skill vai tự ghi |

## State

Quy ước: `state/<brand>/` cho thứ của một brand; `state/` gốc chỉ cho thứ chung cả
máy (nhật ký 9router, khoá). Tên tệp/thư mục chỉ lấy từ `state_paths.py`.

Tệp nhiều tiến trình cùng ghi (`meta.json`, `drafts/<id>.json`, sidecar `duyet_*`)
phải ghi qua `env_load.ghi_json` (tmp + `os.replace`), không `write_text` thẳng.

| Tệp | Tạo | Sửa | Đọc |
|---|---|---|---|
| `drafts/<id>.meta.json` | `approve_pick` | `image_prepare`, `blackboard` | vai ảnh, vai viết, Ada |
| `drafts/<id>.img.json` | `approve_pick` | `approve_post` | `approve_post`, Ada |
| `drafts/<id>.writer.json` | `approve_pick` | `approve_post` | `approve_post`, Ada |
| `drafts/<id>.json` | `draft_write` | `approve_post`, `moat_publish` | `approve_post`, `publish` |
| `state/<brand>/prepare/<id>/manifest.json` | `image_prepare` | — | mọi `*_prepare`, `*_submit` |
| `state/<brand>/used_images.jsonl` | `submit_common.send_album` | `approve_post` | `check_not_reused` |
| `state/cron_audit.json` | `audit_cron` | `audit_cron` (brand kia) | `audit_cron` |

## Sau mỗi `hermes update`

`content-team` đọc vài thứ bên trong hermes mà không có API bảo đảm. Chạy ngay:

```bash
venv/bin/python check_hermes.py
venv/bin/pip install -r requirements.txt
venv/bin/python sync_hermes.py --kiem-upstream
```

## Model

Cả 20 profile chạy chính bằng combo `DS-v4Flash` của 9router. `agent.reasoning_effort`
là `none` cho mọi vai nội dung (tắt suy luận để tránh trả về rỗng); Bob đặt `medium`,
Ada dùng mặc định. Đừng tin bảng model chép trong tài liệu, hãy hỏi máy chủ.

Hai nguyên tắc khi dùng nhiều model:

1. **Phải có giám sát.** Hermes fallback im lặng: dùng `model_watch.py` (model còn
   sống không) và `monitor_9router.py` (model nào thật sự được gọi).
2. **Ghim mỗi hội thoại vào một model**, chỉ chuyển tầng ở ranh giới task. Cache là
   per-model; cột `cache%` trong nhật ký ngày tụt nghĩa là đang lật model.

## Lưu ý

`.secrets.env` chứa bot token Telegram và khoá moat — **không bao giờ commit**.
Mỗi bot token chỉ một tiến trình được long-poll; `approve_service.py` giữ vai trò đó.
