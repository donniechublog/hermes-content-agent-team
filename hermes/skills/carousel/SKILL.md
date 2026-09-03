---
name: carousel
description: "Dựng carousel nhiều slide kiểu bảng tin bằng carousel.py — chữ chìm vào ảnh qua scrim liền mạch kiểu bìa (bắt đầu tối từ ~42% cao, đậm dần xuống ~80% ở chữ, không đường mép, không vùng đen riêng). NEOBRUTALISM đồng bộ hero card: chip tên kênh + chip category + khung quote đều khối đặc viền đen, bóng cứng, font JetBrains Mono, màu CYAN nhận diện (donniechublog #00cce0, dcgr trắng). Cách kể chuyện qua các slide, cách viết copy từng slide, luật chọn ảnh (1:1/4:5, mỗi hình duy nhất), các cổng chặn, và slide quote (một câu hook + dấu ngoặc kép + nguồn). Dùng chung cho Dre (donniechublog) và Dre (dcgr.tech), khác đúng cờ --brand."
version: 1.2.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [carousel, slide, dre, bang-tin, album, donniechublog, dcgr]
---

# carousel — bộ nhiều slide kể một tin

Kiểu ảnh thứ hai của đội, bên cạnh hero image. **Dre** (donniechublog) và
**Dre** (dcgr.tech) dựng nó — cùng một `carousel.py`, khác đúng cờ `--brand`,
giống hệt quan hệ Ethan bên hero image. Trong khi vai designer (Ethan) dựng
**một thẻ bìa** kiểu tràn cho một tin, Dre kể **cùng một tin qua nhiều
slide**: một chuỗi ảnh 4:5 nền đen, lướt sang phải để đọc tiếp.

`carousel.py` lo hết phần vẽ. Việc của bạn là **chia tin thành các slide**,
**viết copy từng slide**, và **chọn một ảnh thật cho mỗi slide**.

## Carousel khác hero image ở đâu

| | Hero image (Ethan) | Carousel (Dre) |
|---|---|---|
| Số ảnh | một thẻ bìa | 5–8 slide (tối thiểu 5), tối đa 10 |
| Chữ | một tiêu đề đè lên ảnh | hook ở bìa + đoạn chữ dưới mỗi slide |
| Vai trò ảnh | ảnh là chính, chữ nhường ảnh | ảnh minh hoạ từng ý, chữ mang nội dung |
| Người đọc làm gì | nhìn một nhịp | lướt, đọc dần, tới cuối mới hiểu hết |

Hero image nén cả tin vào một câu. Carousel trải tin ra: mỗi slide một ý, người
đọc lướt tới đâu hiểu tới đó, và slide cuối để lại một câu hỏi hay một điều cần
theo dõi. Dùng carousel khi tin **có nhiều tầng** — một con số gây sốc, một hệ
quả không hiển nhiên, một đối thủ — mà nén vào một câu thì mất.

## Bố cục mỗi slide (carousel.py tự vẽ)

Khổ **1080×1350 (4:5), nền đen tuyệt đối**. Hai loại slide:

**Slide bìa (slide 1)** — cửa để người ta dừng lướt:
```
        ảnh phủ kín thẻ (cover)
              ↓
        màn tối dày dần ở đáy
              ↓
      HOOK, chữ đậm trắng, canh trái,
      sát đáy — câu giật khiến người ta
      muốn lướt tiếp
        NHÃN NGẮN
```

**Slide thân (slide 2..N)** — từng nhịp của tin:
```
        ảnh phủ kín thẻ (cover)
              ↓
        scrim liền mạch từ ~42% cao, đậm dần
        xuống ~80% ở chữ — KHÔNG đường mép
              ↓
        đoạn chữ trắng, canh trái
        1–2 đoạn, mỗi đoạn 2–4 dòng
        (hoặc một câu quote — xem "Slide quote")
              ↓
   chip tên kênh (neobrutalism, góc dưới-trái mọi slide, không đè lên ảnh)
```

### Nguyên tắc liền mạch — không đường mép

Cả bìa lẫn thân đều là **chữ trên ảnh qua màn tối liền mạch**, không có vùng đen
riêng, không đường mép:

- **Bìa:** hook đè ảnh, màn tối tan dần từ trên xuống (`_scrim`), góc dưới-trái
  thoáng cho chữ.
- **Thân:** đoạn văn nằm trên một **scrim liền mạch kiểu bìa** — màn tối bắt đầu
  từ **cao** (khoảng 42% chiều cao, luôn trên dòng chữ đầu), đậm **dần** xuống
  theo đường cong tới ~80% ở vùng chữ. Vì gradient dài và bắt đầu từ cao nên
  **không lộ đường mép** kể cả trên ảnh sáng (logo, nền trắng) — chữ *chìm* vào
  ảnh. Vẫn là ảnh làm mờ (không phải hộp đen): chỗ đậm nhất ảnh vẫn còn hiện.

Điểm mấu chốt: màn tối **không bắt đầu ngay ở dòng chữ đầu** — bắt đầu ở đó tạo
một bước nhảy tối ngay trên dòng đầu, trên ảnh sáng là lộ mép, đọc ra "ảnh +
bảng chữ". `carousel.py` dựng sẵn scrim liền mạch; việc của bạn là **không chọn
ảnh phá lại** (nửa dưới quá sáng thì chữ trắng vẫn khó đọc — cổng chặn có cảnh báo).

## Bước 1 — nhận tin đã duyệt

Task của bạn có tiêu đề tin và link gốc, giống task của Ethan. Đây là tin
Ông Chủ đã chọn từ danh sách Finn/Vera/Nova. **Đọc kỹ link gốc trước khi chia
slide** — carousel sống chết ở chỗ bạn hiểu tin đủ sâu để tách ra nhiều tầng.
Không đọc đủ thì các slide chỉ là một câu bị cắt làm năm khúc.

## Bước 2 — chia tin thành các slide, và viết copy

Đây là phần khó nhất và là lý do Dre tồn tại. Một carousel tốt có **nhịp**:
mỗi slide đẩy người đọc sang slide sau.

### Khung kể chuyện (không cứng, nhưng hầu hết tin AI hợp)

1. **Bìa — HOOK.** Một câu giật khiến người ta dừng lướt. Thường là một **nghịch
   lý** hoặc một **con số**. Không phải nhan đề trung tính. Mẫu tham chiếu:
   "OpenAI đang xây điện thoại AI. Một startup Trung Quốc vừa ship trước."
2. **Cái gì vừa xảy ra.** Slide đầu tiên trả lời "chuyện gì": sản phẩm/mô hình gì
   vừa ra, ai làm, điểm lạ là gì.
3. **Con số gây sốc.** Một tầng làm người đọc "à hoá ra to vậy". Số nghìn tỉ tham
   số, số tiền gọi vốn, tốc độ, quy mô. Diễn giải số cho dễ hình dung ("đếm tới
   một nghìn tỉ mất 31.700 năm").
4. **Ý nghĩa thật / được mất.** Slide bẻ góc: tin này **thật ra** nói về cái gì.
   "Mục tiêu không phải phần cứng Apple, mà là nền kinh tế ứng dụng." Đây là chỗ
   carousel hơn hẳn một dòng tin.
5. **Đối thủ / diễn biến.** Ai đang cạnh tranh, rào cản là gì, ai sắp ra cái
   tương tự.
6. **Cái cần theo dõi.** Slide cuối để lại một mốc thời gian, một câu hỏi mở, hay
   một điều sắp tới. Không chốt cụt.

**Tối thiểu 5 slide** (bìa + 4) — cổng chặn `carousel.py` dừng nếu ít hơn (chuẩn
social content chất lượng). Tin nhiều tầng thì **6–8**. Đừng kéo dài cho đủ số:
mỗi slide phải mang **một ý mới**, slide không có ý mới là slide thừa — thiếu ý
thì đào sâu tin hoặc thêm góc, đừng nhồi rác.

### Giọng và độ dài

- **Câu ngắn, chủ động.** Mỗi slide thân 1–2 đoạn, mỗi đoạn 2–4 dòng. Đoạn cách
  nhau bằng một dòng trống (`\n\n` trong spec).
- **Một ý một slide.** Người đọc lướt nhanh; slide nào nhồi hai ý là mất một ý.
- **Số nằm trong câu**, không tách ra thành nhãn.
- **Tiếng Việt có dấu.** Cổng chặn sẽ dừng nếu thiếu (xem Cổng chặn). Chỉ dùng
  `--bo-qua-dau` khi copy **thật sự** là tiếng Anh.
- **Không em-dash.** `carousel.py` tự thay `—` thành dấu phẩy, nhưng cứ gõ đúng.
- Hook ở bìa: **một câu, đậm, giật**. Càng ngắn chữ càng to. Câu dài script tự
  thu nhỏ và xuống dòng, nhưng hook 2 dòng mạnh hơn hook 4 dòng.

## Bước 3 — chọn một ảnh thật cho mỗi slide

**KHÔNG BAO GIỜ tự vẽ minh hoạ.** Luật cứng của cả đội. Vẽ ra là bịa. Không có
ảnh thật cho một slide thì đổi cách chia slide, hoặc báo lại — đừng dựng hình giả.

Lấy ảnh từ chính tin:

```bash
venv/bin/python anh_bai.py \
  --tieu-de "<tiêu đề tin>" --link "<link gốc>" --json
```

Script gom ảnh từ link gốc và các báo đưa cùng tin, lọc logo/favicon, xếp hạng.
Một tin thường cho vài ảnh — chia chúng cho các slide theo ý từng slide nói.

**Tin model ra mắt: ưu tiên benchmark table/chart có trong bài.** Bảng so sánh
điểm benchmark (MMLU, HumanEval, lập trình, toán…) và biểu đồ là bằng chứng
mạnh nhất — ưu tiên dùng làm ảnh slide trước cả ảnh logo/hero. Chụp/trích chúng
từ bài gốc hoặc bài review; slide con số gây sốc ghép với bảng benchmark rất
khớp. Nhớ crop về 1:1/4:5 và cạnh ngắn ≥1000px (bảng chữ nhỏ thì càng phải bản
to).

### Gom ảnh CHẤT LƯỢNG: kết hợp official site + magazine (BẮT BUỘC nghĩ rộng)

`anh_bai.py` fetch **tĩnh** — trang sản phẩm hiện đại (JS render) nó chỉ nhặt
được `og:image` (thường là banner/sitecard chung chung), BỎ SÓT hết screenshot
UI thật. Đừng kết luận "bài không có ảnh" từ một lần chạy `anh_bai.py`. Một
carousel chất lượng **trộn hai nguồn**:

1. **Official / main brand** (trang chính chủ): mở bằng **BROWSER thật** (JS
   render) rồi lấy screenshot sản phẩm/hero từ DOM — vd trang chủ có `<img>`
   screenshot UI, video demo (trích 1 frame bằng `cv2` nếu cần, server đã có).
2. **Magazine / bài review**: The Verge, TechCrunch, The New Stack, BetterStack,
   9to5Google... thường embed screenshot UI thật, góc chụp khác, chú thích rõ.
   Dùng WebSearch tìm bài review rồi mở lấy ảnh. LƯU Ý: ảnh review hay dính
   **webcam mặt reviewer ở góc** → crop bỏ (luật ảnh một-người-vô-danh).

Ưu tiên screenshot **nền tối** cho slide có chữ (contrast). Ảnh tải về nhỏ hơn
1000px cạnh ngắn thì phóng lên sẽ mềm — chỉ dùng khi làm nền mờ sau chữ, còn có
bản to hơn thì thay. Trộn official + magazine mới ra bộ đủ 5+ ảnh khác nhau,
đúng chủ đề, không stock.

**MỖI SLIDE MỘT ẢNH DUY NHẤT — không lặp lại.** Luật cứng: không dùng cùng một
ảnh cho hai slide, và **cũng không dùng hai crop khác nhau của CÙNG một tấm
ảnh** (người xem vẫn nhận ra là một hình) — mỗi slide phải là một hình thật
khác hẳn. Một bộ 6 slide cần 6 nguồn ảnh riêng biệt.

Không đủ ảnh trong đúng bài gốc thì **tìm thêm ảnh thật liên quan** — không giới
hạn ở ảnh nhúng sẵn: ảnh sự kiện góc khác, ảnh sản phẩm/chip chính hãng, trụ sở,
người trình bày, logo... (Wikimedia Commons, các báo khác đưa cùng tin). Tất cả
đều là hãng lớn, material không thiếu. Chỉ khi **thật sự** không kiếm đủ ảnh
riêng thì mới **gộp hai ý** vào một slide để giảm số ảnh cần (đừng lặp ảnh để
lấp). Tránh ảnh **rò rỉ/chưa xác thực** (leak) — rủi ro sai và bản quyền.

Bài **arxiv** không có ảnh minh hoạ thì chụp trang bìa paper làm ảnh bìa:

```bash
venv/bin/python arxiv_bia.py --link "<link arxiv>" --out /tmp/src_bia.png
```

### Ảnh nào hợp — khác hero image một điểm quan trọng

Ở hero image, chữ **đè lên ảnh**, nên nửa dưới ảnh phải trống. Ở carousel
**thân**, chữ nằm trong **vùng đen riêng bên dưới ảnh**, không đè lên ảnh. Nên
ảnh thân **được phép dày đặc chi tiết** — ảnh chụp sự kiện, ảnh sản phẩm, thậm
chí ảnh có sẵn chữ. Đó là chỗ carousel dễ tìm ảnh hơn hero image.

Chỉ **ảnh bìa** là ngoại lệ: hook đè lên nó, nên bìa cần **góc dưới-trái tương
đối thoáng** để chữ đọc rõ (màn tối đã đỡ một phần). Chọn ảnh bìa mạnh nhất,
giàu thông tin nhất trong bộ.

| Tiêu chí | Ngưỡng |
|---|---|
| Cạnh ngắn ảnh | từ 1000px trở lên (dưới đó phóng full bề ngang là vỡ nét) |
| Tỉ lệ | **1:1 (vuông) hoặc 4:5** — bắt buộc. Xem bên dưới |
| Ảnh bìa: góc dưới-trái | tương đối thoáng cho hook |
| Ảnh thân | không ràng buộc chỗ trống — nền chữ là ảnh làm mờ ở đáy |

### Tỉ lệ ảnh: 1:1 hoặc 4:5 — không thì tự crop trước

Ảnh dùng trong carousel phải là **1:1 (vuông)** hoặc **4:5**. Vuông fit bề ngang
1080px ra cao ~1080 (phủ ~80% khung); 4:5 lấp kín khung. Cả hai đều cao đủ để
nền chữ (ảnh làm mờ + tối ở ~30% đáy) phủ liền, không hở dải đen. Ảnh ngang
(16:9, 4:3) fit bề ngang chỉ ra ~600px — hụt, phải cover-crop hai cạnh (mất nội
dung mép, vd cắt chữ trên screenshot).

**Tìm được ảnh đúng tỉ lệ thì thôi; KHÔNG thì crop về 1:1/4:5 TRƯỚC khi đưa vào
carousel** (đừng để `carousel.py` tự xoay xở). Dùng `crop_ti_le.py`:

```bash
venv/bin/python crop_ti_le.py --anh vao.jpg --ra ra.png              # 1:1, giữa
venv/bin/python crop_ti_le.py --anh vao.jpg --ra ra.png --ti-le 4:5  # 4:5
venv/bin/python crop_ti_le.py --anh vao.jpg --ra ra.png --cx 0.62    # tâm lệch phải, ôm chủ thể
```

Crop là **chọn khung ảnh thật**, không phải bịa ảnh — vẫn đúng luật "không tự
vẽ". Chọn `--cx/--cy` để ôm đúng chủ thể (chip, sản phẩm, mặt người) vào khung.

### Ảnh quá ngang mà có TIÊU ĐỀ (slide, bảng, chart, banner): GHÉP hai ảnh, đừng crop

Crop một slide/bảng có tiêu đề là mất tiêu đề, ảnh đọc ra vô nghĩa (Ông Chủ
bắt lỗi 03/09/2026). Với ảnh kiểu này: **tìm thêm MỘT ảnh ngang nữa** cùng bài
(slide kế tiếp, bảng khác, banner) và xếp DỌC hai ảnh trong cùng khung. Ghi
`"images": [a, b]` thay cho `"image"`, ở bìa hoặc slide thân đều được:

```json
{"images": ["slide_1.png", "slide_2.png"], "text": "..."}
```

`carousel.py` tự ghép: mỗi ảnh full bề ngang, nguyên tỉ lệ, cách nhau 12px nền
đen, rồi chạy mọi cổng chặn như ảnh thường (kết quả ghép lưu `<out>_N.ghep.png`).
Hai ảnh 16:9 ghép ra ~0.88 (nằm giữa 4:5 và 1:1) — cổng tỉ lệ chấp nhận cả dải
**4:5 → 1:1**. Ảnh dưới nằm dưới scrim chữ, nên đặt ảnh QUAN TRỌNG hơn ở trên.

**Chọn hai ảnh CÙNG TONE.** Hai ảnh lệch tone (một nền trắng một nền đen, gam
màu khác hẳn) đọc ra như hai vùng riêng biệt, mất cảm giác một khung. Ưu tiên
cùng nền sáng/tối, cùng gam màu, tốt nhất là hai slide cùng một bộ. Script đo
độ sáng và màu trung bình, lệch nhiều sẽ in `[CANH BAO] ghep anh` — thấy là
đổi ảnh, đừng để qua.

Không có ảnh vuông sẵn: tự crop vuông từ một ảnh ngang thật (chọn khung ôm
đúng nội dung chính) — đây là chọn khung, không phải bịa ảnh, vẫn đúng luật
"không tự vẽ minh hoạ". Cứ hỏi `anh_bai.py` như thường; công cụ đó chấm điểm
theo tỉ lệ đẹp nhưng không tự động ưu tiên vuông, bạn phải tự cân.

Không giới hạn ảnh trong đúng bài nguồn — tin đủ lớn (hãng lớn, sự kiện có
đưa tin ảnh) thường có nhiều ảnh thật liên quan nằm rải ở các bài khác cùng
chủ đề (ảnh sự kiện góc khác, ảnh sản phẩm chính hãng, trụ sở, logo...). Cứ
tìm thêm — miễn ảnh **thật** và **đúng chủ đề**, không giới hạn ở ảnh nhúng
sẵn trong link gốc. Tránh dùng lại đúng một tấm cho quá nhiều slide; 6 slide
mà chỉ xoay vòng 2 ảnh là một điểm trừ trải nghiệm rõ rệt — cứ 4–6 ảnh khác
nhau cho một bộ 6 slide là hợp lý. Cẩn thận với ảnh **rò rỉ** (leak, chưa
chính thức xác nhận): rủi ro cả về độ chính xác (có thể sai/giả) lẫn bản
quyền — bỏ qua, tìm ảnh chính thức khác thay vào.

## Slide quote — BẮT BUỘC ≥2 mỗi bộ (câu trích dẫn)

Slide thân có hai loại: **đoạn-văn** (`text`) và **trích dẫn** (`quote`). **Mỗi
carousel PHẢI có ít nhất 2 slide quote** — cổng chặn dừng nếu <2. Đây là câu
trích dẫn mạnh (phát biểu, con số gây sốc, nhận định sắc, câu chốt) đặt trong
khung ngoặc, để format trích dẫn xuất hiện đều mỗi ngày.

Chọn **những câu đắt nhất** trong bài làm quote; các slide còn lại là đoạn-văn.
Vẫn **đừng ép cả bộ thành quote** (mất nhịp kể) — cân 2 quote + phần còn lại kể.
Một bộ 6 slide: ~2–3 quote + 3–4 đoạn-văn là hợp.

Trong spec, slide đó dùng `quote` (và `attrib` tuỳ chọn) thay cho `text`:

```json
{"image": "<ảnh>", "quote": "<câu nói DỊCH sang tiếng Việt có dấu — giữ tên riêng/thuật ngữ/số liệu>",
 "attrib": "Đọc bài “<tên bài>” - <tác giả>"}
```

`carousel.py` tự vẽ đúng dạng pull-quote: câu lớn canh trái trong một **khung 2
góc ngoặc bo tròn** (dấu " mở góc trên-trái, đóng góc dưới-phải, nét ngang xuyên
giữa dấu), dòng nguồn **canh giữa** dưới khung, trên cùng lớp veil liền mạch.
Brand text (tên kênh) ở **góc dưới-trái** như mọi slide. **Bạn không đặt dấu tay,
không sửa** — tất cả tự vẽ. Về màu:

- **Nét khung + chip tên kênh + chip category = `CYAN` nhận diện** (đồng bộ với
  hero card): donniechublog `#00cce0`, dcgr **trắng**. Chip là khối đặc viền đen
  dày, bóng cứng lệch, font JetBrains Mono (neobrutalism). Không còn xanh Apple.
- **Dấu " đổi màu theo HÃNG được nhắc** trong quote/nguồn (Nvidia → xanh lá,
  Hugging Face → vàng…); không nhận ra hãng nào thì dấu cũng CYAN. Dùng chung
  bảng màu hãng với `card.py`.

- Mỗi slide thân là **một trong hai**: `text` (đoạn văn) hoặc `quote` (câu trích
  dẫn). Thiếu cả hai → cổng chặn dừng.
- Câu quote **DỊCH sang tiếng Việt có dấu** — bài gốc tiếng Anh thì dịch câu
  trích (giữ tên riêng/thuật ngữ/số liệu), **ĐỪNG chép nguyên văn tiếng Anh** vào
  ảnh. "Giữ hoa/thường như gốc" chỉ nói về CÁCH viết hoa (không viết hoa toàn bộ),
  KHÔNG phải giữ nguyên ngôn ngữ. Quá dài (chạm 7 dòng ở cỡ nhỏ nhất) → cổng chặn
  báo cắt. Quote sống ở chỗ **ngắn**.
- Ảnh slide quote chọn như mọi slide thân: 1:1/4:5, cạnh ngắn ≥1000px, đáy đủ
  tối cho chữ trắng đọc rõ.

## Bước 4 — dựng

Viết spec JSON rồi chạy:

```bash
cat > /tmp/carousel_<id>.json <<'JSON'
{
  "handle": "donniechublog",
  "cover":  {"image": "<ảnh bìa>", "hook": "<câu giật>", "label": "AI PHONE"},
  "slides": [
    {"image": "<ảnh 2>", "text": "đoạn một.\n\nđoạn hai."},
    {"image": "<ảnh 3>", "text": "..."},
    {"image": "<ảnh 4>", "quote": "<câu trích dẫn>", "attrib": "Đọc bài “...” - <tác giả>"}
  ]
}
JSON

cd /home/donniechu/content-team && venv/bin/python carousel.py \
  --spec /tmp/carousel_<id>.json \
  --out drafts/<id>.png \
  --brand donniechublog
```

Ra: `drafts/<id>.png` (bìa) + `drafts/<id>_2.png`, `_3.png`… Đánh số này **khớp
đúng** glob của `draft_write.py`, nên bộ slide tự thành **album** khi đăng — bạn
không phải làm gì thêm ở khâu đăng.

Cờ:
- **`--out drafts/<id>.png`** — dùng đúng `<id>` của task để album gom đúng bài.
- **`--brand`** — `donniechublog` (mặc định) hay `dcgr`. Quyết định handle
  watermark mặc định và org bên moat.
- **`--handle`** — ghi đè watermark nếu cần tên khác.
- **`--bo-qua-dau`** — chỉ khi copy thật sự là tiếng Anh.
- **`--spec -`** — đọc spec từ stdin thay vì file.

## Cổng chặn

Mọi luật dưới đây `carousel.py` TỰ kiểm — vi phạm là dừng hẳn kèm hướng dẫn
sửa. Bạn không cần (và không thể) tự nhớ thay nó; việc của bạn là sửa theo
thông báo rồi chạy lại.

1. **Tiếng Việt không dấu** trong bất kỳ chữ nào (hook, label, mọi slide) →
   **dừng hẳn**, in ra chỗ sai. Gõ lại có dấu. `--bo-qua-dau` chỉ cho tiếng Anh.
2. **Dưới 5 slide** (kể cả bìa) → **dừng** (chuẩn tối thiểu). **Quá 10 slide** →
   dừng (`draft_write` chỉ gom tới `_9`).
3. **Thiếu `cover.image`, `cover.hook`, hay `image` của một slide** → dừng. Mỗi
   slide thân phải có **`text` hoặc `quote`** — thiếu cả hai cũng dừng.
4. **Dưới 2 slide quote** → dừng (mỗi carousel cần ≥2 pull-quote).
5. **Trùng ảnh** (hai slide cùng một tệp, so theo nội dung tệp) → dừng. Lưu ý:
   hai CROP khác nhau của cùng một tấm thì code không bắt được — cái đó bạn
   vẫn phải tự soi.
6. **Ảnh sai tỉ lệ** (ngoài dải 4:5..1:1, dung sai 3%) → dừng, kèm sẵn lệnh
   `crop_ti_le.py` để cắt.
7. **Copy dài quá vùng chữ 30%** (ở cỡ chữ nhỏ nhất vẫn tràn) → dừng, báo cần
   cắt bớt bao nhiêu phần trăm chữ.
8. **Cảnh báo (không chặn)**:
   - cạnh ngắn ảnh <1000px (phóng lên sẽ mềm nét);
   - 25% dưới của ảnh quá sáng (chữ trắng trên nền 60% sẽ khó đọc);
   - **phát hiện mặt người** trong ảnh (YuNet) → **chỉ cảnh báo, KHÔNG chặn**,
     album vẫn dựng. Code chỉ báo *có mặt hay không*; bạn phán *có phải nhân vật
     cụ thể trong bài không*. Tin xoay quanh một người (Elon Musk, Peter Thiel,
     founder Palantir / partner a16z, tác giả phát biểu…) thì ảnh **đúng người
     đó là ảnh NÊN dùng** — bỏ qua cảnh báo, cứ dùng. Chỉ đổi/crop khi mặt là
     **người vô danh** không liên quan (vd webcam reviewer ở góc, stock persona).
     Cần `assets/face_detection_yunet_2023mar.onnx`; thiếu model thì cổng tự bỏ
     qua (không crash).
9. **Em-dash** → không chặn, tự thay `—` thành phẩy.

## Bàn giao

Watermark trên slide **không phải là ghi nguồn**. Nguồn ảnh và nguồn tin vẫn
phải chuyển cho người viết caption (Miles) để đưa vào chú thích bài đăng,
đúng như hero image. Khi bàn giao, nói rõ: link gốc, và nguồn từng ảnh nếu lấy
từ nhiều báo.

## Nhìn lại trước khi giao

Mở cả bộ slide ra xem, theo thứ tự:

1. **Bìa có khiến muốn lướt tiếp không?** Hook trung tính là bìa hỏng. Viết lại
   cho giật.
2. **Mỗi slide có một ý mới không?** Slide lặp ý slide trước là slide thừa, bỏ.
3. **Slide cuối có để lại gì không?** Chốt cụt thì thêm một mốc/câu hỏi.
4. **Chữ trên bìa có đọc rõ trên ảnh không?** Không thì đổi ảnh bìa thoáng hơn.
5. **Ảnh nào bị phóng vỡ nét không?** Có thì đổi ảnh cạnh ngắn ≥1000px.

Spec đầy đủ của khổ, font và màu ở `carousel.py` (đầu tệp) và
`/home/donniechu/content-team/STYLE_TEXT_SPEC.md`.
