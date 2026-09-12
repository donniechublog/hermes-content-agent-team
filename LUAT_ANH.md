# LUẬT ẢNH — tài liệu chuẩn dùng chung

Bộ tiêu chí ảnh của cả đội, **một nguồn sự thật duy nhất**. Ông Chủ chốt
04/09/2026: làm một bộ chung thay vì mỗi vai một bộ.

**Đường cắt — một câu:**

> *"Ảnh này có được dùng không"* → **chung**, nằm ở đây (và thành cổng chặn
> trong `luat_anh.py`).
> *"Đặt nó lên khung thế nào"* → **riêng** từng vai, nằm trong SKILL của vai đó.

**Ai phải theo:** mọi vai **tạo ra** ảnh mới — Ethan (`hero-image`, `card.py`),
Dre (`carousel`, `carousel.py`), Kite (`carousel-edu`, `render_edu.py`). Gin và
Itachi **không tạo ảnh**, chỉ chỉnh sửa trên ảnh gốc có sẵn (`doi_chu_anh.py` →
`deck.py`), nên không áp bộ này — họ có tiêu chí riêng của việc remake.

**Vì sao phải chung.** Đo thật trong repo trước khi gom (04/09/2026): cổng mặt
người, dấu vết crop, ảnh trùng, chart nguyên vẹn — cả bốn chỉ tồn tại trong
**đúng một tệp** (`carousel.py`), và nằm ở đó không phải vì thiết kế mà vì đó là
chỗ Ông Chủ bắt lỗi. Giá của việc chia lẻ đã trả trong đúng một ngày: hai phiên
làm hai lần cùng việc "nhận diện chart", một bản ra kết quả sai và chặn nhầm
việc đúng.

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
> ảnh nữa** — `anh_chuan_bi.py` tìm sẵn và brief chỉ đưa ra danh sách mã; vai
> chọn mã. Nên §1.1 → §1.4 dưới đây là **luật của engine**, và các lệnh CLI in
> kèm là **công cụ tay** để Ông Chủ hoặc người sửa code chạy lại một bước khi
> nghi ngờ — **không phải việc giao cho vai**. `task_bodies.py` cấm vai chạy
> chúng, và cấm đúng: chạy tay giữa chừng là đè lên kết quả engine.
>
> Đọc §1.2b trước nếu chỉ có thời gian đọc một mục: đó là hợp đồng thật đang chạy.

### 1.1 Luôn chạy `anh_bai.py` trước

Đừng tự đoán từ `image_url` trong task.

```bash
venv/bin/python anh_bai.py --tieu-de "<tiêu đề tin>" --link "<link gốc>" --json
```

Script lấy ảnh từ link gốc **và** từ các báo khác đưa cùng tin, lọc bỏ
logo/favicon/thẻ thương hiệu, đo kích thước thật rồi xếp hạng.

Vì sao phải tìm rộng: link Finn nhặt thường là trang tài liệu, và `og:image` của
nó là thẻ thương hiệu chung. Ví dụ thật: `api-docs.deepseek.com` trả
`deepseek-social-card.jpeg` cho mọi bài.

### 1.2 Trộn hai nguồn: official site + magazine

`anh_bai.py` fetch **tĩnh** — trang sản phẩm hiện đại (JS render) nó chỉ nhặt
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
`anh_chuan_bi.py` tìm, vai chỉ chọn mã — nên luật này là luật của **engine**:

- Chỉ lấy ảnh **trong bài** (`article`/`main`); loại quảng cáo, widget, sidebar,
  nav/footer, placeholder, onboarding, logo — theo cả tổ tiên DOM lẫn src/alt.
- **Trần mỗi trang**: bài gốc ≤ 4 ảnh, báo khác ≤ 3. Một URL không lấp cả kho.
- Báo khác phải **cùng tin**: chung ≥ 2 từ đặc trưng với tiêu đề gốc (Google
  News trả cả bài bệnh thận vì cùng chữ "AI").
- **Mỗi ảnh được nhìn** (vision): một câu "ảnh là gì" + LIÊN_QUAN. Không liên quan
  → ❌, `dre_nop.py` chặn. Ảnh trắng, ảnh rỗng bỏ ngay khi tải.
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
  đi (`anh_thuong_hieu.trang_cong_bo`, nối ở `vong_bu._them_trang_cong_bo`
  **trước** khi mở browser): Wikidata `P856` (website chính thức) → `/news/`,
  `/en/news/`, `/blog/`… hoặc RSS của hãng khi HTML chặn bot (openai.com) → khớp
  slug tên model đã tách (`xep_hang.tach_model`, bỏ hậu tố effort `-max`/`-high`,
  khoá ngắn nhất còn ≥ 2 mảnh để không khớp mọi bài của hãng). Trang đó vào
  `nguon_<id>.json` với `loai: "công bố"` (Miles cùng dùng), browser mở nó
  **trước** báo khác và lấy **4 ảnh** như bài gốc — chart benchmark ở đó là ảnh
  đắt nhất của tin model. Vì sao cần đường riêng: đo 11/09, trang
  `deepseek.com/en/news/deepseek-v4-1-flash/` có 4 chart 5148×2640… nhưng Google
  News không index nó và 13/14 báo đưa tin không link sang; engine cũ không có
  cách nào tới, Dre bị chặn "thiếu ảnh" với 5/8 tấm toàn logo + rack data center.
- **Truy vấn báo khác phải giữ tên model** (cùng LOW-21): tiêu đề Việt rơi về
  `nguon_bai._ten_rieng_khong_dau` thì token có gạch nối (`deepseek-v4.1-flash-max`)
  là **một** tên riêng, không xoá gạch rồi tách; Bing thử thêm bản bỏ gạch trước
  (`deepseek v4.1 flash max` → 6 báo, bản có gạch → 1).

### 1.2b2 Chụp chính trang nguồn ở khung mobile — nấc TRƯỚC ảnh khái niệm

Ông Chủ 06/09/2026, nhắc lại 12/09: *"vào trang nào chụp thì cũng hay duyệt theo
kích thước mobile, vì hình luôn đang ở ratio 4:5"* và *"có thể capture màn hình
mobile source gốc mà?"*. Trước 12/09 luật này chỉ sống trong `xep_hang.py` (trang
bảng xếp hạng) và §1.3 (tin model/xếp hạng), nên đường ảnh của **tin thường**
nhảy thẳng từ ảnh thương hiệu xuống ảnh khái niệm — tin *"AI giải toán giỏi, nền
toán học thì lệch chuẩn"* ra bìa là một tấm dây mạng phòng máy.

- **Khi nào**: sau vòng thương hiệu mà vẫn thiếu ảnh, **trước** vòng khái niệm.
  Khối lead là vật **thật** của chính tin; ảnh khái niệm thì không.
- **Chụp gì**: `chup_trang.chup_lead_mobile` mở trang ở khung điện thoại
  (`phien_browser.MOBILE_VIEWPORT` 414×896, DPR 3, UA iPhone — **một bản duy
  nhất**, dùng chung với `xep_hang`), clip **đúng khung ảnh hero** của bài —
  không kèm tít/byline. Ông Chủ 12/09 (sửa lại bản "khối lead" cùng ngày):
  *"dùng ảnh hero trong main article làm thumbnail cho hero slide, vì ảnh đó là
  chữ nhật ngang, nên nó hiển thị vừa vặn với nửa trên của hero slide"*.
- **Đặt lên bìa Kite thế nào** (`render_edu`, cùng ngày): ảnh full bề ngang neo
  dưới masthead, **nền là màu palette của theme** — *"blur toàn bộ tấm ảnh để làm
  nền cho hero slide CHƯA-BAO-GIỜ là việc được yêu cầu với Kite"*. Lớp mờ chỉ
  dành cho ảnh **dọc** kéo xuống quá vùng chữ (bảng xếp hạng): mờ phần dưới để
  title/subtitle hiện lên, bật/tắt theo dòng chữ đầu thật.
- **Bỏ nguồn khi**: trang là tường chặn bot (`phien_browser.bi_chan` — không tìm
  cách vượt), hoặc không đo được tít lẫn ảnh lead. Thử tối đa 3 trang: bài gốc
  rồi các báo khác cùng tin.
- **Lớp nổi** (banner đồng ý cookie, popup) chỉ bị **ẩn khi chụp**; không bấm
  "Đồng ý", không bấm nút đóng — đọc một trang thì không được thay người dùng
  chấp nhận điều khoản của họ.
- **Được làm bìa**, khác chart của người khác: `phan_loai` đọc ảnh chụp trang là
  "chart/screenshot" rồi dán *KHÔNG LÀM BÌA*, nhãn đó bị gỡ cho ảnh chụp nguồn —
  **trừ khi có mặt người**, lúc đó §6 vẫn đòi khai `nhan_vat`.
- **Không hỏi vision** "có liên quan bài không": đây là trang của **chính** tin.

### 1.2c Ảnh khái niệm: tin không có ảnh riêng thì tìm theo chủ đề, không bỏ

Ông Chủ 07/09/2026: *"trong resource gốc không có hình hoặc hình không đạt là bỏ
qua luôn. Nhắc tới Nhật thì tìm cờ hoặc bản đồ nước Nhật, Nhật đầu tư xây
compute thì lấy hình datacenter"*. Trước 04/09 Dre tự làm việc này bằng
web_search; từ kiến trúc 3 lớp vai không còn công cụ, nên nó là luật của
**engine** (`anh_khai_niem.py`, chạy trong `anh_chuan_bi.py`):

- **Khi nào**: sau vòng tìm rộng **và sau nấc chụp trang nguồn (§1.2b2)** mà vẫn
  thiếu ảnh, *hoặc* có ảnh mà không tấm nào làm bìa/hero được. Không chạy khi tin
  đã có ảnh riêng đủ dùng. Đây là nấc **cuối**, không phải nấc đầu: từ khoá sai
  thì cả slide nói sai chuyện (xem `\bhack` bắt nhầm "reward hacking", 12/09/2026).
- **Từ khoá**: nước/khối được nhắc → cờ đang bay; chủ đề → vật thể **chụp được**
  (data center → dãy rack, chip → wafer, chứng khoán → sàn giao dịch, chính
  sách → toà nhà quốc hội…). Bảng cố định trước, model text bù tới 3 từ khoá.
  Không tìm khái niệm trừu tượng (funding, partnership): Commons chỉ trả minh hoạ tệ.
  Minh hoạ biên tập CÓ SẴN (vẽ tay/digital, kiểu The Economist) được dùng như ảnh
  chụp — §0 cấm *tự vẽ*, không cấm *dùng*; vẫn gạt icon/clipart/sơ đồ/logo (Ông
  Chủ 12/09/2026). Từ khoá LLM bị CẤM đề xuất phần cứng ngành AI (rack, datacenter,
  GPU, chip, robot) khi tin không nói về phần cứng — "tin nào cũng AI" không phải
  lý do ra phòng máy.
- **Nguồn**: chỉ Wikimedia Commons, chỉ JPEG/PNG cạnh ngắn ≥ 700, tên tệp phải
  chứa ≥ 2 từ đặc trưng của từ khoá và không phải logo/CGI/variant/bản đồ phẳng.
  Đây là **ảnh thật** — cờ thật, toà nhà thật — nên không vi phạm §0.
- **Nhìn**: vision được hỏi câu riêng ("có đúng là *cờ Nhật* chụp thật, hợp làm
  bìa không"), không hỏi "có phải ảnh của tin" vì chắc chắn không phải. Ảnh có
  mặt người hay là đồ hoạ → bỏ.
- **Chỗ đứng**: nhãn 🧭 ẢNH KHÁI NIỆM, chỉ **bìa/hero** (ngang thì chỉ ghép dọc),
  không vào slide thân; gợi ý bìa xếp **sau** mọi ảnh riêng của tin; caption
  "via Wikimedia Commons". Vai vẫn chỉ chọn mã, và vẫn được nói "thiếu ảnh" nếu
  thấy cờ/bản đồ không hợp tin.
- **Có cổng chặn thật, không chỉ là câu dặn** (`kite_nop`, §9): `image` là ảnh
  khái niệm ở slide khác slide 1 → chặn. Đo 10/09/2026 ở đường Kite: cờ Nhật đặt
  vào `figure` thân đi qua cổng **không một dòng lỗi**, vì nó là **ảnh chụp
  thật** nên sạch với mọi cổng kỹ thuật (rỗng · trùng · độ nét · mặt người) —
  cái sai của nó là **chỗ dùng**, mà chỗ dùng thì chỉ tài liệu này biết. Ở
  `figure` thân nó đọc như bằng chứng của bài, trong khi nó chỉ minh hoạ chủ đề.
  Vẫn để nó trong `kite_chuan_bi.hinh_that` (ứng viên cho `image` của **bìa**) và
  brief ghi thẳng nhãn 🧭 ở dòng của nó — loại khỏi danh sách là mất luôn đường
  lên bìa, tức mất cả tác dụng của §1.2c.
- **§1.2e không được ép nó xuống thân**: xem chỗ `hinh_phai_dung` ở mục đó.

### 1.2d Ảnh thương hiệu: tin về hãng lớn thì tìm trụ sở của chính hãng đó

Ông Chủ 09/09/2026: *"Dre vẫn chưa tự tìm thêm hình liên quan khi làm các nội
dung có Big Brand"*. Sáng hôm đó năm tin liên tiếp (Qualcomm × Amazon, xưởng
Samsung, kiện Anthropic, DeepSeek gọi vốn, Philippines) đều dừng ở nút *"chỉ 2/5
ảnh thật dùng được — Kite vẽ vector / Dre làm với N ảnh"*, toàn hãng mà Commons
có hàng trăm ảnh thật. Luật của **engine** (`anh_thuong_hieu.py`):

- **Khi nào**: **mọi tin nhắc tới một hãng trong watchlist**, kể cả khi bài gốc
  đã đủ ảnh — chạy sau vòng tìm rộng, **trước** ảnh khái niệm. Ông Chủ
  10/09/2026, lần thứ hai của cùng một câu: *"Dre vẫn ko chịu đi tìm các hình
  liên quan như logo, brand, founder, trụ sở... của chủ đề được nhắc tới"*. Bản
  09/09 treo vòng này sau điều kiện *thiếu ảnh*, nên tin nào bài gốc đủ ảnh là
  không bao giờ hỏi tới Commons/Wikidata — mà vai thì bị cấm tự tải thêm, nên bộ
  ảnh giao cho vai trắng trơn dù máy móc đã sẵn. Tin không nhắc hãng nào:
  `hang_trong_tin` trả rỗng, vòng thoát ngay, không một request nào.
- **Trần**: thêm tối đa 4 ảnh một bộ (`TOI_DA_THEM_TH`), và tổng ảnh không quá
  `TOI_DA_ANH + 4`. Riêng việc **mở browser đi chụp bảng xếp hạng** làm ảnh bối
  cảnh thì vẫn chỉ chạy khi **thật sự thiếu ảnh** — đó là phần đắt.
- **Chỗ đứng**: ảnh của hãng xếp **sau** ảnh riêng của tin trong gợi ý bìa
  (`goi_y_bia`), nên bài có ảnh riêng tốt không bị chúng chiếm bìa.
- **Hãng nào**: mọi hãng trong `scan_business.WATCHLIST` mà tin nhắc tới, tối đa
  3, theo thứ tự xuất hiện — **không phải chỉ tên riêng đầu tiêu đề**. Tên
  model/chip quy về hãng chủ (Claude → Anthropic, Xring → Xiaomi). Tên trần mà
  watchlist không giữ (Google, Meta, Snapdragon) bù bằng `TEN_THEM`.
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
     Đi **kèm tên**, nên khai được `nhan_vat`: đúng ngoại lệ của §6, khác hẳn
     mặt vô danh. Bỏ người **đã thôi chức** (qualifier `P582`) — hỏi CEO OpenAI
     mà không lọc thì Wikidata trả cả CEO tạm quyền cũ, brief ghi sai tên.
     Brief vẫn dặn: **bài không nhắc tên người này thì bỏ**.
  3. 📊 **bảng xếp hạng có model của hãng** — mượn `xep_hang.py` chụp bảng, chỉ
     cho hãng **có làm model** (`hang_co_model`; Qualcomm/TSMC không khớp hàng
     nào). **Chỉ nhận ảnh chụp thật**: hết đường thì `tim_va_chup` tự dựng *thẻ
     dự phòng* "`<model> #<hạng>`" — thẻ đó cho một tin KHÔNG PHẢI tin xếp hạng
     là bịa ra một thứ hạng không ai nói, nên phải vứt.
  4. 🔖 **thẻ logo** — logo chính thức (`P154`) đặt trên nền trơn, dồn lên nửa
     trên để hook đè nửa dưới; nền sáng hay tối **chọn theo độ sáng của chính
     logo** (wordmark chữ đen trên nền tối là mất chữ). Cùng nguyên tắc với
     `xep_hang.the_du_phong`: không thêm một nét nào của ta, chỉ là chỗ đặt —
     nên không vướng §0. Là đường **cuối**, chỉ khi không còn ảnh chụp nào.
- **Lọc**: tên tệp phải chứa **đủ** từ đặc trưng của tên hãng theo *biên giới từ*
  ("Arm" ≠ "Armstrong"); bỏ đồ hoạ (`TEN_LOAI`); bỏ **nhiễu theo hãng** (Amazon →
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
  `luat_anh.dem_mat` trả `None` khi thiếu cv2/model và §6 cho phép cổng mặt tự
  tắt, nên lấy `mat == 0` làm "không phải chân dung" là bỏ câm lặng mọi chân
  dung trên máy thiếu cv2. Để **con mắt** phán, bằng câu hỏi riêng cho từng loại
  tư liệu (`cau_hoi_vision`) — câu chung hỏi "có phải ảnh của tin không" thì
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
`img.json` mang `chuyen_tu` (tên vai cũ) — **xong.json không có**, vì nút được
bấm sau khi engine đã ghi xong. Đọc nhầm chỗ là cổng dưới không bao giờ bật.

- **Cả n mã hình thật đều phải xuất hiện** trong spec, không phải "ít nhất một".
  Cổng cũ (§ `kite_nop`) chỉ đòi một tấm, nên Kite đặt đúng một tấm lên bìa rồi
  vẽ vector cả thân — đúng cái bị chê.
- **Phải có hình ở BODY**, không chỉ ở bìa: mỗi tấm một slide `figure`.
- **Trần 6 tấm** (`TOI_DA_EP_HINH`): bộ chỉ được 6..10 slide, trừ bìa và cta còn
  8. Ép hết khi engine tìm được 9 tấm là hai cổng đá nhau, vai không có đường nộp.
- Chỉ ép ảnh **đã được nhìn** (`lien_quan is True`). Vision tắt thì mọi ảnh là
  `None`, ép lúc đó là đẩy quảng cáo/widget lên slide — cùng bài học với cổng
  "ít nhất một".
- **Không ép ảnh khái niệm** (§1.2c). Cổng này đòi mỗi mã một slide `figure`
  *và* ít nhất một tấm ở **thân**, nên để ảnh khái niệm lọt vào tập bị ép là
  **ép nó xuống đúng chỗ §1.2c cấm** — hai cổng đá nhau. Đo 10/09/2026: tin
  chuyển sang Kite mà engine chỉ tìm được **một tấm cờ nước** thì đường nộp
  *duy nhất* qua được là đặt cờ vào `figure` thân. Nó rơi khỏi
  `hinh_phai_dung` và về bìa qua `hinh_hero` (§1.2f) — đó là đường nộp còn lại.
  **Ảnh thương hiệu thì ở lại**: §1.2d cho nó vào thân, vì nó là ảnh thật của
  chính hãng được nhắc trong tin.
- **Trừ tấm đã lên bìa** (`hinh_hero`, §1.2f): cùng một ảnh không lên được hai
  slide (`kiem_trung` §8), nên để nó trong tập bị ép là đòi một thứ bất khả. Hệ
  quả: tin chỉ có **đúng một** tấm thì tập này **rỗng** — tấm đó lên bìa và thân
  không đòi gì nữa.
- `kite_chuan_bi.hinh_phai_dung` là **một nguồn** cho cả brief lẫn cổng chặn, và
  khung spec in sẵn một `figure` cho mỗi mã — đừng bắt vai tự suy ra "ba hình thì
  ba slide". `_ep_tho` là tập chưa trừ bìa, chỉ `hinh_hero` dùng (cắt vòng gọi).

Brief của Kite còn ghi rõ **từng tấm là loại gì** (🏢 cơ sở · 👤 chân dung ·
📊 bảng xếp hạng · 🔖 thẻ logo, §1.2d), vì caption của chúng khác hẳn nhau: chú
thích một thẻ logo thành "ảnh trụ sở" là sai sự thật.

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

Bản trước (08/09) chỉ chỉ định hero khi ảnh có `paper_hinh` — tức **chỉ bài
arxiv** (§1.4). Mọi tin còn lại thì brief nói "bìa `image` **hoặc** `figure`"
(tuỳ chọn) và `kite_nop` chỉ đòi "dùng ít nhất một ảnh ở đâu đó", nên nhét hết
ảnh vào `figure` thân rồi vẽ sơ đồ lên bìa là **hợp lệ**. Đo 10/09: ba ca — tin
thường, tin chuyển sang vì thiếu ảnh, và ảnh khái niệm đặt nhầm vào thân — đều
qua cổng không một dòng lỗi.

- **`kite_chuan_bi.hinh_hero`** chọn tấm lên bìa, **một nguồn** cho cả brief lẫn
  cổng chặn (cùng lý do với `hinh_phai_dung` §1.2e). Thứ tự: hình paper (§1.4) →
  ảnh riêng của tin → ảnh thương hiệu (§1.2d) → ảnh khái niệm (§1.2c); hai loại
  bù xếp sau mọi ảnh riêng, đúng như hai mục đó ghi.
- **Cổng**: slide `cover` không có `image` → `kite_nop` chặn, **luôn**. Cổng đòi
  **có** ảnh ở bìa, không đòi đúng mã nào — `hinh_hero` chỉ gợi ý. Ba lời báo
  khác nhau theo nguyên nhân, vì việc phải làm khác nhau: có ứng viên → *đặt mã
  này vào slide 1*; ảnh có mà **vision chưa nhìn** → *bật vision rồi
  `--lam-moi`*; **0 ảnh** → *chạy lại vòng tìm ảnh, vẫn trắng thì `kanban_block`*.
- Chỉ ép ảnh **đã được nhìn** (`lien_quan is True`), trừ hình paper (bóc thẳng từ
  PDF nên không thể là quảng cáo). Vision tắt thì mọi ảnh là `None`, và cổng
  **vẫn chặn** — chỉ là không chỉ định mã nào: đẩy một banner chưa ai nhìn lên
  bìa còn tệ hơn vẽ vector. Đây là hỏng khâu vận hành (thiếu `OPENAI_API_KEY`),
  không phải một lựa chọn bố cục.
- **Kite phải TỰ TÌM LẠI, không được thừa kế thất bại của vai cũ.** Ông Chủ
  10/09/2026, ngay sau khi xem cổng chặn ở trên: *"Dre tìm được ảnh đúng, nên kỹ
  năng tìm ảnh đó dùng được. ko có lý gì mà ko tìm được ảnh để báo hỏng"*. Đo cả
  chuỗi hôm đó, và đây là chỗ hỏng thật sự:
  1. `anh_chuan_bi.chay` trả **thẳng** `xong.json` cũ khi tệp đã có
     (`if xong.exists() and not lam_moi`);
  2. task body giao cho Kite chạy `kite_chuan_bi.py <id>` — **không** `--lam-moi`;
  3. `tao_task_kite` còn ghi vào body *"tin này không có ảnh thật dùng được: vẽ
     vector hoàn toàn"* — chính hệ thống giục vai làm thứ mục này cấm.

  Nên tin chuyển sang Kite **đọc lại đúng kết quả đã thất bại của vai cũ** và
  vòng tìm ảnh không bao giờ chạy lần nữa. Kỹ năng có sẵn, chỉ là không ai gọi
  nó cho Kite. Mà **hai vai dừng ở hai ngưỡng khác nhau**: vai cũ cần đủ ~5 ảnh
  cho carousel rồi mới thôi, Kite chỉ cần **một tấm lên bìa** — rẻ hơn hẳn, nên
  "vai cũ không đủ" không hề có nghĩa "Kite không đủ".
  `kite_chuan_bi.bao_dam_co_bia` chạy lại vòng tìm **đúng một lượt** khi chưa có
  tấm nào lên bìa được, trước khi in brief.
- **Chặn cứng không làm vai treo**: nước đi đầu là *tìm lại*, không phải *báo
  hỏng*. Hết đường thì `nop_chung.dem_vong_loi` đếm ba vòng lỗi *y hệt nhau* rồi
  bảo vai gọi `kanban_block` và đẩy lên Ông Chủ — đúng đường đã dành sẵn cho
  *"cổng đang đợi một thứ không thể có"*. Engine về trắng cho một tin có thật là
  việc của Ông Chủ, không phải của vai.

**Đo 10/09/2026 — máy móc tìm ảnh KHÔNG hỏng, đừng đi vá nhầm chỗ.** Chín tiêu
đề tin thật lấy từ chính tài liệu này (Philippines 34 tỷ, Qualcomm × Amazon,
xưởng Samsung, kiện Anthropic, DeepSeek gọi vốn, Nemotron, Google Antigravity,
Thinking Machines, SWE-bench) đều **ra từ khoá** qua `hang_trong_tin` (§1.2d)
hoặc `tu_khoa_khai_niem` (§1.2c) — 9/9, **không cần LLM**, chỉ bảng tĩnh. Và
`anh_khai_niem.anh_khai_niem("flag of Philippines")` trả về ảnh thật từ Commons.
Chỗ trắng chỉ xuất hiện với tiêu đề *không nhắc hãng nào trong watchlist, không
nhắc nước nào, và không khớp mẫu `CHU_DE` nào* — chưa gặp trong lưu lượng thật.
Nên đừng nhét từ khoá chung chung vào `CHU_DE` để "cho chắc": Commons trả minh
hoạ tệ cho khái niệm trừu tượng (§1.2c), và thêm một từ khoá sai làm hỏng đúng
cái §0 giữ.
- **Hai cổng không được đá nhau**: tin chuyển sang Kite đòi hình thật nằm ở slide
  **thân** (§1.2e), mà cùng một ảnh không lên được hai slide (`kiem_trung` §8).
  Tấm nào bị thân giữ độc quyền thì **lùi xuống ứng viên kế tiếp**, không bỏ
  cuộc ngay: ảnh khái niệm không nằm trong tập bị ép (§1.2c cấm nó ở thân) nên
  tin có một ảnh riêng + một ảnh khái niệm thì ảnh riêng ở thân còn **ảnh khái
  niệm lên bìa** — đúng chỗ của nó, và cả hai tấm đều được dùng.
- **Hết ứng viên thì BÌA THẮNG**, không phải thân. Tin chỉ có **đúng một** tấm:
  tấm đó lên bìa, và `hinh_phai_dung` trừ nó ra nên thân không đòi gì nữa. Đòi
  của §1.2e sinh ra từ ca **nhiều** tấm mà Kite chỉ dùng một; còn một tấm thì nó
  **vẫn được dùng**, chỉ là dùng ở bìa. Bản 10/09 sáng cho thân thắng ở ca này —
  đó chính là một trong ba ca ra hero vector mà Ông Chủ chặn.
- Bìa có ảnh thì **cả bộ không vẽ hero art** (`chon_theme_tu_dong` trả
  `hero=None`), nên đây là thay thế chứ không phải thêm một lớp trang trí.

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

Từ 06/09 việc này là của **engine**, không phải của vai: `xep_hang.py` chạy
trong `anh_chuan_bi.py` khi tiêu đề là tin xếp hạng. Nó tách tên model, đi qua
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
`nguon_dung=chup_xep_hang|the_xep_hang` kèm model/hạng/site.

Vai chỉ còn một việc: **`"anh": "XH"`** (hero) / **bìa `"anh": "XH"`** (carousel).
`ethan_nop` / `dre_nop` chặn ảnh chính khác khi `xong.json` có `tin_xep_hang` —
không phải "chưa đạt", là **sai đề tài**. `XH` được miễn hai cổng cấm chart lên bìa/hero vì nó *là* chủ
thể của tin; vẫn chịu mọi cổng khác.

Chart đi đâu, theo khung:

- **Hero (`quote`/`tran`)** — chart ở `anh`, thêm `anh2` là một ảnh ngang cùng
  tone: script ghép dọc, chart nằm nửa trên **nguyên vẹn**. `ethan_nop.py` gợi ý
  sẵn cặp ghép (`cap_ghep_hero`).
- **Carousel slide thân** — `"chart": true`, dán full bề ngang nguyên vẹn.

Nguồn không có sẵn ảnh chart thì **chụp từ chính trang nguồn**: engine
`anh_chuan_bi.py` mở browser thật và tự chụp `figure/table/canvas/svg` (mã ảnh
loại `chart`, đóng dấu `chup_chart`). Chụp tay thì dùng `chup_chart.py` — full
chiều rộng trước, chiều cao xét sau (mục 2).

### 1.4 Bài arxiv: hình trong paper trước, trang bìa sau

**Ảnh thật của một bài paper là hình của chính nó** — Figure 1 (thường là biểu đồ
kết quả tổng), Figure 2, Figure 3. Do nhóm tác giả vẽ, bằng số của họ: không ảnh
nào của tin đó đúng hơn được nữa. Engine bóc thẳng từ PDF, tự động cho mọi tin
arxiv/PDF; chạy tay thì:

```bash
venv/bin/python arxiv_hinh.py --link "<link arxiv>" --ra /tmp/hinh
```

**Figure 1 là hero.** Kite đặt nó vào `image` của slide `cover`, kèm caption
`"Figure 1 trong paper · via <ai>"` — bìa lấy chính tấm hình đó làm hero thay vì
vẽ hero art. Ông Chủ 08/09/2026: *"ngay đầu paper có image mà Kite không dùng để
làm hero"*. Các hình còn lại để cho slide `figure`.

Chỉ **hình**, không bảng: chú thích bảng khi ở trên khi ở dưới tuỳ nơi đăng, và
từng dòng của bảng trông y như một dòng thân bài — không có mốc nào chắc để chặn
vùng cắt, mà cắt sai một cái bảng là dán lên slide một bảng **khác** với bảng
trong bài.

Không bóc được hình nào (paper ảnh scan, PDF hỏng) thì mới tới **trang bìa**
paper — ngoại lệ duy nhất của luật "không tự vẽ":

```bash
venv/bin/python arxiv_bia.py --link "<link arxiv>" --out /tmp/src_bia.png
```

---

## 2. Chụp chart: full chiều rộng trước, chiều cao xét sau

**Luật Ông Chủ 04/09/2026.** Bề ngang của một chart là **nội dung**: trục, nhãn
chuỗi, cột cuối của bảng, cái điểm được tô sáng mà cả bài đang nói tới. Cắt mất
một phần bề ngang thì thứ còn lại không phải thiếu một tí — **nó nói sai**.
Chiều cao thì khác: cắt bớt mép trên/dưới thường chỉ mất khoảng thở.

Đừng chụp bằng khung mặc định của công cụ nào. Khung mặc định luôn hẹp
(`chup_trang.py` trong repo này đặt 820px), và một chart rộng 1400px trong khung
đó thì hoặc bị cắt, hoặc bị trang reflow xuống bố cục điện thoại — lúc đó có
chụp đủ bề ngang cũng không còn là cái chart trên desktop nữa.

```bash
venv/bin/python chup_chart.py --url "<trang có chart>" --ra chart.png
venv/bin/python chup_chart.py --url "<trang>" --chon "figure.chart" --ra chart.png
venv/bin/python chup_chart.py --url "<link ảnh trực tiếp>" --ra chart.png
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

### Cách nhận diện (`luat_anh.la_chart`), đo trên bản thu nhỏ 480px

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

- **Hero (`quote`/`tran`)**: chart đi một mình bị chặn — hook đè lên thì chart
  nằm dưới chữ, đọc không ra. Ghép dọc bằng `--image2`, hoặc để chart cho carousel.
- **Carousel slide thân**: khai `"chart": true`. Ảnh được dán **full bề ngang
  nguyên vẹn**, không crop, không ép tỉ lệ; phần trên/dưới là chính ảnh làm mờ.
- **Carousel bìa**: chart làm bìa bị chặn — ghép dọc `"images": [a, b]`, hoặc
  đổi bìa và để chart ở slide thân.
- **Ảnh ghép dọc** được miễn hẳn cổng này: nó đã nguyên vẹn + full bề ngang sẵn.

Kiểu `quote` (mặc định) không còn màn tối nữa (06/09/2026): chart hiện
NGUYÊN VẸN từ đầu tới sát mép khối chữ, chỉ đúng dải chữ đè lên mới bị làm mờ
cục bộ (không phải làm tối) — trục x/nhãn/chú thích của chart phía TRÊN khối
chữ không hề bị ảnh hưởng. Kiểu `tran` vẫn còn màn tối riêng của nó và tự lùi
điểm bắt đầu xuống dưới mép chart để đáy chart không bị làm tối.

---

## 4. Tỉ lệ và crop

### 4.1 Crop chỉ được làm qua `crop_ti_le.py`

```bash
venv/bin/python crop_ti_le.py --anh vao.jpg --ra ra.png              # 1:1, giữa
venv/bin/python crop_ti_le.py --anh vao.jpg --ra ra.png --ti-le 4:5  # 4:5
venv/bin/python crop_ti_le.py --anh vao.jpg --ra ra.png --cx 0.62    # tâm lệch phải
```

Crop là **chọn khung ảnh thật**, không phải bịa ảnh — vẫn đúng luật "không tự
vẽ". Chọn `--cx/--cy` để ôm đúng chủ thể vào khung.

**Chỉ crop ảnh chụp KHÔNG có chữ** (sản phẩm, sự kiện, trụ sở). Ảnh có chữ
(chart, bảng, slide, banner, screenshot UI có tiêu đề) **không crop** — ghép dọc.

**`crop_ti_le.py` tự chặn ở đầu kia:** mặc định nó **chỉ cắt chiều cao**. Ảnh gốc
ngang (tỉ lệ ≥1.4) mà đòi cắt bề ngang thì script dừng — bề ngang của chart/bảng
là nội dung. Muốn cắt bề ngang phải thêm `--cat-ngang`, và **chỉ được dùng cho
ảnh chụp người/sản phẩm không có chữ**. Nên với ảnh ngang, đường đúng gần như
luôn là **ghép dọc** hoặc `"chart": true`, không phải crop.

Ảnh gốc rõ ràng **ngang** (tỉ lệ ≥1.4) mà đi qua crop thì bị chặn, trừ khi khai
`"crop_ok": "<lý do>"` — chỉ dành cho ảnh chụp người/sản phẩm không có chữ.

### 4.2 Dấu xuất xứ — vì sao không được cắt tay

Mọi công cụ sinh ảnh của đội **tự đóng dấu vào PNG**: `crop_ti_le.py`,
`arxiv_hinh.py`, `arxiv_bia.py`, `chup_chart.py`, `doi_chu_anh.py`, và ảnh ghép dọc.

Trước 04/09/2026, cổng crop chỉ đọc dấu của `crop_ti_le.py`. Vai cắt bằng
PIL/cv2/ImageMagick thì không để lại dấu, cổng không thấy gì để chặn — tức cổng
**phạt người làm đúng và tha người lách**. Cả 7 ảnh bộ K2 Horizon đều đúng khít
4:5 (0.7996–0.8004) mà không ảnh nào có dấu.

Nay: **ảnh đúng khít 4:5 hoặc 1:1 mà không có dấu xuất xứ nào → CHẶN.** Ảnh thật
tải về gần như không bao giờ đúng khít (đo trên kho ảnh của đội: 1.16, 1.50,
1.78, 1.91…). **Không cờ nào miễn trừ, kể cả `crop_ok`** — `crop_ok` nói "tôi cố
ý crop", cổng này nói "crop bằng gì thì không ai biết".

Đường thoát rẻ: ảnh gốc **vốn đã** 4:5/1:1 thì vẫn chạy qua `crop_ti_le.py` một
lần để đóng dấu — cắt 0, không mất gì.

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

**Điều kiện duy nhất: hai hình không được quá khác tone.** Lệch tone (một nền
trắng một nền đen, gam màu khác hẳn) đọc ra như hai vùng riêng biệt. Ưu tiên
cùng nền sáng/tối, cùng gam màu, tốt nhất là hai slide cùng một bộ. Từ 04/09
đây là **cổng chặn dừng hẳn** ở cả hero lẫn carousel (trước chỉ cảnh báo nên vai
cứ cho qua). Bị chặn thì **đổi ảnh** — không có cờ nào để lách.

---

## 6. Mặt người

**Không dùng ảnh một người vô danh.** Ông Chủ bắt lỗi 03/09/2026: bìa tin GPT-6
Astra dùng mặt một người không liên quan, đọc ra như ảnh stock.

Có mặt người là **CHẶN**, trừ khi khai `"nhan_vat": "<tên>"` — người trong ảnh
phải là nhân vật **cụ thể được nhắc trong bài** (CEO phát biểu, tác giả paper,
founder). **Không gọi được tên thì không được dùng.** Khai sai tên là bịa đặt.

Tin model/sản phẩm: ảnh là **sản phẩm, screenshot, chart** — không phải mặt người.

Code chỉ báo có mặt hay không; phán đoán "có đúng là nhân vật trong bài không"
là việc của vai. Cổng dùng YuNet, cần `assets/face_detection_yunet_2023mar.onnx`;
thiếu model thì cổng tự bỏ qua chứ không làm hỏng bản dựng — nhưng **luật vẫn
nguyên**.

---

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
    "rối" (`carousel.py::_lop_neu_can`).
  - **Hero cả hai kiểu** `quote` (06/09/2026) và `tran` (07/09/2026): không còn
    TỐI nào cả — chỉ làm MỜ CỤC BỘ đúng dải chữ đè lên (`_mo_vung_chu`, tan dần
    theo đường cong power, không đột ngột), màu chữ tự đổi tương phản với vùng
    đã mờ đó (`_mau_doi_nen`). Phần ảnh phía trên dải chữ giữ nguyên sắc nét 100%.
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
  là bản cover **làm mờ** của chính tấm đó (`_lop_anh`, dùng chung cho cả hai
  kiểu thẻ). Kiểu `tran` từng có một nhánh lấy màu nền bộ nhận diện làm nền cho
  phần ảnh thiếu — ảnh 16:9 trên khổ 4:5 ra hơn nửa thẻ là màu đặc; bỏ
  07/09/2026.
- **Không vạch, không đường kẻ NGANG cắt qua khung** chia thẻ làm hai. Khung
  chữ nhật **khép kín** bao quanh khối chữ thì được (`quote` và `tran`): nó là
  một vật nằm TRÊN mặt phẳng ảnh, không cắt mặt phẳng đó ra.
- **Không để lộ bản sao sắc nét của chính tấm ảnh** làm nền. Chỗ nào lớp ảnh sắc
  không phủ hết thì nền là chính tấm đó **làm mờ mạnh** — một mảng màu liền.
- **Không ghép hai ảnh lệch tone** (mục 5).
- **Không làm tối riêng một mảng** quanh chart để "cho nổi": mảng tối có mép
  thẳng chính là vùng thứ hai.

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
đã thử và bỏ vì chồng lấn với chart sạch). `chup_chart.py` nay tự dừng ngay khi
chụp ra ảnh rỗng; `kiem_anh_rong` chặn thêm một lớp ở renderer. **Vẫn phải mở
ảnh ra xem trước khi ghi vào spec** — tên tệp không nói ảnh có gì.

---

## 9. Bảng cổng chặn (`luat_anh.py`)

| Cổng | Hàm | Chặn hay cảnh báo |
|---|---|---|
| **Ảnh rỗng** (trắng trơn / một màu) | `kiem_anh_rong` | chặn — chạy **trước** cổng chart |
| Ảnh trùng (theo nội dung tệp) | `kiem_trung` | chặn |
| Chart/screenshot thiếu `chart: true` | `kiem_chart` | chặn |
| Khai `chart: true` mà máy không nhận ra chart | `kiem_chart` | **chỉ cảnh báo** (mục 3) |
| Ảnh gốc ngang đã crop, không khai `crop_ok` | `kiem_crop_ngang` | chặn |
| Ảnh đúng khít 4:5/1:1 mà không có dấu xuất xứ | `kiem_xuat_xu` | chặn |
| Ghép hai ảnh quá khác tone | `kiem_lech_tone` | chặn |
| Mặt người mà không khai `nhan_vat` | `kiem_mat_nguoi` | chặn |
| Sai dải tỉ lệ của khung | `kiem_ti_le` | chặn |
| Chart đi một mình vào khung đặt chữ đè lên ảnh | `kiem_chart_mot_minh` | chặn (miễn ảnh `XH`) |
| Ảnh quá ngang so với khung khoá khổ (<50%) | `kiem_anh_thap` | chặn |
| Tin xếp hạng mà ảnh chính không phải bảng xếp hạng | `ethan_nop` / `dre_nop` | chặn |
| Bìa Kite không có `image` — mọi trường hợp, kể cả 0 ảnh (§1.2f) | `kite_nop` | chặn |
| Ảnh khái niệm đặt ở slide **thân** của Kite (§1.2c) | `kite_nop` | chặn |
| Dùng lại ảnh đã gửi trong 14 ngày (dHash, mọi bài, mọi vai) | `kiem_da_dung` | chặn |
| Cạnh ngắn <1000px | `kiem_do_phan_giai` | cảnh báo |
| Đáy ảnh quá sáng | `kiem_day_sang` | cảnh báo |

Mỗi hàm trả về `(lỗi, cảnh báo)` và **không hàm nào biết đến canvas**, nên vai
nào cũng gọi được. Vai tự chọn cổng nào hợp với khung của mình rồi gộp lại.

Uỷ quyền crop bề ngang có **hai** đường, cổng nhận cả hai: khai `crop_ok` trong
spec, hoặc cắt bằng `crop_ti_le.py --cat-ngang` (cờ đó đóng dấu vào PNG, đọc
bằng `doc_cat_ngang`). Trước 04/09 chỉ card.py đọc dấu thứ hai nên carousel vẫn
chặn oan một tấm đã được cho phép cắt.

**Vai nào đã gọi cổng nào** (cập nhật 04/09/2026 — luật Ông Chủ: *"ảnh do ai làm
mà chả phải đạt tiêu chuẩn"*):

| | Ethan (`card.py`) | Dre (`carousel.py`) | Kite (`render_edu.py`) | Itachi (`deck.py`) |
|---|:--:|:--:|:--:|:--:|
| ảnh rỗng · trùng trong bộ · độ nét | ✅ | ✅ | ✅ | ❌ |
| xuất xứ · đáy sáng | ✅ | ✅ | – | ❌ |
| mặt người | ✅ | ✅ | ⚠️ | ❌ |
| trùng liên phiên (14 ngày) | ✅ | ✅ | ✅ | ❌ |
| tin xếp hạng → ảnh xếp hạng | ✅ | ✅ | – | ❌ |
| crop ngang · lệch tone | ✅ | ✅ | – | ❌ |
| chart một mình | ✅ | – | – | ❌ |
| ảnh quá ngang | ✅ | – | – | ❌ |
| `chart: true` · dải tỉ lệ | – | ✅ | – | ❌ |

Dấu `–` là **không áp dụng cho khung đó**, khác hẳn `❌` là **chưa đấu**. Cột
Itachi còn trống nguyên.

`⚠️` của Kite là **cảnh báo, không chặn**: spec của `render_edu` không có trường
`nhan_vat` (khác `card.py`/`carousel.py`), nên chặn cứng sẽ khoá mọi ảnh sự kiện
mà vai không có đường khai. Muốn nâng lên ✅ thì phải thêm trường đó vào spec
trước. Kite không đi qua các cổng có dấu `–` vì `kind: figure` dán ảnh nguyên
khổ, không crop và không đè chữ lên ảnh.

Sửa một luật ở đây là **cả đội đổi theo** — đó là lý do tài liệu này tồn tại.
Đừng chép luật sang SKILL của vai. (SKILL **không** trỏ về đây: từ a757f61 luật
ảnh đi vào brief do `*_chuan_bi.py` tự sinh, nên tệp này là nguồn cho **code và
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
