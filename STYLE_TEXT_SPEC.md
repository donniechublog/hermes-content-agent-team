# Style text trên thẻ — spec hiện tại (card.py)

Baseline từ phân tích thẻ thật đã render. Dùng làm điểm so sánh khi có ảnh mẫu mới.

## Hệ chữ — thẻ tin kiểu `dai` (Iris, Ethan)
| Vai trò | Font | Cỡ | Kiểu |
|---|---|---|---|
| Tiêu đề | JetBrains Mono ExtraBold | 38–104px (tự nở theo chỗ trống) | IN HOA toàn bộ, đơn cách |
| Subtitle | Noto Serif | 20–50px | chữ thường, có dấu, serif |
| Chip nhãn | JetBrains Mono Bold | 26px | IN HOA |
| Via | Inter weight 500 | 29px | chữ thường |
| Tên kênh | Inter weight 500 | 27px | chữ thường |

## Hệ chữ — hero image kiểu `tran` (Chad)

| Vai trò | Font | Cỡ | Kiểu |
|---|---|---|---|
| Tiêu đề | Oswald weight 700 | 38–150px (tự nở theo chỗ trống) | IN HOA, sans condensed |
| Kicker | Inter weight 700 | 30px, giãn chữ cái 7px | IN HOA, tiếng Anh |
| Tên kênh | Inter weight 500 | 27px | chữ thường |

Không dùng font đơn cách ở đây. JetBrains Mono bắt mỗi chữ cái chiếm đúng một ô,
nên một câu dài ăn rất nhiều bề ngang và đọc ra "code" chứ không ra "báo".
Oswald hẹp ngang nên chứa được câu dài ở cỡ chữ to.

Tên hãng trong tiêu đề được tô màu CYAN tự động, tra theo `BRAND_TU` và
`BRAND_CUM` trong `card.py`. Riêng `AI` đứng một mình không tô. Bảng màu dcgr
đơn sắc nên không tô được, và đó là đúng ý đồ.

## Bố cục kiểu `dai` — thẻ tin của Iris và Ethan (1200px ngang)
1. Vùng ảnh nguồn trên cùng — ảnh thật, không chèn chữ đè lên (trừ mascot nếu còn góc trống).
2. Khung kỹ thuật: 4 góc vát — 2 góc trên cyan, 2 góc dưới trắng; 2 đường dọc đôi; đường chia ngắt quãng ngay ranh giới ảnh/text.
3. Chip category trái: nền đặc cyan, chữ đen, đè lên ranh giới ảnh/textbox, có 2 tam giác gấp xuống phải (kiểu ruy-băng).
4. Chip category phải: nền trong suốt, viền cyan, chữ trắng, gấp lên.
5. Tiêu đề: căn trái, tối đa 2 dòng, trắng FG.
6. Subtitle: căn trái, tối đa 3 dòng, màu xám nhạt (donniechublog) hoặc trắng 95% (dcgr).
7. Chân thẻ: `via: <nguồn>` trái, màu cyan mờ; hàng icon social + @handle phải, icon mờ hơn chữ.

## Bố cục kiểu `tran` — hero image của Chad

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

## Nguyên tắc
- Tiêu đề font đơn cách → thẻ tin kiểu dài tối đa 60 ký tự, quá bị thu/cắt.
  Hero image kiểu tràn KHÔNG có trần này: tiêu đề là một câu, chữ tự co theo.
- Em-dash (—) bị chặn ở mọi văn bản thẻ.
- Tiếng Việt không dấu trên thẻ bị chặn (từng in ra "CONG CU").
- Ảnh là chính, textbox là phụ: text nhường chỗ cho ảnh, không ngược lại.
- Phân tầng thị giác: tiêu đề to nhất → subtitle → via/icon mờ dần.

## Cần ảnh mẫu
Chưa rõ "họ" là ai / style nào. Gửi ảnh mẫu (đường dẫn file hoặc URL) để diff ra khác biệt: font? cách đặt chữ đè lên ảnh? chip? màu?
