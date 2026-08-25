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

**Trên thẻ chỉ còn đúng bốn thứ, tất cả cân giữa:**

```
        ảnh phủ kín, không viền
              ↓
       màn tối dày dần
              ↓
       TIÊU ĐỀ CÂN GIỮA
        phụ đề cân giữa
          @tên kênh
```

Không nhãn ruy-băng, không cụm `via`, không dãy icon mạng xã hội.

Vì sao bỏ hết: cả ba thứ đó đều **bám mép**. Chúng hợp với thẻ tin, nơi mọi thứ
lấy mép trái textbox làm mốc. Ở hero image thì khung đã gỡ, ranh giới đã gỡ, chữ
đã về giữa; để lại chúng thì tấm ảnh chỉ còn vài vết dính ở hai góc dưới, kéo
mắt ra khỏi trục.

**Tiêu đề và phụ đề cân giữa** vì mốc duy nhất còn lại là trục đối xứng của tấm
ảnh, chứ không phải mép nào cả.

`--category`, `--category-right` và `--via` **vẫn phải truyền** vì lệnh cần,
nhưng ở kiểu tràn chúng không được vẽ ra.

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
cd /home/donniechu/content-team && venv/bin/python card.py \
  --kieu tran --ratio 4:5 \
  --image <ảnh nguồn> --title "<tiêu đề>" --subtitle "<tóm tắt 1 câu>" \
  --via "@nguồn" --category "<nhãn>" --category-right "<nhãn phụ>" \
  --brand <donniechublog|dcgr> --out <đường dẫn ra>
```

**`--kieu tran` là lý do vai này tồn tại.** Thiếu nó là ra thẻ tin kiểu dài, tức
là làm lại việc của Iris.

**`--ratio 4:5` là khổ đăng chuẩn.** Mặc định của script là `free` (chiều cao
trôi theo ảnh), phải truyền tay.

**`--brand` chọn theo kênh sẽ đăng**: `donniechublog` xanh đêm, `dcgr` trắng đen.

Giá trị hợp lệ khác: `--ratio` nhận `free` `1:1` `4:5` `3:4`; `--handle` ghi đè
tên kênh; `--tagline` là mô tả ngắn dưới tên kênh.

Lưu ý về `--ratio`: nếu ảnh quá dọc so với tỉ lệ bạn khoá, script tự nâng lên tỉ
lệ cao hơn để không phải thu ảnh. Dòng in ra cuối lệnh cho biết thẻ thật sự ra
bao nhiêu, đọc nó.

## Bốn cổng chặn

Ba cái đầu làm lệnh **dừng hẳn**:

1. **Tiếng Việt không dấu** ở tiêu đề, phụ đề, category, category-right hoặc
   via. Từng in ra "CONG CU" trên thẻ thật. Gõ lại có dấu rồi chạy lại. Chỉ dùng
   `--bo-qua-dau` khi chữ **thật sự** là tiếng Anh.
2. **Thương hiệu không nhận ra** ở `--brand`.
3. **Thiếu cờ bắt buộc**: `--image --title --subtitle --via --out`.
4. **Em-dash** thì không chặn mà **tự thay**: `—` thành dấu phẩy, `–` thành gạch
   nối. Đừng dựa vào nó, cứ gõ đúng từ đầu.

## Giới hạn độ dài chữ

- **Tiêu đề tối đa 60 ký tự.** Font tiêu đề là JetBrains Mono, đơn cách, chiếm
  nhiều bề ngang. Quá thì bị thu nhỏ. Viết ngắn và đắt.
- **Phụ đề tối đa 140 ký tự**, một câu, tóm ý chính.
- Cả hai đều **tiếng Việt có dấu**.

Ở kiểu tràn chữ nằm đè lên ảnh, nên tiêu đề dài còn tệ hơn ở thẻ tin: nó ăn thêm
chiều cao textbox, và textbox cao lên thì màn tối trùm lên nhiều ảnh hơn.

## Nhãn category

Ở kiểu tràn **không nhãn nào được vẽ ra**, nhưng lệnh vẫn cần hai cờ. Truyền
`--category MODEL --category-right UPDATE` cho gọn là xong, đừng mất công cân
nhắc nhãn nào đúng.

(Luật chọn nhãn đầy đủ chỉ áp cho thẻ tin kiểu dài của Iris và Ethan.)

## Ghi nguồn vẫn bắt buộc, nhưng ghi ở chỗ khác

Kiểu tràn không in `via` lên thẻ nữa. Điều đó **không** có nghĩa là thôi ghi
nguồn: nó chuyển nghĩa vụ đó sang **chú thích bài đăng**.

Khi bàn giao, nói rõ nguồn ảnh cho người viết caption để họ đưa vào bài. Không
xác định được nguồn thì ghi tên miền của trang lấy ảnh, vẫn hơn là bỏ trống, và
tuyệt đối không thay bằng hình tự vẽ.

Đây là chỗ dễ rơi nhất của kiểu tràn: thẻ không còn nhắc bạn, nên phải tự nhớ.

## Nhìn lại trước khi giao

Mở tệp ra xem. Ba câu hỏi:

1. Có thấy đường kẻ, ngoặc góc, nhãn ruy-băng hay dãy icon nào không? Có là
   sai, báo lại. Trên thẻ chỉ được có ảnh, tiêu đề, phụ đề, tên kênh.
2. Chữ có nằm đè lên chi tiết dày của ảnh không? Có thì đổi ảnh.
3. Ảnh có bị phóng vỡ nét, hoặc rơi vào phương án nền mờ không? Có thì đổi ảnh.

Spec đầy đủ của hệ chữ và bảng màu ở
`/home/donniechu/content-team/STYLE_TEXT_SPEC.md`.
