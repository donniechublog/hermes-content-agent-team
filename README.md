# content-team

Dây chuyền nội dung tự động cho kênh Telegram AI, chạy trên hermes-agent.

## Đội hình

Mỗi profile giờ chỉ có **Tên** và **role** (dạng `Tên - role`) — **không còn hậu tố
org** `.blog`/`.dcgr` vì mỗi brand đã tách thành container riêng, trong một container
chỉ có một vai mỗi loại. Các role: `scout`, `designer`, `carousel` (bảng-tin ảnh thật),
`carousel.rep` (remake nguồn có sẵn), `carousel.edu` (kiến thức & nghiên cứu, tech × magazine),
`writer`, `teaser`, `market`, `model`, `analyst`, `clean`. Slug `Profile hermes` là
định danh thật (lệnh, assignee, topic map) — không đổi; nhãn chỉ là chữ nhìn thấy.
Bảng dưới gộp cả hai brand container để tiện đối chiếu; cột **Việc** ghi rõ brand.

| Tên | Profile hermes | Role | Việc |
|---|---|---|---|
| Finn | `scout` | scout | Quét HN/Reddit/arXiv, chấm điểm, gửi danh sách đánh số — **chỉ donniechublog** (dcgr chỉ có Vera) |
| Ethan | `designer` | designer | Dựng ảnh cho **donniechublog** — kiểu tràn, không khung |
| Ethan | `designer` | designer | Dựng ảnh cho **dcgr.tech** — cùng kiểu, khác đúng một cờ `--brand` |
| Dre | `carousel` | carousel | Dựng **carousel nhiều slide** cho **donniechublog** — ảnh trên, chữ dưới, kiểu bảng tin, ra album |
| Dre | `carousel` | carousel | Dựng **carousel nhiều slide** cho **dcgr.tech** — cùng kiểu Dre, khác đúng một cờ `--brand` |
| Gin | `gin` | clean | Xoá chữ tiếng Anh trên ảnh nền (OCR+LaMa, `doi_chu_anh.py`), trả nền sạch cho Itachi. Chạy **trên server** (torch+cpu đã cài từ 28/08/2026) như cả đội |
| Itachi | `itachi` | carousel.rep | Dựng lại carousel kiểu **editorial-deck** (`deck.py`) từ nền sạch của Gin — remake carousel nguồn sang tiếng Việt |
| Kite | `kite` | carousel.edu | Dựng carousel **EDU** (kiến thức & nghiên cứu, tech × magazine) cho **donniechublog** bằng **art vector gốc** — diễn đạt lại paper/nghiên cứu (paper trắng, không ảnh) cho tường minh. Tối thiểu 6 slide. Ngoại lệ có chủ đích với luật không-tự-vẽ (chỉ art trừu tượng, cấm ảnh/logo/số liệu giả). Generator = `render_edu.py` — đã chạy live trên server |
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
  brand text góc dưới-trái. Màu: **net khung + brand xanh Apple cố định**, **dấu " theo
  hãng nhắc trong chủ đề**. Kiểu `dai` còn trong mã nhưng hiện không vai nào dùng
- `arxiv_bia.py` — bài arxiv không có ảnh minh hoạ thì chụp trang đầu paper (tên
  công trình + tác giả) làm ảnh, thay vì bó tay. Cần `pymupdf`
- `carousel.py` — dựng **carousel nhiều slide** (Dre cho donniechublog, Dre
  cho dcgr.tech — chung script, khác cờ `--brand`): ảnh phủ kín thẻ
  (ảnh 1:1 hoặc 4:5 — xem skill), chữ ở đáy **chìm vào ảnh qua scrim liền mạch
  kiểu bìa** (màn tối bắt đầu từ ~42% chiều cao, đậm dần xuống ~80% ở vùng chữ;
  không đường mép, không mảng đen đặc — kể cả trên ảnh sáng), brand text (tên kênh)
  ở **góc dưới-trái** một màu xanh Apple/Finder (`#0A84FF`) font San Francisco (SFNS). Nhận spec JSON,
  ra `<id>.png` + `<id>_2.png`… đúng khuôn album của `draft_write.py`. Tái dùng
  helper của `card.py` (nạp font, wrap chữ, fit ảnh, cổng chặn tiếng Việt). Slide
  thân có thể là đoạn văn (`text`) hoặc một câu trích dẫn pull-quote (`quote` +
  `attrib`) — tùy slide
- Nhận diện chart nằm ở `card.la_chart()` (thuần PIL: độ phẳng hàng + số màu
  riêng biệt sau lượng hoá 5 bit). `card.py` và `carousel.py` dùng chung nó để
  **ép ảnh chart vào đúng đường** — `"chart": true` ở slide thân, ghép dọc ở
  bìa/hero — thay vì để vai đối xử với chart như ảnh thường rồi crop mất trục
- **Kiến trúc 3 lớp cho mọi vai (04/09/2026): CHUẨN BỊ (script, chạy nền) →
  VIẾT (LLM, một tệp) → NỘP (script).** Đo trước khi đổi: Dre 51–60 tool
  call/task, Ethan 19–43, Kite 32, Miles 14–24, Finn/Nova/Vera 14–22, phần lớn
  là việc cơ học (curl tải ảnh, ls/grep dò file, cat JSON, tự đếm ký tự, chạy
  cổng chặn nhiều vòng, web_search lại tin vì link Google News đọc ra rỗng).
  Giờ mỗi task là **3 lệnh**, kỳ vọng ~4 tool call.
  - `anh_chuan_bi.py` — **engine dùng chung** cho mọi vai làm ảnh/chữ từ một tin,
    `approve_service.create_pair` khởi chạy nền (`--im`) ngay lúc Ông Chủ chọn:
    giải mã link Google News, tiêu đề tiếng Anh, Bing News RSS tìm báo khác, một
    phiên chromium (chữ bài, img lớn, chụp table/figure/canvas), `anh_bai`,
    Wikimedia Commons khi < 5 ảnh; dHash bỏ trùng; phân loại chart (luật bổ sung
    nền trắng ≥45% & cạnh ≥8%, đo trên ảnh thật), mặt người, tỉ lệ; cắt sẵn
    1:1/4:5 qua `crop_ti_le`; cặp ghép cùng tone; tư liệu (lọc câu liên quan).
    Kết quả `state/<brand>/chuan_bi/<id>/xong.json` + `bang_anh.png`.
  - Mỗi vai một cặp **brief + nop** đọc chung `xong.json`: `dre_chuan_bi/dre_nop`
    (carousel), `ethan_chuan_bi/ethan_nop` (hero `card.py`, `anh2` ghép dọc,
    `nhan_vat`), `kite_chuan_bi/kite_nop` (`render_edu.py`, hình thật cho
    `figure`, theme/hero không trùng), `miles_chuan_bi/miles_nop` (caption: chuẩn
    hoá em-dash, đếm, `caption_check`, `draft_write`, push). Nop chặn sớm lỗi hay
    mắc, chạy cổng chặn của renderer, gửi kèm nút duyệt, ghi `drafts/<id>.ban_giao.md`
    (approve_service dán vào task Miles khi bấm Duyệt), `da_dung.json` để "Làm
    lại" bắt buộc đổi ảnh/hook/tone. `--khong-gui`/`--out`/`--khong-push` để thử.
  - Bốn vai theo chat cùng mẫu, khoá là message_id/URL: `gin_chuan_bi/gin_nop`
    (OCR đánh số vùng, đo màu; LaMa xoá trừ vùng `giu`; `vung.json` cho Itachi),
    `itachi_chuan_bi/itachi_nop` (tự làm phần Gin nếu chưa; chữ Anh từng vùng
    in sẵn; vẽ tại chỗ đúng box/màu/cỡ hoặc `deck.py`; retouch/blend chờ GPU,
    xem dưới), `jean_chuan_bi/jean_nop` (bóc bài, ráp teaser, gửi topic; `--draft`
    cho task sau này), `ada_chuan_bi/ada_nop` (số liệu N ngày: chọn theo bậc điểm/
    nguồn/category, draft, kanban, token theo vai, chi phí 9router → nhận xét có
    bằng chứng → báo cáo topic analyst). `tao_nen_ai.py` (skill ai-background) và
    bộ skill retouch/blend của Gin/Itachi **chờ GPU** (sửa/sinh ảnh bằng CPU quá
    nặng): không phải lỗi, hoàn thiện đợt tới. Tới lúc đó hai vai chỉ xoá chữ +
    vẽ tại chỗ/deck.
  - `quet_chuan_bi.py --vai scout|nova|market` + `quet_nop.py`: ba vai đi tìm tin
    nhận danh sách ứng viên **một dòng mỗi tin** + mục BẮT BUỘC + khung tệp nộp;
    nop ghép manifest (`manifest_build`/`manifest_ghi`), kiểm bắt buộc, viết báo
    cáo, gửi topic; `--khong-co` gửi dòng "hôm nay không có gì"; `--thu` không
    ghi manifest thật, không xoá bắt buộc.
- `chup_chart.py` — chụp **chart / bảng benchmark** đúng luật *full chiều rộng
  trước, chiều cao xét sau* (Ông Chủ chốt 04/09/2026). Mở trang ở khung 1920px,
  đo bề ngang **thật** của phần tử (`scrollWidth`), **nới khung** cho vừa rồi mới
  chụp ở DPR 2; chụp xong đo lại ảnh ra, thiếu bề ngang thì dừng chứ không giao
  ảnh mất nửa phải. Link ảnh trực tiếp thì tải nguyên bản. Cần `playwright` +
  chromium
- **`LUAT_ANH.md` — tài liệu chuẩn về LUẬT ẢNH, dùng chung cho mọi vai TẠO ra
  ảnh** (Ethan/`card.py`, Dre/`carousel.py`, Kite/`render_edu.py`). Một nguồn sự
  thật duy nhất: không tự vẽ, tìm ảnh thật, chụp chart full chiều rộng, chart
  nguyên vẹn, tỉ lệ và crop, dấu xuất xứ, ghép dọc, mặt người, không hai vùng.
  Code là `luat_anh.py`. **Đừng chép luật đó vào SKILL của vai** — chép là trôi
  khác nhau. Gin/Itachi không tạo ảnh (chỉ sửa trên ảnh gốc) nên không áp bộ này
- `crop_ti_le.py` — cắt một ảnh về **1:1 hoặc 4:5** trước khi đưa vào carousel
  (luật: ảnh carousel phải đúng một trong hai tỉ lệ đó). Cắt center, hoặc
  `--cx/--cy` để ôm chủ thể. Là chọn khung ảnh thật, không phải bịa ảnh.
  **Chỉ cắt chiều cao**: ảnh gốc ngang (≥1.4) mà đòi cắt bề ngang thì script
  dừng — bề ngang của chart/bảng là nội dung. Ép cắt bằng `--cat-ngang`, chỉ cho
  ảnh chụp người/sản phẩm không có chữ
- `render_edu.py` — renderer của **Kite** (role `carousel.edu`): dựng carousel
  **tech-editorial art vector gốc** (masthead, folio, hero orbit) bằng HTML/CSS/SVG,
  chụp bằng **Chromium headless (Playwright)** ra `<id>.png` + `<id>_2.png`… đúng
  khuôn album. Nhận spec JSON (5 kind: cover/statement/steps/loop/cta), font nhúng
  base64 từ `assets/fonts`, cổng chặn tiếng Việt tái dùng `card.tim_mat_dau`.
  **Không ảnh thật** — khác hẳn `carousel.py`/`deck.py`. Cần `playwright install
  chromium` trên server (xem skill `carousel-edu`). Đã test local, **đã chạy live trên server**
- `hermes/skills/hero-image/` — skill dùng chung của vai designer (Ethan, hai brand). Nằm thẳng
  trong git, profile trỏ vào qua `skills.external_dirs` nên `hermes update`
  không xoá được
- `hermes/skills/carousel/` — skill dùng chung của vai carousel (Dre, hai brand): khung kể
  chuyện qua các slide, cách viết copy từng slide, luật chọn ảnh, lệnh dựng.
  Cùng cơ chế trỏ vào như
  hero-image
- `hermes/skills/carousel-edu/` — skill của **Kite** (role `carousel.edu`):
  carousel tech-editorial bằng **art vector gốc** (không ảnh thật). Chứa hệ thiết
  kế (màu, font, khung magazine, hero motif), ranh giới ngoại lệ với luật
  không-tự-vẽ, `reference/` — bộ /boost 5 slide (`.dc.html`) + `boost.spec.json`
  làm nguồn sự thật, và mục **Toolchain** cho `render_edu.py` (lệnh, cài Chromium,
  font). Generator = hướng B (HTML→PNG)
- `publish.py` — gửi text/ảnh lên Telegram, hỗ trợ topic
- `approve_service.py` — dịch vụ nền: nghe nút duyệt và lệnh chọn số
  Từ 03/09/2026: **mọi tin nhắn vào đều có log** (`state/<brand>/approve.log`, xoay
  vòng 5 MB×3, và journal) theo các nhãn `vao → route → chat/chon/lenh → tele`,
  và **mọi nhánh đều kết thúc bằng một tin trả về** (kể cả lỗi, hết giờ). Chat
  chạy qua `_chay_nen` (bọc traceback → ⚠️ về đúng topic), báo tiến độ ở phút 2
  và 6, tự dừng ở phút 10 và trả phần agent đã in được
- `chat_router.py` — định tuyến chat Telegram → hermes CLI theo topic. Ghép
  `CHAT_HINT` (chat thì trả lời ngắn, không tự chạy scan/task) trước mọi tin cho
  mọi vai; hết giờ thì giết cả process group (`start_new_session` + `killpg`)
- `ghi_log.py` — log dùng chung (stdout + tệp theo brand) cho hai tệp trên
- `nguon_bai.py` — research của Finn chạy lúc chọn tin. Từ 04/09/2026 tự **giải
  mã link Google News** (`giai_ma_gnews`, thử tĩnh rồi chromium) — tin của Vera
  luôn mang link chuyển hướng, trước đó `anh_bai`/`tu_lieu` đọc ra rỗng và Dre
  phải web_search lại. `approve_service` dùng link thật cho mọi task sau và ghi
  vào meta. Task body giờ nhận đường dẫn nguồn thật `state/<brand>/nguon_<id>.json`
  (trước trỏ `state/` gốc nên vai nào cũng không thấy bộ nguồn của Finn).
- `manifest_ghi.py` / `manifest_build.py` — ghi manifest đánh số vào
  `state/<brand>/` qua `env_load.state_dir()` — **cùng chỗ approve_service đọc**.
  Trước 03/09 ghi cứng `state/` gốc nên trả lời số trong topic Vera/Nova luôn ra
  "Chưa có danh sách"
- `moat_publish.py` — đẩy bài đã duyệt sang moat (`push <draft_id>`) và hỏi trạng thái
  đăng social (chạy không tham số); khoá ở `.secrets.env` (`MOAT_BASE_URL`, `MOAT_PUBLISH_KEY`)
- `model_audition.py` — thử model: tiếng Việt đủ dấu, gọi tool thật, có prompt caching không
- `scan_models.py` — quét của Nova. Từ 04/09/2026 có mục **"RA MẮT THEO BẢNG CHẤM
  ĐIỂM"** (artificialanalysis, nhóm theo tên gốc, mỗi model báo đúng một lần nhờ
  `aa_da_bao` trong `models_seen.json`) và bảng coding AA được so hạng với lần trước
  (`xep_hang.coding`). Trước đó "mới" chỉ là id mới trên router, một lần duy nhất:
  GPT-6 Astra (03/09, #8 coding) không lên router nên Nova báo "0 model mới"
- `bat_buoc.py` — **danh sách BẮT BUỘC** cho ba vai đi tìm tin (luật Ông Chủ 04/09/2026:
  script quét thấy là phải đưa, hôm trước sót thì hôm sau bổ sung, vai không có quyền bỏ).
  Script quét gieo mục (`state/<brand>/bat_buoc_<vai>.json`), script ghi manifest
  (`manifest_build.py` cho Finn, `manifest_ghi.py` cho Nova/Vera) **từ chối** nếu thiếu và
  xoá mục đã đưa. Tiêu chí: Finn = tiêu đề nhắc hãng frontier hoặc HN/Reddit ≥150 điểm có
  dấu hiệu AI; Nova = mọi model ra mắt / vào bảng / leo hạng ở 12 bảng; Vera = một mục mỗi
  hãng lõi mỗi ngày (hoặc tin ≥2 báo), khớp theo tên hãng
- `model_watch.py` — dò sức khoẻ model đang dùng, báo Telegram khi trạng thái đổi
- `usage_audit.py` — soi usage thật từ 9router: bắt fallback âm thầm và model tụt cache
- `theo_doi_9router.py` — nhật ký 9router **theo ngày** (`state/9router/nhat_ky/9router_<ngày>.md|json`):
  req/prompt/cache%/$ theo model @ kết nối, theo khoá API, theo giờ VN, fallback thật
  v4-flash→deepseek-chat, lỗi, 5 prompt nặng nhất, IP máy gọi. `--canh` là watcher IP
  (9router không lưu IP, xem "Điểm mù thứ ba"). Ada đọc qua `tai(ngày)` để so ngày với ngày
- `cost_squeeze.py` — chạy lặp trên việc thật, tìm model rẻ nhất mà vẫn ổn định
- `assets/` — font (JetBrains Mono, Inter, Be Vietnam Pro, Noto Serif, Oswald…),
  icon SVG, mascot, và `face_detection_yunet_2023mar.onnx` (~230KB, YuNet) cho
  cổng chặn phát hiện mặt người của `carousel.py`
- `requirements.txt` — phụ thuộc Python. venv dùng chung với hermes nên `hermes
  update` có thể làm mất `pymupdf`; cài lại bằng `venv/bin/pip install -r requirements.txt`

## Chạy tuần tự, không song song

Từ 03/09/2026, theo yêu cầu Ông Chủ, các vai **không làm cùng lúc**:

- `kanban.max_in_progress: 1` trong `~/.hermes-<brand>/config.yaml` — dispatcher mỗi
  container chỉ chạy một task tại một thời điểm, FIFO theo `created_at`.
- Lệnh chọn nhiều tin nhiều vai ("1, 3 - Ethan, 2 - Dre") được **sắp theo vai** trước
  khi tạo task, nên vai xuất hiện trước làm hết bài của mình rồi vai sau mới bắt đầu.
- Hàng đợi có tiếng nói: mỗi task bắt đầu / xong / dừng, approve_service đưa một dòng
  vào topic của vai đó kèm số việc còn xếp hàng (`bao_tien_do_kanban`, mỗi vòng poll).
  Ngày 04/09 Ông Chủ chọn 7 bài lúc 05:33, Nova xếp thứ 8, im lặng cả tiếng trông
  như hệ thống đứng — nên có mục này.
- Chat Telegram (đổi 04/09): **không còn một hàng chung cho cả 12 vai** — với khoá
  chung, Gin xoá chữ 2 phút là hỏi Miles/Ethan gì cũng đứng im theo (Itachi đợi Gin
  108 s chỉ để trả lời "xác nhận"). Giờ hai tầng trong `approve_service.py`:
  - mỗi phiên `tele-<vai>` một hàng FIFO (`_HangFIFO`) — cùng vai không chạy hai lượt
    cùng lúc, tin trước trả lời trước, có báo "đang trả lời N tin trước";
  - semaphore chung `CT_CHAT_SONG_SONG` (mặc định **4**) chỉ là van an toàn cho
    9router/DeepSeek, **không** phải thứ làm reply đợi nhau — một người gõ thực tế không
    hỏi quá 3–4 vai cùng lúc; đặt `=1` trong unit systemd là về hành vi cũ.
  - **Nguyên tắc (Ông Chủ, 04/09): task làm lần lượt được, reply phải song song và
    nhanh** — reply đơ là công việc treo theo hết. Task kanban vẫn `max_in_progress: 1`.
- Chat giữ mạch bằng `hermes chat -c tele-<vai> --create-if-missing -Q -q` (`chat_router.py`).
  Trước 04/09 dùng `--continue … -z`: `-z` được xử lý trước và thoát luôn nên `--continue`
  bị bỏ qua im lặng — **mọi** tin của **mọi** vai đều mở phiên trắng, vai nào cũng
  "không nhớ gì" (Ethan 03/09, Itachi 04/09). Dòng `phien=↻ Resumed session …` trong
  `approve.log` là chỗ đối chiếu khi nghi vai mất mạch.

## Dịch vụ systemd

- `hermes-gateway` — gateway hermes, chứa dispatcher kanban
- `hermes-approve` — dịch vụ duyệt bài (tệp này)
- `hermes-dashboard` — bảng điều khiển web, cổng 9119
- `9router-ket-noi` — user unit (`hermes/systemd/9router-ket-noi.service`), watcher IP kết nối
  tới cổng 20128 → `state/9router/ket_noi_<ngày>.jsonl`. Không root, không đọc nội dung

## Cron (7 job, xem `~/.hermes/cron/jobs.json`)

- `finn-daily-scan`, `nova-daily-scan`, `vera-daily-scan` — **05:00 VN** (22:00 UTC, từ 04/09/2026), ba vai đi tìm tin, chạy nối tiếp vì `max_in_progress: 1`
- `usage-audit` — 06:00 VN, soi usage thật, bắt fallback âm thầm
- `nhat-ky-daily` — 06:00 VN, dựng nhật ký ngày hôm trước + chốt nhật ký 9router hôm qua
  (`theo_doi_9router.py --canh-bao`: IP ngoài loopback / fallback thật / lỗi → topic analyst)
- `model-watch` — 30 phút/lần, dò sức khoẻ model
- `moat-publish-watch` — 1 phút/lần, hỏi moat xem bài đã lên social chưa. Im lặng khi
  không có gì mới; hỏi theo `workflow_id` (khoá chính) chứ không phải `external_id`;
  bỏ theo dõi một bài sau 7 ngày và tự xoá file output cron cũ hơn 3 ngày

## Model từng vai

**Chuỗi đang chạy** (nguồn sự thật: `~/.hermes-<brand>/profiles/*/config.yaml`
— mỗi container một home riêng từ khi tách brand, không còn `~/.hermes` gộp
chung). Đo lại 04/09/2026, theo brand:

| Vai | donniechublog | dcgr.tech | Suy luận |
|---|---|---|---|
| Ada (analyst) | `ds/deepseek-reasoner` | `ds/deepseek-reasoner` | **bật** — vai duy nhất, việc đối chiếu điểm chấm cần suy luận thật |
| Bob | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | **medium** |
| Ethan (designer) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Dre (carousel) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Kite (carousel-edu) | `ds/deepseek-v4-flash` | — (chưa deploy) | tắt |
| Gin / Itachi | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Nova / Vera (market) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Finn (scout) | `ds/deepseek-v4-flash` | — (dcgr chỉ có Vera) | tắt |
| Jean (teaser) | `ds/deepseek-v4-flash` | — (blog only) | tắt |
| Miles (writer) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |

Dự phòng của mọi vai (trừ Ada): `v4flash@api.b.ai → ds/deepseek-chat` (xem
mục Provider). Gin chạy việc thật **trên server** (torch+cpu cài từ 28/08/2026,
xem skill `inplace-translate`) — không còn phụ thuộc máy local. Kite ĐÃ DEPLOY
(2026-09-01), generator `render_edu.py` chạy live trên server.

**Đã thử glm-5.3 rồi hạ lại 04/09/2026:** Finn/Jean/Miles bên donniechublog và
Ethan bên dcgr.tech từng chạy chính bằng `xk/z-ai/glm-5.3`, kết quả một đợt A/B
chỉnh trực tiếp trên server ngày 01/09/2026 — không đi qua git nên không có
commit nào ghi lại lý do chọn. Audit 04/09 đo bằng `usage_audit.py`: glm-5.3 tốn
**$0,416 / 20 request** (~$0,0208/req) so với v4-flash **$0,0997 / 204 request**
(~$0,0005/req trong cùng cửa sổ) — đắt hơn khoảng **40 lần mỗi request** mà
không có bảng audition nào chứng minh bù lại được bằng chất lượng, nên cả bốn
vai đã hạ về `ds/deepseek-v4-flash` cùng ngày. Bản config trước khi hạ được giữ
ở `profiles/<vai>/config.yaml.bak-truoc-doi-v4flash-0904` trong từng home,
phòng khi cần so lại hoặc thử lại có kiểm soát hơn.

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

**Đã bắt được một nguyên nhân lật cụ thể (cron 05/09/2026, cả Finn/Nova/Vera):**
bước phụ `title_generation` (Hermes tự đặt tên phiên) gửi `response_format` mà
DeepSeek v4-flash trả `400 This response_format type is unavailable now`; 9router
coi đó là lỗi provider và đưa `deepseek/deepseek-v4-flash` vào cooldown ~30s
(`reset after 28s`); hai lần retry của vòng chính (cách 2–3s) rơi trọn trong
cooldown → `Fallback activated: v4-flash → deepseek-chat`, dính tới hết phiên
(1 call v4-flash rồi 11–24 call deepseek-chat). Dòng log nằm ở
`profiles/<vai>/logs/agent.log`, **không** có trong `logs/gateway.log`. Đếm
19/08–04/09: lỗi này 5–48 lần/ngày, fallback 4–33 lần/ngày. Chặn bằng
`auxiliary.title_generation.enabled: false` trong `config.yaml` từng profile:
`venv/bin/python tat_title_generation.py` (có `--thu`, backup
`.bak-truoc-tat-title-0905`); tiêu đề phiên vô dụng với task kanban/cron.

**Từ 05/09/2026 model chính là combo `DS-v4Flash` của 9router** (`doi_model_combo.py`,
có `--thu`, backup `.bak-truoc-doi-combo-0905`; analyst giữ `ds/deepseek-reasoner`).
9router chỉ xoay giữa các connection *cùng* provider; ba route v4-flash (deepseek trực
tiếp `ds/`, xKiro `dsx/deepseek/deepseek-v4-flash`, aellm `dsa/deepseek-v4-flash`) chỉ
nối được với nhau qua Combo, gọi bằng đúng tên combo làm model (không có prefix
`combo/`). Trước đó cả ba node đều đặt prefix `ds` nên hai node ngoài bị che, 7 ngày
0 request. Đo route thật bằng `usageHistory.provider` của 9router; Hermes chỉ thấy
model `DS-v4Flash`. Combo còn chứa mục chết (`ds/ds/…`, `tokenrouter/…` không có
credential, `oc/…-free` unavailable) và chưa có `dsa/`: dọn trên dashboard.

## Provider

Mọi vai trừ Ada chạy chính bằng `ds/deepseek-v4-flash` trên connection DeepSeek
gốc, dự phòng là `v4flash` của
provider mới (connection `openai-compatible-chat-ba685909…`, baseUrl `api.b.ai`)
rồi `ds/deepseek-chat`. Ada giữ `ds/deepseek-reasoner` vì provider mới không có.

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

**Điểm mù thứ hai: cả hai brand dùng CHUNG một instance 9router cục bộ**
(`http://127.0.0.1:20128/v1` trong cả hai `config.yaml`), và trong log
`usageHistory` cả hai brand hiện ra đúng **một** `apiKey` duy nhất. `usage_audit.py`
có sẵn cờ `--api-key` để tách theo client, nhưng vô dụng ở trạng thái hiện tại vì
chỉ có một khoá — nên báo cáo usage-audit của blog và dcgr luôn ra **cùng một
con số tổng**, không tách được brand nào tốn bao nhiêu. Muốn tách được: cấp thêm
một virtual key trong 9router, gán cho một brand qua `config.yaml`, rồi thêm
`--api-key <khoá đó>` vào cron `usage_audit.sh` của brand đó.

**Điểm mù thứ ba: 9router KHÔNG ghi IP máy gọi.** `usageHistory` không có cột IP,
`meta` luôn `{}`; `custom-server.js` có tính `x-9r-real-ip` nhưng chỉ dùng cho
rate-limit. Trong khi service đang bind `0.0.0.0` (LAN 192.168.1.61 + netbird),
ai trong mạng cũng gọi được bằng khoá chung. Đo 05/09: `theo_doi_9router.py --canh`
đọc bảng TCP mỗi 2s (psutil, mọi trạng thái trừ LISTEN nên curl mở-đóng 1s vẫn để
vết TIME_WAIT), ghi IP theo **kết nối**, không theo request — Hermes dùng httpx
keep-alive nên một kết nối chở nhiều request. Muốn quy request về máy gọi thì vẫn
phải cấp khoá riêng như trên. Nhật ký ngày `9router_<ngày>.md` gộp cả hai nguồn;
cột "đổi model liên tiếp" chỉ tin cặp v4-flash→deepseek-chat là fallback thật,
các cặp khác phần lớn là vai chạy song song (9router không ghi session).

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
