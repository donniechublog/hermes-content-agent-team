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
cron `moat-publish-watch` (5 phút/lần) hỏi trạng thái rồi báo vào topic Miles.
Moat hỏng không làm hỏng khâu duyệt: bài vẫn lên Telegram channel, thẻ duyệt chỉ
ghi thêm một dòng cảnh báo.

## Tệp

- `card.py` — dựng ảnh. Kiểu `tran` (cả hai vai ảnh đang dùng): ảnh full bề ngang,
  không khung, chữ đè lên qua màn tối. Kiểu `quote`: thẻ trích dẫn pull-quote —
  câu lớn trong **khung 2 góc ngoặc bo tròn**, dòng nguồn `--attrib` canh giữa,
  brand text góc dưới-trái. Màu: **net khung + brand xanh Apple cố định**, **dấu " theo
  hãng nhắc trong chủ đề**. Kiểu `dai` (thẻ tin có textbox, nhãn, icon social,
  mascot) đã bỏ khỏi mã 05/09/2026 vì không vai nào dùng
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
    xem dưới), `jean_chuan_bi/jean_nop` (bóc bài, ráp teaser, gửi topic),
    `ada_chuan_bi/ada_nop` (số liệu N ngày: chọn theo bậc điểm/
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
- `xep_hang.py` — **ảnh cho tin xếp hạng** (Ông Chủ chốt 06/09/2026): tách tên model
  từ tiêu đề, đi qua registry **18 nguồn xếp hạng** (arena.ai ×6, artificialanalysis,
  tbench, swebench, livebench, aider, openrouter, livecodebench, bfcl, gaia, hle,
  vellum, opencompass — mỗi nguồn đã đo thật trước khi thêm), mở browser tìm **hàng**
  chứa model, chụp cửa sổ top-N full bề ngang, **khoanh vàng hàng model**, đọc
  thứ hạng. Bảng dạng `<ol>/<li>` (openrouter dàn top-10 thành hai cột 5 hàng) đi
  đường `chup_danh_sach`, ghép dọc các cột lại cho vừa khổ hero. Không ra →
  thẻ dự phòng (model + #hạng + logo + site). Chạy trong `anh_chuan_bi.py`, ảnh
  mang mã `XH`; `ethan_nop`/`dre_nop` ép tin xếp hạng dùng đúng mã đó.
  **Chụp bằng khung MOBILE trước, mọi nguồn** (Ông Chủ 06/09/2026: "vào trang nào
  chụp thì cũng hãy duyệt theo kích thước mobile, vì hình luôn đăng ở ratio 4:5"):
  414px × DPR 3 = 1242px, gần khớp khổ thẻ 1200px nên chữ gần như không bị co;
  desktop 2400 × DPR 2 = 4800px phải co bốn lần. Bảng rộng hơn khung (nằm trong
  khung cuộn ngang) bị loại tự động vì chụp ra chỉ được lát cắt trái. 8 nguồn đã
  ĐO là mobile không dùng được mang `khung: "desktop"` kèm lý do ghi ngay trong
  `NGUON` — gỡ cờ đó ra thì vẫn chạy đúng, chỉ tốn thêm một lượt mở trang.
  Danh sách mobile của arena chỉ hiện ~11-12 mục đầu, không tải thêm khi cuộn (đã
  thử `.scrollTop` lẫn `mouse.wheel()`) — model sâu hơn thì tự rơi về bảng desktop.

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
  GPT-6 Astra (03/09, #8 coding) không lên router nên Nova báo "0 model mới".

  **06/09/2026 — 12 bảng → 23 bảng.** Khảo sát 16 nguồn ứng viên, mỗi kết luận
  "lấy được" bị một lần fetch độc lập phản biện. Ba nhóm thay đổi:

  1. *Sửa chỗ tràn trước đã.* Ở trạng thái production (arena sống + có mốc cũ)
     báo cáo ra **13.635 ký tự** trong khi brief cắt ở 12.000 — `LIVEBENCH` và
     `OPENROUTER USAGE` bị nuốt **câm lặng**, Nova không biết hai bảng đó tồn
     tại. Ba mục `MODEL MOI`, trích benchmark, `ENGINE SUY LUAN` trước đó không
     có cận trên. Nay có `TRAN_*`, trần brief lên 22.000, và `_cat()` nói rõ khi
     đã cắt. Thêm nguồn trước khi vá chỗ này là làm phủ sóng **tệ đi**.
  2. *Số đã tải về mà chưa dùng.* `agenticIndex` nằm sẵn trong payload AA từ lâu
     nhưng chưa bao giờ được dựng bảng → `so_hang()` mù với "leo hạng agentic"
     (cùng loại sự cố qwen3.8-max WebDev 02/09). SWE-bench trả 5 split trong
     **một** request, ta chỉ dùng `Verified`. Cả hai không tốn thêm request nào.
  3. *Chiều thật sự mới* — `tbench` (agent gõ lệnh trong container), `arcagi`
     (bài chưa từng thấy), `hle` (trần kiến thức), `eci` (Epoch, có khoảng tin
     cậy), `opencompass` (đề đóng, phần lớn lab TQ), `tts`/`stt`/`i2v` (mảng
     không phải văn bản — trước đây mù hẳn), `hf_trending` (bắt model thả trọng
     số trước router 1–3 ngày).

  **Bảng bị loại và lý do** — không phải vì lấy không được, cả 5 đều lấy được:
  BFCL đóng băng từ 13/04/2026, LiveCodeBench từ 01/08/2025, Aider Polyglot từ
  03/10/2025, BigCodeBench từ 16/04/2025, Papers With Code đã đóng cửa. Thêm
  bảng chết vào script quét = mỗi lần chạy tốn một request để nhận `diff = 0`
  vĩnh viễn. Vellum bị loại vì tự nó ghi là trang **tổng hợp** lại số của người
  khác; GAIA vì nó xếp hạng **hệ thống agent** chứ không phải model (cột model
  là chuỗi viết tay, không join được). SWE-bench `Lite`/`Full`/`Multimodal` đều
  quá hạn nên chỉ lấy `Verified` + `Multilingual`.

  Nợ kỹ thuật đã biết: `TBENCH` là edge function moi từ bundle JS của tbench.ai,
  không phải API công bố — đổi project ref là chết im, cần theo dõi. `ids` trong
  `models_seen.json` chỉ tăng, chưa có cơ chế cắt tỉa (~40 byte/model/ngày).
- `bat_buoc.py` — **danh sách BẮT BUỘC** cho ba vai đi tìm tin (luật Ông Chủ 04/09/2026:
  script quét thấy là phải đưa, hôm trước sót thì hôm sau bổ sung, vai không có quyền bỏ).
  Script quét gieo mục (`state/<brand>/bat_buoc_<vai>.json`), script ghi manifest
  (`manifest_build.py` cho Finn, `manifest_ghi.py` cho Nova/Vera) **tự thêm** mục thiếu vào
  manifest kèm ghi chú "vai bỏ sót, script tự thêm" trên báo cáo (từ 05/09/2026, hết vòng
  từ chối rồi bắt vai sửa) và xoá mục đã đưa. Finn và Vera chọn tin bằng **số thứ tự `k`**
  trong brief, script tự lấy link và số báo — không chép URL nữa. Tiêu chí: Finn = tiêu đề nhắc hãng frontier hoặc HN/Reddit ≥150 điểm có
  dấu hiệu AI; Nova = mọi model ra mắt / vào bảng / leo hạng ở 23 bảng; Vera = một mục mỗi
  hãng lõi mỗi ngày (hoặc tin ≥2 báo), khớp theo tên hãng
- `model_watch.py` — dò sức khoẻ model đang dùng, báo Telegram khi trạng thái đổi
- `theo_doi_9router.py` — nhật ký 9router **theo ngày** (`state/9router/nhat_ky/9router_<ngày>.md|json`):
  req/prompt/cache%/$ theo model @ kết nối, theo khoá API, theo giờ VN, **model lạ**
  (không ở chuỗi cấu hình nào của bất kỳ HERMES_HOME) và **cache thấp** (gộp từ
  `usage_audit.py` 05/09/2026, tệp đó đã xoá), fallback thật
  v4-flash→deepseek-chat, lỗi, 5 prompt nặng nhất, phiên rỗng (ok nhưng ≤5 token out dù
  prompt ≥1k), snapshot connection lỗi (lastError/errorCode/backoff), **$ theo vai** (ghép
  `session_model_usage` mọi HERMES_HOME × đơn giá 9router trong ngày, phủ ~98%), $/task done,
  $/bài published theo brand, model lạ, cache thấp
  (9router không ghi IP máy gọi, xem "Điểm mù thứ ba"). Ada đọc qua `tai(ngày)` để so ngày với ngày
- `cost_squeeze.py` — chạy lặp trên việc thật, tìm model rẻ nhất mà vẫn ổn định
- `assets/` — font (JetBrains Mono, Inter, Be Vietnam Pro, Noto Serif, Oswald…),
  và `face_detection_yunet_2023mar.onnx` (~230KB, YuNet) cho
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

## Bảng đen kanban (swarm) — dcgr từ 05/09/2026

Ông Chủ hỏi "các vai có trao đổi với nhau được không, như clip Hermes". Có ba cách trong
Hermes; đội chọn **kanban swarm** vì hai cách kia (mỗi vai một bot Telegram, hoặc `delegate_task`
sinh agent con) hoặc tốn 8 bot hoặc không phải vai thật. Không dùng `create_swarm()` nguyên khối
vì nó chạy thẳng worker → verifier → synthesizer, không có chỗ cho cổng **Ông Chủ duyệt ảnh**.
`bang_den.py` dùng đúng các viên gạch của nó và dựng đồ thị theo tiến trình thật của bài:

```
thẻ gốc "Bài: …"   (done ngay; assignee `ban_bien_tap` — không ai nhận việc; là bảng đen)
  └─ task Dre        parent = gốc              ← tạo khi Ông Chủ chọn số
       └─ task Miles parent = [Dre, gốc]       ← tạo khi Ông Chủ bấm "Duyệt ảnh" (cổng giữ nguyên)
```

- Vai **không nhắn nhau**. Mỗi vai kết thúc bằng `kanban_complete(summary, metadata)`; hermes tự
  đưa summary/metadata đó vào context task con ("Parent task results"), nên Miles thấy Dre.
  `dre_nop.py` / `miles_nop.py` **tự ghi** bàn giao có cấu trúc lên bảng đen (comment
  `[swarm:blackboard] {…}` trên thẻ gốc) và in dòng `[metadata]` để vai dán vào `kanban_complete`.
- Task **Ada "Soát"** từng nối sau Miles (05/09 sáng) đã **bỏ 05/09 chiều**: một task LLM mỗi bài
  để kiểm bốn điểm mà `caption_check.py` giờ làm bằng code (số trong caption phải có trong tư liệu,
  cụm cấm, độ dài, tiếng Việt). Ông Chủ vẫn là người bấm; push CLI vẫn lưu `tg_card_message_id`
  để Ada đối chiếu bài với thẻ khi phân tích.
- Nhìn toàn chuỗi: `hermes kanban show <thẻ gốc>` hoặc dashboard — quan hệ cha-con nằm trong
  `task_links`, bàn giao trong `task_comments`/`task_runs`, không trôi như chat.
- Bảng đen là lớp thêm, **best-effort**: `bang_den.py` lỗi thì task vẫn tạo như cũ, chỉ mất bảng
  đen.
- Bật theo `CT_BANG_DEN` (mặc định `dcgr`). **Blog bật từ 05/09/2026 chiều** qua drop-in
  `hermes-approve@blog.service.d/override.conf` (`Environment=CT_BANG_DEN=dcgr,blog`); đã thử thẻ gốc
  trên kanban blog.

## Dịch vụ systemd

- `hermes-gateway` — gateway hermes, chứa dispatcher kanban
- `hermes-approve` — dịch vụ duyệt bài (tệp này)
- `hermes-dashboard` — bảng điều khiển web, cổng 9119
- `nhat-ky-web` — user unit (`hermes/systemd/nhat-ky-web.service`), `nhat_ky_web.py` cổng 9130:
  `/` danh sách ngày, `/9router/<ngày>` bảng đầy đủ, `.json` số thô. Tin Telegram 6h sáng
  (chỉ brand blog gửi, tránh trùng) là tóm tắt req · $ · cache% · fallback + $/bài + link
  `http://100.87.121.46:9130/9router/<ngày>` (netbird; đổi bằng `NHAT_KY_URL`). Không ảnh, không bảng trong Telegram

## Cron (7 job, xem `~/.hermes/cron/jobs.json`)

- `finn-daily-scan`, `nova-daily-scan`, `vera-daily-scan` — **05:00 VN** (22:00 UTC, từ 04/09/2026), ba vai đi tìm tin, chạy nối tiếp vì `max_in_progress: 1`
- `usage-audit` — đã gộp vào `daily-log` 05/09/2026; script chỉ còn in một dòng. Xoá job này trên server
- `daily-log` (trước là `nhat-ky-daily`) — 06:00 VN, dựng nhật ký ngày hôm trước + chốt nhật ký 9router hôm qua
  (`theo_doi_9router.py --gui`: tóm tắt ngày + cảnh báo IP ngoài / fallback / lỗi / phiên rỗng / connection chết + link web → topic analyst)
- `model-watch` — 30 phút/lần, dò sức khoẻ model
- `moat-publish-watch` — 5 phút/lần (nhịp ghi trong script; `jobs.json` còn 1 phút thì đổi),
  hỏi moat xem bài đã lên social chưa. Im lặng khi
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
Cần cả hai lớp: `model_watch.py` (model còn sống không) và `theo_doi_9router.py`
(model nào **thật sự** được gọi).

**2. Ghim mỗi hội thoại vào một model. Chuyển tầng thì chuyển ở ranh giới task.**
`try_activate_fallback` đổi model ngay giữa lượt, `restore_primary_runtime` lật
về model chính ở lượt sau — một hội thoại có thể chạy qua 2–3 model mà không ai
biết. Cache là per-model, mỗi lần lật là mất sạch prefix đã cache và cả ngữ cảnh
bị tính lại giá gốc. Cột `cache%` trong nhật ký ngày của `theo_doi_9router.py` chính là thước đo
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
script `tat_title_generation.py` (đã chạy xong và xoá khỏi repo 05/09, xem git log; quay lại
bằng tệp `.bak-truoc-tat-title-0905` trong từng profile); tiêu đề phiên vô dụng với task kanban/cron.

**Từ 05/09/2026 model chính là combo `DS-v4Flash` của 9router** (đổi bằng script
`doi_model_combo.py`, đã chạy xong và xoá khỏi repo cùng `bo_fallback_chat.py`; quay lại bằng
`.bak-truoc-doi-combo-0905` / `.bak-truoc-bo-fallback-chat-0905`; analyst giữ `ds/deepseek-reasoner`).
9router chỉ xoay giữa các connection *cùng* provider; ba route v4-flash (deepseek trực
tiếp `ds/`, xKiro `dsx/deepseek/deepseek-v4-flash`, aellm `dsa/deepseek-v4-flash`) chỉ
nối được với nhau qua Combo, gọi bằng đúng tên combo làm model (không có prefix
`combo/`). Trước đó cả ba node đều đặt prefix `ds` nên hai node ngoài bị che, 7 ngày
0 request. Đo route thật bằng `usageHistory.provider` của 9router; Hermes chỉ thấy
model `DS-v4Flash`. Combo còn chứa mục chết (`ds/ds/…`, `tokenrouter/…` không có
credential, `oc/…-free` unavailable) và chưa có `dsa/`: dọn trên dashboard.

**dcgr chạy chat theo bot mode chuẩn của Hermes từ 05/09/2026 (thí điểm, blog giữ
chat_router để so ~1 tuần).** Gateway dcgr: `multiplex_profiles: true`, 8 `profile_routes`
theo thread_id, bot riêng @hermesdcgr_bot; approve dcgr vẫn dùng @hermesmodebot cho chọn
số/Duyệt/Làm lại, chỉ nhường phần chat qua cờ `CT_CHAT_QUA_GATEWAY=1` đặt trong drop-in
`~/.config/systemd/user/hermes-approve@dcgr.service.d/override.conf` (unit template dùng
chung, blog không có cờ). Mỗi profile cần `profiles/<vai>/.env` với `OPENAI_API_KEY` +
`TELEGRAM_ALLOWED_USERS` (multiplex fail-closed, không fallback `.env` gốc) nhưng
**KHÔNG** được chứa `TELEGRAM_BOT_TOKEN`/`TELEGRAM_HOME_CHANNEL`: `backfill_profile_envs`
của Hermes chép cả token → gateway từ chối 8 profile vì "same credential" (đã gặp 05/09,
phải xoá dòng token khỏi 8 tệp). Đo bằng journal `hermes-gateway@dcgr` + `logs/gateway.log`
(INFO không vào journal) so với approve.log blog: độ trễ, mất mạch, 429/timeout. Nhận xét
đầu: reply qua gateway ngắn và không biết tình trạng task kanban như approve.
Bản chụp config + drop-in + mẫu .env để tái tạo: `hermes/gateway/dcgr/` (xem DOC.md ở đó).

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
con số tổng**, không tách được brand nào tốn bao nhiêu.

**Đã tách 05/09/2026:** 9router có hai khoá `hermes blog` và `hermes dcgr` (bảng
`apiKeys`); khoá vào Hermes qua `OPENAI_API_KEY` trong `~/.hermes-<brand>/.env`
(config.yaml chỉ ghi `${OPENAI_API_KEY}`). **Nhưng** dcgr chạy multiplex nên 8
`profiles/<vai>/.env` cũng có `OPENAI_API_KEY`, và Hermes nạp `.env` của profile với
`override=True` (`hermes_cli/env_loader.py`) → khoá trong profile **đè** khoá gốc. Lúc
05/09 12:55 chỉ `.env` gốc mang khoá `hermes dcgr`, 8 profile vẫn mang khoá `hermes blog`
→ 9router ghi 181/182 request dcgr vào khoá blog, tách mà như chưa tách. Đổi khoá cho
dcgr = sửa `.env` gốc **và** cả 8 `profiles/*/.env` (blog không có profile .env nên chỉ
một dòng), rồi restart gateway brand đó. Từ đó `theo_doi_9router.py` tự tách req/$ theo
brand ở mục "theo khoá API" (đọc tên khoá từ bảng `apiKeys`, không cần sửa code).

**Điểm mù thứ ba: 9router KHÔNG ghi IP máy gọi.** `usageHistory` không có cột IP,
`meta` luôn `{}`; `custom-server.js` có tính `x-9r-real-ip` nhưng chỉ dùng cho
rate-limit. Service đang bind `0.0.0.0` (LAN 192.168.1.61 + netbird) nên ai trong
mạng cũng gọi được bằng khoá chung. Watcher socket `--canh` (đọc bảng TCP mỗi 2s,
ghi IP theo kết nối) đo 05/09 sáng rồi **bỏ 05/09 chiều**: nó chỉ thấy kết nối,
không thấy request (httpx keep-alive chở nhiều request một kết nối), và cách đúng
là bind 9router về `127.0.0.1` hoặc địa chỉ netbird rồi cấp khoá riêng cho từng
máy (mục "theo khoá API" tự tách). Nhật ký ngày `9router_<ngày>.md` cột "đổi model
liên tiếp" chỉ tin cặp v4-flash→deepseek-chat là fallback thật,

Token burn đo được cho một luồng trọn vẹn (Finn quét → vai ảnh dựng → vai viết,
17 lượt gọi): **~398.000 token chạm model**, cache 36%, 227 giây, ước $0,038.

## Bài học một tuần config 9router không chuẩn (29/08–05/09/2026)

1. **Hai chuỗi dự phòng chồng nhau, không ai nhìn cả hai.** Combo của 9router và
   `fallback_providers` của Hermes là hai cơ chế độc lập. Tắt deepseek-chat trên 9router
   xong vẫn thấy nó trong log vì 19 config Hermes còn giữ nó làm dự phòng. Quy tắc: đổi
   model là phải sửa CẢ HAI chỗ, kiểm bằng `grep deepseek-chat ~/.hermes-*/**/config.yaml`.
2. **Một route chết trong combo kéo cả chuỗi lật.** xKiro trả 404 "model does not exist"
   từ 06:34 05/09 mà vẫn nằm trong combo → combo lỗi định kỳ → Hermes fallback. Trước khi
   thêm route vào combo phải gọi thử; snapshot connection lỗi trong nhật ký ngày để bắt.
3. **Bước phụ làm lật model chính.** `title_generation` gửi `response_format`, v4-flash trả
   400, 9router cooldown 30s, 2 retry của Hermes rơi đúng cooldown → cả phiên chạy
   deepseek-chat. Mọi bước phụ (title, summary, vision) phải cùng model hoặc tắt hẳn.
4. **9router chỉ xoay connection cùng provider.** Ba route v4-flash khác provider chỉ nối
   được qua Combo; gọi bằng đúng tên combo, không có tiền tố `combo/`. Prefix trùng
   (`ds`) từng che mất hai node ngoài.
5. **Tên model lệch ba kiểu.** Hermes ghi `ds/deepseek-v4-flash`, `DS-v4Flash`,
   `DeepSeek-V4-Flash`; 9router ghi `deepseek-v4-flash`, `deepseek/deepseek-v4-flash`.
   Mọi script đối chiếu phải chuẩn hoá (bỏ tiền tố nhà cung cấp, không phân biệt hoa
   thường, resolve combo qua bảng `combos`), không so chuỗi thô.
6. **Nhìn số gộp thì không thấy gì.** usage_audit in một bảng N giờ rồi quên; glm-5.3 đắt
   40x/request ăn 70% tiền suốt nhiều ngày mà README vẫn nói v4-flash. Phải có nhật ký
   theo ngày, $ theo vai, $/bài, và đọc config thật trên server chứ không tin README.
7. **Hạ tầng dùng chung thì không tách được ai tốn gì.** Một 9router, một apiKey cho hai
   brand, bind 0.0.0.0 không ghi IP. Muốn tách brand cần khoá riêng; muốn biết máy nào
   gọi phải tự bắt ở socket. Đừng để mặc định của công cụ quyết định độ quan sát.

8. **Cache là của từng nhà cung cấp, không phải của model.** Cùng v4-flash, qua DeepSeek
   trực tiếp cache 93–96%, qua aellm (bán lại) 49% → đắt ~7x mỗi token prompt. Combo phải
   xếp DeepSeek trực tiếp TRƯỚC, reseller chỉ để dự phòng; và đừng để hết credit (402 hôm
   05/09 đẩy cả ngày sang aellm).
9. **System prompt đổi mỗi task vì một dòng.** Hermes in `Current working directory:` vào
   giữa prompt; workspace `scratch` tạo thư mục mới mỗi task nên 37% cuối prompt (skills,
   memory) không bao giờ trúng cache giữa hai task. Đo 05/09: hai task carousel cách 5 phút
   chỉ khác đúng dòng đó. Sửa: `approve_service.kanban_create` tạo task với
   `--workspace dir:~/.hermes-<brand>/kanban/workspaces/co-dinh`. Còn lại trong prompt chỉ
   đổi theo ngày (`Conversation started`) và theo model (`Model:`) — thêm lý do ghim model.
   Sửa SOUL cũng làm cache về 0 cho vai đó, gom sửa thành đợt. Chạy thử từ `~/hermes-agent`
   thì bị nhét cả AGENTS.md của Hermes (prompt 115k ký tự) — chỉ thử từ `~/content-team`.

Trạng thái sau khi sửa (05/09): combo = [ds trực tiếp, dsx xKiro, dsa aellm], 19 profile dự
phòng `ds/deepseek-v4-flash`, title_generation tắt, nhật ký ngày + web + tin 6h đã chạy.
Chỉ tiêu: fallback = 0 từ 06/09; sai thì trang chi tiết chỉ ra route nào.

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
