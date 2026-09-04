---
name: hero-image
description: "Dựng ảnh cho kênh AI bằng card.py. MẶC ĐỊNH là --kieu quote (thẻ HOOK): một câu lớn trong khung dấu ngoặc kép + chip category (--tagline) + dòng nguồn (--attrib), đập vào mắt trong 3 giây; câu hook có thể là tiêu đề/góc giật hoặc lời có thật của người trong bài, không bắt buộc là trích dẫn. Kiểu --kieu tran (kicker + tiêu đề mono, liền một mặt phẳng, không khung không vạch) là lựa chọn đổi không khí. Gồm cách điều phối ảnh/chữ, các cờ bắt buộc, tô tên hãng, cổng chặn, chữ chìm vào ảnh. Dùng chung cho Ethan (donniechublog) và Ethan (dcgr.tech)."
version: 1.1.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [hero-image, card, tran, quote, trich-dan, designer, chad, donniechublog, dcgr]
---

# hero-image — mặc định kiểu quote, dự phòng kiểu tràn

Thẻ ảnh của đội, một mặt phẳng liền. **Ethan** dựng cho donniechublog, **Ethan**
dựng cho dcgr.tech. Hai người làm y hệt nhau, khác đúng một cờ:

| Vai | Profile | Cờ riêng |
|---|---|---|
| Ethan | `designer` | không cần gì thêm, donniechublog là mặc định |
| Ethan | `ethan` | `--brand dcgr` |

Ngoài cờ đó ra, mọi thứ trong tài liệu này áp cho cả hai như nhau.

**Kiểu mặc định là `--kieu quote`** — thẻ **HOOK** (mục "Kiểu quote" bên dưới):
một câu lớn trong khung dấu `"` sao cho **đập vào mắt trong 3 giây**, khiến người
ta phải đọc tiếp. Câu đó **không nhất thiết là lời ai nói** — đừng máy móc: nó có
thể là chính **tiêu đề / một góc giật** (mạnh nhất khi có **con số sốc**), hoặc
một **câu nói có thật** của người trong bài. `--tagline` là **chip category**
(MODEL RELEASE / FUNDING / ROBOTICS / IN BRIEF...). `--attrib`: nếu là lời thật
thì ghi `Phát biểu của <tên>`, nếu là hook/tiêu đề thì ghi nguồn `via <báo>` —
**không gán câu tự viết thành lời một người cụ thể** (bịa lời là sai). Kiểu **hero
tràn** (`--kieu tran`, phần đầu) vẫn dùng khi muốn đổi không khí. Đọc phần hero
tràn để nắm luật chọn ảnh/chữ chung; hai kiểu dùng chung mọi nguyên tắc về ảnh.

## Kiểu tràn là gì, và vì sao nó tồn tại

Kiểu mặc định `dai` cắt thẻ thành hai ô: ảnh ở trên, textbox màu đặc ở dưới,
giữa là một vạch ngang. Ranh giới thẳng băng đó làm bức ảnh nhìn như bị cắt cụt,
và mắt đọc thành hai thứ rời nhau.

Kiểu `tran` bỏ ranh giới. Ảnh chạy hết chiều cao thẻ, chữ nằm đè lên phần dưới,
và cái giữ cho chữ đọc được là một **màn tối dày dần** chứ không phải một mảng
màu đặc.

**Không vẽ khung, không một nét nào.** Không ngoặc góc, không nét dọc, không vạch
ngang. Đó là điều kiện để thẻ đọc ra là một mặt phẳng liền. Ngoặc góc chính là
một cái viền, và nét dọc trong vùng chữ lại tố ra đúng cái ranh giới mà kiểu
tràn sinh ra để xoá.

**Trên thẻ chỉ có bốn thứ, tất cả cân giữa:**

```
        ảnh phủ kín, không viền
              ↓
       màn tối dày dần
              ↓
        K I C K E R
      TIÊU ĐỀ, MỘT CÂU,
     TO VÀ CHẠY MẤY DÒNG
       CŨNG ĐƯỢC, CHIẾM
      CHỪNG MỘT PHẦN BA
              ↓
          @tên kênh
```

Không phụ đề, không nhãn ruy-băng, không cụm `via`, không dãy icon mạng xã hội.

Chữ tiêu đề là **Oswald**, sans condensed, không chân và không đơn cách. Thẻ tin
kiểu `dai` cũ dùng JetBrains Mono, font đơn cách. Hero image thì không: font đơn cách bắt mỗi chữ cái chiếm đúng
một ô, nên một câu dài ăn rất nhiều bề ngang và nhìn ra "code" chứ không ra
"báo". Oswald hẹp ngang nên chứa được câu dài ở cỡ chữ to.

Vì sao bỏ hết: cả ba thứ đó đều **bám mép**. Chúng hợp với thẻ tin, nơi mọi thứ
lấy mép trái textbox làm mốc. Ở hero image thì khung đã gỡ, ranh giới đã gỡ, chữ
đã về giữa; để lại chúng thì tấm ảnh chỉ còn vài vết dính ở hai góc dưới, kéo
mắt ra khỏi trục.

**Tiêu đề và phụ đề cân giữa** vì mốc duy nhất còn lại là trục đối xứng của tấm
ảnh, chứ không phải mép nào cả.

`--category`, `--category-right`, `--via` và `--subtitle` đều **không cần truyền**
ở kiểu tràn. Lệnh vẫn nhận nếu bạn có truyền, nhưng không vẽ ra thứ nào.

`card.py` lo hết phần vẽ. Việc của bạn là **chọn đúng ảnh** và **truyền đúng cờ**.

### Nguyên tắc một câu: chữ chìm vào ảnh

Cái giữ cho thẻ "liền" không phải font hay ảnh, mà là **không để lộ đường mép**
giữa chữ và ảnh. Ba lỗi phá nó — `card.py` đã chặn sẵn, việc của bạn là **không
chọn ảnh phá lại**:

- **Không hộp, không blur-strip.** Màn tối là gradient tan dần (đường cong,
  không mép), không phải một mảng màu đặc hay một dải mờ có cạnh. Nhìn thấy một
  đường ngang cắt qua thẻ là hỏng — mắt đọc thành "ảnh + bảng chữ" thay vì một mặt.
- **Màn tối tô bằng màu nền brand, không đen tuyền.** Script đã làm (nó trộn về
  `BG`); đen `#000` dán lên trông như tấm kính đặt trên ảnh, không phải ảnh tối lại.
- **Nửa dưới ảnh phải trống** để chữ nhường chủ thể (xem Bước 2). Chữ đè lên chi
  tiết dày là lỗi chọn ảnh, không phải lỗi màn tối.

Tóm lại: script lo phần vẽ liền mạch; bạn lo **chọn ảnh có bãi đáp** cho nó liền được.

## Bước 1 — tìm ảnh thật

**KHÔNG BAO GIỜ tự vẽ minh hoạ.** Vẽ ra là bịa đặt. Hero image phải phản ánh
đúng cái có thật trong nguồn. Không tìm được ảnh thật thì **báo lại, không dựng
thẻ**. Ông Chủ quyết định bỏ tin hay tự đưa ảnh vào. Luật cứng.

Ngoại lệ duy nhất là **bài arxiv**: xem mục "Bài arxiv" bên dưới. Với paper thì
"ảnh thật" chính là trang bìa của nó, chụp lại được chứ không phải vẽ ra.

Luôn chạy lệnh này trước, đừng tự đoán từ `image_url` trong task:

```bash
venv/bin/python anh_bai.py \
  --tieu-de "<tiêu đề tin>" --link "<link gốc>" --json
```

Script lấy ảnh từ link gốc **và** từ các báo khác đưa cùng tin, lọc bỏ
logo/favicon/thẻ thương hiệu, đo kích thước thật rồi xếp hạng.

Vì sao phải tìm rộng: link Finn nhặt thường là trang tài liệu, và `og:image` của
nó là thẻ thương hiệu chung. Ví dụ thật: `api-docs.deepseek.com` trả
`deepseek-social-card.jpeg` cho mọi bài.

### Chụp chart / bảng benchmark: full chiều rộng trước, chiều cao xét sau

**Luật Ông Chủ 04/09/2026.** Bề ngang của một chart là **nội dung**: trục, nhãn
chuỗi, cột cuối của bảng, cái điểm được tô sáng mà cả bài đang nói tới. Cắt mất
một phần bề ngang thì thứ còn lại không phải thiếu một tí — **nó nói sai**. Chiều
cao thì khác: cắt bớt mép trên/dưới một chart thường chỉ mất khoảng thở.

Đừng chụp bằng khung mặc định của công cụ nào. Khung mặc định luôn hẹp
(`screenshot.js` trong repo này đặt 820px), và một chart rộng 1400px trong khung
đó thì hoặc bị cắt, hoặc bị trang reflow xuống bố cục điện thoại — lúc đó có
chụp đủ bề ngang cũng không còn là cái chart trên desktop nữa.

```bash
venv/bin/python chup_chart.py --url "<trang có chart>" --ra chart.png
venv/bin/python chup_chart.py --url "<trang>" --chon "figure.chart" --ra chart.png
venv/bin/python chup_chart.py --url "<link ảnh trực tiếp>" --ra chart.png
```

Script mở ở khung 1920px, **đo bề ngang thật** của phần tử (`scrollWidth`, bắt cả
phần tràn ra ngoài khung nhìn), **nới khung** cho vừa rồi mới chụp ở DPR 2. Chụp
xong nó **đo lại ảnh ra**: bề ngang ảnh nhỏ hơn bề ngang thật của chart thì lệnh
dừng chứ không giao một tấm thiếu nửa phải. Ảnh rất cao thì nó chỉ cảnh báo —
chiều cao được phép cắt.

Link trỏ thẳng vào một tấm ảnh thì script tải **nguyên bản**, không resize, không
crop: bản gốc luôn đầy đủ hơn mọi bản chụp lại.

## Bước 2 — chọn ảnh, và cách ảnh được điều phối

**Ảnh luôn hiện full bề ngang.** Đó là ưu tiên số một và không thương lượng: cắt
bề ngang là mất nội dung. Chiều cao tự nhiên của ảnh ở bề ngang đó quyết định
phần còn lại, và chỉ có hai trường hợp.

**Ảnh cao hơn khổ thẻ** (dọc, gần vuông): ảnh phủ kín, cắt bớt theo chiều dọc,
**lớp chữ chèn lên** phần dưới qua màn tối. Không mất bề ngang nào.

**Ảnh thấp hơn khổ thẻ** (ngang, 16:9): ảnh nằm sát trên giữ nguyên tỉ lệ, và
**lớp nền của vùng chữ cao lên** bù đúng phần thiếu. Ảnh KHÔNG bị phóng to cho
vừa chiều cao: phóng lên là cắt mất bề ngang hoặc vỡ nét, cả hai đều tệ hơn một
mảng nền phẳng. Đáy ảnh tan dần vào nền nên không lộ ra đường ngang nào.

**Ảnh quá ngang mà có TIÊU ĐỀ** (slide, bảng, chart, banner): đừng crop mất
tiêu đề (Ông Chủ bắt lỗi 03/09/2026). Tìm thêm MỘT ảnh ngang nữa cùng bài và
đưa `--image2 <ảnh ngang thứ hai>`: script ghép DỌC hai ảnh trong cùng khung
(full bề ngang, nguyên tỉ lệ, cách 12px). Dùng được cho cả ba kiểu `dai`,
`tran`, `quote`; ở `tran`/`quote` ảnh dưới nằm dưới màn tối của chữ, nên đặt
ảnh quan trọng hơn ở `--image`. **Chọn hai ảnh CÙNG TONE** (cùng nền sáng/tối,
cùng gam màu): lệch tone đọc ra như hai vùng riêng biệt. Script in
`[CANH BAO] ghep anh` khi lệch nhiều — thấy là đổi ảnh.

Vậy nên **đừng loại ảnh chỉ vì nó ngang**. Cả hai hướng đều ra thẻ đúng. Chỉ còn
hai điều thật sự phải chọn:

| Tiêu chí | Ngưỡng | Vì sao |
|---|---|---|
| Cạnh ngắn | từ 1000px trở lên | Dưới mức đó phóng lên full bề ngang là vỡ nét |
| Nửa dưới ảnh | phải trống | Chỗ đó sắp có chữ đè lên |

**Nửa dưới phải trống là ràng buộc quan trọng nhất.** Màn tối làm chữ đọc được,
nhưng nó không xoá được chữ có sẵn trong ảnh. Ảnh chụp màn hình đầy chữ, bảng
benchmark dày đặc số: đọc thì tốt nhưng không làm nền được. Gặp loại đó thì chọn
ảnh khác, hoặc báo lại.

### Chart phải đi đường của chart

Với ảnh chart/bảng/screenshot thì vấn đề **không phải** "nửa dưới có trống
không" mà là **chart phải nguyên vẹn và trải full bề ngang**. Nên `card.py` nhận
diện loại ảnh này rồi ép sang đúng đường, thay vì bảo bạn "đổi ảnh khác".

Cách nhận diện (`card.la_chart`), đo trên bản thu nhỏ 480px:

| Phép đo | Chart/screenshot | Ảnh thật |
|---|---|---|
| `phẳng` — tỉ lệ cặp pixel kề nhau gần bằng nhau | 0,89–0,99 | 0,31–0,95 |
| `số màu` — số màu riêng biệt sau lượng hoá 5 bit | 42–65 | 350–4552 |

Phải **cả hai** mới kết luận là chart. Số màu là phép tách bạch nhất: đồ hoạ
vector dùng một bảng màu tay nên ra vài chục màu, ảnh chụp thật ra hàng nghìn.
Đo thử trên 16 thẻ thật trong `drafts/` — đều là ảnh thật cộng scrim phẳng, tức
là tình huống khó nhất — không tấm nào bị gọi nhầm.

Nhận ra là chart thì:

- **Hero (`quote`/`tran`)**: chart đi một mình bị chặn (cổng #4). Ghép dọc bằng
  `--image2`, hoặc để chart cho carousel.
- **Carousel slide thân**: bắt khai `"chart": true` — cờ đó cho `carousel.py`
  dán full bề ngang nguyên vẹn. Khai cờ đó cho một ảnh **không** phải chart cũng
  bị bắt: cờ này bỏ qua cổng tỉ lệ, dùng cho ảnh thường là lách cổng.
- **Carousel bìa**: chart làm bìa bị chặn (hook đè lên ảnh thì chart nằm dưới
  chữ) — ghép dọc `"images": [a, b]`, hoặc đổi bìa và để chart ở slide thân.

Còn "nửa dưới phải trống" ở trên vẫn là **luật biên tập**, không phải cổng chặn.
Đã thử làm nó thành cổng (đo độ sáng + độ phẳng của vùng dưới màn tối) rồi **gỡ
bỏ 04/09/2026**: nó bắt đúng những tấm mà cổng chart đã bắt, nhưng báo sai lý do
("đổi ảnh khác") nên đẩy vai đi sửa sai chỗ — trong khi việc phải làm là đưa
chart sang đường của chart.

Ảnh càng dọc thì chữ càng đè lên ảnh; ảnh càng ngang thì mảng nền phẳng càng
nhiều. Cả hai đều đúng, chọn theo ảnh nào mang thông tin thật.

Ảnh phụ giữ nguyên bản gốc, không đóng khung, chỉ đổi tên `<draft>_2.png`,
`_3.png`… tối đa 4 ảnh, và mỗi ảnh phải mang thông tin thật chứ không phải
trang trí.

## Bài arxiv: chụp trang bìa thay vì bó tay

Bài arxiv (link `arxiv.org/abs/...` hoặc `/pdf/...`) hầu như không có ảnh minh
hoạ. Trước đây gặp loại này là dừng và báo lại. Nhưng **"ảnh thật" của một paper
chính là trang đầu của nó**: tên công trình và nhóm tác giả, in trên nền trắng.
Chụp lại trang đó không phải vẽ ra hình bịa, nên nguyên tắc "không tự vẽ" vẫn giữ.

Khi `anh_bai.py` không trả ảnh nào **và** link là arxiv, chụp bìa:

```bash
venv/bin/python arxiv_bia.py --link "<link arxiv>" --out /tmp/src_<draft>.png
```

Script tải PDF, render **cả trang đầu** ở khổ điện thoại 4:5 (tên công trình
và tác giả ở trên, thân bài chạy tiếp xuống), rồi làm tối sẵn nửa dưới để
headline tiếng Việt đè lên đọc rõ. Thoát 0 là xong, coi như đã có ảnh chính, dựng
thẻ như bình thường. Không có ảnh phụ.

Thoát khác 0 nghĩa là không tải được PDF (paywall, link hỏng): lúc đó mới quay
lại quy tắc dừng và báo lại.

Chỉ arxiv. Nguồn khác chưa hỗ trợ; gặp loại paper khác mà muốn chụp bìa thì báo
lại để mở rộng `arxiv_bia.py`.

## Bước 3 — dựng

```bash
cd /home/donniechu/content-team && cd /home/donniechu/content-team && cd /home/donniechu/content-team && venv/bin/python card.py \
  --kieu tran --ratio 4:5 --kicker "<nhãn ngắn>" \
  --image <ảnh nguồn> --title "<một câu bao quát cả tin>" \
  --brand <donniechublog|dcgr> --out <đường dẫn ra>
```

Chỉ chừng đó cờ. **Không `--subtitle`, không `--via`, không nhãn** — kiểu tràn
không vẽ thứ nào trong số đó.

**`--kieu tran` là bắt buộc.** Thiếu nó là ra kiểu `dai` cũ: có khung, có vạch
ngăn, có phụ đề. Không vai nào dùng kiểu đó nữa.

**`--ratio 4:5` là khổ đăng chuẩn.** Mặc định của script là `free` (chiều cao
trôi theo ảnh), phải truyền tay.

**`--brand` chọn theo kênh sẽ đăng**: `donniechublog` xanh đêm, `dcgr` trắng đen.

Giá trị hợp lệ khác: `--ratio` nhận `free` `1:1` `4:5` `3:4`; `--handle` ghi đè
tên kênh.

Lưu ý về `--ratio`: nếu ảnh quá dọc so với tỉ lệ bạn khoá, script tự nâng lên tỉ
lệ cao hơn để không phải thu ảnh. Dòng in ra cuối lệnh cho biết thẻ thật sự ra
bao nhiêu, đọc nó.

## Sáu cổng chặn

Năm cái đầu làm lệnh **dừng hẳn**:

1. **Tiếng Việt không dấu** ở tiêu đề. Từng in ra "CONG CU" trên thẻ thật. Gõ
   lại có dấu rồi chạy lại. Chỉ dùng `--bo-qua-dau` khi chữ **thật sự** là
   tiếng Anh.
2. **Ảnh bị cắt bề ngang**, ở **mọi** kiểu. `card.py` đọc dấu vết
   `crop_ti_le.py` ghi trong metadata PNG: ảnh gốc ngang (≥1.4) mà đã bị cắt bớt
   bề ngang thì lệnh dừng. `crop_ti_le.py` cũng tự chặn ở đầu kia — nó chỉ cắt
   chiều cao, muốn cắt bề ngang phải `--cat-ngang` và chỉ được dùng cho ảnh chụp
   người/sản phẩm **không có chữ**.
3. **Chart đi một mình vào hero** (`--kieu quote`/`tran`). `card.py` tự nhận ra
   ảnh là chart/screenshot (xem "Chart phải đi đường của chart" bên dưới) và
   dừng: ở hai kiểu đó ảnh phủ kín thẻ, màn tối ăn ~40% đáy, chart đứng một mình
   là mất trục x và chú thích. Đường đúng: `--image2` để ghép dọc (chart ở
   `--image` nằm nửa trên còn nguyên), hoặc đưa chart về slide thân carousel với
   `"chart": true`. Ghi đè bằng `--bo-qua-anh` — cờ này giờ **chỉ** phục vụ cổng
   này.
4. **Thương hiệu không nhận ra** ở `--brand`.
5. **Thiếu cờ bắt buộc**: `--image --title --out`.
6. **Em-dash** thì không chặn mà **tự thay**: `—` thành dấu phẩy, `–` thành gạch
   nối. Đừng dựa vào nó, cứ gõ đúng từ đầu.

## Tiêu đề: viết như thế nào

Đây là chỗ dễ làm sai nhất, vì thói quen viết nhan đề rất khó bỏ.

Thẻ tin thông thường có tiêu đề là **nhan đề** còn phụ đề mới mang nội dung, nên
tiêu đề phải ngắn và không quá hai dòng.

Ở hero image **không có phụ đề**. Tiêu đề gánh toàn bộ: nó phải là **một câu
hoàn chỉnh bao quát được nội dung chính của tin**, đọc xong là hiểu chuyện gì
xảy ra mà không cần đọc gì thêm.

- **Không giới hạn số dòng, không giới hạn ký tự.** Script tự chọn cỡ chữ lớn
  nhất còn vừa chỗ, câu dài thì chữ nhỏ lại và xuống thêm dòng. Đừng cắt câu cho
  ngắn rồi để nó thành nhan đề cụt.
- **Một câu, không hai.** Không chấm giữa chừng, không nối bằng dấu chấm phẩy.
  Một hơi đọc hết.
- **Có số nếu tin có số.** Nhìn các mẫu tham khảo: con số nằm ngay trong câu
  ("2,6 tỉ năm trong 4 phút", "400 triệu đô ở định giá 5,4 tỉ"), đó là thứ giữ
  mắt người đọc.
- **Tiếng Việt có dấu**, và script sẽ chặn nếu thiếu.

Câu càng dài thì chữ càng nhỏ. Đó là đánh đổi thật, không phải lỗi: một câu 4
dòng chữ vừa vẫn hơn một nhan đề 1 dòng chữ to mà không nói được gì.

## Kicker

Nhãn ngắn phía trên tiêu đề, cỡ nhỏ, giãn chữ cái, màu nhấn. Không to nhưng đủ
làm điểm nhấn và cho người đọc biết ngay đây là loại tin gì.

```bash
--kicker "MODEL RELEASE"
```

Dùng **TIẾNG ANH**, viết hoa (script tự viết hoa nếu bạn quên). Vài giá trị hay
dùng:

`BREAKING` · `MODEL RELEASE` · `AGENT` · `FUNDING` · `BENCHMARK` · `OPEN SOURCE`
· `M&A` · `RESEARCH` · `INFRA` · `POLICY`

Không phải danh sách đóng, gặp loại tin khác thì đặt tên khác, miễn ngắn: **tối
đa hai từ**. Giãn chữ cái làm nhãn dài nở ra rất nhanh, ba từ là tràn.

Bỏ trống `--kicker` thì không vẽ gì cả, thẻ vẫn đúng. Nhưng có kicker thì hơn:
nó là thứ duy nhất còn lại nói cho người đọc biết đây là tin loại gì, sau khi
nhãn category đã bỏ.

## Tô tên thương hiệu trong tiêu đề

Tên hãng xuất hiện trong tiêu đề được **tô màu nhấn tự động**. Bạn không phải
làm gì cả: cứ viết tiêu đề bình thường, script tự nhận ra và tô.

```
META vừa phát hành mô hình...     ->  META màu cyan, phần còn lại trắng
HUGGING FACE và NVIDIA rót...     ->  cả hai tên đều được tô
```

Nhận diện theo danh sách trong `card.py`: `BRAND_TU` cho tên một từ, `BRAND_CUM`
cho tên nhiều từ như Hugging Face hay Boston Dynamics, `MAU_HANG` và `MAU_CUM`
cho màu của từng hãng. Gặp hãng chưa có trong danh sách thì **báo lại để thêm
vào**, đừng tìm cách đánh dấu tay.

Riêng `AI` đứng một mình **không** được tô: nó là từ hay gặp nhất trong mọi tiêu
đề, tô lên thì cả câu nhấp nháy.

### Hai thương hiệu tô khác nhau

**donniechublog** tô tên hãng bằng CYAN của bộ nhận diện. Bảng màu này đã có một
màu nhấn mạnh sẵn, dùng luôn nó thì thẻ vẫn nằm trong hệ màu của kênh.

**dcgr** tô bằng **màu riêng của chính hãng đó**. Nhắc Spotify thì ra xanh lá
Spotify, nhắc Nvidia thì ra xanh lá Nvidia, nhắc Anthropic thì ra màu đất của
Anthropic. Bảng màu dcgr chỉ có trắng và đen nên màu nhấn của nó chính là màu
chữ; màu thứ ba phải đến từ đâu đó, và lấy từ chủ thể đang được nhắc tới là hợp
lý nhất: bảng màu vẫn đơn sắc ở mọi chỗ khác, và chấm màu duy nhất trên thẻ luôn
mang ý nghĩa.

Màu hãng nào quá đậm để đọc trên nền tối (xanh navy Samsung, xanh TSMC) được tự
kéo sáng vừa đủ. Vẫn ra đúng sắc đó, chỉ sáng hơn.

Hãng chưa biết màu thì dcgr dùng màu hổ phách mặc định. Gặp trường hợp đó,
**báo lại để thêm màu thật vào `MAU_HANG`** trong `card.py`.

## Ghi nguồn vẫn bắt buộc, nhưng ghi ở chỗ khác

Kiểu tràn không in `via` lên thẻ nữa. Điều đó **không** có nghĩa là thôi ghi
nguồn: nó chuyển nghĩa vụ đó sang **chú thích bài đăng**.

Khi bàn giao, nói rõ nguồn ảnh cho người viết caption để họ đưa vào bài. Không
xác định được nguồn thì ghi tên miền của trang lấy ảnh, vẫn hơn là bỏ trống, và
tuyệt đối không thay bằng hình tự vẽ.

Đây là chỗ dễ rơi nhất của kiểu tràn: thẻ không còn nhắc bạn, nên phải tự nhớ.

## Kiểu quote — thẻ HOOK (KIỂU MẶC ĐỊNH)

Cùng `card.py`, khác đúng `--kieu quote`. **Đây là kiểu chuẩn/mặc định của kênh**:
**một câu lớn trong khung dấu `"`** phải **đập vào mắt trong 3 giây đầu**, khiến
người ta phải đọc tiếp. Đừng máy móc coi nó là "trích dẫn": câu đó **không nhất
thiết là lời ai nói trong bài** — nó có thể là:
- chính **tiêu đề / một góc giật** của tin (mạnh nhất khi có **con số sốc**), hoặc
- một **câu nói có thật** của người trong bài (nếu bài có câu đủ đắt).

Chọn cái nào gây ấn tượng hơn trong 3 giây. Ranh giới cứng duy nhất: **nếu ghi
`--attrib` là lời của một người** (`Phát biểu của <tên>`) thì câu phải **đúng là
lời có thật** của họ. Còn khi câu là tiêu đề/hook do mình soạn thì `--attrib` ghi
**nguồn** (`via <báo>`), **không** gán thành lời một người — bịa lời là sai.
Tin nhiều tầng không nén được vào một câu thì để carousel.

`--tagline` là **chip category** góc trên-trái: MODEL RELEASE / FUNDING / ROBOTICS
/ CYBERSECURITY / APPS / IN BRIEF... (không còn mặc định "daily AI update").

Bố cục script tự vẽ, đúng dạng pull-quote của báo:
- ảnh phủ kín + màn tối liền mạch (cùng bài với kiểu tràn, cùng nguyên tắc trên),
- câu trích dẫn lớn, đậm trong **khung 2 góc ngoặc bo tròn** (dấu " mở góc
  trên-trái, đóng góc dưới-phải, nét ngang xuyên giữa dấu). **Không đặt tay,
  không sửa** — script tự vẽ; bạn chỉ cần câu đủ ngắn để đọc lớn.
- tagline góc **trên-trái**, brand text (tên kênh) góc **trên-phải**, dòng nguồn
  **canh giữa** dưới khung.
- **Hai chữ trên đỉnh theo phong cách NEOBRUTALISM**: mỗi chữ nằm trong một
  **chip khối đặc** — viền đen dày, **bóng cứng lệch** (không mờ), chữ **JetBrains
  Mono** đậm. Tagline chip **trắng** (trái), tên kênh chip **`CYAN` nhận diện**
  (donniechublog `#00cce0`, dcgr trắng — trái/phải vẫn phân biệt bằng vị trí),
  chữ trong chip đều **đen**. Script tự vẽ, không chỉnh tay.
- **Màu phần khung**: nét khung = **`CYAN` của bộ nhận diện** (không dùng xanh
  Apple). **Dấu " đổi theo HÃNG được nhắc** trong quote/nguồn (Nvidia→xanh lá,
  Hugging Face→vàng…), không nhận ra hãng thì dấu " cũng CYAN.

```bash
venv/bin/python card.py --kieu quote --ratio 4:5 \
  --image <ảnh thật> \
  --tagline "<CATEGORY ngắn tiếng Anh>" \
  --title "<CÂU HOOK có dấu, đập vào mắt trong 3s>" \
  --attrib "<'via <báo>' hoặc 'Phát biểu của <tên>' nếu là lời thật>" \
  --brand <donniechublog|dcgr> --out drafts/<id>.png
```

- **`--title` là câu HOOK** — đập vào mắt trong 3 giây. Có thể là **tiêu đề/góc
  giật** (mạnh nhất khi có con số) HOẶC **lời có thật** của người trong bài. Giữ
  hoa/thường tự nhiên (KHÔNG viết hoa toàn bộ như tiêu đề tràn). Câu quá dài
  script thu nhỏ dần rồi thêm "…"; sống ở chỗ **ngắn, đọc lớn** — chạm 7 dòng là
  nên cắt.
- **`--tagline` là chip category** (góc trên-trái): MODEL RELEASE / FUNDING /
  ROBOTICS / CYBERSECURITY / APPS / IN BRIEF... — chọn đúng chủ đề tin.
- **`--attrib` là dòng nguồn**: hook/tiêu đề → `via <báo>`; lời có thật của một
  người → `Phát biểu của <tên>, <chức/hãng>`. **Không** gán câu tự viết thành lời
  một người cụ thể. Vẫn có cổng chặn tiếng Việt không dấu như mọi chữ khác.
- **Ảnh chọn như hero image**: cạnh ngắn ≥1000px, nửa dưới thoáng để câu đè lên
  đọc rõ; ảnh vuông/dọc hợp hơn ảnh ngang. Vẫn luật cứng **không tự vẽ minh hoạ** —
  ảnh phải thật và liên quan tới tin.

## Nhìn lại trước khi giao

Mở tệp ra xem. Ba câu hỏi:

1. Có thấy đường kẻ, ngoặc góc, nhãn ruy-băng, phụ đề hay dãy icon nào không?
   Có là sai, báo lại. Trên thẻ chỉ được có ảnh, kicker, tiêu đề, tên kênh.
2. Tiêu đề có tên hãng nào mà **không** được tô màu không? Có nghĩa là hãng đó
   chưa có trong danh sách, báo lại để thêm.
3. Chữ có nằm đè lên chi tiết dày của ảnh không? Có thì đổi ảnh.
4. Ảnh có bị phóng vỡ nét, hoặc rơi vào phương án nền mờ không? Có thì đổi ảnh.

Spec đầy đủ của hệ chữ và bảng màu ở
`/home/donniechu/content-team/STYLE_TEXT_SPEC.md`.

## Tiêu chí ảnh dùng chung — `luat_anh.py`

Ông Chủ chốt 04/09/2026: **một bộ tiêu chí chung cho mọi vai làm ảnh**, thay vì
mỗi vai một bộ. Đường cắt một câu:

> *"Ảnh này có được dùng không"* → **chung**, nằm ở `luat_anh.py`.
> *"Đặt nó lên khung thế nào"* → **riêng** từng vai, nằm ở renderer.

Nên các luật dưới đây **giống hệt nhau** ở Ethan (`card.py`), Dre
(`carousel.py`) và bất kỳ vai làm ảnh nào sau này — sửa một chỗ là cả đội đổi
theo, không còn cảnh mỗi bên một bản rồi trôi khác nhau:

| Cổng | Chặn hay cảnh báo |
|---|---|
| Ảnh trùng (theo nội dung tệp) | chặn |
| Chart/screenshot thiếu `chart: true` | chặn |
| Khai `chart: true` mà máy không nhận ra chart | **chỉ cảnh báo** — phép đo bỏ sót chart có đường màu khử răng cưa, chặn ở chiều này là giết việc đúng |
| Ảnh gốc ngang đã crop, không khai `crop_ok` | chặn |
| Ảnh đúng khít 4:5/1:1 mà không có dấu xuất xứ (cắt tay) | chặn |
| Ghép hai ảnh quá khác tone | chặn |
| Mặt người mà không khai `nhan_vat` | chặn |
| Cạnh ngắn <1000px, đáy ảnh quá sáng | cảnh báo |

**Dấu xuất xứ:** mọi công cụ trong đội sinh ra ảnh đều tự đóng dấu vào PNG
(`crop_ti_le.py`, `arxiv_bia.py`, `chup_chart.py`, `doi_chu_anh.py`, ghép dọc).
Ảnh không dấu mà lại đúng khít tỉ lệ là dấu hiệu cắt tay bằng công cụ ngoài —
bị chặn. Ảnh gốc vốn đã đúng tỉ lệ thì chạy qua `crop_ti_le.py` một lần để đóng
dấu, cắt 0, không mất gì.
