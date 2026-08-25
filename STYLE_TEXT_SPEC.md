# Style text trên thẻ — spec hiện tại (card.py)

Baseline từ phân tích thẻ thật đã render. Dùng làm điểm so sánh khi có ảnh mẫu mới.

## Hệ chữ
| Vai trò | Font | Cỡ | Kiểu |
|---|---|---|---|
| Tiêu đề | JetBrains Mono ExtraBold | 38–104px (tự nở theo chỗ trống) | IN HOA toàn bộ, đơn cách |
| Subtitle | Noto Serif | 20–50px | chữ thường, có dấu, serif |
| Chip nhãn | JetBrains Mono Bold | 26px | IN HOA |
| Via | Inter weight 500 | 29px | chữ thường |
| Tên kênh | Inter weight 500 | 27px | chữ thường |

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
3. Hai chip category **nằm hẳn trong khối chữ**, thành hàng đầu tiên của nó,
   không vắt qua mốc ảnh/chữ như kiểu dài. Để chip ở cao độ đó thì chính chip
   trở thành vật đánh dấu cái đường vừa xoá.
4. Tiêu đề, phụ đề, chân thẻ: y hệt kiểu dài.

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
- Tiêu đề font đơn cách → tối đa 60 ký tự, quá bị thu/cắt.
- Em-dash (—) bị chặn ở mọi văn bản thẻ.
- Tiếng Việt không dấu trên thẻ bị chặn (từng in ra "CONG CU").
- Ảnh là chính, textbox là phụ: text nhường chỗ cho ảnh, không ngược lại.
- Phân tầng thị giác: tiêu đề to nhất → subtitle → via/icon mờ dần.

## Cần ảnh mẫu
Chưa rõ "họ" là ai / style nào. Gửi ảnh mẫu (đường dẫn file hoặc URL) để diff ra khác biệt: font? cách đặt chữ đè lên ảnh? chip? màu?
