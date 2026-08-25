---
name: hero-image
description: "Dựng hero image kiểu tràn cho kênh AI bằng card.py — liền một mặt phẳng, không khung, không vạch ngăn. Cách chọn ảnh cho kiểu tràn, các cờ bắt buộc, và bốn cổng chặn. Dùng cho vai Chad (profile designer)."
version: 1.0.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [hero-image, card, tran, designer, chad, donniechublog, dcgr]
---

# hero-image — kiểu tràn, liền một mặt

Hero image là ảnh mở đầu, thứ **đứng một mình được**. Iris và Ethan dựng thẻ tin
hằng ngày; đây là việc khác.

Khác biệt nằm ở **bố cục**, không nằm ở nguồn ảnh. Mọi ràng buộc về ảnh thật
giống hệt hai vai kia.

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
của Iris và Ethan vẫn dùng JetBrains Mono, font đơn cách đó là một phần nhận
diện của chúng. Hero image thì không: font đơn cách bắt mỗi chữ cái chiếm đúng
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

## Bước 1 — tìm ảnh thật

**KHÔNG BAO GIỜ tự vẽ minh hoạ.** Vẽ ra là bịa đặt. Hero image phải phản ánh
đúng cái có thật trong nguồn. Không tìm được ảnh thật thì **báo lại, không dựng
thẻ**. Ông Chủ quyết định bỏ tin hay tự đưa ảnh vào. Luật cứng, không ngoại lệ.

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

## Bước 2 — chọn ảnh, và đây là chỗ kiểu tràn kén hơn hẳn

Kiểu tràn phải phóng ảnh lên phủ kín thẻ. Nên **đừng chỉ nhìn điểm, hãy nhìn
kích thước và tỉ lệ**.

| Tiêu chí | Ngưỡng | Vì sao |
|---|---|---|
| Hướng | dọc hoặc gần vuông | Khổ đăng là 4:5, ảnh dọc mới phủ kín mà không cắt nhiều |
| Cạnh ngắn | từ 1000px trở lên | Dưới mức đó phóng lên là vỡ nét |
| Nửa dưới ảnh | phải trống | Chỗ đó sắp có chữ đè lên |

**Ảnh ngang dẹt kiểu og:image 1200x630 là trường hợp tệ nhất**: phải phóng hơn 2
lần mới phủ kín khổ 4:5, chữ trong ảnh bay mất một nửa.

Script chặn ở **ngưỡng phóng 1.35 lần**. Quá ngưỡng thì nó tự đổi cách: nền là
bản cover làm mờ, còn bản sắc nét đặt trọn vẹn lên trên. Vẫn liền một mặt phẳng,
không có vạch, nhưng ảnh không còn phủ kín. **Đó là phương án đỡ, không phải
phương án đúng.** Thấy nó kích hoạt thì quay lại chọn ảnh khác trước đã.

**Nửa dưới phải trống là ràng buộc riêng của kiểu tràn.** Màn tối làm chữ đọc
được, nhưng nó không xoá được chữ có sẵn trong ảnh. Ảnh chụp màn hình đầy chữ,
bảng benchmark dày đặc số: hợp với thẻ tin của Iris, không hợp hero image. Gặp
loại đó mà vẫn muốn dùng thì báo lại, đừng cố.

Ảnh phụ giữ nguyên bản gốc, không đóng khung, chỉ đổi tên `<draft>_2.png`,
`_3.png`… tối đa 4 ảnh, và mỗi ảnh phải mang thông tin thật chứ không phải
trang trí.

## Bước 3 — dựng

```bash
cd /home/donniechu/content-team && cd /home/donniechu/content-team && cd /home/donniechu/content-team && venv/bin/python card.py \
  --kieu tran --ratio 4:5 --kicker "<nhãn ngắn>" \
  --image <ảnh nguồn> --title "<một câu bao quát cả tin>" \
  --brand <donniechublog|dcgr> --out <đường dẫn ra>
```

Chỉ chừng đó cờ. **Không `--subtitle`, không `--via`, không nhãn** — kiểu tràn
không vẽ thứ nào trong số đó.

**`--kieu tran` là lý do vai này tồn tại.** Thiếu nó là ra thẻ tin kiểu dài, tức
là làm lại việc của Iris.

**`--ratio 4:5` là khổ đăng chuẩn.** Mặc định của script là `free` (chiều cao
trôi theo ảnh), phải truyền tay.

**`--brand` chọn theo kênh sẽ đăng**: `donniechublog` xanh đêm, `dcgr` trắng đen.

Giá trị hợp lệ khác: `--ratio` nhận `free` `1:1` `4:5` `3:4`; `--handle` ghi đè
tên kênh.

Lưu ý về `--ratio`: nếu ảnh quá dọc so với tỉ lệ bạn khoá, script tự nâng lên tỉ
lệ cao hơn để không phải thu ảnh. Dòng in ra cuối lệnh cho biết thẻ thật sự ra
bao nhiêu, đọc nó.

## Bốn cổng chặn

Ba cái đầu làm lệnh **dừng hẳn**:

1. **Tiếng Việt không dấu** ở tiêu đề. Từng in ra "CONG CU" trên thẻ thật. Gõ
   lại có dấu rồi chạy lại. Chỉ dùng `--bo-qua-dau` khi chữ **thật sự** là
   tiếng Anh.
2. **Thương hiệu không nhận ra** ở `--brand`.
3. **Thiếu cờ bắt buộc**: `--image --title --out`.
4. **Em-dash** thì không chặn mà **tự thay**: `—` thành dấu phẩy, `–` thành gạch
   nối. Đừng dựa vào nó, cứ gõ đúng từ đầu.

## Tiêu đề: viết như thế nào

Đây là chỗ khác thẻ tin nhiều nhất, và là chỗ dễ làm sai nhất nếu bạn quen tay
với Iris.

Ở thẻ tin, tiêu đề chỉ là **nhan đề** còn phụ đề mới mang nội dung, nên tiêu đề
phải ngắn dưới 60 ký tự và không được quá 2 dòng.

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

Nhận diện theo danh sách trong `card.py` (`BRAND_TU` cho tên một từ, `BRAND_CUM`
cho tên nhiều từ như Hugging Face, Boston Dynamics). Gặp hãng chưa có trong danh
sách thì **báo lại để thêm vào**, đừng tìm cách đánh dấu tay.

Riêng `AI` đứng một mình **không** được tô: nó là từ hay gặp nhất trong mọi tiêu
đề, tô lên thì cả câu nhấp nháy.

**Bảng màu dcgr không tô được.** Nó chỉ có trắng và đen, màu nhấn chính là màu
chữ, nên tô hay không cũng như nhau. Đó là đúng ý đồ đơn sắc, không phải lỗi.

## Ghi nguồn vẫn bắt buộc, nhưng ghi ở chỗ khác

Kiểu tràn không in `via` lên thẻ nữa. Điều đó **không** có nghĩa là thôi ghi
nguồn: nó chuyển nghĩa vụ đó sang **chú thích bài đăng**.

Khi bàn giao, nói rõ nguồn ảnh cho người viết caption để họ đưa vào bài. Không
xác định được nguồn thì ghi tên miền của trang lấy ảnh, vẫn hơn là bỏ trống, và
tuyệt đối không thay bằng hình tự vẽ.

Đây là chỗ dễ rơi nhất của kiểu tràn: thẻ không còn nhắc bạn, nên phải tự nhớ.

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
