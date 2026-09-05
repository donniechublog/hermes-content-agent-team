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
ảnh vào. Luật cứng, không có ngoại lệ nào ngoài mục 1.4 (bìa paper arxiv).

Bỏ thẳng, không cần cân nhắc:

- **Ảnh AI tạo có người** (stock persona) và **ảnh người lạ lấy từ báo**.
- **Ảnh rò rỉ** (leak, chưa được xác nhận chính thức): rủi ro cả về độ chính xác
  lẫn bản quyền. Tìm ảnh chính thức khác thay vào.

---

## 1. Tìm ảnh thật

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
  đã lọc liên quan + Wikimedia Commons), nhìn và đếm lại. Vẫn thiếu → brief nói
  thẳng "THIẾU ẢNH", vai gộp ý/giảm slide hoặc báo — **không nhồi rác cho đủ**.
- Brief ghi số **nguồn** của ảnh dùng được; bộ ≥ 4 slide mà chỉ một nguồn là dấu
  hiệu cần xem lại.

### 1.3 Tin model ra mắt: ưu tiên benchmark table/chart

Bảng so sánh điểm benchmark (MMLU, HumanEval, lập trình, toán…) và biểu đồ là
**bằng chứng mạnh nhất** — ưu tiên trước cả ảnh logo/hero. Chụp bản to (cạnh
ngắn ≥1000px; bảng chữ nhỏ càng phải to).

### 1.4 Bài arxiv: chụp trang bìa paper

Ngoại lệ duy nhất của luật "không tự vẽ" — với paper thì "ảnh thật" chính là
trang bìa của nó.

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
(`screenshot.js` trong repo này đặt 820px), và một chart rộng 1400px trong khung
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

Renderer còn tự **lùi điểm bắt đầu màn tối xuống dưới mép chart**, để đáy chart
(trục x, nhãn, dòng chú thích) không bị làm tối.

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
`arxiv_bia.py`, `chup_chart.py`, `doi_chu_anh.py`, và ảnh ghép dọc.

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
hai vùng, đã bỏ 04/09/2026). Ảnh dưới nằm dưới màn tối của chữ, nên đặt **ảnh
quan trọng hơn ở trên**.

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

- **Không vùng đen riêng** đặt dưới ảnh để chứa chữ. Chữ luôn đè lên ảnh qua
  gradient dài.
- **Không vạch, không viền, không đường kẻ** ngang giữa khung.
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
| Chart đi một mình vào khung đặt chữ đè lên ảnh | `kiem_chart_mot_minh` | chặn |
| Ảnh quá ngang so với khung khoá khổ (<50%) | `kiem_anh_thap` | chặn |
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

| | Ethan (`card.py`) | Dre (`carousel.py`) | Itachi (`deck.py`) |
|---|:--:|:--:|:--:|
| trùng · xuất xứ · mặt người · độ nét · đáy sáng | ✅ | ✅ | ❌ |
| crop ngang · lệch tone | ✅ | ✅ | ❌ |
| chart một mình | ✅ | – | ❌ |
| ảnh quá ngang | ✅ | – | ❌ |
| `chart: true` · dải tỉ lệ | – | ✅ | ❌ |

Dấu `–` là **không áp dụng cho khung đó**, khác hẳn `❌` là **chưa đấu**. Cột
Itachi còn trống nguyên.

Sửa một luật ở đây là **cả đội đổi theo** — đó là lý do tài liệu này tồn tại.
Đừng chép luật sang SKILL của vai; SKILL chỉ trỏ về đây.

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
