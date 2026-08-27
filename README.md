# content-team

Dây chuyền nội dung tự động cho kênh Telegram AI, chạy trên hermes-agent.

## Đội hình

| Vai | Profile hermes | Việc |
|---|---|---|
| Finn | `scout` | Quét HN/Reddit/arXiv, chấm điểm, gửi danh sách đánh số |
| Chad | `designer` | Dựng ảnh cho **donniechublog** — kiểu tràn, không khung |
| Ethan | `ethan` | Dựng ảnh cho **dcgr.tech** — cùng kiểu, khác đúng một cờ `--brand` |
| Heller | `heller` | Dựng **carousel nhiều slide** cho **donniechublog** — ảnh trên, chữ dưới, kiểu bảng tin, ra album |
| Dre | `dre` | Dựng **carousel nhiều slide** cho **dcgr.tech** — cùng kiểu Heller, khác đúng một cờ `--brand` |
| Quinn | `writer` | Viết caption tiếng Việt cho **donniechublog**, đẩy vào hàng duyệt |
| Miles | `miles` | Viết caption tiếng Việt cho **dcgr.tech**, cùng khuôn Quinn nhưng người đọc là dân kinh doanh, tài chính, truyền thông |
| Nova | `nova` | Quét bảng xếp hạng model mới, báo cái đáng chú ý |
| Vera | `market` | Quét tin kinh doanh/đầu tư quanh AI (Google News + feed báo) |
| Ada | `analyst` | Đo phản hồi, đối chiếu điểm chấm với lựa chọn thực tế |
| Jean | `teaser` | Ghép teaser từ bài đã duyệt |

## Luồng

```
cron 07:00 VN → task kanban cho Finn → Finn quét, ghi manifest, gửi báo cáo
                                              ↓
        Ông Chủ trả lời số thứ tự trong topic Finn
                                              ↓
     approve_service tạo cặp task vai ảnh → vai viết (vai viết chờ ảnh xong)
                                              ↓
        Bản nháp + thẻ ảnh vào topic Quinn kèm nút ✅ / ❌
                                              ↓
                     ✅ → đăng lên channel      ❌ → đánh dấu bỏ
                              ↓
                  đẩy sang moat → extension đăng lên
                  Facebook / Instagram / TikTok
```

Bài đã duyệt đi tiếp sang moat (org `dcgr.tech`) làm hàng đợi publish; extension
trình duyệt claim và đăng lên mạng xã hội. Moat không gọi ngược về máy này —
cron `moat-publish-watch` (1 phút/lần) hỏi trạng thái rồi báo vào topic Quinn.
Moat hỏng không làm hỏng khâu duyệt: bài vẫn lên Telegram channel, thẻ duyệt chỉ
ghi thêm một dòng cảnh báo.

## Tệp

- `card.py` — dựng ảnh. Kiểu `tran` (cả hai vai ảnh đang dùng): ảnh full bề ngang,
  không khung, chữ đè lên qua màn tối. Kiểu `dai` còn trong mã nhưng hiện không
  vai nào dùng
- `arxiv_bia.py` — bài arxiv không có ảnh minh hoạ thì chụp trang đầu paper (tên
  công trình + tác giả) làm ảnh, thay vì bó tay. Cần `pymupdf`
- `carousel.py` — dựng **carousel nhiều slide** (Heller cho donniechublog, Dre
  cho dcgr.tech — chung script, khác cờ `--brand`): ảnh full bề ngang ở trên
  (ảnh 1:1 hoặc 4:5 — xem skill), chữ ở đáy trên **nền là chính ảnh làm mờ +
  tối dần ở ~30% dưới** (dòng đầu gần trong suốt, hoà vào ảnh; càng xuống càng
  đậm; không ranh giới cứng, không mảng đen đặc), watermark thẳng đáy tự tô màu
  hãng được nhắc tới trong bài. Nhận spec JSON, ra `<id>.png` + `<id>_2.png`…
  đúng khuôn album của `draft_write.py`. Tái dùng helper của `card.py` (nạp
  font, wrap chữ, fit ảnh, cổng chặn tiếng Việt, nhận diện + màu thương hiệu)
- `crop_ti_le.py` — cắt một ảnh về **1:1 hoặc 4:5** trước khi đưa vào carousel
  (luật: ảnh carousel phải đúng một trong hai tỉ lệ đó). Cắt center, hoặc
  `--cx/--cy` để ôm chủ thể. Là chọn khung ảnh thật, không phải bịa ảnh
- `hermes/skills/hero-image/` — skill dùng chung của Chad và Ethan. Nằm thẳng
  trong git, profile trỏ vào qua `skills.external_dirs` nên `hermes update`
  không xoá được
- `hermes/skills/carousel/` — skill dùng chung của Heller và Dre: khung kể
  chuyện qua các slide, cách viết copy từng slide, luật chọn ảnh, lệnh dựng.
  Cùng cơ chế trỏ vào như
  hero-image
- `publish.py` — gửi text/ảnh lên Telegram, hỗ trợ topic
- `approve_service.py` — dịch vụ nền: nghe nút duyệt và lệnh chọn số
- `moat_publish.py` — đẩy bài đã duyệt sang moat (`push <draft_id>`) và hỏi trạng thái
  đăng social (chạy không tham số); khoá ở `.secrets.env` (`MOAT_BASE_URL`, `MOAT_PUBLISH_KEY`)
- `model_audition.py` — thử model: tiếng Việt đủ dấu, gọi tool thật, có prompt caching không
- `model_watch.py` — dò sức khoẻ model đang dùng, báo Telegram khi trạng thái đổi
- `usage_audit.py` — soi usage thật từ 9router: bắt fallback âm thầm và model tụt cache
- `cost_squeeze.py` — chạy lặp trên việc thật, tìm model rẻ nhất mà vẫn ổn định
- `assets/` — font (JetBrains Mono, Inter, Oswald), icon SVG, mascot
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
`model_watch.py`): 8 vai thường — chính `ds/deepseek-v4-flash`, dự phòng
`v4flash@api.b.ai → ds/deepseek-chat`. Riêng Ada — chính `ds/deepseek-reasoner`
(**bật** suy luận, vai duy nhất), dự phòng `v4-pro → deepseek-chat`. Bảng dưới
là KẾT QUẢ ĐO chọn model, không phải cấu hình:

| Vai | Model đo được là hợp nhất | Suy luận |
|---|---|---|
| Finn / Chad / Ethan / Heller | `ds/deepseek-v4-flash` | tắt |
| Quinn / Miles / Jean | `ds/deepseek-chat` | tắt |
| Ada | `ds/deepseek-reasoner` | **bật** |

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
**thực chạy**. Đã bắt được một lần Quinn lặng lẽ tụt xuống `ds/deepseek-v4-pro`
mà tệp usage vẫn khai là đang chạy provider mới — chỉ lộ ra khi đối chiếu với log
9router.

Token burn đo được cho một luồng trọn vẹn (Finn quét → vai ảnh dựng → vai viết,
17 lượt gọi): **~398.000 token chạm model**, cache 36%, 227 giây, ước $0,038.

## Suy luận (reasoning)

Mọi vai trừ Ada đặt `agent.reasoning_effort: none` (8/9 profile).

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
