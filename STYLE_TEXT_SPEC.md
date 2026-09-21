# Style text trên thẻ — spec hiện tại (`card.py`)

Baseline từ phân tích thẻ thật đã render. Dùng làm điểm so sánh khi đổi renderer.

`card.py` có **hai** kiểu thẻ, và **mặc định là `quote`** (`card.build(kieu="quote")`,
`ethan_submit` cũng vậy). `--kieu full_bleed` là lựa chọn có chủ đích khi muốn ảnh phủ kín
thẻ. Kiểu `dai` đã bỏ khỏi mã 05/09/2026; bản mô tả thiết kế của nó chuyển sang
[INCIDENT_LOG.md](INCIDENT_LOG.md).

Luật *"ảnh này có được dùng không"* — riêng từng vai từ LOW-182 (16/09/2026) —
nằm ở [IMAGE_RULES_ETHAN.md](IMAGE_RULES_ETHAN.md) /
[IMAGE_RULES_DRE.md](IMAGE_RULES_DRE.md) / [IMAGE_RULES_KITE.md](IMAGE_RULES_KITE.md);
tệp này chỉ nói *"đặt chữ lên khung thế nào"*.

## Hệ chữ — kiểu `quote`

| Vai trò | Font | Cỡ | Kiểu |
|---|---|---|---|
| Câu trích dẫn | Be Vietnam Pro **Bold** | 40–66px, tự nở theo chỗ trống; tối đa 7 dòng | giữ nguyên HOA/thường (**không** `.upper()` như tiêu đề) |
| Dòng nguồn (`--attrib`) | Be Vietnam Pro Regular | 26px | canh giữa, sát đáy thẻ |
| Chip tên kênh | JetBrains Mono Regular | 22px | góc TRÊN-PHẢI khung |
| Chip tagline | JetBrains Mono Bold | 20px | góc DƯỚI-TRÁI khung |

## Hệ chữ — kiểu `full_bleed`

| Vai trò | Font | Cỡ | Kiểu |
|---|---|---|---|
| Tiêu đề | Oswald weight 700 | 38–150px (tự nở theo chỗ trống) | IN HOA, sans condensed |
| Kicker | Inter weight 700 | 30px, giãn chữ cái 7px | IN HOA, tiếng Anh |
| Tên kênh | Inter weight 500 | 27px | chữ thường |

Không dùng font đơn cách ở đây. JetBrains Mono bắt mỗi chữ cái chiếm đúng một ô,
nên một câu dài ăn rất nhiều bề ngang và đọc ra "code" chứ không ra "báo".
Oswald hẹp ngang nên chứa được câu dài ở cỡ chữ to.

Tên hãng trong tiêu đề được tô màu tự động, tra theo `BRAND_FROM` và `BRAND_PHRASE`
trong `card.py`. Riêng `AI` đứng một mình không tô.

Hai thương hiệu tô khác nhau, khai báo bằng khoá `company_name_color`:

- **donniechublog** (`"cyan"`) — dùng CYAN của bộ nhận diện.
- **dcgr** (`"company"`) — dùng **màu riêng của chính hãng** được nhắc tới, tra
  `COLOR_RANK` / `COLOR_PHRASE`. Đây là màu thứ ba của bảng đơn sắc: nó không cố định,
  mà đến từ chủ thể của tin. Màu quá đậm được `_enough_bright()` kéo lên đủ đọc trên
  nền tối. Hãng chưa biết màu thì dùng `fallback_company_color` (hổ phách).

Cùng bảng `COLOR_RANK` đó còn góp vào **palette của carousel EDU** (Kite). Tin
DeepSeek xanh dương đã hai lần ra slide xanh lá (LOW-11, LOW-340). Từ LOW-340
(Ông Chủ 21/09/2026), hãng lớn có **palette riêng** (`render_edu.BRAND_THEME`:
deepseek, anthropic, gemini, meta, qwen, mistral, nvidia, huggingface,
perplexity), khoá theo hãng chủ thể của tin, và theme do Kite tự ghi không thắng
được. Hãng tông đen trắng (OpenAI, xAI, Apple…) không có palette và bỏ qua tầng
màu hãng. Thứ tự trong `render_edu.pick_theme_auto`: palette hãng → màu ảnh bìa
thật → màu hãng chưa có palette (theme tâm trạng gần hue nhất) → xoay vòng.

Giãn dòng và khoảng cách kicker đo bằng `_step_line()`, tức là đo **chính các
dòng sắp vẽ**, không đo bằng chuỗi mẫu `"Ây"`. Tiêu đề tiếng Việt viết hoa trải
rộng hơn chuỗi mẫu đó: dấu sắc trên `Ắ` cao hơn dấu mũ, dấu nặng dưới `Ạ` thấp
hơn đuôi `y`. Đo bằng chuỗi mẫu thì với giãn dòng bó sát, hai dòng liền nhau
chồng lên nhau tới 11px.

## Bố cục kiểu `quote` — mặc định (1200px ngang, khoá khổ 4:5)

Đây là dạng thẻ trích dẫn của báo: **một câu** trong ngoặc kép, có dòng nguồn ở
dưới. Khác hero (một tiêu đề bao quát tin) và khác carousel (nhiều slide).

1. **Ảnh luôn hiện full bề ngang, không cắt hai cạnh.** Ảnh cao hơn khổ thì chỉ
   cắt theo chiều dọc. Ảnh thấp hơn khổ thì đặt sát trên và **tan dần** vào lớp
   nền mờ ở đúng đáy ảnh — không đặt màn tối, không để lộ một đường ranh ngang.
2. **KHÔNG CÓ MÀN TỐI** (Ông Chủ chốt 06/09/2026). Thay vào đó chỉ **làm mờ cục
   bộ** đúng vùng chữ đè lên (`_open_region_text`, Gaussian `QUOTE_BLUR = 28`). Ảnh
   phía trên vùng chữ giữ nguyên 100% sắc nét — bảng xếp hạng, chart hiện trọn
   tới sát mép khối chữ. Mờ tan dần từ `frame_top - QUOTE_BLUR_COUNT` tới
   `frame_top` để ranh giới NÉT/MỜ không đọc ra thành hai vùng.
3. **Màu chữ đo theo TỪNG DẢI DÒNG**, không phải một trung bình cho cả khối
   (`_bright_region` + `THRESHOLD_BACKGROUND_BRIGHT = 116`). Ảnh có ranh sáng/tối ngang cắt qua
   khối chữ là ca rất thường; một phép trung bình thì nửa khối thành
   trắng-trên-trắng hoặc đen-trên-đen.
4. **Dòng nguồn đo riêng**: nó nằm DƯỚI khung, ngoài hộp vừa đo, nên lấy màu
   theo dải của chính nó.
5. **Khung chữ nhật bo góc** quanh câu trích, hai dấu `“` `”` cỡ lớn gần góc
   trên-trái / dưới-phải. Nét khung và dấu ngoặc **theo quyết định sáng/tối của
   khối**: nền sáng thì kéo màu nhận diện về phía tối (`_enough_dark`), nếu không thì
   trên ảnh nền trắng chúng biến mất.
6. **Hai chip neobrutalism** (khối đặc, viền đen 4px, bóng cứng lệch, chữ mono):
   tên kênh góc trên-phải khung, tagline góc dưới-trái, tâm chip ngang mức nét
   khung. Chip **không** đặt ở góc thẻ — ở đó nó đè lên tiêu đề của ảnh nguồn.

## Bố cục kiểu `full_bleed` — vai designer Ethan (cả hai brand)

**Ông Chủ chốt 07/09/2026** — bản này thay hẳn bản "không vẽ khung, không một
nét nào" trước đó. Ba thứ đổi: bỏ nền đặc, chữ tự đổi màu tương phản, và có một
**khung chữ nhật nét** bao quanh khối chữ, đi theo cách kiểu `quote` của Dre.
Khác quote đúng một chỗ: không có dấu ngoặc kép, vì đây là tiêu đề chứ không
phải câu trích dẫn — nên bốn nét khép kín thay cho hai góc ngoặc đối nhau.

Vì sao khung không phá luật "một mặt phẳng liền" (IMAGE_RULES mục 7): thứ bị cấm là
**đường cắt ngang chia thẻ làm hai**. Một khung khép kín bao quanh khối chữ là
một vật nằm TRÊN mặt phẳng ảnh, không cắt mặt phẳng đó ra — đúng như khung của
kiểu `quote` vẫn làm từ trước.

1. **Ảnh phủ kín thẻ ở mọi trường hợp**, cùng một lớp ảnh với kiểu `quote`
   (`_layer_image`): nền là bản cover **làm mờ** phủ kín khung, lớp sắc là ảnh
   nguyên tỉ lệ full bề ngang đặt sát trên; ảnh cao hơn khung thì chỉ cắt theo
   chiều dọc, ảnh thấp hơn thì mép dưới của lớp sắc **tan dần** vào lớp nền mờ
   qua một dải smoothstep. **Không còn nhánh "ảnh thấp → nền màu đặc"**: trước
   07/09/2026 ảnh 16:9 trên khổ 4:5 để lại hơn **một nửa thẻ** là màu nền của bộ
   nhận diện — đúng "vùng thứ hai" mà IMAGE_RULES mục 7 cấm, và cũng trái với chính
   mục 1 này. Hai kiểu thẻ dùng chung một hàm nên không lệch nhau được nữa.
2. **KHÔNG CÓ MÀN TỐI** — giống kiểu `quote` từ 06/09/2026. Chỉ **làm mờ cục bộ**
   dải chữ đè lên (`_open_region_text`), ảnh phía trên khối chữ giữ nguyên 100% sắc
   nét. Màn tối dài chính là thứ biến vùng chữ thành mảng thứ hai.
2b. **Màu chữ đo theo TỪNG DẢI DÒNG** (`_bright_region` + `THRESHOLD_BACKGROUND_BRIGHT = 116`),
   không phải một trung bình cho cả khối. Nét khung, kicker, tên hãng trong tiêu
   đề và tên kênh đều theo phe sáng/tối đo được: nền sáng thì kéo về phía tối
   (`_enough_dark`), nếu không thì trên ảnh nền trắng chúng biến mất. Tên kênh đo
   **riêng** dải của chính nó — nó nằm ngoài khung, và ảnh có khối chữ tối nhưng
   đáy thẻ sáng là ca rất thường.
2c. Chữ **thụt vào trong khung** (`CEILING_TEXT_X = CEILING_FRAME_X + 44`), không ăn
   ra sát lề thẻ như trước: có khung rồi mà chữ chạm nét là khối chữ đọc ra chật.
3. **Kicker** phía trên tiêu đề: nhãn ngắn tiếng Anh, cỡ nhỏ, giãn chữ cái,
   màu nhấn. Đây là thứ duy nhất còn lại nói cho người đọc biết loại tin, sau
   khi nhãn category đã bỏ. Tối đa hai từ, giãn chữ cái làm nhãn dài nở nhanh.
4. **Không chip category, không cụm `via`, không dãy icon social.** Cả ba đều
   bám mép, hợp với thẻ tin nơi mọi thứ lấy mép trái textbox làm mốc. Ở đây
   khung đã gỡ và chữ đã về giữa, để lại chúng thì chỉ còn vài vết dính ở hai
   góc dưới kéo mắt ra khỏi trục.
5. **Không phụ đề.** Tiêu đề gánh toàn bộ nội dung: một câu hoàn chỉnh bao quát
   cả tin. Không giới hạn số dòng, không giới hạn ký tự; script chọn cỡ chữ lớn
   nhất còn vừa vùng chữ, câu dài thì chữ nhỏ lại và xuống thêm dòng.
6. **Tiêu đề cân giữa**, không căn trái như kiểu dài. Kiểu dài có mép trái
   textbox làm mốc; kiểu tràn không còn textbox nên lấy trục đối xứng của ảnh.
7. **Giãn dòng bó sát** (`TRAN_LEAD = 2` so với `LEAD = 6` ở kiểu dài). Chữ
   display cỡ lớn để khoảng hở mặc định thì đọc ra rời rạc; bó lại cho khối chữ
   thành một mảng.
8. Vùng chữ chiếm `CEILING_TEXTBOX = 0.40` chiều cao thẻ, **không thương lượng với
   chiều cao ảnh** như kiểu dài, vì ảnh phủ kín thẻ và vùng chữ chỉ là một lớp
   đè lên.
9. Chân thẻ rút còn **đúng tên kênh, cân giữa**.

Hệ quả biên tập: nguồn ảnh không còn được in trên thẻ, nên nghĩa vụ ghi nguồn
chuyển sang chú thích bài đăng.

Không mascot: ảnh đã phủ kín nên mascot chỉ che mất nội dung.

## Màu (donniechublog)
- BG #0E1117, BG_CARD #161B22
- FG #E6EDF3 (chữ chính), MUTED #8B939E (subtitle)
- ACCENT #58A6FF, CYAN #00CCE0 (chip đặc, via, góc trên)
- LINE #30363D

## Màu (dcgr — chỉ trắng đen)
- BG #0A0A0A, BG_CARD #1A1A1A
- FG trắng, MUTED #969696
- ACCENT/CYAN = trắng. Chip trái không dùng (nền trắng đặc hút mắt).

## Nguyên tắc chung

- Em-dash (—) bị chặn ở mọi văn bản thẻ.
- Tiếng Việt không dấu trên thẻ bị chặn (từng in ra "CONG CU").
- Ảnh là chính, chữ là lớp đè lên: chữ nhường chỗ cho ảnh, không ngược lại.
- Tên hãng trong tiêu đề được tô màu tự động, tra `COLOR_RANK` / `COLOR_PHRASE` trong
  `card.py`. Riêng `AI` đứng một mình không tô.
- Giãn dòng đo bằng `_step_line()`, tức đo **chính các dòng sắp vẽ**, không đo
  bằng chuỗi mẫu `"Ây"`: tiêu đề tiếng Việt viết hoa trải rộng hơn chuỗi đó (dấu
  sắc trên `Ắ` cao hơn dấu mũ, dấu nặng dưới `Ạ` thấp hơn đuôi `y`), đo bằng
  chuỗi mẫu thì hai dòng liền nhau chồng lên nhau tới 11px.
- Ảnh chart/bảng/screenshot: `image_rules.is_chart()` nhận diện rồi ép vào đường
  của chart — hero thì ghép dọc `--image2`, carousel thì `"chart": true`. Chart
  luôn phải nguyên vẹn và trải full bề ngang.
- Phân tầng thị giác: câu trích / tiêu đề to nhất → dòng nguồn → chip mờ dần.
