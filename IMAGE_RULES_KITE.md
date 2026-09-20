# LUẬT ẢNH CỦA KITE (`carousel-edu`, `render_edu.py`)

**LOW-182 (16/09/2026):** Ông Chủ đảo ngược quyết định 04/09/2026 ("làm một bộ
chung thay vì mỗi vai một bộ") — tách tài liệu dùng chung `IMAGE_RULES_KITE.md`
thành **ba bản riêng**, mỗi vai làm ảnh (Ethan/Dre/Kite) một bản, bắt đầu từ
đúng nội dung bản chung tại thời điểm tách. Đây là **bản của Kite** — sửa ở
đây không còn tự động áp sang bản của Ethan/Dre nữa.

Toàn bộ nội dung dưới đây là **lịch sử** dẫn tới bộ luật hiện tại của Kite
(nhiều sự cố thật, xem từng mục) — giữ lại để không mất ngữ cảnh, nhưng từ
16/09/2026 các bảng so sánh "cả ba vai" / "cổng dùng chung" chỉ còn đúng cho
tới ngày tách; đọc chúng như ảnh chụp một thời điểm, không phải trạng thái
hiện tại của hai vai kia.

**Đường cắt — một câu, vẫn còn đúng cho riêng Kite:**

> *"Ảnh này có được dùng không"* → nằm ở đây (và thành cổng chặn trong
> `image_rules_kite.py`).
> *"Đặt nó lên khung thế nào"* → nằm trong `render_edu.py`.

---

## 0. Nguyên tắc trên hết: KHÔNG BAO GIỜ tự vẽ minh hoạ

Vẽ ra là **bịa đặt**. Ảnh phải phản ánh đúng cái có thật trong nguồn. Không tìm
được ảnh thật thì **báo lại, không dựng** — Ông Chủ quyết định bỏ tin hay tự đưa
ảnh vào. Luật cứng, không có ngoại lệ nào ngoài mục 1.4 (hình & bìa paper arxiv).

Bỏ thẳng, không cần cân nhắc:

- **Ảnh AI tạo có người** (stock persona) và **ảnh người lạ lấy từ báo**.
- **Ảnh rò rỉ** (leak, chưa được xác nhận chính thức): rủi ro cả về độ chính xác
  lẫn bản quyền. Tìm ảnh chính thức khác thay vào.

---

## 1. Tìm ảnh thật

> **AI làm việc này (rõ một lần, 06/09/2026).** Từ 04/09/2026 **vai không đi tìm
> ảnh nữa** — `image_prepare.py` tìm sẵn và brief chỉ đưa ra danh sách mã; vai
> chọn mã. Nên §1.1 → §1.4 dưới đây là **luật của engine**, và các lệnh CLI in
> kèm là **công cụ tay** để Ông Chủ hoặc người sửa code chạy lại một bước khi
> nghi ngờ — **không phải việc giao cho vai**. `task_bodies.py` cấm vai chạy
> chúng, và cấm đúng: chạy tay giữa chừng là đè lên kết quả engine.
>
> Đọc §1.2b trước nếu chỉ có thời gian đọc một mục: đó là hợp đồng thật đang chạy.

### 1.1 Luôn chạy `article_images.py` trước

Đừng tự đoán từ `image_url` trong task.

```bash
venv/bin/python article_images.py --tieu-de "<tiêu đề tin>" --link "<link gốc>" --json
```

Script lấy ảnh từ link gốc **và** từ các báo khác đưa cùng tin, lọc bỏ
logo/favicon/thẻ thương hiệu, đo kích thước thật rồi xếp hạng.

Vì sao phải tìm rộng: link Finn nhặt thường là trang tài liệu, và `og:image` của
nó là thẻ thương hiệu chung. Ví dụ thật: `api-docs.deepseek.com` trả
`deepseek-social-card.jpeg` cho mọi bài.

### 1.2 Trộn hai nguồn: official site + magazine

`article_images.py` fetch **tĩnh** — trang sản phẩm hiện đại (JS render) nó chỉ nhặt
được `og:image`, **bỏ sót hết screenshot UI thật**. Đừng kết luận "bài không có
ảnh" từ một lần chạy.

1. **Official / chính chủ**: mở bằng **browser thật** rồi lấy screenshot
   sản phẩm/hero từ DOM; video demo thì trích một frame bằng `cv2`.
2. **Magazine / bài review**: The Verge, TechCrunch, The New Stack,
   BetterStack, 9to5Google… thường embed screenshot UI thật, góc chụp khác,
   chú thích rõ. Dùng WebSearch tìm bài review rồi mở lấy ảnh. Lưu ý ảnh review
   hay dính **webcam mặt reviewer** ở góc — dính là vướng mục 6.

Không giới hạn ở ảnh nhúng trong đúng link gốc. Tin đủ lớn thường có nhiều ảnh
thật liên quan rải ở các bài khác: ảnh sự kiện góc khác, ảnh sản phẩm chính
hãng, trụ sở, logo (Wikimedia Commons, các báo cùng đưa tin).

### 1.2b Engine tự tìm rộng — không lấy hết ảnh của một URL

Ông Chủ 05/09/2026: *"designer gần như luôn né tránh việc tìm nguồn ảnh, toàn lấy
ảnh trong một URL, kể cả banner quảng cáo"*. Từ 04/09 vai không tìm ảnh nữa —
`image_prepare.py` tìm, vai chỉ chọn mã — nên luật này là luật của **engine**:

- Chỉ lấy ảnh **trong bài** (`article`/`main`); loại quảng cáo, widget, sidebar,
  nav/footer, placeholder, onboarding, logo — theo cả tổ tiên DOM lẫn src/alt.
- **Trần mỗi trang**: bài gốc ≤ 4 ảnh, báo khác ≤ 3. Một URL không lấp cả kho.
- Báo khác phải **cùng tin**: chung ≥ 2 từ đặc trưng với tiêu đề gốc (Google
  News trả cả bài bệnh thận vì cùng chữ "AI").
- **Mỗi ảnh được nhìn** (vision): một câu "ảnh là gì" + LIÊN_QUAN. Không liên quan
  → ❌, `dre_submit.py` chặn. Ảnh trắng, ảnh rỗng bỏ ngay khi tải.
- Đếm **thật**: chỉ ảnh dùng được *và* liên quan. **Thiếu → tìm rộng** (thêm báo
  đã lọc liên quan + Wikimedia Commons), nhìn và đếm lại. **Ảnh thương hiệu**
  (§1.2d) chạy cho **mọi tin có hãng trong watchlist**, đủ ảnh hay không. Vẫn
  thiếu sau đó → **ảnh khái niệm** (§1.2c) cho bìa/hero. Vẫn thiếu → brief nói
  thẳng "THIẾU ẢNH", vai gộp ý/giảm slide hoặc báo — **không nhồi rác cho đủ**.
- Brief ghi số **nguồn** của ảnh dùng được; bộ ≥ 4 slide mà chỉ một nguồn là dấu
  hiệu cần xem lại.
- **Trang công bố chính chủ của model** (LOW-21, Ông Chủ 11/09/2026: *"khi làm
  carousel từ một topic gốc, phải tìm tất cả ảnh liên quan chứ không phải chỉ tìm
  ảnh trong nguồn topic, đặc biệt là những thông tin liên quan tới benchmark của
  model"*). Tin nhắc tới một model của hãng trong watchlist thì engine **luôn**
  ghé trang công bố của hãng — không đợi thiếu ảnh, cùng lý do với §1.2d. Đường
  đi (`image_brand.announcement_page`, nối ở `fallback_rounds._extra_announcement_page`
  **trước** khi mở browser): Wikidata `P856` (website chính thức) → `/news/`,
  `/en/news/`, `/blog/`… hoặc RSS của hãng khi HTML chặn bot (openai.com) → khớp
  slug tên model đã tách (`ranking.extract_model`, bỏ hậu tố effort `-max`/`-high`,
  khoá ngắn nhất còn ≥ 2 mảnh để không khớp mọi bài của hãng). Trang đó vào
  `article_source_<id>.json` với `kind: "announcement"` (Miles cùng dùng), browser mở nó
  **trước** báo khác và lấy **4 ảnh** như bài gốc — chart benchmark ở đó là ảnh
  đắt nhất của tin model. Vì sao cần đường riêng: đo 11/09, trang
  `deepseek.com/en/news/deepseek-v4-1-flash/` có 4 chart 5148×2640… nhưng Google
  News không index nó và 13/14 báo đưa tin không link sang; engine cũ không có
  cách nào tới, Dre bị chặn "thiếu ảnh" với 5/8 tấm toàn logo + rack data center.
- **Truy vấn báo khác phải giữ tên model** (cùng LOW-21): tiêu đề Việt rơi về
  `article_sources._name_own_no_mark` thì token có gạch nối (`deepseek-v4.1-flash-max`)
  là **một** tên riêng, không xoá gạch rồi tách; Bing thử thêm bản bỏ gạch trước
  (`deepseek v4.1 flash max` → 6 báo, bản có gạch → 1).

### 1.2b2 Chụp chính trang nguồn ở khung mobile — nấc TRƯỚC ảnh khái niệm

Ông Chủ 06/09/2026, nhắc lại 12/09: *"vào trang nào chụp thì cũng hay duyệt theo
kích thước mobile, vì hình luôn đang ở ratio 4:5"* và *"có thể capture màn hình
mobile source gốc mà?"*. Trước 12/09 luật này chỉ sống trong `ranking.py` (trang
bảng xếp hạng) và §1.3 (tin model/xếp hạng), nên đường ảnh của **tin thường**
nhảy thẳng từ ảnh thương hiệu xuống ảnh khái niệm — tin *"AI giải toán giỏi, nền
toán học thì lệch chuẩn"* ra bìa là một tấm dây mạng phòng máy.

- **Khi nào**: sau vòng thương hiệu mà vẫn thiếu ảnh, **trước** vòng khái niệm.
  Khối lead là vật **thật** của chính tin; ảnh khái niệm thì không.
- **Chụp gì**: `capture_page.capture_lead_mobile` mở trang ở khung điện thoại
  (`browser_session.MOBILE_VIEWPORT` 414×896, DPR 3, UA iPhone — **một bản duy
  nhất**, dùng chung với `xep_hang`), clip **đúng khung ảnh hero** của bài —
  không kèm tít/byline. Ông Chủ 12/09 (sửa lại bản "khối lead" cùng ngày):
  *"dùng ảnh hero trong main article làm thumbnail cho hero slide, vì ảnh đó là
  chữ nhật ngang, nên nó hiển thị vừa vặn với nửa trên của hero slide"*.
- **Đặt lên bìa Kite thế nào** (`render_edu`, cùng ngày): ảnh full bề ngang neo
  dưới masthead, **nền là màu palette của theme** — *"blur toàn bộ tấm ảnh để làm
  nền cho hero slide CHƯA-BAO-GIỜ là việc được yêu cầu với Kite"*. Lớp mờ chỉ
  dành cho ảnh **dọc** kéo xuống quá vùng chữ (bảng xếp hạng): mờ phần dưới để
  title/subtitle hiện lên, bật/tắt theo dòng chữ đầu thật.
- **Bỏ nguồn khi**: trang là tường chặn bot (`browser_session.got_block` — không tìm
  cách vượt), hoặc không đo được tít lẫn ảnh lead. Thử tối đa 3 trang: bài gốc
  rồi các báo khác cùng tin.
- **Lớp nổi** (banner đồng ý cookie, popup) chỉ bị **ẩn khi chụp**; không bấm
  "Đồng ý", không bấm nút đóng — đọc một trang thì không được thay người dùng
  chấp nhận điều khoản của họ.
- **Được làm bìa**, khác chart của người khác: `classify` đọc ảnh chụp trang là
  "chart/screenshot" rồi dán *KHÔNG LÀM BÌA*, nhãn đó bị gỡ cho ảnh chụp nguồn —
  **trừ khi có mặt người**, lúc đó §6 vẫn đòi khai `subject`.
- **Không hỏi vision** "có liên quan bài không": đây là trang của **chính** tin.

### 1.2c Ảnh khái niệm: tin không có ảnh riêng thì tìm theo chủ đề, không bỏ

Ông Chủ 07/09/2026: *"trong resource gốc không có hình hoặc hình không đạt là bỏ
qua luôn. Nhắc tới Nhật thì tìm cờ hoặc bản đồ nước Nhật, Nhật đầu tư xây
compute thì lấy hình datacenter"*. Trước 04/09 Dre tự làm việc này bằng
web_search; từ kiến trúc 3 lớp vai không còn công cụ, nên nó là luật của
**engine** (`image_concept.py`, chạy trong `image_prepare.py`):

- **Khi nào**: sau vòng tìm rộng **và sau nấc chụp trang nguồn (§1.2b2)** mà vẫn
  thiếu ảnh, *hoặc* có ảnh mà không tấm nào làm bìa/hero được. Không chạy khi tin
  đã có ảnh riêng đủ dùng. Đây là nấc **cuối**, không phải nấc đầu: từ khoá sai
  thì cả slide nói sai chuyện (xem `\bhack` bắt nhầm "reward hacking", 12/09/2026).
- **Từ khoá**: nước/khối được nhắc → cờ đang bay; chủ đề → vật thể **chụp được**
  (data center → dãy rack, chip → wafer, chứng khoán → sàn giao dịch, chính
  sách → toà nhà quốc hội…). Bảng cố định trước, model text bù tới 3 từ khoá.
  Minh hoạ biên tập CÓ SẴN (vẽ tay/digital, kiểu The Economist) được dùng như ảnh
  chụp — §0 cấm *tự vẽ*, không cấm *dùng*; vẫn gạt icon/clipart/sơ đồ/logo (Ông
  Chủ 12/09/2026). Từ khoá LLM bị CẤM đề xuất phần cứng ngành AI (rack, datacenter,
  GPU, chip, robot) khi tin không nói về phần cứng — "tin nào cũng AI" không phải
  lý do ra phòng máy.
- **Nguồn**: chỉ Wikimedia Commons, chỉ JPEG/PNG cạnh ngắn ≥ 700, tên tệp phải
  chứa ≥ 2 từ đặc trưng của từ khoá và không phải logo/CGI/variant/bản đồ phẳng.
  Đây là **ảnh thật** — cờ thật, toà nhà thật — nên không vi phạm §0. **Giới hạn
  này CHỈ áp dụng khi tin không nhắc tên hãng nào** (cờ nước, ngành chung chung
  không gắn với một hãng cụ thể) — tin CÓ tên hãng thì đi theo nguyên tắc nguồn
  mở ở đầu §1.2d (13/09/2026: không giới hạn thời gian/sự kiện/nguồn, chỉ giữ
  Anh/Trung), kể cả khi khái niệm đó nghe trừu tượng (funding, partnership) —
  hễ có tên hãng là có thể tìm được ảnh thật/minh hoạ rõ nét về đúng hãng đó.
- **Nhìn**: vision được hỏi câu riêng ("có đúng là *cờ Nhật* chụp thật, hợp làm
  bìa không"), không hỏi "có phải ảnh của tin" vì chắc chắn không phải. Ảnh có
  mặt người hay là đồ hoạ → bỏ.
- **Chỗ đứng (nới lỏng LOW-58, Ông Chủ 15/09/2026: *"ảnh nào cũng dùng được
  hết, không phải câu nệ"*)**: nhãn 🧭 ẢNH KHÁI NIỆM, ưu tiên **bìa/hero**
  (ngang thì chỉ ghép dọc) nhưng **được phép vào slide thân** nếu vai thấy hợp
  — không còn là loại ảnh bị cấm theo chỗ dùng. Gợi ý bìa vẫn xếp **sau** mọi
  ảnh riêng của tin. Vai vẫn chỉ chọn mã, và
  vẫn được nói "thiếu ảnh" nếu thấy cờ/bản đồ không hợp tin.
- **Không còn cổng chặn cứng** (`kite_submit`, §9): trước 15/09/2026 `image` là
  ảnh khái niệm ở slide khác slide 1 sẽ bị chặn (đo 10/09/2026 ở đường Kite: cờ
  Nhật đặt vào `figure` thân đi qua cổng không một dòng lỗi, vì nó là ảnh chụp
  thật nên sạch với mọi cổng kỹ thuật — cái "sai" khi đó là **chỗ dùng**). Từ
  LOW-58 cổng chỉ còn **CẢNH BÁO** (🧭 nhãn ở slide thân) để người duyệt biết
  đây là ảnh minh hoạ chủ đề chứ không phải ảnh chụp đúng sự kiện, không còn
  chặn bài. Vẫn để nó trong `kite_prepare.figure_real` (ứng viên cho `image`
  của bìa lẫn thân) và brief ghi thẳng nhãn 🧭 ở dòng của nó.
- **§1.2e không ép nó xuống thân**: đây vẫn là thứ tự ƯU TIÊN (concept image
  hợp bìa hơn) chứ không phải luật cấm — xem chỗ `figure_right_use` ở mục đó.

### 1.2e Vai TỰ ĐI TÌM khi ban chuẩn bị thiếu — `find_more_images.py`

Ông Chủ 12/09/2026 (tin TSMC t_a8ffd2f6): *"designer mà không được phép đi tìm
ảnh, ai nghĩ ra cái luật thiểu năng này?"*. Luật 04/09 "vai chỉ chọn mã" cắt cả
quyền **tìm**, trong khi cái đắt là **tải/crop/nhìn**, không phải tìm. Engine
chỉ có một danh sách nguồn cố định, hết vòng tìm rộng là dừng cả bài.

- **Giữ**: engine vẫn chuẩn bị, cổng chặn vẫn của script, vai vẫn không tự
  curl/crop/mở ảnh.
- **Bỏ**: thiếu ảnh không còn là "block ngay". Vai chạy
  `find_more_images.py <id> --tu-khoa "<tiếng Anh cụ thể>"` (hãng, sản phẩm, nhà
  máy, sự kiện, người trong bài; hoặc `--url` trang/ảnh vai biết). Script hỏi
  Bing News + Wikimedia Commons + **Openverse** (ảnh CC: Wikimedia, Flickr CC…;
  chỉ giấy phép by / by-sa / cc0 / pdm, cạnh ngắn ≥ 700), mở trang, tải, **nhìn**,
  đo, cắt sẵn y như engine, nối vào `manifest.json`, in ảnh mới. Vai chọn, máy xử lý.
- **Tối đa 3 lượt** một bài, mỗi lượt đổi từ khoá khác hẳn — không quay lại
  60 tool call/task. Từ khoá tiếng Việt bị từ chối (§ tìm kiếm chỉ tiếng Anh).
- Hết 3 lượt vẫn thiếu mới `kanban_block`, lý do **phải kể từ khoá đã thử**.
- Đếm **slide dựng được**, không đếm tấm (`schema.count_image_use_ok`): ảnh ngang
  thấp hơn 700px chỉ ghép được, hai tấm mới thành một slide, một tấm lẻ = 0.
  Cùng số này quyết định engine có tìm tiếp không (`role.has_enough_material`).
- Ảnh **chụp** có biển hiệu, số nhà, logo trên tường vẫn là ảnh chụp — cắt dọc
  được. "Có chữ" cấm crop chỉ là chart, bảng, slide, banner, screenshot có tiêu đề.

### 1.2d Ảnh thương hiệu: tin về hãng lớn thì tìm trụ sở của chính hãng đó

> **Nguyên tắc nguồn, chốt lại 13/09/2026 — thay cho mọi giới hạn về nguồn bên
> dưới.** Ông Chủ: *"thay vì quá nhiều rule cấm về phần nguồn, loại bỏ toàn bộ
> các yêu cầu cấm"*. Khi tin đã nhắc tới TÊN một hãng cụ thể (TSMC, Moonshot
> AI...), tìm ảnh của hãng đó — logo, nhà máy/trụ sở, biểu đồ giá cổ phiếu, sản
> phẩm — theo đúng MỘT nguyên tắc:
>
> - **Không giới hạn thời gian, không đòi cùng một sự kiện.** Bài gốc là "TSMC
>   tăng doanh thu 53% trong Q3 2026" thì KHÔNG cần ảnh từ đúng bài nói về việc
>   tăng doanh thu đó — chỉ cần bài có NHẮC TỚI TSMC, tìm ở bất cứ đâu và bất cứ
>   lúc nào: Bing News, Google News, RSS của chính hãng, trang tin bất kỳ.
> - **Không giới hạn nguồn/định dạng** — ảnh chụp thật hay **minh hoạ biên tập**
>   (illustration, kiểu The Economist) đều được, miễn RÕ NÉT và đúng là hãng đó
>   (logo/nhà máy/biểu đồ/sản phẩm), không riêng gì Wikimedia Commons.
> - **Ngôn ngữ truy vấn: chỉ tiếng Anh hoặc tiếng Trung** — tuyệt đối không dùng
>   ngôn ngữ khác (kể cả tiếng Việt, xem quy tắc "Tìm kiếm chỉ tiếng Anh" đã có
>   từ 05/09 — nay mở thêm tiếng Trung cho các hãng Trung Quốc, TUYỆT ĐỐI không
>   mở thêm ngôn ngữ nào khác).
> - **Ngoài ba điều trên, không còn cấm đoán nào khác về nguồn ảnh** — các mục
>   "Nguồn: chỉ Wikimedia Commons", "không tìm khái niệm trừu tượng" ghi ở nơi
>   khác trong tài liệu này chỉ còn áp dụng cho ca KHÔNG có tên hãng nào được
>   nhắc (§1.2c thuần khái niệm — cờ nước, ngành chung chung); một khi CÓ tên
>   hãng, nguyên tắc ở đây thắng. Vẫn phải qua đủ mọi cổng chặn khác không đổi
>   (mặt người vô danh §6, ảnh trùng, chất lượng nhìn thấy — mờ/chụp lại màn
>   hình — vẫn CẤM như cũ, đây là luật về CHẤT LƯỢNG chứ không phải về NGUỒN).
>
> Cài đặt: `article_sources.report_about_keyword` (tìm theo tên hãng, không đòi cùng sự
> kiện) + `prepare.fallback_rounds._report_brand_empty` (quét ảnh từ các bài tìm
> được) — trước 13/09/2026 chỉ chạy khi Commons/Wikidata RỖNG; nay chạy
> **song song, luôn luôn**, không còn là phương án cuối.

Ông Chủ 09/09/2026: *"Dre vẫn chưa tự tìm thêm hình liên quan khi làm các nội
dung có Big Brand"*. Sáng hôm đó năm tin liên tiếp (Qualcomm × Amazon, xưởng
Samsung, kiện Anthropic, DeepSeek gọi vốn, Philippines) đều dừng ở nút *"chỉ 2/5
ảnh thật dùng được — Kite vẽ vector / Dre làm với N ảnh"*, toàn hãng mà Commons
có hàng trăm ảnh thật. Luật của **engine** (`image_brand.py`):

- **Khi nào**: **mọi tin nhắc tới một hãng trong watchlist**, kể cả khi bài gốc
  đã đủ ảnh — chạy sau vòng tìm rộng, **trước** ảnh khái niệm. Ông Chủ
  10/09/2026, lần thứ hai của cùng một câu: *"Dre vẫn ko chịu đi tìm các hình
  liên quan như logo, brand, founder, trụ sở... của chủ đề được nhắc tới"*. Bản
  09/09 treo vòng này sau điều kiện *thiếu ảnh*, nên tin nào bài gốc đủ ảnh là
  không bao giờ hỏi tới Commons/Wikidata — mà vai thì bị cấm tự tải thêm, nên bộ
  ảnh giao cho vai trắng trơn dù máy móc đã sẵn. Tin không nhắc hãng nào:
  `vendors_in_story` trả rỗng, vòng thoát ngay, không một request nào.
- **Trần**: thêm tối đa 4 ảnh một bộ (`MAX_EXTRA_BRAND_`), và tổng ảnh không quá
  `MAX_IMAGE + 4`. Riêng việc **mở browser đi chụp bảng xếp hạng** làm ảnh bối
  cảnh thì vẫn chỉ chạy khi **thật sự thiếu ảnh** — đó là phần đắt.
- **Chỗ đứng**: ảnh của hãng xếp **sau** ảnh riêng của tin trong gợi ý bìa
  (`cover_suggestions`), nên bài có ảnh riêng tốt không bị chúng chiếm bìa.
- **Hãng nào**: mọi hãng trong `scan_business.WATCHLIST` mà tin nhắc tới, tối đa
  3, theo thứ tự xuất hiện — **không phải chỉ tên riêng đầu tiêu đề**. Tên
  model/chip quy về hãng chủ (Claude → Anthropic, Xring → Xiaomi). Tên trần mà
  watchlist không giữ (Google, Meta, Snapdragon) bù bằng `NAME_EXTRA`.
- **Hỏi gì**: `"<Hãng> headquarters"`, `"<Hãng> building"`, `"<Hãng> campus"` —
  hỏi thẳng thứ hãng nào cũng có ảnh, không hỏi tên trần. Hỏi tên trần
  ("Anthropic") ra ảnh khảo cổ *anthropic cut marks*.
- **Bốn loại tư liệu**, theo độ "là ảnh chụp thật của hãng" giảm dần. Ông Chủ
  09/09/2026: *"ko thấy ảnh liên quan thì lấy ảnh logo, ảnh founder, ảnh chụp
  trên các bảng xếp hạng của model… có thiếu tư liệu đâu?"*
  1. 🏢 **cơ sở** — trụ sở/campus. Tìm tên tệp Commons **và** `P18` của
     Wikidata: hãng thuần phần mềm không có tệp nào tên "<hãng> headquarters",
     mà trụ sở OpenAI trên Commons lại tên *"Pioneer Building, San Francisco"* —
     không một chữ "openai" nào. Wikidata trỏ thẳng tới nó.
  2. 👤 **chân dung founder/CEO** — `P112`/`P169` → `P18` của chính người đó.
     Đi **kèm tên**, nên khai được `subject`: đúng ngoại lệ của §6, khác hẳn
     mặt vô danh. Bỏ người **đã thôi chức** (qualifier `P582`) — hỏi CEO OpenAI
     mà không lọc thì Wikidata trả cả CEO tạm quyền cũ, brief ghi sai tên.
     Brief vẫn dặn: **bài không nhắc tên người này thì bỏ**.
  3. 📊 **bảng xếp hạng có model của hãng** — mượn `ranking.py` chụp bảng, chỉ
     cho hãng **có làm model** (`rank_has_model`; Qualcomm/TSMC không khớp hàng
     nào). **Chỉ nhận ảnh chụp thật**: hết đường thì `find_and_capture` tự dựng *thẻ
     dự phòng* "`<model> #<hạng>`" — thẻ đó cho một tin KHÔNG PHẢI tin xếp hạng
     là bịa ra một thứ hạng không ai nói, nên phải vứt.
  4. 🔖 **thẻ logo** — logo chính thức (`P154`) đặt trên nền trơn, dồn lên nửa
     trên để hook đè nửa dưới; nền sáng hay tối **chọn theo độ sáng của chính
     logo** (wordmark chữ đen trên nền tối là mất chữ). Cùng nguyên tắc với
     `ranking.fallback_card`: không thêm một nét nào của ta, chỉ là chỗ đặt —
     nên không vướng §0. Là đường **cuối**, chỉ khi không còn ảnh chụp nào.
- **Lọc**: tên tệp phải chứa **đủ** từ đặc trưng của tên hãng theo *biên giới từ*
  ("Arm" ≠ "Armstrong"); bỏ đồ hoạ (`NAME_TYPE`); bỏ **nhiễu theo hãng** (Amazon →
  rừng/sông, Apple → quả táo, Tesla → Nikola Tesla) và **nhiễu chung** (mít tinh,
  đình công, biểu tình — đo thật: "Amazon building" trả về hai tấm *Solidarity
  With Alabama Amazon Workers*). JPEG trước, ảnh to trước, cạnh ngắn ≥ 700.
- **Chỗ đứng**: nhãn 🏢 ẢNH THƯƠNG HIỆU. **Khác ảnh khái niệm ở hai điểm**: nó
  vào được **slide thân** (là ảnh thật của chính hãng trong tin, đúng loại "trụ
  sở/sản phẩm" §1.2 vẫn kể là liên quan) và nó **đếm đủ**, không gộp cả chùm
  thành một. Gợi ý bìa vẫn xếp sau mọi ảnh riêng của tin. Trần **4 tấm** một bộ,
  2 tấm mỗi hãng — để một bộ không thành album trụ sở.
- **Mặt người**: ảnh **cơ sở** có mặt là bỏ — người đứng trước cửa hàng trên
  Commons thì không ai gọi được tên (§6). Ảnh **chân dung** thì ngược lại: mặt
  là thứ ta đi tìm, và tên đi kèm sẵn. Đừng chặn chân dung theo số mặt đếm được:
  `image_rules.count_faces` trả `None` khi thiếu cv2/model và §6 cho phép cổng mặt tự
  tắt, nên lấy `faces == 0` làm "không phải chân dung" là bỏ câm lặng mọi chân
  dung trên máy thiếu cv2. Để **con mắt** phán, bằng câu hỏi riêng cho từng loại
  tư liệu (`sentence_ask_vision`) — câu chung hỏi "có phải ảnh của tin không" thì
  chân dung và thẻ logo chắc chắn trượt.

**Wikimedia đòi User-Agent riêng.** Robot policy của Wikimedia trả **403** cho UA
kiểu trình duyệt; phải có tên công cụ + **đường liên hệ trong ngoặc**
(`env_load.UA_WIKI`). Áp cho **cả** API `commons.wikimedia.org` **lẫn** bước tải
byte từ `upload.wikimedia.org`. Ba chỗ gọi Commons đều `except → []`, nên khi UA
sai thì cả đường Wikimedia — ảnh thương hiệu *và* ảnh khái niệm — **chết câm
lặng**, không một dòng lỗi nào lên tới brief.

### 1.2e Chuyển sang Kite vì thiếu ảnh thì Kite vẫn phải dùng ảnh đã tìm được

Ông Chủ 09/09/2026: *"sau khi tìm được hình tốt mà vẫn ko đủ để làm và pass qua
cho Kite thì Kite cũng phải dùng những hình đó trong body"*.

Đường vào Kite **luôn là** đường thiếu ảnh: engine tự chuyển khi 0 ảnh, hoặc Ông
Chủ bấm "🎨 Gửi Kite vẽ vector" ở một trong hai thông báo thiếu ảnh. Lúc đó
`img.json` mang `transferred_from` (tên vai cũ) — **manifest.json không có**, vì nút được
bấm sau khi engine đã ghi xong. Đọc nhầm chỗ là cổng dưới không bao giờ bật.

- **Cả n mã hình thật đều phải xuất hiện** trong spec, không phải "ít nhất một".
  Cổng cũ (§ `kite_submit`) chỉ đòi một tấm, nên Kite đặt đúng một tấm lên bìa rồi
  vẽ vector cả thân — đúng cái bị chê.
- **Phải có hình ở BODY**, không chỉ ở bìa: mỗi tấm một slide `figure`.
- **Trần 6 tấm** (`MAX_FORCE_FIGURE`): bộ chỉ được 6..10 slide, trừ bìa và cta còn
  8. Ép hết khi engine tìm được 9 tấm là hai cổng đá nhau, vai không có đường nộp.
- Chỉ ép ảnh **đã được nhìn** (`relevant is True`). Vision tắt thì mọi ảnh là
  `None`, ép lúc đó là đẩy quảng cáo/widget lên slide — cùng bài học với cổng
  "ít nhất một".
- **Không ép ảnh khái niệm** vào tập này — chỉ là **ưu tiên** (§1.2c nới lỏng
  LOW-58 15/09/2026, không còn cấm nó ở thân): ảnh khái niệm hợp bìa hơn nên để
  nó rơi khỏi `figure_right_use` và về bìa qua `figure_hero` (§1.2f); vai vẫn
  có thể tự đặt nó vào `figure` thân nếu muốn, cổng chỉ còn cảnh báo.
  **Ảnh thương hiệu thì ở lại**: §1.2d cho nó vào thân, vì nó là ảnh thật của
  chính hãng được nhắc trong tin.
- **Trừ tấm đã lên bìa** (`figure_hero`, §1.2f): cùng một ảnh không lên được hai
  slide (`check_duplicate` §8), nên để nó trong tập bị ép là đòi một thứ bất khả. Hệ
  quả: tin chỉ có **đúng một** tấm thì tập này **rỗng** — tấm đó lên bìa và thân
  không đòi gì nữa.
- `kite_prepare.figure_right_use` là **một nguồn** cho cả brief lẫn cổng chặn, và
  khung spec in sẵn một `figure` cho mỗi mã — đừng bắt vai tự suy ra "ba hình thì
  ba slide". `_force_raw` là tập chưa trừ bìa, chỉ `figure_hero` dùng (cắt vòng gọi).

Brief của Kite còn ghi rõ **từng tấm là loại gì** (🏢 cơ sở · 👤 chân dung ·
📊 bảng xếp hạng · 🔖 thẻ logo, §1.2d), vì dùng nhầm loại là sai sự thật: một
thẻ logo không thay được ảnh chụp trụ sở.

### 1.2e-bis Slide KHÔNG ghi dòng nguồn ảnh (LOW-292, Ông Chủ 20/09/2026)

Album Gemini (task `t_22d038a3`) bị khoanh đỏ đúng dòng `— <mô tả ảnh> · via
<trang>` ở cả bìa lẫn slide thân: *"nội dung không được phép xuất hiện"*. Từ
20/09/2026 `render_edu.py` không vẽ dòng đó nữa, `kite_submit.py` không còn đòi
`caption` khi slide có ảnh, và brief không in khuôn caption nữa.

Nguồn ảnh **không mất**: nó vẫn nằm ở bàn giao cho writer (`<draft>.ban_giao.md`)
và metadata PNG (`image_provenance`). Đây chỉ là chuyện không hiện trên hình.

`caption` của kind `bars` là chuyện KHÁC — đó là nguồn của CON SỐ ("Số trong bài
· via <ai>"), vẫn bắt buộc, vì số là của bài chứ không phải của ta.

### 1.2f Bìa của Kite LUÔN phải là ảnh thật — không có hero vector

Ông Chủ 10/09/2026, hai lần trong một ngày. Lần đầu: *"kite vẫn dùng vector làm
hero, chưa sử dụng ảnh"*. Bản vá buổi sáng chặn **khi có ứng viên**, nên đo lại
vẫn còn **ba ca ra bìa vector**: 0 ảnh, vision tắt, và tin chuyển sang chỉ còn
một tấm (thân giành mất). Lần thứ hai, sau khi xem đúng ba ca đó:

> *"không chấp nhận việc dùng vector ở hero slide, thời đại này không có ảnh gì
> mà không thể tìm được"*

Nên vế điều kiện bị bỏ: **bìa không có `image` là chặn, không trừ ca nào.** Vế
sau của câu là điều quan trọng hơn — "không có ảnh" **không phải một trạng thái
hợp lệ của tin**, nó là *thất bại của vòng tìm ảnh*. Lặng lẽ vẽ vector là giấu
thất bại đó dưới một bộ slide trông như thật, nên cổng phải nói ra.

Bản trước (08/09) chỉ chỉ định hero khi ảnh có `paper_figure` — tức **chỉ bài
arxiv** (§1.4). Mọi tin còn lại thì brief nói "bìa `image` **hoặc** `figure`"
(tuỳ chọn) và `kite_submit` chỉ đòi "dùng ít nhất một ảnh ở đâu đó", nên nhét hết
ảnh vào `figure` thân rồi vẽ sơ đồ lên bìa là **hợp lệ**. Đo 10/09: ba ca — tin
thường, tin chuyển sang vì thiếu ảnh, và ảnh khái niệm đặt nhầm vào thân — đều
qua cổng không một dòng lỗi.

- **`kite_prepare.figure_hero`** chọn tấm lên bìa, **một nguồn** cho cả brief lẫn
  cổng chặn (cùng lý do với `figure_right_use` §1.2e). Thứ tự: hình paper (§1.4) →
  ảnh riêng của tin → ảnh thương hiệu (§1.2d) → ảnh khái niệm (§1.2c); hai loại
  bù xếp sau mọi ảnh riêng, đúng như hai mục đó ghi.
- **Cổng**: slide `cover` không có `image` → `kite_submit` chặn, **luôn**. Cổng đòi
  **có** ảnh ở bìa, không đòi đúng mã nào — `figure_hero` chỉ gợi ý. Ba lời báo
  khác nhau theo nguyên nhân, vì việc phải làm khác nhau: có ứng viên → *đặt mã
  này vào slide 1*; ảnh có mà **vision chưa nhìn** → *bật vision rồi
  `--lam-moi`*; **0 ảnh** → *chạy lại vòng tìm ảnh, vẫn trắng thì `kanban_block`*.
- Chỉ ép ảnh **đã được nhìn** (`relevant is True`), trừ hình paper (bóc thẳng từ
  PDF nên không thể là quảng cáo). Vision tắt thì mọi ảnh là `None`, và cổng
  **vẫn chặn** — chỉ là không chỉ định mã nào: đẩy một banner chưa ai nhìn lên
  bìa còn tệ hơn vẽ vector. Đây là hỏng khâu vận hành (thiếu `OPENAI_API_KEY`),
  không phải một lựa chọn bố cục.
- **Kite phải TỰ TÌM LẠI, không được thừa kế thất bại của vai cũ.** Ông Chủ
  10/09/2026, ngay sau khi xem cổng chặn ở trên: *"Dre tìm được ảnh đúng, nên kỹ
  năng tìm ảnh đó dùng được. ko có lý gì mà ko tìm được ảnh để báo hỏng"*. Đo cả
  chuỗi hôm đó, và đây là chỗ hỏng thật sự:
  1. `image_prepare.run` trả **thẳng** `manifest.json` cũ khi tệp đã có
     (`if xong.exists() and not lam_moi`);
  2. task body giao cho Kite chạy `kite_prepare.py <id>` — **không** `--lam-moi`;
  3. `create_task_kite` còn ghi vào body *"tin này không có ảnh thật dùng được: vẽ
     vector hoàn toàn"* — chính hệ thống giục vai làm thứ mục này cấm.

  Nên tin chuyển sang Kite **đọc lại đúng kết quả đã thất bại của vai cũ** và
  vòng tìm ảnh không bao giờ chạy lần nữa. Kỹ năng có sẵn, chỉ là không ai gọi
  nó cho Kite. Mà **hai vai dừng ở hai ngưỡng khác nhau**: vai cũ cần đủ ~5 ảnh
  cho carousel rồi mới thôi, Kite chỉ cần **một tấm lên bìa** — rẻ hơn hẳn, nên
  "vai cũ không đủ" không hề có nghĩa "Kite không đủ".
  `kite_prepare.ensure_has_cover` chạy lại vòng tìm **đúng một lượt** khi chưa có
  tấm nào lên bìa được, trước khi in brief.
- **Chặn cứng không làm vai treo**: nước đi đầu là *tìm lại*, không phải *báo
  hỏng*. Hết đường thì `submit_common.count_round_error` đếm ba vòng lỗi *y hệt nhau* rồi
  bảo vai gọi `kanban_block` và đẩy lên Ông Chủ — đúng đường đã dành sẵn cho
  *"cổng đang đợi một thứ không thể có"*. Engine về trắng cho một tin có thật là
  việc của Ông Chủ, không phải của vai.

**Đo 10/09/2026 — máy móc tìm ảnh KHÔNG hỏng, đừng đi vá nhầm chỗ.** Chín tiêu
đề tin thật lấy từ chính tài liệu này (Philippines 34 tỷ, Qualcomm × Amazon,
xưởng Samsung, kiện Anthropic, DeepSeek gọi vốn, Nemotron, Google Antigravity,
Thinking Machines, SWE-bench) đều **ra từ khoá** qua `vendors_in_story` (§1.2d)
hoặc `keyword_concept` (§1.2c) — 9/9, **không cần LLM**, chỉ bảng tĩnh. Và
`image_concept.image_concept("flag of Philippines")` trả về ảnh thật từ Commons.
Chỗ trắng chỉ xuất hiện với tiêu đề *không nhắc hãng nào trong watchlist, không
nhắc nước nào, và không khớp mẫu `TOPIC` nào* — chưa gặp trong lưu lượng thật.
Nên đừng nhét từ khoá chung chung vào `TOPIC` để "cho chắc": Commons trả minh
hoạ tệ cho khái niệm trừu tượng (§1.2c), và thêm một từ khoá sai làm hỏng đúng
cái §0 giữ.
- **Hai cổng không được đá nhau**: tin chuyển sang Kite đòi hình thật nằm ở slide
  **thân** (§1.2e), mà cùng một ảnh không lên được hai slide (`check_duplicate` §8).
  Tấm nào bị thân giữ độc quyền thì **lùi xuống ứng viên kế tiếp**, không bỏ
  cuộc ngay: ảnh khái niệm không nằm trong tập bị ép (§1.2c ưu tiên nó ở bìa,
  không còn cấm ở thân từ LOW-58) nên tin có một ảnh riêng + một ảnh khái niệm
  thì ảnh riêng ở thân còn **ảnh khái niệm lên bìa** — đúng chỗ ưu tiên của nó,
  và cả hai tấm đều được dùng.
- **Hết ứng viên thì BÌA THẮNG**, không phải thân. Tin chỉ có **đúng một** tấm:
  tấm đó lên bìa, và `figure_right_use` trừ nó ra nên thân không đòi gì nữa. Đòi
  của §1.2e sinh ra từ ca **nhiều** tấm mà Kite chỉ dùng một; còn một tấm thì nó
  **vẫn được dùng**, chỉ là dùng ở bìa. Bản 10/09 sáng cho thân thắng ở ca này —
  đó chính là một trong ba ca ra hero vector mà Ông Chủ chặn.
- Bìa có ảnh thì **cả bộ không vẽ hero art** (`pick_theme_auto` trả
  `hero=None`), nên đây là thay thế chứ không phải thêm một lớp trang trí.

### 1.2g Con mắt trả lời mà không đọc ra được thì hỏi lại, không mặc định duyệt

- `relevant` có 3 giá trị: `True` (liên quan), `False` (không liên quan — vision
  đã xem và từ chối), `None` (chưa biết). Mọi nơi lọc `dung_duoc` viết
  `relevant is not False`, tức **`None` từng được coi là duyệt** — đây là lỗ
  fail-open. Ông Chủ 12/09/2026 đóng lại: *"đóng luôn cổng fail-open"*.
- `None` có **hai nguồn gốc khác hẳn nhau**, và chỉ một nguồn được đóng:
  1. **Không hỏi được** (thiếu `OPENAI_API_KEY`, router hỏng cả 3 lần thử lại
     429/5xx) — đây là "vision tắt" có chủ đích ở nơi khác (`kite_submit.py`:
     "vision tắt thì ép là đẩy quảng cáo/banner lên bìa"), **giữ nguyên `None`**.
     Không hỏi lại ở đây — `_call_router` đã có backoff riêng.
  2. **Hỏi được nhưng không đọc ra dòng `LIEN_QUAN`** (model trả lời lệch định
     dạng) — đo 12/09/2026 trên máy chủ: ảnh trụ sở Tesla (Terafab) và một ứng
     viên thương hiệu Anthropic đều lọt bìa qua đường này dù router đã trả lời,
     chỉ là câu trả lời không parse được. Ca này **hỏi lại đúng 1 lần**
     (`prepare/vision.description_image`); vẫn không đọc ra thì **coi là RỚT**
     (`relevant = False`), không còn là `None` nữa.
- Không gộp hai ca làm một: nếu "không hỏi được" cũng bị đóng thì mọi lần vision
  tắt (thiếu key ở môi trường dev/test) sẽ biến TOÀN BỘ ảnh của tin thành rớt —
  không còn ảnh nào để dùng, sai với hợp đồng "chưa ai nhìn" mà nhiều nơi khác
  (brief, `figure_hero`, `kite_submit`) đang dựa vào.

### 1.3 Tin model ra mắt / xếp hạng: ưu tiên benchmark table/chart

Bảng so sánh điểm benchmark (MMLU, HumanEval, lập trình, toán…) và biểu đồ là
**bằng chứng mạnh nhất** — ưu tiên trước cả ảnh logo/hero. Chụp bản to (cạnh
ngắn ≥1000px; bảng chữ nhỏ càng phải to).

**Tin về THỨ HẠNG thì bảng xếp hạng chính là ảnh của tin.** Ông Chủ chốt
06/09/2026, nguyên văn, sau ba thẻ liền nhau dùng bảng tỉ số golf rồi bảng câu cá
trên băng:

> nói về ranking phải là table / chart / standing / rank · nếu không có ảnh thì
> capture screen · tìm tất cả các nguồn, không giới hạn, miễn là capture được
> hình tử tế · khi capture phải khoanh lại đúng model đang được nhắc tới · không
> dùng lại ảnh đã dùng trong phiên · không dùng ảnh không liên quan · không
> capture được thì ảnh = tên model + thứ hạng + logo model + site đánh giá.
> Không ra output tương tự đồ hoạ tham chiếu (arena.ai) là **fail**.

Từ 06/09 việc này là của **engine**, không phải của vai: `ranking.py` chạy
trong `image_prepare.py` khi tiêu đề là tin xếp hạng. Nó tách tên model, đi qua
registry nguồn (arena.ai text/code/vision/t2i/**image-edit**/t2v/search,
artificialanalysis.ai, tbench.ai, swebench.com, livebench.ai, aider — nguồn
được nhắc trong bài đi trước), mở browser, tìm **hàng** chứa model trong bảng
lớn nhất (khớp bỏ dấu
cách/gạch/chấm: "Claude Opus 4.6" ≡ "claude-opus-4-6"), chụp cửa sổ từ hàng 1
(hoặc từ hàng model-2 nếu nằm sâu) kéo xuống cho tới khi rộng/cao ≤ 1.5 — đủ
để đi một mình vào hero. Trang chỉ có một bảng mà bảng quá ngang (tbench: 15
hàng trải 2319px) thì **thu hẹp cửa sổ** (1500 → 1200 → 1000) cho bảng responsive
tự dồn cột — đủ cột, đúng từng ô, chỉ bố cục hẹp lại; có nhiều bảng thì chọn
bảng vừa khổ, còn quá ngang mới ghép dọc hai bảng cùng trang — **full bề ngang bảng, khoanh vàng hàng model, đọc thứ
hạng từ ô đầu**. Không nguồn nào ra → thẻ dự phòng: tên model + #hạng + logo (nếu
chụp được từ hàng) + site. Ảnh vào kho với mã **`XH`**, đóng dấu
`provenance=ranking_capture|ranking_card` kèm model/hạng/site (PNG cũ trước LOW-237 mang
`nguon_dung=chup_xep_hang|the_xep_hang` — hàm đọc nhận cả hai).

Vai chỉ còn một việc: **`"image": "XH"`** (hero) / **bìa `"image": "XH"`** (carousel).
`ethan_submit` / `dre_submit` chặn ảnh chính khác khi `manifest.json` có `is_ranking_story` —
không phải "chưa đạt", là **sai đề tài**. `XH` được miễn hai cổng cấm chart lên bìa/hero vì nó *là* chủ
thể của tin; vẫn chịu mọi cổng khác.

Chart đi đâu, theo khung:

- **Hero (`quote`/`full_bleed`)** — chart ở `image`, thêm `image2` là một ảnh ngang cùng
  tone: script ghép dọc, chart nằm nửa trên **nguyên vẹn**. `ethan_submit.py` gợi ý
  sẵn cặp ghép (`stackable_pairs_hero`).
- **Carousel slide thân** — `"chart": true`, dán full bề ngang nguyên vẹn.

Nguồn không có sẵn ảnh chart thì **chụp từ chính trang nguồn**: engine
`image_prepare.py` mở browser thật và tự chụp `figure/table/canvas/svg` (mã ảnh
loại `chart`, đóng dấu `capture_chart`). Chụp tay thì dùng `capture_chart.py` — full
chiều rộng trước, chiều cao xét sau (mục 2).

### 1.4 Bài arxiv: hình trong paper trước, trang bìa sau

**Ảnh thật của một bài paper là hình của chính nó** — Figure 1 (thường là biểu đồ
kết quả tổng), Figure 2, Figure 3. Do nhóm tác giả vẽ, bằng số của họ: không ảnh
nào của tin đó đúng hơn được nữa. Engine bóc thẳng từ PDF, tự động cho mọi tin
arxiv/PDF; chạy tay thì:

```bash
venv/bin/python arxiv_figures.py --link "<link arxiv>" --ra /tmp/hinh
```

**Figure 1 là hero.** Kite đặt nó vào `image` của slide `cover` — bìa lấy chính
tấm hình đó làm hero thay vì vẽ hero art. Ông Chủ 08/09/2026: *"ngay đầu paper có image mà Kite không dùng để
làm hero"*. Các hình còn lại để cho slide `figure`.

Chỉ **hình**, không bảng: chú thích bảng khi ở trên khi ở dưới tuỳ nơi đăng, và
từng dòng của bảng trông y như một dòng thân bài — không có mốc nào chắc để chặn
vùng cắt, mà cắt sai một cái bảng là dán lên slide một bảng **khác** với bảng
trong bài.

Không bóc được hình nào (paper ảnh scan, PDF hỏng) thì mới tới **trang bìa**
paper — ngoại lệ duy nhất của luật "không tự vẽ":

```bash
venv/bin/python arxiv_cover.py --link "<link arxiv>" --out /tmp/src_bia.png
```

---

## 2. Chụp chart: full chiều rộng trước, chiều cao xét sau

**Luật Ông Chủ 04/09/2026.** Bề ngang của một chart là **nội dung**: trục, nhãn
chuỗi, cột cuối của bảng, cái điểm được tô sáng mà cả bài đang nói tới. Cắt mất
một phần bề ngang thì thứ còn lại không phải thiếu một tí — **nó nói sai**.
Chiều cao thì khác: cắt bớt mép trên/dưới thường chỉ mất khoảng thở.

Đừng chụp bằng khung mặc định của công cụ nào. Khung mặc định luôn hẹp
(`capture_page.py` trong repo này đặt 820px), và một chart rộng 1400px trong khung
đó thì hoặc bị cắt, hoặc bị trang reflow xuống bố cục điện thoại — lúc đó có
chụp đủ bề ngang cũng không còn là cái chart trên desktop nữa.

```bash
venv/bin/python capture_chart.py --url "<trang có chart>" --ra chart.png
venv/bin/python capture_chart.py --url "<trang>" --chon "figure.chart" --ra chart.png
venv/bin/python capture_chart.py --url "<link ảnh trực tiếp>" --ra chart.png
```

Script mở ở khung 1920px, **đo bề ngang thật** của phần tử (`scrollWidth`, bắt
cả phần tràn ngoài khung nhìn), **nới khung** cho vừa rồi mới chụp ở DPR 2. Chụp
xong **đo lại ảnh ra**: bề ngang nhỏ hơn bề ngang thật của chart thì lệnh dừng
chứ không giao một tấm thiếu nửa phải. Ảnh rất cao thì chỉ cảnh báo.

Link trỏ thẳng vào một tấm ảnh thì script tải **nguyên bản** — không resize,
không crop: bản gốc luôn đầy đủ hơn mọi bản chụp lại.

---

## 3. Chart phải đi đường của chart

> **Ông Chủ chốt 04/09/2026: "chart phải được hiển thị đầy đủ và full width của
> chiều rộng hình."** Hai vế, cả hai đều bắt buộc. *Đầy đủ* = không mất một chữ
> nào: tiêu đề, trục, nhãn trục, legend, chú thích chân chart. *Full width* =
> trải hết bề ngang khung, không thu nhỏ, không chừa lề.

Với ảnh chart/bảng/screenshot thì vấn đề **không phải** "nửa dưới có trống
không" mà là **nguyên vẹn + full bề ngang**. Nên script tự nhận diện loại ảnh
này rồi ép sang đúng đường, thay vì bảo bạn "đổi ảnh khác".

**Ca bị bắt:** bộ K2 Horizon cắt chart 2015×1099 về 879×1099 để lấp đầy khung —
vứt 56% bề ngang, mất chữ đầu tiêu đề ("…osses across the Horizon fleet") và mất
sạch trục y.

### Cách nhận diện (`image_rules.is_chart`), đo trên bản thu nhỏ 480px

| Phép đo | Chart/screenshot | Ảnh thật |
|---|---|---|
| `phẳng` — tỉ lệ cặp pixel kề nhau gần bằng nhau | 0,89–0,99 | 0,31–0,95 |
| `số màu` — số màu riêng biệt sau lượng hoá 5 bit | 42–65 | 350–4552 |

Phải **cả hai** mới kết luận là chart.

### Cổng chart chạy MỘT CHIỀU — đọc kỹ chỗ này

- **Thiếu cờ mà máy nhận ra là chart → CHẶN.** Sai thì bạn khai thêm cờ, giá rẻ.
- **Có cờ mà máy không nhận ra chart → CHỈ CẢNH BÁO, không chặn.**

Vì sao chiều thứ hai không được chặn: `la_chart` **bỏ sót thật**. Chart có đường
màu khử răng cưa cho ra hàng nghìn màu — `training-losses.png` của K2 Horizon ra
**1176 màu**, quá ngưỡng 220, nên bị chấm là "không phải chart". Có lúc cổng này
chặn cả bộ Horizon **làm đúng** (chart gốc + `chart: true`) kèm lời khuyên "bỏ
cờ đi và cắt về 1:1/4:5" — tức chỉ thẳng vào đúng cái sai đã gây ra sự cố. Chặn
ở chiều này là **giết việc đúng**.

Nên: **khai `chart: true` mà bị cảnh báo thì cứ để cờ đó**, chỉ xem lại nếu đây
thật sự là ảnh chụp thường.

### Nhận ra là chart thì đi đường nào

- **Hero (`quote`/`full_bleed`)**: chart đi một mình bị chặn — hook đè lên thì chart
  nằm dưới chữ, đọc không ra. Ghép dọc bằng `--image2`, hoặc để chart cho carousel.
- **Carousel slide thân**: khai `"chart": true`. Ảnh được dán **full bề ngang
  nguyên vẹn**, không crop, không ép tỉ lệ; phần trên/dưới là chính ảnh làm mờ.
- **Carousel bìa**: chart làm bìa bị chặn — ghép dọc `"images": [a, b]`, hoặc
  đổi bìa và để chart ở slide thân.
- **Ảnh ghép dọc** được miễn hẳn cổng này: nó đã nguyên vẹn + full bề ngang sẵn.

Kiểu `quote` (mặc định) không còn màn tối nữa (06/09/2026): chart hiện
NGUYÊN VẸN từ đầu tới sát mép khối chữ, chỉ đúng dải chữ đè lên mới bị làm mờ
cục bộ (không phải làm tối) — trục x/nhãn/chú thích của chart phía TRÊN khối
chữ không hề bị ảnh hưởng. Kiểu `full_bleed` vẫn còn màn tối riêng của nó và tự lùi
điểm bắt đầu xuống dưới mép chart để đáy chart không bị làm tối.

---

## 4. Tỉ lệ và crop

### 4.1 Crop chỉ được làm qua `crop_ratio.py`

```bash
venv/bin/python crop_ratio.py --anh vao.jpg --ra ra.png              # 1:1, giữa
venv/bin/python crop_ratio.py --anh vao.jpg --ra ra.png --ti-le 4:5  # 4:5
venv/bin/python crop_ratio.py --anh vao.jpg --ra ra.png --cx 0.62    # tâm lệch phải
```

Crop là **chọn khung ảnh thật**, không phải bịa ảnh — vẫn đúng luật "không tự
vẽ". Chọn `--cx/--cy` để ôm đúng chủ thể vào khung.

**Chỉ crop ảnh chụp KHÔNG có chữ** (sản phẩm, sự kiện, trụ sở). Ảnh có chữ
(chart, bảng, slide, banner, screenshot UI có tiêu đề) **không crop** — ghép dọc.

**`crop_ratio.py` tự chặn ở đầu kia:** mặc định nó **chỉ cắt chiều cao**. Ảnh gốc
ngang (tỉ lệ ≥1.4) mà đòi cắt bề ngang thì script dừng — bề ngang của chart/bảng
là nội dung. Muốn cắt bề ngang phải thêm `--cat-ngang`, và **chỉ được dùng cho
ảnh chụp người/sản phẩm không có chữ**. Nên với ảnh ngang, đường đúng gần như
luôn là **ghép dọc** hoặc `"chart": true`, không phải crop.

Ảnh gốc rõ ràng **ngang** (tỉ lệ ≥1.4) mà đi qua crop thì bị chặn, trừ khi khai
`"crop_ok": "<lý do>"` — chỉ dành cho ảnh chụp người/sản phẩm không có chữ.

### 4.2 Dấu xuất xứ — ĐÃ BỎ (13/09/2026)

Cổng này (`kiem_xuat_xu`: ảnh đúng khít 4:5/1:1 mà không có dấu vết
`crop_ratio.py` → chặn) đã bỏ khỏi hệ thống, mọi vai (Ông Chủ 13/09/2026: bỏ
cấm đoán này cùng đợt với `kiem_day_sang`/`kiem_lech_tone`/`kiem_anh_thap`).
`crop_ratio.py` vẫn là công cụ crop chuẩn, chỉ là không còn cổng nào ép dùng nó
thay vì công cụ khác. `crop_ratio.py`/`arxiv_figures.py`/`capture_chart.py` vẫn tự
đóng dấu như cũ — chỉ không ai đọc dấu đó để chặn nữa.

---

## 5. Ghép dọc hai ảnh ngang

**Ông Chủ chốt 04/09/2026: ảnh ngang chữ nhật thì cứ ghép cho đỡ phải cắt
nhiều.** Ghép là đường **bình thường**, không phải phương án chữa cháy: cắt một
ảnh 16:9 về 1:1 là bỏ đi gần một nửa bề ngang, ghép dọc hai ảnh giữ trọn cả hai.

Riêng ảnh có **tiêu đề / chữ** thì ghép là **bắt buộc**, không được crop.

Cách ghi: `--image2 <ảnh thứ hai>` (hero), hoặc `"images": [a, b]` thay cho
`"image"` (carousel, dùng được ở cả bìa lẫn slide thân).

Script xếp dọc: mỗi ảnh full bề ngang, nguyên tỉ lệ, **áp sát nhau không vạch
ngăn** (trước đây chèn 12px nền đen — vạch đó là một đường kẻ giữa khung, đọc ra
hai vùng, đã bỏ 04/09/2026). Chữ (hero kiểu quote) hay slide sau (carousel) đè
lên ảnh dưới — quote thì chỉ làm mờ cục bộ đúng vùng chữ (không còn màn tối,
xem mục 7), carousel thì vẫn qua màn tối riêng của nó — nên đặt **ảnh quan
trọng hơn ở trên** để nó hiện trọn, không bị chữ/vùng mờ/màn tối chia sẻ.

**Cổng "không được lệch tone" ĐÃ BỎ (13/09/2026)** — `kiem_lech_tone`
(và bản dùng trực tiếp `image_rules.tone_mismatch` trong `dre_submit.py`) không còn chặn
gì, ở mọi vai. Ghép hai ảnh dù khác tone hẳn (một nền trắng một nền đen) vẫn
qua được cổng; `prepare/manifest.py::cap_ghep` cũng không còn loại cặp lệch
tone khỏi gợi ý. Việc chọn cặp cùng tone cho đẹp giờ là **gu**, không phải luật.

---

## 6. Mặt người

**Không dùng ảnh một người vô danh.** Ông Chủ bắt lỗi 03/09/2026: bìa tin GPT-6
Astra dùng mặt một người không liên quan, đọc ra như ảnh stock.

Có mặt người là **CHẶN**, trừ khi khai `"subject": "<tên>"` — người trong ảnh
phải là nhân vật **cụ thể được nhắc trong bài** (CEO phát biểu, tác giả paper,
founder). **Không gọi được tên thì không được dùng.** Khai sai tên là bịa đặt.

Tin model/sản phẩm: ảnh là **sản phẩm, screenshot, chart** — không phải mặt người.

**Mặt nào mới tính (LOW-279, 19/09/2026)** — đo 1.128 ảnh có mặt trên máy chủ, tin
Lovable mua Sutro bị loại oan ba ảnh thật của hãng:
- Mặt **thấp hơn 4% chiều cao ảnh** không tính: avatar trong giao diện app, người
  đứng xa trong ảnh toà nhà/sàn giao dịch — không ai nhận ra được là ai.
- **Ảnh đám đông / tập thể** (≥ 10 mặt, không mặt nào cao tới 10% ảnh) không đòi khai
  tên: không có "một người" nào là tiêu điểm. Họp 4–6 người lạ, hay một diễn giả
  nổi bật giữa khán giả, **vẫn phải khai tên**.
- **Tên IN trên ảnh** (dòng chú thích lower-third, bảng tên trước mặt) là bằng chứng
  tên như alt/caption: vision chép lại ở trường `printed_name`, chỉ chép chữ đọc được,
  không đoán tên từ khuôn mặt.
Ngưỡng nằm ở `subject_fit.faces_needing_name`, `count_faces` của cả ba vai đều gọi nó.

Code chỉ báo có mặt hay không; phán đoán "có đúng là nhân vật trong bài không"
là việc của vai. Cổng dùng YuNet, cần `assets/face_detection_yunet_2023mar.onnx`;
thiếu model thì cổng tự bỏ qua chứ không làm hỏng bản dựng — nhưng **luật vẫn
nguyên**.

---

## 6b. Chủ thể chính phải nằm TRÊN vùng chữ (LOW-273, 19/09/2026)

Ông Chủ, nguyên văn: *"ko chấp nhận những hình như thế này ở mọi designer. ko phải là tìm
hình có tỷ lệ 4:5, mà là tìm hình có main character đặt vừa trong 4:5"*.

- **Ảnh gần như trống** (vision `empty_share` ≥ `image_rules_kite.EMPTY_SHARE_MAX` = 0.60: logo nhỏ trên
  nền trơn) → chặn, `submit_common.check_empty_image`.
- **Chủ thể dưới vùng chữ** → chặn, `kite_submit.check_subject_above_text`. Người: hộp đầu từ mặt đo bằng code
  (`image_rules_kite.face_boxes`, YuNet; `subject_fit.head_box` nới 0.1 lần chiều cao mặt dưới cằm);
  còn lại hộp vision `subject_box`. Dung sai `image_rules_kite.SUBJECT_TEXT_TOLERANCE` = 2% khung.
- **Chỉ ảnh CHỤP** ở bìa/`figure`. Bảng/biểu đồ/bảng xếp hạng KHÔNG xét: ảnh chuẩn 19/09 (bảng
  DeepSeek, slide 07) chạy xuống dưới khối chữ và Ông Chủ coi là chuẩn.
- Đỉnh khối chữ `#figtxt` đo bằng CHÍNH Chromium + html của `render_edu.slide_read`
  (`kite_submit.measure_text_tops`, ~2 giây một bộ) vì chiều cao khối chữ chỉ trình duyệt biết.
  Đo 19/09 trên 4 bộ thật: 53–62% khung. Ảnh đặt như `render_edu.set_image` (dưới masthead,
  cao tự nhiên, cắt dưới). Không sửa `render_edu.py`.
- Ảnh chụp trang nguồn đã đệm viền (`unpadded_path`) chưa xét: hộp vision đo trên bản đệm.
- Manifest cũ (không `subject_box`, không mặt) → không chặn.

## 7. Không bao giờ để ra hai vùng riêng biệt

Mỗi tấm phải đọc ra **một mặt phẳng liền**. Cấm mọi thứ chia khung thành hai
mảng nhìn tách rời:

- **Không vùng đen riêng** đặt dưới ảnh để chứa chữ — mặc định là **đổi màu
  chữ**, không phủ thêm gì lên ảnh. Ông Chủ chốt việc này **một lần, áp dụng
  cùng lúc cho cả Dre và Kite** (08/09/2026, `e883880`) — **không phải luật
  riêng của Dre rồi lây sang Kite**. Mỗi khung tự đo trên pixel thật của chính
  nó, và mỗi khung dùng một cơ chế khác nhau để đạt "đủ tương phản" vì bố cục
  chữ của chúng khác nhau:
  - **Carousel (Dre)**: FG một màu cố định cho cả bộ; chỉ thêm lớp mờ+tinh khi
    đo THẬT trên pixel WYSIWYG thấy vùng dưới chữ không đủ tương phản hoặc quá
    "rối" (`carousel.py::_layer_if_can`).
  - **Hero cả hai kiểu** `quote` (06/09/2026) và `full_bleed` (07/09/2026): không còn
    TỐI nào cả — chỉ làm MỜ CỤC BỘ đúng dải chữ đè lên (`_open_region_text`, tan dần
    theo đường cong power, không đột ngột), màu chữ tự đổi tương phản với vùng
    đã mờ đó (`_color_change_background_hide_whole`, đo qua `_can_board_line` nên một mảng sáng cục
    bộ trong dải chữ không làm chọn sai màu). Phần ảnh phía trên dải chữ giữ nguyên
    sắc nét 100%.
  - **Carousel-edu (Kite)**: màu chữ đổi theo **từng dải dòng** (eyebrow, tiêu
    đề, accent, standfirst, caption, card, byline — không dồn vào một chỗ như
    Dre/Ethan, vì Kite chữ nhiều và đa dạng hơn hẳn nên không thể fix một màu
    cho cả bộ). Blur cả tấm ảnh làm nền **chưa bao giờ** là yêu cầu với Kite
    (Ông Chủ 12/09/2026, `0b395ad`, nguyên văn: *"blur toàn bộ tấm ảnh để làm
    nền cho hero slide CHƯA-BAO-GIỜ là việc được yêu cầu với Kite cả, chỉ cần
    chọn color palette tương đồng"*). Ngoại lệ **duy nhất, và chỉ của Kite**:
    ảnh **DỌC** chờm qua dòng chữ đầu thì riêng phần chờm được mờ + tint, tính
    từ dòng chữ đó trở xuống (`render_edu.py::anh_lam_nen`, `window.__datMan`).

  **Ba cơ chế riêng cho một nguyên tắc chung — đừng suy luận chéo.** Dre và
  Ethan giữ một màu chữ cố định vì chữ trên ảnh ít, đo một lần là đủ; Kite đổi
  màu theo từng dải vì chữ nhiều và đa dạng hơn — **cùng đi đến kết luận
  "không cần phủ lớp"**, bằng hai con đường khác hẳn nhau, không phải một bên
  chép lại bên kia. Ngoại lệ blur-khi-ảnh-dọc-chờm-chữ hiện chỉ được đo và xác
  nhận cho **hero của Kite** (bảng xếp hạng) — chưa ai đo nó cho Dre/Ethan,
  nên đừng tự suy ra là nó cũng áp dụng ở đó.
- **Không có màu nền đặc ở đâu hết.** Chỗ nào lớp ảnh sắc không phủ tới thì nền
  là bản cover **làm mờ** của chính tấm đó (`_layer_image`, dùng chung cho cả hai
  kiểu thẻ). Kiểu `full_bleed` từng có một nhánh lấy màu nền bộ nhận diện làm nền cho
  phần ảnh thiếu — ảnh 16:9 trên khổ 4:5 ra hơn nửa thẻ là màu đặc; bỏ
  07/09/2026.
- **Không vạch, không đường kẻ NGANG cắt qua khung** chia thẻ làm hai. Khung
  chữ nhật **khép kín** bao quanh khối chữ thì được (`quote` và `full_bleed`): nó là
  một vật nằm TRÊN mặt phẳng ảnh, không cắt mặt phẳng đó ra.
- **Không để lộ bản sao sắc nét của chính tấm ảnh** làm nền. Chỗ nào lớp ảnh sắc
  không phủ hết thì nền là chính tấm đó **làm mờ mạnh** — một mảng màu liền.
- **Không ghép hai ảnh lệch tone** (mục 5).
- **Không làm tối riêng một mảng** quanh chart để "cho nổi": mảng tối có mép
  thẳng chính là vùng thứ hai.

### 7.1 Ảnh rối: chỉ dùng khi hết ảnh sạch, dùng thì nền chữ đậm hơn (vẫn là overlay)

Ông Chủ 13/09/2026 (LOW-47), nguyên văn: *"không ưu tiên sử dụng tất cả những
ảnh nhìn rối, trong trường hợp buộc phải dùng, thì lớp nền của text phải làm
cho nghiêm chỉnh, đừng nham nhở"*.

- **Ảnh rối** = nhiều chữ in sẵn đè lên hình (tiêu đề báo, banner chữ,
  infographic nhồi chữ), chụp màn hình web/app nhiều chữ, cắt ghép nhiều hình,
  đồ hoạ nhồi nhét, **hoặc có một mảng sáng/tối/màu lệch tông rõ rệt so với
  xung quanh, trải rộng từ vài trăm px trở lên** (LOW-165, 15/09/2026: một
  khối ảnh khác sáng hơn/tối hơn/màu khác hẳn phần còn lại — loại mảng này lớp
  mờ cục bộ đằng sau chữ (`card._open_region_text`, bán kính `QUOTE_BLUR`) san
  phẳng KHÔNG NỔI dù mờ bao nhiêu, vì Gaussian blur chỉ đều được chi tiết cỡ
  bán kính của nó, không xoá được một khối lệch tông cỡ hàng trăm px). Biểu
  đồ/bảng số liệu gọn gàng, sáng tối đều **không** tính là rối. Chỉ con mắt
  phân biệt được: vision trả thêm dòng `CLUTTERED` (`prepare/vision.py`,
  `SENTENCE_CLUTTERED`), ghi vào manifest thành `cluttered`. (Tag từng gọi là
  `ROI` — đổi tên 15/09/2026 vì đó là "RỐI" gõ không dấu, trùng chữ với viết
  tắt tiếng Anh "return on investment", gây hiểu nhầm khi đọc code/manifest.)
- **Không ưu tiên:** ảnh rối không bao giờ là bìa. Làm thân chỉ khi **hết ảnh
  sạch** — `submit_common.check_image_fall` chặn Dre và Ethan nếu còn ảnh sạch dùng
  một mình được mà chưa dùng, chưa lên bài khác.
- **Rối nhưng đủ từ khoá thì được, và hợp làm bìa.** Ông Chủ cùng ngày, về
  chính đồ hoạ "Nvidia Weighs $10B...": *"ảnh này xứng đáng làm hero, thể hiện
  được đầy đủ mọi từ khoá quan trọng"*. Vision trả thêm dòng `TU_KHOA` (đọc ra
  đủ tên các hãng/nhân vật chính VÀ con số/sự kiện chính) → manifest
  `has_keywords`; ảnh rối có cờ này được miễn `check_image_fall`, được làm bìa (kể cả
  khi đo ra là chart), và bìa hiện **nguyên bề ngang** như slide thân —
  cover-crop cắt hai mép là mất chữ khoá ở mép.
- **Buộc dùng thì nền chữ đậm hơn — nhưng vẫn chỉ là OVERLAY** (LOW-330, Ông Chủ
  20/09/2026, xem bìa dcgr "Anthropic tự đặt thước đo": *"đừng để cho nền đặc, trông
  rất thiếu chuyên nghiệp"*). Chữ in sẵn trong ảnh vẫn lộ lem nhem qua lớp mờ mặc
  định, nên ảnh rối được phủ đậm nhất (80%: `carousel.OVERLAY_CLUTTERED`, thẻ Ethan
  `card.TEXT_OVERLAY_CLUTTERED`) — **đậm hơn, không phải đặc**. Ảnh luôn còn lộ qua.
  Áp cho **mọi** đường ra hình: slide thân, slide quote, **bìa** và **thẻ Ethan**.
  Đường nền đặc cũ (`_background_solid_below_text`, `_text_bg_strict`, máy tìm khoảng
  lặng `_timestamp_background_solid`) đã **gỡ khỏi code** — không còn chỗ nào sinh ra
  mảng màu đặc nữa.
- **Overlay TỰ LÙI, không để thành mảng màu.** Mức tối cố định vẫn thoái hoá thành nền
  đặc trên ảnh SÁNG và nhiều chi tiết: đo thật hai slide dcgr 20/09, vùng dưới chữ đi từ
  độ lệch 99,7 xuống 3,5 — mất 96% chi tiết, mắt nhìn ra một mảng trắng. Từ LOW-330
  `_overlay_text` đo lại chính kết quả trên pixel; còn đặc hơn `TEXT_BG_SAFE_OPACITY`
  (82%) thì hạ cả mờ lẫn tinh theo `OVERLAY_BACKOFF` rồi vẽ lại. Ảnh bình thường dùng
  ngay bước đầu (hệ số 1.0) nên **không** nhạt đi.
- **Cổng đo trên pixel thật:** `carousel._text_bg_report` + `_gate_text_background`
  chấm mọi slide VÀ bìa trước khi vẽ chữ. Phủ đặc hơn `TEXT_BG_MAX_OPACITY` (88%) là
  **lỗi CODE**, không phải lỗi spec: dừng, không gửi album. Trần diện tích: slide thân
  `TEXT_BG_MAX_SHARE` (42%), bìa `TEXT_BG_MAX_SHARE_COVER` (68%) vì hook cao hơn đoạn
  văn — trần **độ đặc** thì bìa và slide thân như nhau.

**Tự soi trước khi giao:** nhìn có thấy **một đường ranh ngang** nào không. Thấy
là hỏng, dựng lại — đừng gửi đi.

---

## 8. Ngưỡng kỹ thuật

| Tiêu chí | Ngưỡng | Vì sao |
|---|---|---|
| Cạnh ngắn ảnh | từ **1000px** trở lên | dưới mức đó phóng lên full bề ngang là vỡ nét |
| Đáy ảnh (25% dưới) | không quá sáng | chữ trắng đè lên qua màn tối sẽ nhạt |
| Mỗi slide/thẻ | **một hình duy nhất** | bắt theo nội dung tệp (hash) |

Về ảnh trùng: **không dùng cùng một ảnh cho hai slide**, và cũng **không dùng
hai crop khác nhau của cùng một tấm** — người xem vẫn nhận ra là một hình. Code
bắt được trường hợp đầu (hash), trường hợp sau **vẫn phải mắt người soi**.

Một bộ 6 slide cần 4–6 nguồn ảnh riêng biệt; xoay vòng 2 ảnh cho 6 slide là điểm
trừ trải nghiệm rõ rệt.

**Ảnh rỗng.** Bộ Broadcom dcgr 04/09/2026: bước chụp trả về ảnh **trắng trơn**
(2 màu, phẳng 100%), ra một slide không có gì ngoài chữ. Không cổng nào bắt —
trớ trêu là ảnh trắng lại là thứ "giống chart" nhất theo phép đo, nên cổng chart
cho qua ngay. Đo trên 76 ảnh trong kho: ảnh rỗng = 2 màu, ảnh thật ít màu nhất
= 40 màu — cách nhau 20 lần nên chặn được chắc (khác các phép đo "slide trống"
đã thử và bỏ vì chồng lấn với chart sạch). `capture_chart.py` nay tự dừng ngay khi
chụp ra ảnh rỗng; `check_blank_image` chặn thêm một lớp ở renderer. **Vẫn phải mở
ảnh ra xem trước khi ghi vào spec** — tên tệp không nói ảnh có gì.

---

## 9. Bảng cổng chặn (`image_rules_kite.py`)

| Cổng | Hàm | Chặn hay cảnh báo |
|---|---|---|
| **Ảnh rỗng** (trắng trơn / một màu) | `check_blank_image` | chặn — chạy **trước** cổng chart |
| Ảnh trùng (theo nội dung tệp) | `check_duplicate` | chặn |
| Cùng MỘT ảnh chụp tải từ hai nguồn (cắt/nén khác) lên hai slide (LOW-284) | `submit_common.check_same_photo` (`same_photo.py`: ORB+RANSAC ≥ 200 điểm VÀ tương quan pixel sau khi căn ≥ 0.82; chart/bảng xếp hạng không xét) | chặn |
| Chart/screenshot thiếu `chart: true` | `check_chart_integrity` | chặn |
| Khai `chart: true` mà máy không nhận ra chart | `check_chart_integrity` | **chỉ cảnh báo** (mục 3) |
| Ảnh gốc ngang đã crop, không khai `crop_ok` | `check_crop_landscape` | chặn |
| Mặt người mà không khai `subject` | `check_unnamed_face` | chặn |
| Sai dải tỉ lệ của khung | `check_aspect_ratio` | chặn |
| Chart đi một mình vào khung đặt chữ đè lên ảnh | `check_chart_standalone` | chặn (miễn ảnh `XH`) |
| Tin xếp hạng mà ảnh chính không phải bảng xếp hạng | `ethan_submit` / `dre_submit` | chặn |
| Bìa Kite không có `image` — mọi trường hợp, kể cả 0 ảnh (§1.2f) | `kite_submit` | chặn |
| Ảnh khái niệm đặt ở slide **thân** của Kite (§1.2c, nới lỏng LOW-58 15/09/2026) | `kite_submit` | **chỉ cảnh báo** |
| Dùng lại ảnh đã gửi trong 14 ngày (dHash, mọi bài, mọi vai) | `check_not_reused` | chặn |
| Cạnh ngắn <1000px | `check_resolution` | cảnh báo |

**Đã bỏ khỏi bảng này (13/09/2026, Ông Chủ: bỏ cấm đoán, mọi vai):**
`kiem_xuat_xu` (đúng khít 4:5/1:1 không dấu xuất xứ), `kiem_lech_tone` (ghép
lệch tone), `kiem_anh_thap` (ảnh quá ngang so với khung khoá khổ),
`kiem_day_sang` (đáy ảnh quá sáng — vốn chỉ cảnh báo, chưa từng chặn). Xem
§4.2 và §5.

Mỗi hàm trả về `(lỗi, cảnh báo)` và **không hàm nào biết đến canvas**, nên vai
nào cũng gọi được. Vai tự chọn cổng nào hợp với khung của mình rồi gộp lại.

Uỷ quyền crop bề ngang có **hai** đường, cổng nhận cả hai: khai `crop_ok` trong
spec, hoặc cắt bằng `crop_ratio.py --cat-ngang` (cờ đó đóng dấu vào PNG, đọc
bằng `allows_landscape_crop`). Trước 04/09 chỉ card.py đọc dấu thứ hai nên carousel vẫn
chặn oan một tấm đã được cho phép cắt.

**Vai nào đã gọi cổng nào** (cập nhật 04/09/2026 — luật Ông Chủ: *"ảnh do ai làm
mà chả phải đạt tiêu chuẩn"*):

| | Ethan (`card.py`) | Dre (`carousel.py`) | Kite (`render_edu.py`) | Itachi (`deck.py`) |
|---|:--:|:--:|:--:|:--:|
| ảnh rỗng · trùng trong bộ · độ nét | ✅ | ✅ | ✅ | ❌ |
| mặt người | ✅ | ✅ | ⚠️ | ❌ |
| trùng liên phiên (14 ngày) | ✅ | ✅ | ✅ | ❌ |
| tin xếp hạng → ảnh xếp hạng | ✅ | ✅ | – | ❌ |
| crop ngang | ✅ | ✅ | – | ❌ |
| chart một mình | ✅ | – | – | ❌ |
| `chart: true` · dải tỉ lệ | – | ✅ | – | ❌ |

(Hàng "xuất xứ · đáy sáng", "lệch tone" trong cột crop ngang, và "ảnh quá
ngang" đã bỏ 13/09/2026 — xem ghi chú dưới bảng cổng chặn ở trên.)

Dấu `–` là **không áp dụng cho khung đó**, khác hẳn `❌` là **chưa đấu**. Cột
Itachi còn trống nguyên.

`⚠️` của Kite là **cảnh báo, không chặn**: spec của `render_edu` không có trường
`subject` (khác `card.py`/`carousel.py`), nên chặn cứng sẽ khoá mọi ảnh sự kiện
mà vai không có đường khai. Muốn nâng lên ✅ thì phải thêm trường đó vào spec
trước. Kite không đi qua các cổng có dấu `–` vì `kind: figure` dán ảnh nguyên
khổ, không crop và không đè chữ lên ảnh.

Sửa một luật ở đây là **cả đội đổi theo** — đó là lý do tài liệu này tồn tại.
Đừng chép luật sang SKILL của vai. (SKILL **không** trỏ về đây: từ a757f61 luật
ảnh đi vào brief do `*_prepare.py` tự sinh, nên tệp này là nguồn cho **code và
người**, không phải cho prompt của vai.)

---

## 10. Cái gì KHÔNG thuộc tài liệu này

Bố cục là việc riêng của từng khung, và chúng **phải** khác nhau:

- **`hero-image` (Ethan)** — hook chữ to đè lên ảnh, nên **nửa dưới ảnh phải
  trống**; cách ảnh cao/thấp hơn khổ thẻ được điều phối; ngưỡng 50% khổ thẻ ở
  `--kieu quote`; cách tô tên thương hiệu; kicker.
- **`carousel` (Dre)** — màn tối liền mạch bắt từ ~42% chiều cao; khối chữ ≤30%
  neo từ dưới; chip tên kênh góc dưới-trái; chip category ở bìa; số slide tối
  thiểu và luật flagship 8–10 slide; slide quote ≥2.
- **`carousel-edu` (Kite)** — hệ design token, bộ khung magazine, tone/hero mỗi
  bộ một kiểu, `kind: figure`.

Ông Chủ đã chốt riêng: **bố cục bìa/hero là thứ đã duyệt** — không áp luật ≤30%
của carousel lên đó.
