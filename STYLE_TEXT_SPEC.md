# Style text trên thẻ — spec hiện tại (`card.py`)

Baseline từ phân tích thẻ thật đã render. Dùng làm điểm so sánh khi đổi renderer.

`card.py` có **hai** kiểu thẻ, và **mặc định là `quote`** (`card.build(kieu="quote")`,
`ethan_nop` cũng vậy). `--kieu tran` là lựa chọn có chủ đích khi muốn ảnh phủ kín
thẻ. Kiểu `dai` đã bỏ khỏi mã 05/09/2026; bản mô tả thiết kế của nó chuyển sang
[NHAT_KY_SU_CO.md](NHAT_KY_SU_CO.md).

Luật *"ảnh này có được dùng không"* nằm ở [LUAT_ANH.md](LUAT_ANH.md); tệp này chỉ
nói *"đặt chữ lên khung thế nào"*.

## Hệ chữ — kiểu `quote`

| Vai trò | Font | Cỡ | Kiểu |
|---|---|---|---|
| Câu trích dẫn | Be Vietnam Pro **Bold** | 40–66px, tự nở theo chỗ trống; tối đa 7 dòng | giữ nguyên HOA/thường (**không** `.upper()` như tiêu đề) |
| Dòng nguồn (`--attrib`) | Be Vietnam Pro Regular | 26px | canh giữa, sát đáy thẻ |
| Chip tên kênh | JetBrains Mono Regular | 22px | góc TRÊN-PHẢI khung |
| Chip tagline | JetBrains Mono Bold | 20px | góc DƯỚI-TRÁI khung |

## Hệ chữ — kiểu `tran`

| Vai trò | Font | Cỡ | Kiểu |
|---|---|---|---|
| Tiêu đề | Oswald weight 700 | 38–150px (tự nở theo chỗ trống) | IN HOA, sans condensed |
| Kicker | Inter weight 700 | 30px, giãn chữ cái 7px | IN HOA, tiếng Anh |
| Tên kênh | Inter weight 500 | 27px | chữ thường |

Không dùng font đơn cách ở đây. JetBrains Mono bắt mỗi chữ cái chiếm đúng một ô,
nên một câu dài ăn rất nhiều bề ngang và đọc ra "code" chứ không ra "báo".
Oswald hẹp ngang nên chứa được câu dài ở cỡ chữ to.

Tên hãng trong tiêu đề được tô màu tự động, tra theo `BRAND_TU` và `BRAND_CUM`
trong `card.py`. Riêng `AI` đứng một mình không tô.

Hai thương hiệu tô khác nhau, khai báo bằng khoá `to_ten_hang`:

- **donniechublog** (`"cyan"`) — dùng CYAN của bộ nhận diện.
- **dcgr** (`"hang"`) — dùng **màu riêng của chính hãng** được nhắc tới, tra
  `MAU_HANG` / `MAU_CUM`. Đây là màu thứ ba của bảng đơn sắc: nó không cố định,
  mà đến từ chủ thể của tin. Màu quá đậm được `_du_sang()` kéo lên đủ đọc trên
  nền tối. Hãng chưa biết màu thì dùng `mau_du_phong` (hổ phách).

Giãn dòng và khoảng cách kicker đo bằng `_buoc_dong()`, tức là đo **chính các
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
   bộ** đúng vùng chữ đè lên (`_mo_vung_chu`, Gaussian `QUOTE_BLUR = 28`). Ảnh
   phía trên vùng chữ giữ nguyên 100% sắc nét — bảng xếp hạng, chart hiện trọn
   tới sát mép khối chữ. Mờ tan dần từ `frame_top - QUOTE_BLUR_DEM` tới
   `frame_top` để ranh giới NÉT/MỜ không đọc ra thành hai vùng.
3. **Màu chữ đo theo TỪNG DẢI DÒNG**, không phải một trung bình cho cả khối
   (`_sang_vung` + `NGUONG_NEN_SANG = 116`). Ảnh có ranh sáng/tối ngang cắt qua
   khối chữ là ca rất thường; một phép trung bình thì nửa khối thành
   trắng-trên-trắng hoặc đen-trên-đen.
4. **Dòng nguồn đo riêng**: nó nằm DƯỚI khung, ngoài hộp vừa đo, nên lấy màu
   theo dải của chính nó.
5. **Khung chữ nhật bo góc** quanh câu trích, hai dấu `“` `”` cỡ lớn gần góc
   trên-trái / dưới-phải. Nét khung và dấu ngoặc **theo quyết định sáng/tối của
   khối**: nền sáng thì kéo màu nhận diện về phía tối (`_du_toi`), nếu không thì
   trên ảnh nền trắng chúng biến mất.
6. **Hai chip neobrutalism** (khối đặc, viền đen 4px, bóng cứng lệch, chữ mono):
   tên kênh góc trên-phải khung, tagline góc dưới-trái, tâm chip ngang mức nét
   khung. Chip **không** đặt ở góc thẻ — ở đó nó đè lên tiêu đề của ảnh nguồn.
7. Ảnh thấp hơn 50% khổ thẻ bị chặn hẳn (`luat_anh.kiem_anh_thap`): nửa thẻ bỏ
   trống. Đường ra là ghép dọc `--image2`.

## Bố cục kiểu `tran` — vai designer Ethan (cả hai brand)

**Không vẽ khung, không một nét nào.** Không ngoặc góc, không đường dọc, không
vạch ngang. Đó là điều kiện để thẻ đọc ra là một mặt phẳng liền: ngoặc góc chính
là một cái viền, và nét dọc trong vùng chữ lại tố ra đúng cái ranh giới mà kiểu
tràn sinh ra để xoá.

1. Ảnh phủ kín thẻ, chạy sát bốn mép. Quá ngưỡng phóng 1.35 lần thì đổi sang nền
   mờ cộng ảnh sắc đặt lên trên — vẫn liền mặt, nhưng là phương án đỡ.
2. Màn tối dày dần từ trên xuống, đậm hẳn ở vùng chữ. Điểm uốn đặt cao hơn mốc
   chữ một đoạn để không lộ ra một đường gãy.
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
8. Vùng chữ chiếm `TRAN_TEXTBOX = 0.40` chiều cao thẻ, **không thương lượng với
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
- Tên hãng trong tiêu đề được tô màu tự động, tra `MAU_HANG` / `MAU_CUM` trong
  `card.py`. Riêng `AI` đứng một mình không tô.
- Giãn dòng đo bằng `_buoc_dong()`, tức đo **chính các dòng sắp vẽ**, không đo
  bằng chuỗi mẫu `"Ây"`: tiêu đề tiếng Việt viết hoa trải rộng hơn chuỗi đó (dấu
  sắc trên `Ắ` cao hơn dấu mũ, dấu nặng dưới `Ạ` thấp hơn đuôi `y`), đo bằng
  chuỗi mẫu thì hai dòng liền nhau chồng lên nhau tới 11px.
- Ảnh chart/bảng/screenshot: `luat_anh.la_chart()` nhận diện rồi ép vào đường
  của chart — hero thì ghép dọc `--image2`, carousel thì `"chart": true`. Chart
  luôn phải nguyên vẹn và trải full bề ngang.
- Phân tầng thị giác: câu trích / tiêu đề to nhất → dòng nguồn → chip mờ dần.
