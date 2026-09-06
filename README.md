# content-team

Dây chuyền nội dung tự động cho kênh Telegram AI, chạy trên hermes-agent.

Tệp này chỉ mô tả **hiện trạng**. Chẩn đoán, số đo một lần và bài học rút ra
nằm ở [NHAT_KY_SU_CO.md](NHAT_KY_SU_CO.md). Luật ảnh dùng chung ở
[LUAT_ANH.md](LUAT_ANH.md); spec chữ trên thẻ ở
[STYLE_TEXT_SPEC.md](STYLE_TEXT_SPEC.md).

Nguồn sự thật của cấu hình là chính máy chủ, không phải tệp này:

```bash
grep -h "^  model:" ~/.hermes-*/profiles/*/config.yaml | sort | uniq -c
```

## Đội hình

Hai brand là hai container riêng (`~/.hermes-blog`, `~/.hermes-dcgr`), trong một
container chỉ có một vai mỗi loại — nên profile chỉ còn **Tên** và **role**,
không còn hậu tố `.blog`/`.dcgr`. Slug **Profile hermes** là định danh thật
(lệnh, assignee, topic map); nhãn chỉ là chữ nhìn thấy.

Brand đi theo **sidecar của bài**, vai không truyền cờ `--brand`: `nop_chung.nap`
đọc ra từ `drafts/<id>.*.json`. Cùng một script phục vụ cả hai brand.

| Tên | Profile hermes | Role | Việc |
|---|---|---|---|
| Finn | `scout` | scout | Quét HN/Reddit/arXiv, chấm điểm, gửi danh sách đánh số — **chỉ donniechublog** (dcgr chỉ có Vera) |
| Ethan | `designer` | designer | Dựng ảnh hero cho cả hai brand — mặc định thẻ **quote** (pull-quote có khung), `--kieu tran` khi muốn ảnh phủ kín |
| Dre | `carousel` | carousel | Dựng **carousel nhiều slide** cho cả hai brand — ảnh thật, chữ chìm vào ảnh, ra album |
| Kite | `carousel-edu` | carousel.edu | Carousel **EDU** bằng **art vector gốc** (paper/nghiên cứu, không ảnh thật), tối thiểu 6 slide — chỉ donniechublog. Ngoại lệ có chủ đích với luật không-tự-vẽ |
| Gin | `gin` | clean | Xoá chữ tiếng Anh trên ảnh nền (OCR+LaMa, `doi_chu_anh.py`), trả nền sạch cho Itachi |
| Itachi | `itachi` | carousel.rep | Dựng lại carousel kiểu **editorial-deck** (`deck.py`) từ nền sạch của Gin |
| Miles | `writer` | writer | Viết caption tiếng Việt cho cả hai brand, đẩy vào hàng duyệt |
| Nova | `nova` | model | Quét 23 bảng xếp hạng model, báo cái đáng chú ý |
| Vera | `market` | market | Quét tin kinh doanh/đầu tư quanh AI (Google News + feed báo) |
| Ada | `analyst` | analyst | Đo phản hồi, đối chiếu điểm chấm với lựa chọn thực tế |
| Jean | `teaser` | teaser | Ghép teaser từ bài đã duyệt — blog only |
| Bob | `bob` | — | Đóng khung một ảnh bất kỳ từ URL, gắn mascot hợp tâm trạng |

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


## Kiến trúc 3 lớp

Mọi vai đi theo cùng một khuôn (04/09/2026): **CHUẨN BỊ (script, chạy nền) →
VIẾT (LLM, một tệp) → NỘP (script)**. Trước đó mỗi task tốn 14–60 tool call, phần
lớn là việc cơ học: curl tải ảnh, ls/grep dò tệp, tự đếm ký tự, chạy cổng chặn
nhiều vòng. Giờ mỗi task là **3 lệnh**.

- `anh_chuan_bi.py` — **engine dùng chung** cho mọi vai làm ảnh/chữ từ một tin.
  `approve_service.create_pair` khởi chạy nền (`--im`) ngay lúc Ông Chủ chọn số:
  giải mã link Google News, Bing News RSS tìm báo khác, một phiên chromium (chữ
  bài, img lớn, chụp table/figure/canvas), `anh_bai`, Wikimedia Commons khi < 5
  ảnh; dHash bỏ trùng; phân loại chart/mặt người/tỉ lệ; cắt sẵn 1:1 và 4:5 qua
  `crop_ti_le`; cặp ghép cùng tone; tư liệu. Kết quả
  `state/<brand>/chuan_bi/<id>/xong.json` + `bang_anh.png`.
- Mỗi vai một cặp **brief + nop** đọc chung `xong.json`: `dre_chuan_bi/dre_nop`,
  `ethan_chuan_bi/ethan_nop`, `kite_chuan_bi/kite_nop`, `miles_chuan_bi/miles_nop`.
  Nop chạy cổng chặn của renderer, gửi kèm nút duyệt, ghi
  `drafts/<id>.ban_giao.md` và `da_dung.json` (để "Làm lại" bắt buộc đổi
  ảnh/hook/tone). `--khong-gui`/`--out`/`--khong-push` để thử.
- Bốn vai theo chat cùng mẫu, khoá là message_id/URL: `gin_*`, `itachi_*`,
  `jean_*`, `ada_*`. `bob_nop.py` là một lệnh trọn gói (lấy ảnh → nhìn → đóng
  khung → gửi).
- `quet_chuan_bi.py --vai scout|nova|market` + `quet_nop.py`: ba vai đi tìm tin
  nhận danh sách ứng viên một dòng mỗi tin + mục BẮT BUỘC + khung tệp nộp; nop
  ghép manifest, kiểm bắt buộc, viết báo cáo, gửi topic. `--khong-co` gửi dòng
  "hôm nay không có gì"; `--thu` không ghi manifest thật.
- Skill `ai-background` và bộ retouch/blend của Gin/Itachi **chờ GPU** (sửa/sinh
  ảnh bằng CPU quá nặng) — không phải lỗi. Script sinh nền chưa được viết; skill
  mô tả sẵn hợp đồng để khi có GPU thì bắt tay vào đúng chỗ. Tới lúc đó hai vai
  chỉ xoá chữ + vẽ tại chỗ/deck.

## Tệp

**Dựng ảnh**

- `card.py` — thẻ đơn. Kiểu `quote` (mặc định): pull-quote trong khung hai góc
  ngoặc, dòng nguồn `--attrib` canh giữa. Kiểu `tran`: ảnh phủ kín, chữ đè lên
  qua màn tối chuyển dần. Màu chữ/khung đo theo từng dải nền của chính tấm ảnh.
  Spec chữ và bố cục: [STYLE_TEXT_SPEC.md](STYLE_TEXT_SPEC.md).
- `carousel.py` — carousel nhiều slide (Dre): ảnh 1:1 hoặc 4:5 phủ kín thẻ, chữ
  ở đáy chìm vào ảnh, ra `<id>.png` + `<id>_2.png`… đúng khuôn album của
  `draft_write.py`. Dùng lại helper của `card.py`.
- `render_edu.py` — renderer của Kite: carousel tech-editorial **art vector gốc**
  bằng HTML/CSS/SVG, chụp bằng Chromium headless. Spec JSON, **7 kind**:
  `cover` / `statement` / `steps` / `loop` / `figure` / `bars` / `cta`. Không ảnh
  thật. Cần `playwright install chromium`.
- `deck.py` — editorial-deck của Itachi, dựng lại carousel nguồn sang tiếng Việt.
- `crop_ti_le.py` — cắt ảnh về **1:1 hoặc 4:5**. Chỉ cắt chiều cao; ảnh gốc ngang
  (≥1.4) đòi cắt bề ngang thì dừng, vì bề ngang của chart/bảng là nội dung. Ép
  bằng `--cat-ngang`, chỉ cho ảnh người/sản phẩm không có chữ.
- `arxiv_bia.py` — bài arxiv không có ảnh thì chụp trang đầu paper. Cần `pymupdf`.
- `xep_hang.py` — ảnh cho **tin xếp hạng**: tách tên model từ tiêu đề, đi qua
  registry **18 nguồn**, mở browser tìm hàng chứa model, chụp cửa sổ top-N,
  khoanh vàng hàng đó, đọc thứ hạng. Chụp bằng **khung mobile trước** (414px ×
  DPR 3 ≈ khổ thẻ 1200px nên chữ gần như không co); 8 nguồn đã đo là mobile
  không dùng được thì mang `khung: "desktop"` kèm lý do ngay trong `NGUON`.
  Không ra thì thẻ dự phòng. Ảnh mang mã `XH`.
- `chup_chart.py` — chụp chart/bảng benchmark theo luật *full chiều rộng trước,
  chiều cao xét sau*: đo `scrollWidth` thật, nới khung cho vừa rồi mới chụp ở
  DPR 2; thiếu bề ngang thì dừng. Cần `playwright` + chromium.
- `luat_anh.py` + `LUAT_ANH.md` — **một nguồn sự thật** của luật ảnh, dùng chung
  cho mọi vai TẠO ra ảnh (Ethan, Dre, Kite). Đừng chép luật vào SKILL của vai.
  Gin/Itachi chỉ sửa trên ảnh gốc nên không áp bộ này.

**Đi tìm tin**

- `scan_sources.py` / `nguon_bai.py` — quét nguồn của Finn và research lúc chọn
  tin; tự giải mã link Google News (`giai_ma_gnews`).
- `scan_models.py` — quét của Nova: 23 bảng xếp hạng, mục "RA MẮT THEO BẢNG CHẤM
  ĐIỂM" (mỗi model báo đúng một lần nhờ `aa_da_bao` trong `models_seen.json`).
  Bảng chết (BFCL, LiveCodeBench, Aider, BigCodeBench, Papers With Code) bị loại
  có chủ đích — xem nhật ký sự cố.
- `manifest_ghi.py` / `manifest_build.py` — ghi manifest đánh số vào
  `state/<brand>/` qua `env_load.state_dir()`, cùng chỗ approve_service đọc.
- `bat_buoc.py` — **danh sách BẮT BUỘC**: script quét thấy là phải đưa, vai không
  có quyền bỏ. Script ghi manifest tự thêm mục thiếu kèm ghi chú "vai bỏ sót" và
  xoá mục đã đưa. Finn và Vera chọn tin bằng **số thứ tự `k`**, không chép URL.
- `tu_lieu.py` — bóc chữ bài để đối chiếu số liệu và tên người vai khai.

**Duyệt và đăng**

- `approve_service.py` — dịch vụ nền nghe nút duyệt và lệnh chọn số. Mặt tiền
  mỏng; phần thân nằm ở `duyet_co_so` / `duyet_giao_viec` / `duyet_chon_tin` /
  `duyet_bai` / `duyet_chat` / `duyet_lenh`. Mọi tin nhắn vào đều có log
  (`state/<brand>/approve.log`, xoay vòng 5 MB×3) theo nhãn
  `vao → route → chat/chon/lenh → tele`, và mọi nhánh kết thúc bằng một tin trả về.
- `chat_router.py` — định tuyến chat Telegram → hermes CLI theo topic (blog).
- `draft_write.py` — ghi bản nháp + album đúng khuôn tên tệp.
- `publish.py` — gửi text/ảnh lên Telegram, hỗ trợ topic.
- `moat_publish.py` — đẩy bài đã duyệt sang moat và hỏi trạng thái đăng social.
- `bang_den.py` — bảng đen kanban (xem dưới).
- `ghi_log.py`, `env_load.py` — log và nạp môi trường dùng chung.

**Đo đạc**

- `theo_doi_9router.py` — nhật ký 9router theo ngày
  (`state/9router/nhat_ky/9router_<ngày>.md|json`): req/prompt/cache%/$ theo model,
  theo khoá API, theo giờ VN, model lạ, cache thấp, fallback thật, lỗi, phiên
  rỗng, **$ theo vai** và $/bài theo brand. Ada đọc qua `tai(ngày)`.
- `nhat_ky.py` + `nhat_ky_web.py` — nhật ký ngày và trang web cổng 9130.
- `model_watch.py` — dò sức khoẻ model, báo Telegram khi trạng thái đổi.
- `model_audition.py`, `cost_squeeze.py` — thử model trên việc thật.

**Khác**

- `assets/` — font (JetBrains Mono, Inter, Be Vietnam Pro, Noto Serif, Oswald…)
  và `face_detection_yunet_2023mar.onnx` (~230KB, YuNet) cho cổng chặn mặt người.
- `hermes/skills/` — skill dùng chung, nằm thẳng trong git, profile trỏ vào qua
  `skills.external_dirs` nên `hermes update` không xoá được: `hero-image` (Ethan),
  `carousel` (Dre), `carousel-edu` (Kite), `url-mascot-frame` (Bob),
  `inplace-translate` (Gin/Itachi), `social-crawl` (bóc media từ post mạng xã hội),
  `ai-background` (sinh nền — **chờ GPU**).
- `hermes/profiles/` — SOUL/MEMORY của các vai; `shared/` áp cho cả hai home.
  Đồng bộ bằng `dong_bo_hermes.py` (`--ra-hermes` / `--ve-git`).
- `tests/` — chạy thẳng, không cần mạng:
  `for f in tests/*.py; do venv/bin/python $f; done`. `test_cong_chan` giữ các
  cổng chặn, `test_cong_thuan` giữ mấy hàm thuần đã từng hồi quy im lặng (lệnh
  chọn số, `draft_id` ≤ 55 byte, cắt tin nhắn dài), `test_tai_lieu` chặn tài
  liệu trôi khỏi mã.
- `kiem_hermes.py` — kiểm các chỗ lệ thuộc nội bộ hermes (xem mục dưới).
- `requirements.txt` — venv dùng chung với hermes nên `hermes update` có thể làm
  mất `pymupdf`; cài lại bằng `venv/bin/pip install -r requirements.txt`.

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

Đều là **user unit** (`systemctl --user`), mỗi brand một instance:

- `hermes-gateway@blog` / `hermes-gateway@dcgr` — gateway hermes, chứa dispatcher
  kanban. dcgr chạy multiplex (8 `profile_routes`, bot riêng @hermesdcgr_bot).
- `hermes-approve@blog` / `hermes-approve@dcgr` — dịch vụ duyệt bài.
- `hermes-dashboard-blog` — cổng **9120**; `hermes-dashboard-dcgr` — cổng **9121**
  (đều bind 127.0.0.1).
- `nhat-ky-web` — `nhat_ky_web.py` cổng **9130**: `/` danh sách ngày,
  `/9router/<ngày>` bảng đầy đủ, `.json` số thô. Tin Telegram 6h sáng (chỉ brand
  blog gửi, tránh trùng) là tóm tắt req · $ · cache% · fallback + $/bài + link.

## Cron

Mỗi brand một tệp riêng — **không** còn `~/.hermes/cron/jobs.json` gộp chung:
`~/.hermes-blog/cron/jobs.json` (5 job) và `~/.hermes-dcgr/cron/jobs.json` (4 job).

- `finn-daily-scan`, `nova-daily-scan`, `vera-daily-scan` — **05:00 VN**
  (22:00 UTC), chạy nối tiếp vì `max_in_progress: 1`.
- `daily-log` — 06:00 VN, dựng nhật ký ngày hôm trước + chốt nhật ký 9router
  (`theo_doi_9router.py --gui` → topic analyst).
- `model-watch` — 30 phút/lần.
- `moat-publish-watch` — 5 phút/lần, hỏi moat xem bài đã lên social chưa; im
  lặng khi không có gì mới, bỏ theo dõi một bài sau 7 ngày.

## State: tệp nào của ai

Năm tiến trình cùng ghi vào `drafts/` và `state/` — dịch vụ duyệt, engine chuẩn
bị chạy nền, các script nộp, cron moat, và tiến trình hermes của bảng đen. Không
có bảng này thì không ai biết sửa một tệp sẽ đụng vào ai.

| Tệp | Ai TẠO | Ai SỬA | Ai ĐỌC |
|---|---|---|---|
| `drafts/<id>.meta.json` | `duyet_chon_tin.write_meta` | `anh_chuan_bi` (nền), `bang_den` | vai ảnh, vai viết, Ada |
| `drafts/<id>.img.json` | `duyet_chon_tin` | `duyet_bai` (làm lại, chuyển Kite) | `duyet_bai`, Ada |
| `drafts/<id>.writer.json` | `duyet_chon_tin` | `duyet_bai` (duyệt / bỏ hẳn) | `duyet_bai`, Ada |
| `drafts/<id>.json` (bản nháp) | `draft_write` | `duyet_bai.mark_draft`, `moat_publish` (cron) | `duyet_bai`, `publish` |
| `drafts/<id>.ban_giao.md` | `*_nop` | — | `duyet_bai` dán vào task Miles |
| `state/<brand>/chuan_bi/<id>/xong.json` | `anh_chuan_bi` | — | mọi `*_chuan_bi` và `*_nop` |
| `state/<brand>/anh_da_dung.jsonl` | `nop_chung.gui_album` | `duyet_bai` (gỡ khi Bỏ/Làm lại) | `luat_anh.kiem_da_dung` |
| `state/<brand>/bat_buoc_<vai>.json` | script quét | `manifest_ghi` / `manifest_build` (xoá mục đã đưa) | brief của vai quét |
| `state/<brand>/<vai>_candidates_*.json` | `manifest_*` | — | `duyet_chon_tin` (chọn theo mtime) |
| `state/9router/` | `theo_doi_9router` | — | `nhat_ky_web`, Ada |

**Quy ước gốc state:** `state/<brand>/` cho mọi thứ thuộc về một brand;
`state/` gốc **chỉ** cho thứ chung cả máy (nhật ký 9router, khoá). Sổ theme của
Kite từng nằm sai chỗ ở gốc — Kite chạy cả hai brand nên bộ "4 bộ gần nhất" trộn
lẫn, một bộ dcgr vừa dùng theme X là bộ blog kế tiếp bị đẩy sang theme khác mà
không có lý do nào. Đã chuyển về `state/<brand>/` ngày 06/09/2026.

**Mọi tệp JSON state ghi qua `_ghi_json` / `env_load` (tmp + `os.replace`)**,
không `write_text` thẳng: `write_text` cắt ngắn tệp cũ trước khi ghi nội dung
mới, nên restart đúng giữa hai bước đó để lại một sidecar cụt và mọi người đọc
sau đó ném `ValueError` — bài kẹt vĩnh viễn mà không ai biết.

## Sau mỗi `hermes update`

`content-team` đọc vài thứ **bên trong** hermes mà không có API nào bảo đảm:
định dạng in ra của `hermes chat -Q`, schema thô của `kanban.db`, và một hàm
private của `kanban_swarm`. Chúng đổi lúc nào cũng được, và đổi thì hỏng lặng lẽ
— sự cố `-z` nuốt `--continue` (mọi vai mở phiên trắng, "không nhớ gì") mất mấy
ngày mới lộ ra. Chạy ngay sau khi cập nhật:

```bash
venv/bin/python kiem_hermes.py
```

Chỉ đọc, không tạo gì. Thêm `--day-du` nếu muốn một lượt chat thật (tốn LLM).
Kèm theo: `venv/bin/pip install -r requirements.txt` (venv dùng chung nên
`hermes update` có thể làm mất pymupdf), và
`venv/bin/python dong_bo_hermes.py --kiem-upstream` để xem hermes đổi gì trong
plugin kanban kể từ lần port cuối.

## Model

Mọi vai trừ Ada chạy chính bằng **combo `DS-v4Flash` của 9router** (ba route
v4-flash: DeepSeek trực tiếp, xKiro, aellm — DeepSeek trực tiếp xếp trước vì
cache là của từng nhà cung cấp). Ada giữ `ds/deepseek-reasoner` vì việc đối chiếu
điểm chấm cần suy luận thật.

Mọi vai trừ Ada đặt `agent.reasoning_effort: none`: model deepseek đốt hết ngân
sách token vào suy luận rồi trả về **rỗng** (đo thật: 3/24 lần trên v4-pro, tái
hiện y hệt trên v4-flash). Tắt suy luận: 0/24 lần rỗng, nhanh gấp 3, rẻ hơn.

Đừng tin bảng model chép trong tài liệu — hỏi thẳng máy chủ bằng lệnh ở đầu tệp
này. Lịch sử đổi model, số đo giá, và ba điểm mù của 9router: xem
[NHAT_KY_SU_CO.md](NHAT_KY_SU_CO.md).

**Hai nguyên tắc bắt buộc khi dùng nhiều model:**

1. **Phải có giám sát model.** Hermes fallback im lặng hoàn toàn — đặt model
   chính thành model chết, agent vẫn trả lời bình thường, không một dòng báo.
   Cần cả hai lớp: `model_watch.py` (model còn sống không) và
   `theo_doi_9router.py` (model nào **thật sự** được gọi).
2. **Ghim mỗi hội thoại vào một model; chuyển tầng thì chuyển ở ranh giới task.**
   Cache là per-model, mỗi lần lật là mất sạch prefix đã cache. Cột `cache%`
   trong nhật ký ngày chính là thước đo: tụt cache nghĩa là đang lật model.

## Lưu ý

`.secrets.env` chứa bot token Telegram và khoá moat — **không bao giờ commit**.
Chỉ một tiến trình được long-poll một bot token; `approve_service.py` giữ vai trò đó.
