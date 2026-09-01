# content-team

Dây chuyền nội dung tự động cho kênh Telegram AI, chạy trên hermes-agent.

## Đội hình

Mỗi profile giờ chỉ có **Tên** và **role** (dạng `Tên - role`) — **không còn hậu tố
org** `.blog`/`.dcgr` vì mỗi brand đã tách thành container riêng, trong một container
chỉ có một vai mỗi loại. Các role: `scout`, `designer`, `carousel` (bảng-tin ảnh thật),
`carousel.rep` (remake nguồn có sẵn), `carousel.sli` (tech-editorial art vector gốc),
`writer`, `teaser`, `market`, `model`, `analyst`, `clean`. Slug `Profile hermes` là
định danh thật (lệnh, assignee, topic map) — không đổi; nhãn chỉ là chữ nhìn thấy.
Bảng dưới gộp cả hai brand container để tiện đối chiếu; cột **Việc** ghi rõ brand.

| Tên | Profile hermes | Role | Việc |
|---|---|---|---|
| Finn | `scout` | scout | Quét HN/Reddit/arXiv, chấm điểm, gửi danh sách đánh số |
| Ethan | `designer` | designer | Dựng ảnh cho **donniechublog** — kiểu tràn, không khung |
| Ethan | `designer` | designer | Dựng ảnh cho **dcgr.tech** — cùng kiểu, khác đúng một cờ `--brand` |
| Dre | `carousel` | carousel | Dựng **carousel nhiều slide** cho **donniechublog** — ảnh trên, chữ dưới, kiểu bảng tin, ra album |
| Dre | `carousel` | carousel | Dựng **carousel nhiều slide** cho **dcgr.tech** — cùng kiểu Dre, khác đúng một cờ `--brand` |
| Gin | `gin` | clean | Xoá chữ tiếng Anh trên ảnh nền (OCR+LaMa, `doi_chu_anh.py`), trả nền sạch cho Itachi. Chạy **trên server** (torch+cpu đã cài từ 28/08/2026) như cả đội |
| Itachi | `itachi` | carousel.rep | Dựng lại carousel kiểu **editorial-deck** (`deck.py`) từ nền sạch của Gin — remake carousel nguồn sang tiếng Việt |
| Kite | `kite` | carousel.sli | Dựng carousel **tech-editorial (magazine)** cho **donniechublog** bằng **art vector gốc** (masthead, folio, hero quỹ đạo) — không ảnh thật, không nền AI. Ngoại lệ có chủ đích với luật không-tự-vẽ (chỉ art trừu tượng, cấm ảnh/logo/số liệu giả). Generator = `render_sli.py` — đã chạy live trên server |
| Miles | `writer` | writer | Viết caption tiếng Việt cho **donniechublog**, đẩy vào hàng duyệt |
| Miles | `writer` | writer | Viết caption tiếng Việt cho **dcgr.tech**, cùng khuôn Miles nhưng người đọc là dân kinh doanh, tài chính, truyền thông |
| Nova | `nova` | model | Quét bảng xếp hạng model mới, báo cái đáng chú ý |
| Vera | `market` | market | Quét tin kinh doanh/đầu tư quanh AI (Google News + feed báo) |
| Ada | `analyst` | analyst | Đo phản hồi, đối chiếu điểm chấm với lựa chọn thực tế |
| Jean | `teaser` | teaser | Ghép teaser từ bài đã duyệt |

## Luồng

```
cron 07:00 VN → task kanban cho Finn → Finn quét, ghi manifest, gửi báo cáo
                                              ↓
        Ông Chủ trả lời số thứ tự trong topic Finn
                                              ↓
     approve_service tạo cặp task vai ảnh → vai viết (vai viết chờ ảnh xong)
                                              ↓
        Bản nháp + thẻ ảnh vào topic Miles kèm nút ✅ / ❌
                                              ↓
                     ✅ → đăng lên channel      ❌ → đánh dấu bỏ
                              ↓
                  đẩy sang moat → extension đăng lên
                  Facebook / Instagram / TikTok
```

Bài đã duyệt đi tiếp sang moat (org `dcgr.tech`) làm hàng đợi publish; extension
trình duyệt claim và đăng lên mạng xã hội. Moat không gọi ngược về máy này —
cron `moat-publish-watch` (1 phút/lần) hỏi trạng thái rồi báo vào topic Miles.
Moat hỏng không làm hỏng khâu duyệt: bài vẫn lên Telegram channel, thẻ duyệt chỉ
ghi thêm một dòng cảnh báo.

## Tệp

- `card.py` — dựng ảnh. Kiểu `tran` (cả hai vai ảnh đang dùng): ảnh full bề ngang,
  không khung, chữ đè lên qua màn tối. Kiểu `quote`: thẻ trích dẫn pull-quote —
  câu lớn trong **khung 2 góc ngoặc bo tròn**, dòng nguồn `--attrib` canh giữa,
  brand text góc trên. Màu: **net khung + brand xanh Apple cố định**, **dấu " theo
  hãng nhắc trong chủ đề**. Kiểu `dai` còn trong mã nhưng hiện không vai nào dùng
- `arxiv_bia.py` — bài arxiv không có ảnh minh hoạ thì chụp trang đầu paper (tên
  công trình + tác giả) làm ảnh, thay vì bó tay. Cần `pymupdf`
- `carousel.py` — dựng **carousel nhiều slide** (Dre cho donniechublog, Dre
  cho dcgr.tech — chung script, khác cờ `--brand`): ảnh phủ kín thẻ
  (ảnh 1:1 hoặc 4:5 — xem skill), chữ ở đáy **chìm vào ảnh qua scrim liền mạch
  kiểu bìa** (màn tối bắt đầu từ ~42% chiều cao, đậm dần xuống ~80% ở vùng chữ;
  không đường mép, không mảng đen đặc — kể cả trên ảnh sáng), brand text (tên kênh)
  ở **góc trên-trái** một màu xanh Apple/Finder (`#0A84FF`) font San Francisco (SFNS). Nhận spec JSON,
  ra `<id>.png` + `<id>_2.png`… đúng khuôn album của `draft_write.py`. Tái dùng
  helper của `card.py` (nạp font, wrap chữ, fit ảnh, cổng chặn tiếng Việt). Slide
  thân có thể là đoạn văn (`text`) hoặc một câu trích dẫn pull-quote (`quote` +
  `attrib`) — tùy slide
- `crop_ti_le.py` — cắt một ảnh về **1:1 hoặc 4:5** trước khi đưa vào carousel
  (luật: ảnh carousel phải đúng một trong hai tỉ lệ đó). Cắt center, hoặc
  `--cx/--cy` để ôm chủ thể. Là chọn khung ảnh thật, không phải bịa ảnh
- `render_sli.py` — renderer của **Kite** (role `carousel.sli`): dựng carousel
  **tech-editorial art vector gốc** (masthead, folio, hero orbit) bằng HTML/CSS/SVG,
  chụp bằng **Chromium headless (Playwright)** ra `<id>.png` + `<id>_2.png`… đúng
  khuôn album. Nhận spec JSON (5 kind: cover/statement/steps/loop/cta), font nhúng
  base64 từ `assets/fonts`, cổng chặn tiếng Việt tái dùng `card.tim_mat_dau`.
  **Không ảnh thật** — khác hẳn `carousel.py`/`deck.py`. Cần `playwright install
  chromium` trên server (xem skill `carousel-sli`). Đã test local, **đã chạy live trên server**
- `hermes/skills/hero-image/` — skill dùng chung của vai designer (Ethan, hai brand). Nằm thẳng
  trong git, profile trỏ vào qua `skills.external_dirs` nên `hermes update`
  không xoá được
- `hermes/skills/carousel/` — skill dùng chung của vai carousel (Dre, hai brand): khung kể
  chuyện qua các slide, cách viết copy từng slide, luật chọn ảnh, lệnh dựng.
  Cùng cơ chế trỏ vào như
  hero-image
- `hermes/skills/carousel-sli/` — skill của **Kite** (role `carousel.sli`):
  carousel tech-editorial bằng **art vector gốc** (không ảnh thật). Chứa hệ thiết
  kế (màu, font, khung magazine, hero motif), ranh giới ngoại lệ với luật
  không-tự-vẽ, `reference/` — bộ /boost 5 slide (`.dc.html`) + `boost.spec.json`
  làm nguồn sự thật, và mục **Toolchain** cho `render_sli.py` (lệnh, cài Chromium,
  font). Generator = hướng B (HTML→PNG)
- `publish.py` — gửi text/ảnh lên Telegram, hỗ trợ topic
- `approve_service.py` — dịch vụ nền: nghe nút duyệt và lệnh chọn số
- `moat_publish.py` — đẩy bài đã duyệt sang moat (`push <draft_id>`) và hỏi trạng thái
  đăng social (chạy không tham số); khoá ở `.secrets.env` (`MOAT_BASE_URL`, `MOAT_PUBLISH_KEY`)
- `model_audition.py` — thử model: tiếng Việt đủ dấu, gọi tool thật, có prompt caching không
- `model_watch.py` — dò sức khoẻ model đang dùng, báo Telegram khi trạng thái đổi
- `usage_audit.py` — soi usage thật từ 9router: bắt fallback âm thầm và model tụt cache
- `cost_squeeze.py` — chạy lặp trên việc thật, tìm model rẻ nhất mà vẫn ổn định
- `assets/` — font (JetBrains Mono, Inter, Be Vietnam Pro, Noto Serif, Oswald…),
  icon SVG, mascot, và `face_detection_yunet_2023mar.onnx` (~230KB, YuNet) cho
  cổng chặn phát hiện mặt người của `carousel.py`
- `requirements.txt` — phụ thuộc Python. venv dùng chung với hermes nên `hermes
  update` có thể làm mất `pymupdf`; cài lại bằng `venv/bin/pip install -r requirements.txt`

## Dịch vụ systemd

- `hermes-gateway` — gateway hermes, chứa dispatcher kanban
- `hermes-approve` — dịch vụ duyệt bài (tệp này)
- `hermes-dashboard` — bảng điều khiển web, cổng 9119

## Cron (7 job, xem `~/.hermes/cron/jobs.json`)

- `finn-daily-scan`, `nova-daily-scan`, `vera-daily-scan` — 06:00 VN, ba vai đi tìm tin
- `usage-audit` — 06:00 VN, soi usage thật, bắt fallback âm thầm
- `nhat-ky-daily` — 06:00 VN, dựng nhật ký ngày hôm trước
- `model-watch` — 30 phút/lần, dò sức khoẻ model
- `moat-publish-watch` — 1 phút/lần, hỏi moat xem bài đã lên social chưa. Im lặng khi
  không có gì mới; hỏi theo `workflow_id` (khoá chính) chứ không phải `external_id`;
  bỏ theo dõi một bài sau 7 ngày và tự xoá file output cron cũ hơn 3 ngày

## Model từng vai

**Chuỗi đang chạy** (nguồn sự thật: `~/.hermes/profiles/*/config.yaml`, soi bằng
`model_watch.py`): 12 vai thường — chính `ds/deepseek-v4-flash`, dự phòng
`v4flash@api.b.ai → ds/deepseek-chat`. Riêng Ada — chính `ds/deepseek-reasoner`
(**bật** suy luận, vai duy nhất), dự phòng `v4-pro → deepseek-chat`. Bảng dưới
là KẾT QUẢ ĐO chọn model, không phải cấu hình:

| Vai | Model đo được là hợp nhất | Suy luận |
|---|---|---|
| Finn / Ethan / Ethan / Dre | `ds/deepseek-v4-flash` | tắt |
| Miles / Miles / Jean | `ds/deepseek-chat` | tắt |
| Ada | `ds/deepseek-reasoner` | **bật** |

Dre, Gin, Itachi thêm sau, clone từ Dre nên cùng chuỗi `v4-flash` (chưa đo
riêng). Gin chạy việc thật **trên server** (torch+cpu đã cài từ 28/08/2026, xem
skill `inplace-translate`) — không còn phụ thuộc máy local.

Kite ĐÃ DEPLOY (2026-09-01): profile `~/.hermes-blog/profiles/carousel-sli/`
(config clone từ carousel/Dre, chuỗi `v4-flash`, `reasoning_effort: none`), topic
Telegram "Kite · carousel.sli" (thread 52) + `chat_router` wired. Generator
`render_sli.py` **đã chạy live** (Playwright+Chromium cài xong, render
`reference/boost.spec.json` ra 5 slide chuẩn). Còn lại: wire full auto-pipeline
trong `approve_service` (chọn qua "#N carousel-sli" từ list Finn).

Ada là vai duy nhất giữ suy luận: việc của Ada là đối chiếu điểm chấm với tin
được chọn — đúng loại việc cần suy luận thật.

Đo bằng `cost_squeeze.py`, chạy lặp trên việc thật, chấm bằng code:

| Vai | Model | Trượt | USD/1000 lần |
|---|---|---|---|
| teaser | **deepseek-chat** | **0/5** | **0,77** |
| teaser | mimo-v2.5-pro | 1/5 (lan man 2417 từ) | 0,83 |
| teaser | v4-flash | 1/5 (rỗng) | 1,11 |
| teaser | v4-pro | 2/5 (rỗng, mất dấu) | 3,83 |
| writer | deepseek-chat | 0/6 | 0,06 |
| writer | v4-pro | 0/6 | 0,14 |

Gemini đã gỡ khỏi mọi chuỗi: trên số liệu usage thật nó tốn 1,72 USD/1M input
còn v4-flash chỉ 0,04 — **đắt gấp 44 lần**, vì cột cached của gemini trống rỗng,
không cache nổi một token. Kimi K3 đắt gấp 14 lần v4-pro và mọi tuyến Kimi đều
báo `thinkingCanDisable: false` — không tắt suy luận được.

## Hai nguyên tắc bắt buộc khi dùng nhiều model

**1. Bắt buộc phải có giám sát model.** Hermes fallback im lặng hoàn toàn — đặt
model chính thành model chết, agent vẫn trả lời bình thường, không một dòng báo.
Cần cả hai lớp: `model_watch.py` (model còn sống không) và `usage_audit.py`
(model nào **thật sự** được gọi).

**2. Ghim mỗi hội thoại vào một model. Chuyển tầng thì chuyển ở ranh giới task.**
`try_activate_fallback` đổi model ngay giữa lượt, `restore_primary_runtime` lật
về model chính ở lượt sau — một hội thoại có thể chạy qua 2–3 model mà không ai
biết. Cache là per-model, mỗi lần lật là mất sạch prefix đã cache và cả ngữ cảnh
bị tính lại giá gốc. Cột `cache%` trong `usage_audit.py` chính là thước đo
nguyên tắc này: tụt cache nghĩa là đang lật model.

## Provider

Tám vai chạy chính bằng `ds/deepseek-v4-flash` trên connection DeepSeek gốc, dự
phòng là `v4flash` của provider mới (connection `openai-compatible-chat-ba685909…`,
baseUrl `api.b.ai`) rồi `ds/deepseek-chat`. Ada giữ `ds/deepseek-reasoner` vì
provider mới không có.

**Provider mới từng là tuyến chính, đã hạ xuống dự phòng ngày 25/08** khi nó trả
429 hết quota suốt nhiều giờ. Dây chuyền không gãy vì dự phòng gánh được, nhưng
chạy dài ngày ở tuyến dự phòng là mất sạch cache per-model mà không ai đo được
(xem điểm mù bên dưới), nên đảo hẳn thứ tự thay vì để nguyên.

Provider mới **chỉ phục vụ `deepseek-v4-flash`** và bản vision — `deepseek-v4-pro`
trả 403, `deepseek-chat` và `deepseek-reasoner` trả 404.

**Điểm mù cần nhớ: 9router KHÔNG ghi log connection này.** Đo thật: gọi thẳng 5
lượt, số bản ghi trong `usageHistory` đứng yên. Nghĩa là `usage_audit.py` và bảng
usage của 9router không thấy chi phí chạy qua đây. Muốn đo phải dùng
`hermes --usage-file`.

Nhưng `--usage-file` cũng có bẫy: nó ghi model được **cấu hình**, không phải model
**thực chạy**. Đã bắt được một lần Miles lặng lẽ tụt xuống `ds/deepseek-v4-pro`
mà tệp usage vẫn khai là đang chạy provider mới — chỉ lộ ra khi đối chiếu với log
9router.

Token burn đo được cho một luồng trọn vẹn (Finn quét → vai ảnh dựng → vai viết,
17 lượt gọi): **~398.000 token chạm model**, cache 36%, 227 giây, ước $0,038.

## Suy luận (reasoning)

Mọi vai trừ Ada đặt `agent.reasoning_effort: none` (12/13 profile).

Lý do: model deepseek đốt hết ngân sách token vào suy luận rồi trả về **rỗng**.
Đo thật trên v4-pro: 3/24 lần (2/8 ở `max_tokens=800`, 1/8 ở 1200, 0/8 ở 2000).
Tái hiện y hệt trên v4-flash. Lỗi phụ thuộc ngân sách nên im lặng và ngắt quãng —
loại tệ nhất. Tắt suy luận: 0/24 lần rỗng, nhanh gấp 3, rẻ hơn, chữ vẫn đủ dấu.

Đã thử model rẻ hơn cho Jean (`ds/deepseek-chat`, `ds/deepseek-v4-flash`): chữ
vẫn tốt nhưng **lệch giọng** — viết kiểu tường thuật "bài viết nói rằng..." thay
vì giọng mời đọc. Chênh lệch giá chỉ 0,0026 USD/teaser nên không đáng đổi.

Kimi K3 đậu audition nhưng **đắt gấp 14 lần** v4-pro và mọi tuyến Kimi đều báo
`thinkingCanDisable: false` — không tắt suy luận được. Không dùng.

## Lưu ý

`.secrets.env` chứa bot token Telegram và khoá moat — **không bao giờ commit**.
Chỉ một tiến trình được long-poll một bot token; `approve_service.py` giữ vai trò đó.
