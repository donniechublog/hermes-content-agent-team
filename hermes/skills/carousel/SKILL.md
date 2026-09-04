---
name: carousel
description: "Dựng carousel nhiều slide kiểu bảng tin bằng carousel.py — chữ chìm vào ảnh qua scrim liền mạch kiểu bìa (bắt đầu tối từ ~42% cao, đậm dần xuống ~80% ở chữ, không đường mép, không vùng đen riêng). NEOBRUTALISM đồng bộ hero card: chip tên kênh + chip category + khung quote đều khối đặc viền đen, bóng cứng, font JetBrains Mono, màu CYAN nhận diện (donniechublog #00cce0, dcgr trắng). Cách kể chuyện qua các slide, cách viết copy từng slide, luật chọn ảnh (1:1/4:5, mỗi hình duy nhất), các cổng chặn, và slide quote (một câu hook + dấu ngoặc kép + nguồn). Dùng chung cho Dre (donniechublog) và Dre (dcgr.tech), khác đúng cờ --brand."
version: 1.3.0
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
| Số ảnh | một thẻ bìa | 5–8 slide (tối thiểu 5; **flagship tối thiểu 8**), tối đa 10 |
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
   [CATEGORY cyan] [LABEL trắng]   ← KHÔNG có chip tên kênh ở bìa
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

### LUẬT CỨNG: KHÔNG BAO GIỜ ĐỂ RA HAI VÙNG RIÊNG BIỆT

Mỗi slide phải đọc ra **một mặt phẳng liền**. Cấm mọi thứ chia khung thành hai
mảng nhìn tách rời nhau:

- **Không vùng đen riêng** đặt dưới ảnh để chứa chữ. Chữ luôn đè lên ảnh qua
  gradient.
- **Không vạch, không viền, không đường kẻ** ngang giữa khung. Ghép dọc hai ảnh
  là **áp sát**, không chèn dải đen (bỏ từ 04/09/2026).
- **Không để lộ bản sao sắc nét của chính tấm ảnh** làm nền. Chỗ nào lớp ảnh sắc
  không phủ hết (chart ngang, ảnh 1:1), nền là chính tấm đó **làm mờ mạnh**
  (`BG_BLUR`) — thành một mảng màu liền. Trước 04/09 nền là bản cover **sắc nét**,
  nên dưới bảng benchmark hiện lại chính cái bảng đó ở cỡ khác: mắt bắt ngay,
  đọc ra hai vùng và giống lỗi kỹ thuật.
- **Không ghép hai ảnh quá khác tone** (một nền trắng một nền đen) — Ông Chủ chốt
  04/09/2026. Đây là cổng chặn dừng hẳn, không phải cảnh báo. Ghép thì được
  khuyến khích (đỡ phải cắt), nhưng lệch tone là dừng.
- **Không làm tối riêng một mảng** quanh chart để "cho nổi" — mảng tối có mép
  thẳng chính là vùng thứ hai. Chỉ scrim gradient dài mới được làm tối.

Khi tự soi lại slide đã dựng: nhìn có thấy **một đường ranh ngang** nào không.
Thấy là hỏng, dựng lại — đừng gửi đi.

## BỐN LỖI ÔNG CHỦ BẮT 03/09/2026 (carousel GPT-6 Astra, Qwen 3.8) — đọc trước mọi thứ

1. **Mặt người không liên quan.** Bìa dùng ảnh một người lạ chụp ngoài đường,
   chẳng dính gì tới tin model ra mắt. Từ nay `carousel.py` **CHẶN mọi ảnh có
   mặt người** trừ khi slide khai `"nhan_vat": "<tên>"` — người đó phải là nhân
   vật **được nhắc trong bài** (CEO phát biểu, tác giả paper, founder). Không
   gọi được tên thì không được dùng. Tin model/sản phẩm: bìa là **sản phẩm,
   screenshot, chart** — không phải mặt người.
2. **Chart / bảng benchmark bị crop.** Chart cắt mất tiêu đề, mất trục, mất
   legend là ảnh vô nghĩa. **Bắt đầu từ lúc CHỤP** (luật Ông Chủ 04/09/2026):
   full chiều rộng trước, chiều cao xét sau — chụp bằng
   `venv/bin/python chup_chart.py --url "<trang>" --ra chart.png`, script nới
   khung cho vừa bề ngang thật của chart rồi đo lại ảnh ra, thiếu bề ngang là
   nó dừng. Đừng chụp bằng khung mặc định của công cụ nào: khung mặc định luôn
   hẹp, chart rộng thì hoặc bị cắt, hoặc bị trang reflow xuống bố cục điện thoại.
   **Từ 04/09/2026 `carousel.py` tự nhận ra ảnh nào là chart/screenshot**
   (`card.la_chart`: đo độ phẳng + số màu riêng biệt) và **bắt** khai
   `"chart": true` — không khai là chặn, kèm số liệu để bạn thấy vì sao. Bìa mà
   là chart cũng bị chặn (hook đè lên thì chart nằm dưới chữ) — ghép dọc
   `"images": [a, b]`, hoặc đổi bìa và để chart ở slide thân.

   > **Ông Chủ chốt 04/09/2026: "chart phải được hiển thị đầy đủ và full width
   > của chiều rộng hình."** Hai vế, cả hai đều bắt buộc. *Đầy đủ* = không mất
   > một chữ nào: tiêu đề, trục, nhãn trục, legend, chú thích chân chart. *Full
   > width* = trải hết 1080px bề ngang khung, không thu nhỏ, không chừa lề.
   > Đường duy nhất làm được cả hai là `"chart": true` với **ảnh GỐC chưa cắt**.
   > Ca bị bắt: bộ K2 Horizon cắt chart 2015x1099 về 879x1099 để lấp đầy khung
   > — vứt 56% bề ngang, mất chữ đầu tiêu đề ("...osses across the Horizon
   > fleet") và mất sạch trục y. `carousel.py` còn tự lùi điểm bắt đầu scrim
   > xuống dưới mép chart, để đáy chart không bị làm tối.

   **Chart, bảng, slide, banner có chữ PHẢI NGUYÊN
   VẸN** — không crop, không cắt góc. Ảnh ngang thì **ghép dọc hai ảnh cùng
   tone** (`"images": [a, b]`), **hoặc** khai `"chart": true` cho slide thân: cổng
   tỉ lệ bỏ qua, `carousel.py` dán chart **full bề ngang nguyên vẹn**, phần
   trống trên/dưới là chính ảnh làm mờ. Đây là đường mặc định cho benchmark
   chart/bảng — không cần crop, không cần tìm ảnh thứ hai. Bìa thì không (hook
   đè lên ảnh), bìa chart phải ghép dọc. **Crop chỉ được làm qua
   `crop_ti_le.py`**, và cắt tay bằng
   PIL/cv2/ImageMagick là vi phạm — từ 04/09 là **bị bắt**. Cơ chế đầy đủ ở
   [`LUAT_ANH.md`](/home/donniechu/content-team/LUAT_ANH.md) mục 4.
3. **Flagship mà chỉ 5 slide.** GPT-6 Astra là model đầu bảng OpenAI, có
   benchmark, safety, giá, đối thủ, phát biểu… mà bộ chỉ 5 slide. **Tin model
   ra mắt của hãng frontier (OpenAI, Anthropic, Google, Meta, xAI, DeepSeek,
   Qwen, Moonshot/Kimi, Z-AI/GLM, MiniMax…) BẮT BUỘC 8–10 slide.** Script tự
   nhận diện qua tên họ model trong chữ và chặn nếu <8; ghi `"tam_co":
   "flagship"` cho chắc. `"tam_co": "thuong"` chỉ khi Ông Chủ nói rõ tin nhỏ.
   Các tầng để đủ 8+: cái gì ra mắt → bảng benchmark nguyên vẹn → chart thứ
   hai (safety/hallucination/latency) → giá & context & tốc độ → so với đối
   thủ → phát biểu lãnh đạo (quote) → rủi ro/an toàn → cái cần theo dõi.

4. **Chip trên bìa (hero slide) KHÔNG phải tên kênh.** Chip cyan ở bìa là
   **category**: `MODEL RELEASE`, `MODEL UPDATE`, `PRODUCT`, `RESEARCH`,
   `FUNDING`, `POLICY`, `OPINION`… — khai `cover.category`, thiếu là cổng dừng.
   Chip trắng bên cạnh là `label` (tên model/hãng). Tên kênh `donniechublog`
   chỉ nằm ở các slide thân.

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
social content chất lượng). Tin nhiều tầng thì **6–8**. **Tin flagship (model ra
mắt hãng frontier) tối thiểu 8**, cổng chặn tự nhận diện và dừng. Đừng kéo dài cho đủ số:
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
khớp. **Chart/bảng phải NGUYÊN VẸN** (đủ tiêu đề, trục, legend, chú thích) —
KHÔNG crop về 1:1/4:5; chart ngang thì ghép dọc với một chart/bảng khác cùng
tone (`"images": [a, b]`). Chụp bản to (cạnh ngắn ≥1000px; bảng chữ nhỏ càng
phải to).

### Gom ảnh: kết hợp official site + magazine

`anh_bai.py` fetch **tĩnh** nên bỏ sót screenshot UI thật của trang JS. Đừng kết
luận "bài không có ảnh" từ một lần chạy — trộn hai nguồn (chính chủ mở bằng
browser thật + bài review của magazine). Cách làm ở [`LUAT_ANH.md`](/home/donniechu/content-team/LUAT_ANH.md) mục 1.

**MỖI SLIDE MỘT ẢNH DUY NHẤT — không lặp lại**, và cũng không dùng hai crop khác
nhau của cùng một tấm. Một bộ 6 slide cần 6 nguồn ảnh riêng biệt. Không đủ ảnh
riêng thì **gộp hai ý** vào một slide để giảm số ảnh cần — đừng lặp ảnh để lấp.

Bài **arxiv** không có ảnh minh hoạ thì chụp trang bìa paper làm ảnh bìa:

```bash
venv/bin/python arxiv_bia.py --link "<link arxiv>" --out /tmp/src_bia.png
```

### Ảnh nào hợp — giống hero image, chỉ nhẹ tay hơn

**Slide thân KHÔNG có vùng đen riêng.** Chữ đè lên ảnh y như bìa, chỉ khác là
màn tối bắt đầu từ cao hơn và dài hơn (xem "Nguyên tắc liền mạch"). Nền sau chữ
luôn là **chính tấm ảnh đó được làm mờ và làm tối**, không phải một hộp đen đặt
dưới ảnh.

Hệ quả khi chọn ảnh: **nửa dưới ảnh thân phải chịu được chữ trắng đè lên** —
đừng chọn ảnh mà đáy là mảng trắng chói hoặc chi tiết rối (mặt người, chữ to,
hoa văn dày). Ảnh thân vẫn **dễ hơn bìa** vì màn tối ở thân dày hơn: ảnh chụp sự
kiện, ảnh sản phẩm, screenshot, chart đều dùng được, miễn đáy không sáng chói.
Ưu tiên screenshot/ảnh **nền tối** cho slide nhiều chữ.

**Ảnh bìa** khắt khe nhất: hook chữ to đè lên, nên bìa cần **góc dưới-trái tương
đối thoáng**. Chọn ảnh bìa mạnh nhất, giàu thông tin nhất trong bộ.

| Tiêu chí | Ngưỡng |
|---|---|
| Cạnh ngắn ảnh | từ 1000px trở lên (dưới đó phóng full bề ngang là vỡ nét) |
| Tỉ lệ | **1:1 (vuông) hoặc 4:5** — bắt buộc. Xem bên dưới |
| Ảnh bìa: góc dưới-trái | tương đối thoáng cho hook |
| Ảnh thân | nửa dưới không được sáng chói / rối chi tiết (chữ trắng đè lên qua màn tối) |

### Tỉ lệ ảnh: 1:1 hoặc 4:5

Ảnh dùng trong carousel phải là **1:1** hoặc **4:5**. Vuông fit bề ngang 1080px
ra cao ~1080 (phủ ~80% khung); 4:5 lấp kín khung. Cả hai đều cao đủ để nền chữ
phủ liền, không hở dải đen. Ảnh ngang fit bề ngang chỉ ra ~600px — hụt.

Tìm được ảnh đúng tỉ lệ thì thôi. Không thì **ảnh ngang ưu tiên GHÉP DỌC** (mục
dưới) — đỡ phải cắt nhiều, giữ trọn bề ngang. Chỉ khi không kiếm được ảnh thứ
hai cùng tone mới crop, và **chỉ với ảnh không có chữ**.

Luật crop đầy đủ — `crop_ti_le.py`, `crop_ok`, và vì sao **cắt tay bằng
PIL/cv2/ImageMagick là vi phạm và bị chặn** — ở [`LUAT_ANH.md`](/home/donniechu/content-team/LUAT_ANH.md) mục 4.

### Ảnh ngang chữ nhật: GHÉP hai ảnh cho đỡ phải cắt

Ghép là đường **bình thường** cho ảnh ngang, không phải phương án chữa cháy;
với ảnh có tiêu đề/chữ thì ghép là **bắt buộc**. Điều kiện duy nhất: hai hình
không được quá khác tone (cổng chặn dừng hẳn). Đầy đủ ở
[`LUAT_ANH.md`](/home/donniechu/content-team/LUAT_ANH.md) mục 5.

Ở carousel, ghi `"images": [a, b]` thay cho `"image"` — dùng được ở cả bìa lẫn
slide thân:

```json
{"images": ["slide_1.png", "slide_2.png"], "text": "..."}
```

Kết quả ghép lưu `<out>_N.ghep.png` rồi chạy mọi cổng chặn như ảnh thường. Hai
ảnh 16:9 ghép ra ~0.88 — nằm giữa 4:5 và 1:1, cổng tỉ lệ chấp nhận cả dải. Ảnh
dưới nằm dưới scrim chữ, nên đặt ảnh **quan trọng hơn ở trên**.

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
  "tam_co": "flagship",
  "cover":  {"image": "<ảnh bìa>", "hook": "<câu giật>", "category": "MODEL RELEASE", "label": "QWEN 3.8 27B · CEREBRAS"},
  "slides": [
    {"image": "<ảnh 2>", "text": "đoạn một.\n\nđoạn hai."},
    {"image": "<ảnh 3>", "text": "..."},
    {"image": "<ảnh 4>", "quote": "<câu trích dẫn>", "attrib": "Đọc bài “...” - <tác giả>"},
    {"image": "<chart ngang gốc>", "chart": true, "text": "chart full width, nguyên vẹn"},
    {"images": ["<chart ngang 1>", "<chart ngang 2>"], "text": "hai chart nguyên vẹn ghép dọc"},
    {"image": "<ảnh CEO>", "nhan_vat": "Greg Brockman", "quote": "...", "attrib": "Greg Brockman, ..."}
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

### Cổng về CHỮ và BỐ CỤC — riêng của carousel

1. **Tiếng Việt không dấu** trong bất kỳ chữ nào (hook, label, mọi slide) →
   **dừng hẳn**, in ra chỗ sai. Gõ lại có dấu. `--bo-qua-dau` chỉ cho tiếng Anh.
2. **Dưới 5 slide** (kể cả bìa) → **dừng** (chuẩn tối thiểu). **Quá 10 slide** →
   dừng (`draft_write` chỉ gom tới `_9`).
3. **Thiếu `cover.image`, `cover.hook`, hay `image` của một slide** → dừng. Mỗi
   slide thân phải có **`text` hoặc `quote`** — thiếu cả hai cũng dừng.
4. **Thiếu `cover.category`** → dừng (chip cyan ở bìa là category, không phải
   tên kênh).
5. **Dưới 2 slide quote** → dừng (mỗi carousel cần ≥2 pull-quote).
6. **Copy dài quá vùng chữ 30%** (ở cỡ chữ nhỏ nhất vẫn tràn) → dừng, báo cần
   cắt bớt bao nhiêu phần trăm chữ.
7. **Câu quote quá dài** (chạm 7 dòng ở cỡ nhỏ nhất) → dừng, báo cắt.
8. **Flagship <8 slide** → **dừng**. Tự nhận diện qua tên họ model frontier
   trong chữ, hoặc `"tam_co": "flagship"`.
9. **Em-dash** → không chặn, tự thay `—` thành dấu phẩy.

### Cổng về ẢNH — dùng chung cả đội

Ảnh trùng, sai tỉ lệ, chart thiếu `chart: true`, crop ảnh ngang, cắt tay né
cổng, ghép lệch tone, mặt người vô danh, độ phân giải, đáy ảnh sáng — **tất cả
nằm ở [`LUAT_ANH.md`](/home/donniechu/content-team/LUAT_ANH.md) mục 9**, code là `luat_anh.py`.

Cái **riêng** của carousel trong nhóm này chỉ có hai điều:

- Dải tỉ lệ hợp lệ là **4:5 → 1:1** (ảnh ghép dọc hai ảnh ngang rơi vào giữa dải).
- Slide **thân** khai `"chart": true` thì **miễn cổng tỉ lệ** — ảnh ngang được
  dán full bề ngang nguyên vẹn. Bìa thì không, vì hook đè lên ảnh.

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

## Tiêu chí ảnh dùng chung

Mọi luật về **ảnh** — không tự vẽ, tìm ảnh thật, chụp chart, tỉ lệ và crop, dấu
xuất xứ, ghép dọc, mặt người, không hai vùng, bảng cổng chặn — nằm ở **một tài
liệu chuẩn duy nhất**: [`LUAT_ANH.md`](/home/donniechu/content-team/LUAT_ANH.md).

Dùng chung với Ethan (`hero-image`) và Kite (`carousel-edu`); code là
`luat_anh.py`. **Đừng chép luật đó về đây** — chép là trôi khác nhau, đúng cái
đã xảy ra 03–04/09/2026. SKILL này chỉ giữ phần **bố cục riêng của carousel**.
