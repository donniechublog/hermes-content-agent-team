# content-team

Dây chuyền nội dung tự động cho kênh Telegram AI, chạy trên hermes-agent.

Tệp này chỉ mô tả **hiện trạng**. Chẩn đoán, số đo một lần và bài học rút ra
nằm ở [NHAT_KY_SU_CO.md](NHAT_KY_SU_CO.md). Luật ảnh dùng chung ở
[LUAT_ANH.md](LUAT_ANH.md); khuôn ticket Linear 7 bước ở
[KHUON_TICKET.md](KHUON_TICKET.md); spec chữ trên thẻ ở
[STYLE_TEXT_SPEC.md](STYLE_TEXT_SPEC.md). Sơ đồ kiến trúc (Mermaid, theo mô
hình C4) ở [KIEN_TRUC.md](KIEN_TRUC.md).

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

**Hai người viết, cắt theo vai quét** (LOW-13, 10/09/2026): Finn và Nova → **Jika**
(`jika`, donniechublog); Vera → **Miles** (`writer`, dcgr.tech). Quyết định chốt
ngay lúc chọn tin và nằm trong `drafts/<id>.writer.json`; mọi bước sau đọc lại chỗ đó
thay vì đoán lại. Bảng định tuyến ở `vai.vai_viet_cua` — hỏi vai quét trước, brand làm
lưới. Vai **ảnh** không đổi: vẫn do Ông Chủ chọn theo từng tin.

| Tên | Profile hermes | Role | Việc |
|---|---|---|---|
| Finn | `finn` | scout | Quét HN/Reddit/arXiv, chấm điểm, gửi danh sách đánh số — **chỉ donniechublog** (dcgr chỉ có Vera) |
| Ethan | `ethan` | designer | Dựng ảnh hero cho cả hai brand — mặc định thẻ **quote** (pull-quote có khung), `--kieu tran` khi muốn ảnh phủ kín (cũng có khung, từ 07/09/2026) |
| Dre | `dre` | carousel | Dựng **carousel nhiều slide** cho cả hai brand — ảnh thật, chữ chìm vào ảnh, ra album |
| Kite | `kite` | carousel.edu | Carousel **EDU** bằng **art vector gốc** (paper/nghiên cứu, không ảnh thật), tối thiểu 6 slide — **cả hai brand** (blog từ 02/09/2026, dcgr từ 05/09). Ngoại lệ có chủ đích với luật không-tự-vẽ |
| Gin | `gin` | clean | Xoá chữ tiếng Anh trên ảnh nền (OCR+LaMa, `swap_image_text.py`), trả nền sạch cho Itachi |
| Itachi | `itachi` | carousel.rep | Dựng lại carousel kiểu **editorial-deck** (`deck.py`) từ nền sạch của Gin |
| Miles | `miles` | writer | Viết caption tiếng Việt cho tin **kinh doanh, đầu tư** của **dcgr.tech** (từ 10/09/2026, LOW-13; trước đó viết cả hai brand). Profile `miles` bên blog **giữ lại cho việc còn tồn**, không nhận việc mới |
| Jika | `jika` | writer | Viết caption tiếng Việt cho tin **model mới, arXiv/Hacker News** — **chỉ donniechublog** (từ 10/09/2026, LOW-13). Cùng script, cùng luật caption như Miles; khác ở người đọc và ở MEMORY riêng |
| Qinn | `qinn` | scout.x | Đọc tin kỹ thuật trên X (home timeline + các X List) qua cổng đọc của social-publishing, **2 lượt/ngày** (05:00 và 17:00 VN), cửa sổ 12h mỗi lượt — **chỉ donniechublog**, tin đi sang Jika. Không tự crawl X: session X nằm trên máy crawler, `scan_x.py` chỉ đọc lại (từ 12/09/2026) |
| Nova | `nova` | model | Quét 23 bảng xếp hạng model, báo cái đáng chú ý |
| Vera | `vera` | market | Quét tin kinh doanh/đầu tư quanh AI (Google News + feed báo) |
| Ada | `ada` | analyst | Đo phản hồi, đối chiếu điểm chấm với lựa chọn thực tế |
| Cape | `cape` | teaser | Ghép teaser từ bài đã duyệt — blog only |
| Bob | `bob` | — | Đóng khung một ảnh bất kỳ từ URL, gắn mascot hợp tâm trạng |

## Luồng

```
cron 05:00 VN → task kanban cho Finn → Finn quét, ghi manifest, gửi báo cáo
                                              ↓
        Ông Chủ trả lời số thứ tự trong topic Finn
                                              ↓
     approve_service tạo cặp task vai ảnh → vai viết (vai viết chờ ảnh xong)
                                              ↓
        Bản nháp + thẻ ảnh vào topic Miles kèm nút ✅ / ❌
                                              ↓
                     ✅ → đăng lên channel      ❌ → đánh dấu bỏ
                              ↓
                  đẩy sang moat (hàng đợi publish) — hết phần của ta
```

**Phần của ta dừng ở moat.** `moat_publish.py` đẩy bài đã duyệt sang moat (org
`dcgr.tech`) với hai loại: `facebook_post` và `instagram_carousel`
(`moat_publish.PLATFORMS`), rồi cron `moat-publish-watch` (5 phút/lần) hỏi trạng
thái và báo vào topic Miles. Moat hỏng không làm hỏng khâu duyệt: bài vẫn lên
Telegram channel, thẻ duyệt chỉ ghi thêm một dòng cảnh báo.

Từ moat trở đi — extension trình duyệt claim và đăng thế nào, vì sao không có
TikTok — là **hệ thống của người khác**, ta không viết và không kiểm được. Tài
liệu này không mô tả nó; muốn biết thì đọc bên đó, không suy từ mã của ta.


## Kiến trúc 3 lớp

Mọi vai đi theo cùng một khuôn (04/09/2026): **CHUẨN BỊ (script, chạy nền) →
VIẾT (LLM, một tệp) → NỘP (script)**. Trước đó mỗi task tốn 14–60 tool call, phần
lớn là việc cơ học: curl tải ảnh, ls/grep dò tệp, tự đếm ký tự, chạy cổng chặn
nhiều vòng. Giờ mỗi task là **3 lệnh**.

- `image_prepare.py` — **engine dùng chung** cho mọi vai làm ảnh/chữ từ một tin.
  `approve_service.create_pair` khởi chạy nền (`--im`) ngay lúc Ông Chủ chọn số:
  giải mã link Google News, Bing News RSS tìm báo khác, một phiên chromium (chữ
  bài, img lớn, chụp table/figure/canvas), `anh_bai`, Wikimedia Commons khi < 5
  ảnh; vẫn thiếu hoặc không tấm nào làm bìa được thì hai vòng bù theo độ liên
  quan giảm dần — `image_brand.py` tìm **ảnh thương hiệu** (trụ sở/campus của
  chính hãng trong tin, LUAT_ANH §1.2d, vào được slide thân), rồi
  `image_concept.py` tìm **ảnh khái niệm** (cờ nước được nhắc, rack datacenter…
  LUAT_ANH §1.2c, chỉ bìa/hero); dHash bỏ trùng; phân loại chart/mặt người/tỉ lệ; cắt sẵn 1:1 và 4:5 qua
  `crop_ti_le`; cặp ghép cùng tone; tư liệu. Kết quả
  `state/<brand>/chuan_bi/<id>/xong.json` + `bang_anh.png`.
- Tin **chuyển sang Kite vì thiếu ảnh** (engine tự chuyển khi 0 ảnh, hoặc Ông Chủ
  bấm "Gửi Kite"): những ảnh thật engine đã tìm được **vẫn phải vào bộ của Kite,
  và phải có ở body** — `kite_chuan_bi.hinh_phai_dung` là một nguồn cho cả brief
  lẫn cổng `kite_nop` (LUAT_ANH §1.2e). Trừ **ảnh khái niệm**: §1.2c cấm nó ở
  slide thân, nên ép nó vào body là hai cổng đá nhau — nó về bìa qua
  `hinh_hero`, và `kite_nop` chặn nếu nó xuất hiện ở slide khác slide 1.
- **Bìa của Kite luôn phải là ảnh thật** (LUAT_ANH §1.2f, Ông Chủ 10/09/2026:
  *"không chấp nhận việc dùng vector ở hero slide"*). Slide 1 không có `image`
  là `kite_nop` chặn — **kể cả khi engine giao 0 ảnh**: "không có ảnh" là thất
  bại của vòng tìm ảnh, không phải một trạng thái hợp lệ của tin, nên nó phải
  nổ ra chứ không được lặng lẽ thành một bộ slide vẽ tay.
- Và nước đi đầu là **tìm lại**, không phải báo hỏng: `kite_chuan_bi` không được
  thừa kế `xong.json` đã thất bại của vai cũ (`anh_chuan_bi.chay` trả thẳng tệp
  cũ, còn task body của Kite không có `--lam-moi`), nên `bao_dam_co_bia` tự chạy
  lại vòng tìm ảnh một lượt khi chưa có tấm nào lên bìa được. Vai cũ cần ~5 ảnh
  mới đủ, Kite chỉ cần một tấm — "vai cũ không đủ" không có nghĩa Kite không đủ.
  Hết đường thì `dem_vong_loi` đẩy lên Ông Chủ qua `kanban_block`.
- Mỗi vai một cặp **brief + nop** đọc chung `xong.json`: `dre_chuan_bi/dre_nop`,
  `ethan_chuan_bi/ethan_nop`, `kite_chuan_bi/kite_nop`, `miles_chuan_bi/miles_nop`.
  Nop chạy cổng chặn của renderer, gửi kèm nút duyệt, ghi
  `drafts/<id>.ban_giao.md` và `da_dung.json` (để "Làm lại" bắt buộc đổi
  ảnh/hook/tone). `--khong-gui`/`--out`/`--khong-push` để thử.
- Bốn vai theo chat cùng mẫu, khoá là message_id/URL: `gin_*`, `itachi_*`,
  `cape_*`, `ada_*`. `bob_submit.py` là một lệnh trọn gói (lấy ảnh → nhìn → đóng
  khung → gửi).
- `scan_prepare.py --vai finn|nova|vera` + `scan_submit.py`: ba vai đi tìm tin
  nhận danh sách ứng viên một dòng mỗi tin + mục BẮT BUỘC + khung tệp nộp; nop
  ghép manifest, kiểm bắt buộc, viết báo cáo, gửi topic. `--khong-co` gửi dòng
  "hôm nay không có gì"; `--thu` không ghi manifest thật.
  **Một lần quét = một báo cáo**: bản mất tin (`[bo qua]`) hay tiêu đề tiếng
  Việt mất dấu bị `loi_chan_gui` chặn, rc=1, vai sửa tệp nộp rồi chạy lại — chạy
  lại mà vẫn gửi thì topic có nhiều bản gần giống nhau và chỉ bản cuối reply
  được (sự cố Vera 12/09/2026). Gửi xong, `quet_nop` ghim đường dẫn manifest vào
  `state/<brand>/bao_cao_mid.<vai>.json` để lệnh chọn số đọc đúng bản đã gửi.
- Skill `ai-background` và bộ retouch/blend của Gin/Itachi **chờ GPU** (sửa/sinh
  ảnh bằng CPU quá nặng) — không phải lỗi. Script sinh nền chưa được viết; skill
  mô tả sẵn hợp đồng để khi có GPU thì bắt tay vào đúng chỗ. Tới lúc đó hai vai
  chỉ xoá chữ + vẽ tại chỗ/deck.

### Thêm một vai mới

Trước 09/09/2026 việc này đụng tám chỗ và quên một chỗ là hỏng **câm**: "kites"
thiếu trong `TEN_SANG_CAP` làm cả lệnh chọn bị từ chối rồi gửi nhầm cho Finn
(06/09), sidecar ghi slug cũ làm task nằm `ready` hai ngày (01/09). Từ khi có
`role.py` thì còn **ba bước mã** (dưới) cộng **ba bước cấu hình** không dẫn xuất
được từ mã: `hermes/profiles/<brand>/<slug>.SOUL.md`, một khoá trong
`state/topics.<brand>.json` (id topic Telegram), và `hermes/profiles/cau_hinh_that.yaml`.
`chat_router.TOPIC_PROFILE` tự dẫn xuất từ `role.py` (từ 09/09/2026, audit lượt 2),
và `tests/test_vai.py` giữ mọi bảng dẫn xuất khớp bản đăng ký. Bước 1 sinh lại
mọi bảng cũ:

1. **Một dòng trong `role.py`** — `Vai(slug, ten, go=…, slug_cu=…, renderer=…,
   nhan_anh=…, viet=…, anh_toi_thieu=…)`. `slug` phải trùng **tên thư mục
   profile thật** trong `HERMES_HOME`, nếu không `chuan_assignee` từ chối tạo
   task. `go` là mọi chữ Ông Chủ có thể gõ khi chọn tin (kể cả số nhiều kiểu
   "kites"); `slug_cu` chỉ dành cho slug cũ còn nằm trong sidecar trên đĩa.
   `anh_toi_thieu` là số ảnh thật tối thiểu để vai dựng được sản phẩm — engine
   ảnh dùng chung đọc nó qua `so_anh_toi_thieu()`, đặt sai thì bài bị báo thiếu
   ảnh oan (sự cố 10/09/2026). `VAI_ANH`, `TEN_SANG_CAP`, `TEN_VAI_ANH`,
   `VAI_CAROUSEL`, `VAI_EDU`, `SLUG_CU`, `TEN_HIEN` tự có theo.
2. **Một cặp `<vai>_prepare.py` / `<vai>_submit.py`** — cả hai đọc chung
   `xong.json` của engine, không tự chuẩn bị lại. Chép cặp gần nhất về kiểu ảnh
   (`dre_*` cho nhiều slide, `ethan_*` cho thẻ bìa, `kite_*` cho vector).
3. **Một SOUL** trong `hermes/profiles/<brand>/<slug>.SOUL.md` (hoặc `shared/`
   nếu dùng chung cả hai brand), rồi `sync_hermes.py --ra-hermes` đẩy sang
   home đang chạy.

Còn phải làm tay: một topic trong `state/topics.json` (id do Telegram cấp) và
`task_bodies.py` nếu vai cần khuôn body riêng. `tests/test_vai.py` giữ cho các
bảng dẫn xuất không lệch bản viết tay cũ.

## Tệp

**Dựng ảnh**

- `card.py` — thẻ đơn. Kiểu `quote` (mặc định): pull-quote trong khung hai góc
  ngoặc, dòng nguồn `--attrib` canh giữa. Kiểu `tran`: tiêu đề một câu trong
  **khung chữ nhật nét** (Ông Chủ chốt 07/09/2026 — trước đó là "không một nét
  nào"). Cả hai kiểu dùng chung **một** lớp ảnh (`_lop_anh`): nền là bản cover
  làm mờ, lớp sắc full bề ngang đặt sát trên, mép dưới tan dần — **không còn
  màu nền đặc** ở đâu. Không màn tối; màu chữ/khung/tên kênh đo theo từng dải
  nền của chính tấm ảnh. Spec chữ và bố cục:
  [STYLE_TEXT_SPEC.md](STYLE_TEXT_SPEC.md).
- `carousel.py` — carousel nhiều slide (Dre): ảnh 1:1 hoặc 4:5 phủ kín thẻ, chữ
  ở đáy chìm vào ảnh, ra `<id>.png` + `<id>_2.png`… đúng khuôn album của
  `draft_write.py`. Dùng lại helper của `card.py`.
- `render_edu.py` — renderer của Kite: carousel tech-editorial **art vector gốc**
  bằng HTML/CSS/SVG, chụp bằng Chromium headless. Spec JSON, **7 kind**:
  `cover` / `statement` / `steps` / `loop` / `figure` / `bars` / `cta`. Không ảnh
  thật. Cần `playwright install chromium`.
- `deck.py` — editorial-deck của Itachi, dựng lại carousel nguồn sang tiếng Việt.
- `crop_ratio.py` — cắt ảnh về **1:1 hoặc 4:5**. Chỉ cắt chiều cao; ảnh gốc ngang
  (≥1.4) đòi cắt bề ngang thì dừng, vì bề ngang của chart/bảng là nội dung. Ép
  bằng `--cat-ngang`, chỉ cho ảnh người/sản phẩm không có chữ.
- `arxiv_figures.py` — bóc **hình thật trong paper** (Figure 1, 2…) thẳng từ PDF:
  định vị khối chữ `Figure N:`, lấy vùng đồ hoạ ngay trên nó, render nét ở
  ~2200px. Chạy cho mọi tin arxiv/PDF, ảnh mã cao điểm nhất — Figure 1 là tấm để
  Kite làm **hero bìa**. Chỉ hình, **không bảng** (xem `§BẢNG` đầu tệp).
  Cần `pymupdf`.
- `arxiv_cover.py` — đường cuối cho bài arxiv: không còn ứng viên ảnh nào thì chụp
  trang đầu paper (tên công trình + tác giả). Cần `pymupdf`.
- `image_brand.py` — tin về **hãng lớn** mà kho ảnh mỏng thì đi lấy tư liệu
  của chính hãng, bốn loại theo độ "là ảnh chụp thật" giảm dần: 🏢 **cơ sở**
  (tìm tên tệp Commons + `P18` Wikidata), 👤 **chân dung founder/CEO**
  (`P112`/`P169`, kèm tên nên khai được `nhan_vat`, bỏ người đã thôi chức),
  📊 **bảng xếp hạng** có model của hãng (mượn `ranking.py`, chỉ nhận ảnh chụp
  thật), 🔖 **thẻ logo** (`P154` trên nền trơn, đường cuối). Lấy **mọi** hãng
  watchlist tin nhắc tới (tối đa 3), không phải chỉ tên riêng đầu tiêu đề. Lọc
  theo biên giới từ + bảng nhiễu (Amazon → rừng, Apple → quả táo). Vào được
  slide thân và đếm đủ — khác ảnh khái niệm. LUAT_ANH §1.2d.
- `image_concept.py` — tin không có ảnh riêng thì tìm **ảnh khái niệm** trên
  Commons theo nước/chủ đề (cờ, rack datacenter, wafer, toà án). Nhãn 🧭, chỉ
  bìa/hero, cả chùm đếm là một. LUAT_ANH §1.2c.
- `ranking.py` — ảnh cho **tin xếp hạng**: tách tên model từ tiêu đề, đi qua
  registry **19 nguồn**, mở browser tìm hàng chứa model, chụp cửa sổ top-N,
  khoanh vàng hàng đó, đọc thứ hạng. Chụp bằng **khung mobile trước** (414px ×
  DPR 3 ≈ khổ thẻ 1200px nên chữ gần như không co); 8 nguồn đã đo là mobile
  không dùng được thì mang `khung: "desktop"` kèm lý do ngay trong `NGUON`.
  Không ra thì thẻ dự phòng. Ảnh mang mã `XH`.
- `capture_chart.py` — chụp chart/bảng benchmark theo luật *full chiều rộng trước,
  chiều cao xét sau*: đo `scrollWidth` thật, nới khung cho vừa rồi mới chụp ở
  DPR 2; thiếu bề ngang thì dừng. Cần `playwright` + chromium.
- `image_rules.py` + `LUAT_ANH.md` — **một nguồn sự thật** của luật ảnh, dùng chung
  cho mọi vai TẠO ra ảnh (Ethan, Dre, Kite). Đừng chép luật vào SKILL của vai.
  Gin/Itachi chỉ sửa trên ảnh gốc nên không áp bộ này.

**Đi tìm tin**

- `scan_sources.py` / `article_sources.py` — quét nguồn của Finn và research lúc chọn
  tin; tự giải mã link Google News (`giai_ma_gnews`).
- `scan_models.py` — quét của Nova: 23 bảng xếp hạng, mục "RA MẮT THEO BẢNG CHẤM
  ĐIỂM" (mỗi model báo đúng một lần nhờ `aa_da_bao` trong `models_seen.json`).
  **Bảng đăng ký ở `model_boards.py`** — một dòng cho một bảng (khoá, nhãn, tiêu
  đề in, link, lấy hàng từ đâu). Trước 07/09/2026 thêm một bảng phải khai ở
  **sáu** chỗ trong hai tệp; quên một chỗ là loại lỗi không báo gì cả (mất bảng
  trong báo cáo, hoặc mục bắt buộc ra link rỗng). Nay năm chỗ dẫn xuất từ đó;
  chỉ khối `bang_so` trong `main` còn viết tay, và `main` tự đối chiếu nó với
  bảng đăng ký.
  Bảng chết (BFCL, LiveCodeBench, Aider, BigCodeBench, Papers With Code) bị loại
  có chủ đích — xem nhật ký sự cố.
- `manifest_write.py` (Nova/Vera) / `manifest_build.py` (Finn) — ghi manifest đánh
  số vào `state/<brand>/` qua `env_load.state_dir()`, cùng chỗ approve_service
  đọc. Phần cơ học dùng chung nằm ở **`manifest_common.py`**: chọn theo `k`, dọn
  `summary_vi`, đánh số, không ghi đè bản đã có, chốt danh sách bắt buộc, dựng
  báo cáo. Trước 07/09/2026 mỗi script tự viết lại và **đã lệch** — cổng bỏ
  em-dash chỉ có ở nhánh Finn, dù lý do có nó ("em-dash lọt xuống tận caption")
  đúng y hệt với Nova/Vera. Cái *không* gộp là cổng báo title mất dấu: title của
  Nova/Vera do chính vai viết bằng tiếng Việt, còn title của Finn lấy từ
  `candidates.json` tức tiêu đề gốc báo nước ngoài.
- `required.py` — **danh sách BẮT BUỘC**: script quét thấy là phải đưa, vai không
  có quyền bỏ. Script ghi manifest tự thêm mục thiếu kèm ghi chú "vai bỏ sót" và
  xoá mục đã đưa. Finn và Vera chọn tin bằng **số thứ tự `k`**, không chép URL.
- `material.py` — bóc chữ bài để đối chiếu số liệu và tên người vai khai.

**Duyệt và đăng**

- `approve_service.py` — dịch vụ nền nghe nút duyệt và lệnh chọn số. Mặt tiền
  mỏng; phần thân nằm ở `approve_base` / `approve_dispatch` / `approve_pick` /
  `approve_post` / `approve_chat` / `approve_command`. Mọi tin nhắn vào đều có log
  (`state/<brand>/approve.log`, xoay vòng 5 MB×3) theo nhãn
  `vao → route → chat/chon/lenh → tele`, và mọi nhánh kết thúc bằng một tin trả về.
  Lệnh chọn số còn báo **ngay khi nhận** (`_bao_da_nhan`, kèm tiêu đề từng số)
  trước khi vào việc — `create_pair` mất tới 180 giây một tin, đo thật 157 giây
  im lặng ngày 11/09/2026.
- `chat_router.py` — định tuyến chat Telegram → hermes CLI theo topic (blog).
- `draft_write.py` — ghi bản nháp + album đúng khuôn tên tệp.
- `publish.py` — gửi text/ảnh lên Telegram, hỗ trợ topic.
- `moat_publish.py` — đẩy bài đã duyệt sang moat và hỏi trạng thái đăng social.
- `blackboard.py` — bảng đen kanban (xem dưới).
- `write_log.py`, `env_load.py` — log và nạp môi trường dùng chung.

**Đo đạc**

- `monitor_9router.py` — nhật ký 9router theo ngày
  (`state/9router/nhat_ky/9router_<ngày>.md|json`): req/prompt/cache%/$ theo model,
  theo khoá API, theo giờ VN, model lạ, cache thấp, fallback thật, lỗi, phiên
  rỗng, **$ theo vai** và $/bài theo brand. Ada đọc qua `tai(ngày)`.
- `journal.py` + `journal_web.py` — nhật ký ngày và trang web cổng 9130.
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
  Đồng bộ bằng `sync_hermes.py` (`--ra-hermes` / `--ve-git`).
- `tests/` — chạy thẳng, không cần mạng: **`tests/chay.sh`** (thoát khác 0 nếu
  bất kỳ tệp nào hỏng; `tests/chay.sh cong_chan` để lọc). Đừng dùng vòng
  `for f in tests/*.py; do …; done` nữa: nó trả mã thoát của tệp **cuối cùng**,
  nên một tệp hỏng ở giữa vẫn "thành công".
  `test_cong_chan` giữ các cổng chặn và đường báo lỗi của nop, `test_cong_thuan`
  giữ mấy hàm thuần đã từng hồi quy im lặng (lệnh chọn số, `draft_id` ≤ 55 byte,
  cắt tin nhắn dài), `test_ham_thuan` giữ các hàm không ai canh mà quyết định
  nhiều (`co_tieng_viet`, `_url_hop_le`, `route`, `_HangFIFO`, `gom_trung`,
  `tong_hop` của nhật ký 9router),
  `test_soat_cron` giữ người canh cuối cùng (job soát cron — nó im thì không
  còn ai), `test_the_anh` soi chính tấm ảnh ra (mảng nền đặc = một dải pixel
  giống hệt nhau, đếm được), `test_spec_dre` giữ cổng spec carousel của Dre
  (36 nhánh, phần lớn là luật Ông Chủ đặt sau một sự cố thật),
  `test_manifest` giữ phần cơ học của manifest — thứ Ông Chủ đọc rồi **trả lời
  bằng số**, nên sai ở đó không ra lỗi mà ra một danh sách nhìn bình thường
  nhưng số "2" trỏ tới bài khác — `test_caption` giữ cổng caption của Miles
  (thứ cuối cùng trước hàng duyệt, 14 cổng thuần), `test_spec_ethan` /
  `test_spec_kite` giữ hai cổng spec còn lại (cùng fixture manifest với
  `test_spec_dre`; Kite tắt YuNet trong test), `test_khai_niem` giữ từ khoá,
  bộ lọc Commons và nhãn của ảnh khái niệm, và `test_tai_lieu` chặn tài liệu
  trôi khỏi mã. Ba cổng dùng chung của Dre/Ethan nằm ở `nop_chung`
  (`can_anh_xep_hang`, `anh_khong_lien_quan`, `kiem_da_dung_nhieu`) — trước
  07/09/2026 mỗi vai một bản, và đã lệch một lần (Ethan không đọc cờ
  `lien_quan`).
  Đồ dùng chung của test nằm ở `tests/tam.py` — **không** phải tệp test,
  `chay.sh` chỉ chạy `test_*.py`.

  **Hàm chạy thật thì đối chiếu bằng VẾT.** Bảy hàm không chạy offline được
  (duyệt ảnh, router Telegram, tạo cặp task, moat, và ba hàm lái Chromium) đã
  được tách 07/09/2026 bằng cách thay mọi cạnh I/O — `call` Telegram, kanban,
  `subprocess`, `httpx`, Playwright — bằng bản **ghi vết** trả dữ liệu định sẵn,
  rồi chạy 7–26 kịch bản qua bản cũ (snapshot `git show HEAD:`) và bản mới, so
  vết + tệp + giá trị trả về. Playwright giả nằm ở scratchpad phiên audit
  (tệp fake_pw trong scratchpad, ngoài repo): `page.evaluate` chọn kết quả theo
  chuỗi JS, `goto` trả
  status theo kịch bản. Cách này đã bắt được ba lỗi tách trước khi commit
  (biến cục bộ của hàm cũ, import cục bộ, một `def` bị lát cắt nuốt).

  **Test không được đụng vào state thật.** Hai chỗ từng đụng: `assemble` gọi
  thẳng `emoji_deck.next_emoji` (mỗi lần chạy suite đẩy sổ emoji của Jean đi ba
  bước) — nay truyền `lay_emoji=`; và `luat_anh._so_da_dung` bị gán đè không trả
  lại, khiến `kiem_da_dung` trả rỗng vô điều kiện trong mọi test sau đó — nay
  qua `_so_tam()`. Thêm test mới thì giữ đúng hai lối này.
- `check_hermes.py` — kiểm các chỗ lệ thuộc nội bộ hermes (xem mục dưới).
- `requirements.txt` — venv dùng chung với hermes nên `hermes update` có thể làm
  mất `pymupdf`; cài lại bằng `venv/bin/pip install -r requirements.txt`.
- `cai_dat.sh` — **dựng máy mới, chạy lại bao nhiêu lần cũng được**. Ba bước thật
  (pip, `playwright install chromium`) rồi kết thúc bằng `check_env.py`.
  Trước đây các bước này nằm rải trong comment của `requirements.txt` và
  `bob_submit.py`, thiếu một bước là hỏng **câm** (thiếu cv2 → cổng mặt người tự
  tắt). Font và model YuNet đã nằm trong git, không phải tải. `--thu` xem trước,
  không cài gì. **Không còn bước Node nào** từ 09/09/2026 (A6).
- `check_env.py` — chặn đầu: cv2, model YuNet, Chromium, `OPENAI_API_KEY`,
  `TELEGRAM_BOT_TOKEN`. Mỗi mục tự bọc lỗi nên một mục hỏng không giết cả script.

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
`blackboard.py` dùng đúng các viên gạch của nó và dựng đồ thị theo tiến trình thật của bài:

```
thẻ gốc "Bài: …"   (done ngay; assignee `ban_bien_tap` — không ai nhận việc; là bảng đen)
  └─ task Dre        parent = gốc              ← tạo khi Ông Chủ chọn số
       └─ task Miles parent = [Dre, gốc]       ← tạo khi Ông Chủ bấm "Duyệt ảnh" (cổng giữ nguyên)
```

- Vai **không nhắn nhau**. Mỗi vai kết thúc bằng `kanban_complete(summary, metadata)`; hermes tự
  đưa summary/metadata đó vào context task con ("Parent task results"), nên Miles thấy Dre.
  `dre_submit.py` / `miles_submit.py` **tự ghi** bàn giao có cấu trúc lên bảng đen (comment
  `[swarm:blackboard] {…}` trên thẻ gốc) và in dòng `[metadata]` để vai dán vào `kanban_complete`.
- Task **Ada "Soát"** từng nối sau Miles (05/09 sáng) đã **bỏ 05/09 chiều**: một task LLM mỗi bài
  để kiểm bốn điểm mà `caption_check.py` giờ làm bằng code (số trong caption phải có trong tư liệu,
  cụm cấm, độ dài, tiếng Việt). Ông Chủ vẫn là người bấm; push CLI vẫn lưu `tg_card_message_id`
  để Ada đối chiếu bài với thẻ khi phân tích.
- Nhìn toàn chuỗi: `hermes kanban show <thẻ gốc>` hoặc dashboard — quan hệ cha-con nằm trong
  `task_links`, bàn giao trong `task_comments`/`task_runs`, không trôi như chat.
- Bảng đen là lớp thêm, **best-effort**: `blackboard.py` lỗi thì task vẫn tạo như cũ, chỉ mất bảng
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
- `nhat-ky-web` — `journal_web.py` cổng **9130**: `/` danh sách ngày,
  `/9router/<ngày>` bảng đầy đủ, `.json` số thô. Tin Telegram 6h sáng (chỉ brand
  blog gửi, tránh trùng) là tóm tắt req · $ · cache% · fallback + $/bài + link.

## Cron

Mỗi brand một tệp riêng — **không** còn `~/.hermes/cron/jobs.json` gộp chung:
`~/.hermes-blog/cron/jobs.json` (6 job) và `~/.hermes-dcgr/cron/jobs.json` (5 job).

- `finn-daily-scan` (blog), `nova-daily-scan` (blog), `vera-daily-scan` (dcgr)
  — **05:00 VN** (22:00 UTC). Ba job này nằm ở **hai container khác nhau**, nên
  chỉ finn và nova là nối tiếp nhau (`max_in_progress: 1` của blog); vera chạy
  song song ở dcgr. Thân ba script là **một** tệp
  `hermes/scripts/quet_daily_scan.sh <vai>`; `finn_daily_scan.sh` và hai tệp kia
  chỉ còn 7 dòng gọi sang đó, giữ tên cũ để khỏi phải sửa job cron trên máy chủ.
- `daily-log` — 06:00 VN, dựng nhật ký ngày hôm trước + chốt nhật ký 9router
  (`monitor_9router.py --gui` → topic `ada`).
- `model-watch` — `*/30 0,4,5,10-23 * * *`, tức **tắt 08:00–10:59 và
  13:00–16:59 VN**, đúng khung giờ chọn số buổi sáng. Model chết lúc 8h thì 11h
  mới có cảnh báo. Nếu không cố ý thì đổi về `*/30 * * * *` trên máy chủ
  (`hermes cron`), tệp `hermes/cron/jobs.*.json` chỉ là bản chụp.
- `moat-publish-watch` — 5 phút/lần, hỏi moat xem bài đã lên social chưa; im
  lặng khi không có gì mới, bỏ theo dõi một bài sau 7 ngày.
- `soat-cron` — **07:00 VN** ở blog (`0 0 * * *`), **07:10 VN** ở dcgr
  (`10 0 * * *`). Chạy sau ba job quét và `daily-log` nên soi được kết quả buổi
  sáng đó. Mỗi lần chạy soát **cả hai home**, không chỉ home của mình — xem mục
  dưới.

**Job hỏng thì biết bằng cách nào.** Hermes chỉ coi một job là lỗi khi script
thoát khác 0. Trước 06/09/2026 mọi script đều thoát 0 kể cả khi hỏng: ba script
quét in `LOI`/`CANH BAO` rồi kết thúc bình thường, còn `nhat_ky_daily.sh` kết
bằng `| tail -3` (trả mã của `tail`) và một `echo`. Nghĩa là nhật ký chết cả
tuần vẫn hiện `last_status: ok`, `failure_streak: 0`. Nay cả bốn script thoát
khác 0 khi hỏng, nên `failure_streak` trong `~/.hermes-<brand>/cron/jobs.json`
và dashboard là chỗ đối chiếu thật.

**Ai đọc con số đó.** `audit_cron.py` (Ông Chủ chốt 07/09/2026), chạy 07:00 VN.
Nó không đổi `deliver` — đổi `deliver` là đổi cả đường ra của lần chạy **thành
công**, mà `moat-publish-watch` chạy 288 lần/ngày. Nó đọc thẳng
`<home>/cron/jobs.json` của **cả hai brand** rồi nhắn vào topic `ada` khi
thấy một trong sáu thứ:

| Dấu hiệu | Bắt được cái gì |
|---|---|
| `failure_streak > 0`, `last_status != ok`, `last_error` | job có chạy và nổ |
| `last_delivery_error` | job chạy xong nhưng kết quả không tới ai |
| `enabled: false` / `state: paused` | job bị tắt hoặc bị treo — **không sinh lần chạy nào**, nên `failure_streak` đứng ở 0 mãi mãi |
| `next_run_at` nằm lại quá khứ > 15 phút | scheduler không nổ |
| `ticker_heartbeat` cũ hơn 200s | ticker chết → **mọi** job của home đó đóng băng (ngưỡng lấy đúng của `hermes cron status`: `TICKER_INTERVAL_SECONDS * 3 + 20`) |
| `ticker_last_success` tụt xa `ticker_heartbeat` | ticker còn sống nhưng tick nào cũng hỏng |

Ba dòng giữa là lý do phải có job soát thay vì chỉ trông vào `failure_streak`:
chúng **không sinh một lần chạy nào**, nên không cơ chế nào dựa trên kết quả
chạy thấy được.

Chạy ở **cả hai container** (lệch 10 phút) — đặt một bản thì ngày container đó
chết là không còn ai báo, đúng cái lỗ hổng cần bịt. Hai lần chạy không sinh hai
tin: `state/soat_cron.json` (gốc `state/`, dùng chung) ghi bộ vấn đề đã báo
trong ngày, container thứ hai thấy y hệt thì im. Hết vấn đề sau một ngày có
vấn đề thì báo **một** dòng "cron sạch" rồi thôi.

Đăng ký trên máy chủ (tệp `hermes/cron/jobs.*.json` chỉ là **bản chụp**, sửa nó
không tạo được job):

```bash
HERMES_HOME=$HOME/.hermes-blog ~/hermes-agent/venv/bin/python -m hermes_cli.main \
  cron create "0 0 * * *" --name soat-cron --script soat_cron.sh --no-agent --deliver local
HERMES_HOME=$HOME/.hermes-dcgr ~/hermes-agent/venv/bin/python -m hermes_cli.main \
  cron create "10 0 * * *" --name soat-cron --script soat_cron.sh --no-agent --deliver local
```

**Bổ trợ, chưa bật:** hermes có `--failure-deliver` — đường ra **chỉ dùng cho
thông báo hỏng**, cùng ngữ pháp với `--deliver` và nhận cả
`telegram:<chat_id>:<thread_id>`, tức bắn được thẳng vào một topic. Đặt nó cho
ba job quét sẽ cho cảnh báo **tức thì** mà lần chạy thành công vẫn im. Nó không
thay được `soat-cron` (nó chỉ báo được những lần thật sự có chạy), mà đi cùng.

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
| `state/soat_cron.json` | `soat_cron` (brand nào chạy trước) | brand kia | `soat_cron` của brand kia |

**Quy ước gốc state:** `state/<brand>/` cho mọi thứ thuộc về một brand;
`state/` gốc **chỉ** cho thứ chung cả máy (nhật ký 9router, khoá). Sổ theme của
Kite từng nằm sai chỗ ở gốc — Kite chạy cả hai brand nên bộ "4 bộ gần nhất" trộn
lẫn, một bộ dcgr vừa dùng theme X là bộ blog kế tiếp bị đẩy sang theme khác mà
không có lý do nào. Đã chuyển về `state/<brand>/` ngày 06/09/2026.

**Tệp nào có nhiều tiến trình cùng ghi thì phải ghi qua `env_load.ghi_json`**
(tmp + `os.replace`), không `write_text` thẳng — đó là `meta.json` (approve,
engine nền, bảng đen), `drafts/<id>.json` (draft_write, duyet_bai, cron moat) và
mọi sidecar của `duyet_*`. `write_text` cắt ngắn tệp cũ trước khi ghi nội dung
mới, nên hai tiến trình trùng thời điểm để lại một sidecar cụt và mọi người đọc
sau đó ném `ValueError` — bài kẹt vĩnh viễn mà không ai biết. Tệp chỉ một tiến
trình ghi trong thư mục làm việc riêng (`xong.json`, `spec.json`, `vung_ocr.json`)
vẫn `write_text`, và đó là chấp nhận được.

## Sau mỗi `hermes update`

`content-team` đọc vài thứ **bên trong** hermes mà không có API nào bảo đảm:
định dạng in ra của `hermes chat -Q`, schema thô của `kanban.db`, và một hàm
private của `kanban_swarm`. Chúng đổi lúc nào cũng được, và đổi thì hỏng lặng lẽ
— sự cố `-z` nuốt `--continue` (mọi vai mở phiên trắng, "không nhớ gì") mất mấy
ngày mới lộ ra. Chạy ngay sau khi cập nhật:

```bash
venv/bin/python check_hermes.py
```

Chỉ đọc, không tạo gì. Thêm `--day-du` nếu muốn một lượt chat thật (tốn LLM).
Kèm theo: `venv/bin/pip install -r requirements.txt` (venv dùng chung nên
`hermes update` có thể làm mất pymupdf), và
`venv/bin/python sync_hermes.py --kiem-upstream` để xem hermes đổi gì trong
plugin kanban kể từ lần port cuối.

## Model

**Cả 20 profile** chạy chính bằng **combo `DS-v4Flash` của 9router** (ba route
v4-flash: DeepSeek trực tiếp, xKiro, aellm — DeepSeek trực tiếp xếp trước vì
cache là của từng nhà cung cấp). Ada cũng vậy — bản README trước ghi Ada giữ
deepseek-reasoner, điều đó không còn đúng từ khi đổi sang combo (bản chụp
`hermes/profiles/cau_hinh_that.yaml` là chỗ đối chiếu).

`agent.reasoning_effort`: **`none`** cho mọi vai làm nội dung, vì model deepseek
đốt hết ngân sách token vào suy luận rồi trả về **rỗng** (đo thật: 3/24 lần trên
v4-pro, tái hiện y hệt trên v4-flash; tắt suy luận: 0/24 lần rỗng, nhanh gấp 3).
Hai ngoại lệ: **Bob** đặt `medium` (việc duy nhất là nhìn một ảnh chọn mood),
**Ada** không đặt (dùng mặc định của hermes).

Đừng tin bảng model chép trong tài liệu — hỏi thẳng máy chủ bằng lệnh ở đầu tệp
này. Lịch sử đổi model, số đo giá, và ba điểm mù của 9router: xem
[NHAT_KY_SU_CO.md](NHAT_KY_SU_CO.md).

**Hai nguyên tắc bắt buộc khi dùng nhiều model:**

1. **Phải có giám sát model.** Hermes fallback im lặng hoàn toàn — đặt model
   chính thành model chết, agent vẫn trả lời bình thường, không một dòng báo.
   Cần cả hai lớp: `model_watch.py` (model còn sống không) và
   `monitor_9router.py` (model nào **thật sự** được gọi).
2. **Ghim mỗi hội thoại vào một model; chuyển tầng thì chuyển ở ranh giới task.**
   Cache là per-model, mỗi lần lật là mất sạch prefix đã cache. Cột `cache%`
   trong nhật ký ngày chính là thước đo: tụt cache nghĩa là đang lật model.

## Lưu ý

`.secrets.env` chứa bot token Telegram và khoá moat — **không bao giờ commit**.
Chỉ một tiến trình được long-poll một bot token; `approve_service.py` giữ vai trò đó.
