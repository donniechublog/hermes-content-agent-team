---
name: inplace-translate
description: "Ranh giới giữa Gin và Itachi khi remake ảnh có chữ tiếng Anh sang tiếng Việt: nền phẳng ai làm, nền ảnh ai làm, khi nào dịch tại chỗ khi nào thiết kế lại bằng deck, bẫy màu và bẫy cỡ chữ đã đo được. Lệnh, danh sách vùng chữ, khung spec và cách sửa lỗi nằm trong brief mà gin_prepare.py / itachi_prepare.py in mỗi lần và trong báo [LOI] của nop; skill này chỉ giữ phần vai phải nghĩ."
version: 4.0.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [remake, translate, gin, itachi, deck, lama, ocr, instagram]
---

# inplace-translate — dịch ảnh có chữ sang tiếng Việt

Hai vai, chia theo **nền dưới chữ**, không theo công đoạn.

| | Gin | Itachi |
|---|---|---|
| Nhận | chữ trên **thẻ / dải nền phẳng** | chữ ở **mọi chỗ**, kể cả đè lên ảnh thật |
| Xoá bằng | `cv2.inpaint` (~0.1s) | LaMa (~2 phút/ảnh, CPU) |
| Ra | ảnh hoàn chỉnh tiếng Việt | ảnh hoàn chỉnh, hoặc deck thiết kế lại |
| Đầu vào | link IG/X, message_id, đường dẫn | message_id, đường dẫn |

Cả hai vai **tự làm trọn ảnh của mình**, không ai bàn giao nửa chừng cho ai.

```bash
cd /home/donniechu/content-team && venv/bin/python gin_prepare.py "<link|id>"       # Gin 1
cd /home/donniechu/content-team && venv/bin/python gin_submit.py <id>                   # Gin 3 (bước 2: spec.json)
cd /home/donniechu/content-team && venv/bin/python itachi_prepare.py <id> [<id2>…]  # Itachi 1
cd /home/donniechu/content-team && venv/bin/python itachi_submit.py <id>                # Itachi 3 (bước 2: spec.json)
```

`<id>` là message_id trong dòng `[Ảnh đính kèm đã tải về: …/<id>.jpg]`, hoặc
`<shortcode>_NN` mà `gin_prepare.py` sinh ra khi tải từ link.

## Nền phẳng hay nền ảnh: máy quyết, không phải vai

`gin_prepare.py` đo độ lệch chuẩn màu của **nền quanh hộp chữ, đã trừ mọi hộp
chữ khác** — không trừ thì dòng kế bên lọt vào vành và mọi vùng đều ra "nền
ảnh". Số đo trên ảnh thật của đội 07/09/2026:

- nền phẳng thật (dải đen dưới ảnh, nền trắng): **0.0 – 10.5**
- chữ đè lên ảnh thật (mặt người, phố, bokeh): **28.9 – 55.5**

Ngưỡng 12.0 nằm gọn giữa hai nhóm. Vai không phải nhìn ảnh để đoán; preview tô
xanh vùng phẳng, đỏ vùng ảnh. Chắc chắn máy sai thì `"ep_phang": [stt]`, nhưng
xem preview trước đã.

## Khi nào dịch tại chỗ, khi nào deck

- **Tại chỗ**: nhãn, badge, tiêu đề một dòng, slide ít vùng. Chữ Việt vẽ đúng
  box gốc, màu và cỡ đo được từ ảnh.
- **Đoạn nhiều dòng**: `gop` cả dải thành một khối. Cả hai vai đều có `gop`.
- **Deck** (chỉ Itachi): infographic dày chữ, giữ bố cục cũ thì chữ Việt không
  vừa. `bg_anh: true` để lấy nền sạch của slide đó.

## Sáu cái bẫy đã trả giá

**Cỡ chữ đo theo chiều cao MỰC, không theo chiều cao hộp.** Hộp OCR rộng hơn nét
chữ và rộng khác nhau tuỳ dòng có dấu hay không. Và khi so, phải vẽ thử **chính
chuỗi gốc** rồi suy ra cỡ — so bằng chuỗi tiếng Việt là sai: `GLOBAL EMPIRE`
toàn chữ hoa không có nét thòng xuống, bản dịch có dấu và có `g`, `y` sẽ cao hơn
ở cùng cỡ chữ, khớp chiều cao mực sẽ làm chữ Việt **nhỏ đi** thay vì bằng gốc.

**Dịch lẻ từng dòng thì cỡ chữ vỡ.** OCR trả một hộp mỗi dòng; bản dịch dài hơn
bị ép vào bề ngang dòng gốc rồi co nhỏ, nằm cạnh dòng bên là thấy ngay. Đo thật
07/09/2026 trên slide Hello Kitty: một dòng ra chữ bé bằng nửa các dòng còn lại.
`gop` sửa được. `gin_submit.py` có cổng chặn: chữ vẽ ra dưới **75% cỡ chữ gốc** thì
dừng, kèm số đo cả hai — "vừa hộp" không phải là đạt. Căn lề của khối gộp lấy
theo ĐA SỐ các vùng thành viên, không so tâm khối với tâm ảnh: một đoạn căn trái
dài gần hết bề ngang thì tâm nó cũng trùng tâm ảnh và cả đoạn bị thụt vào giữa.

**Font chọn bằng cách hỏi chính font đó, không bằng ngưỡng.** Đo bề ngang trung
bình một ký tự / chiều cao nét của chữ gốc, rồi hỏi từng font "vẽ chuỗi này ra
bề ngang bao nhiêu" và lấy font gần nhất. Ngưỡng cố định thì gãy: ngưỡng chỉnh
trên carousel Hello Kitty (condensed đo 0.386–0.463) làm cùng MỘT tiêu đề ba
dòng của carousel TECHS ra hai font khác nhau. Cách mới chạy lại toàn bộ ảnh đã
có: cả 6 tiêu đề ra đúng font nhìn thấy trên ảnh.

**Nhịp dòng gốc là nhịp của chữ KHÔNG DẤU.** Chữ hoa tiếng Việt có dấu thanh
trên và dấu nặng dưới nên cao hơn ~25% ở cùng cỡ chữ. Ép theo nhịp gốc thì dấu
dòng dưới chồng lên nét dòng trên: ảnh TECHS nhịp gốc 148px, dòng Oswald tiếng
Việt cùng cỡ cao 198px, "NGHỀ RỦI" nhìn như mất dấu. Giữ **khe hở** của nguyên
mẫu, còn chiều cao dòng đo theo chữ Việt thật.

**Mask phải nuốt cả VIỀN chữ.** Chữ trên thẻ quote hay có viền/bóng tối phía sau
để nổi lên khỏi ảnh. Otsu chỉ bắt nét sáng, viền tối bị coi là nền và ở lại —
xoá xong còn nguyên bóng ma đen hình chữ (TECHS, tiêu đề cao 132px, viền dày hơn
10px mặc định). Nới mask theo **15% chiều cao chữ**, không theo số px cố định.

**Trám của vai này không được lấn vùng của vai kia.** Mask nới rộng dễ tràn sang
hộp bên cạnh; hộp đó lại là vùng Itachi giữ nguyên, và Gin trám đè lên giữa chữ
tiếng Anh của nó (dải đen cắt ngang "AI COULD BECOME"). `gin_submit.py` chừa sẵn
mọi vùng nó không nhận.

**Màu đo được có thể lệch ở vùng nhỏ.** Màu chữ lấy bằng trung vị pixel phía chữ
sau khi tách Otsu. Hai dòng cùng khối mà một dòng `[20,55,134]`, dòng kia
`[237,248,249]` → dòng sáng gần chắc sai, ghi `color_rgb` theo dòng đúng. Ảnh
BodyMist 28/08 mất trắng 3 dòng vì bỏ qua.

## Chỗ chưa làm được

**Nền nửa sáng nửa tối thì mask bắt nhầm phía — xoá ra một mảng bôi màu.**
`swap_image_text.use_mask` quyết chữ sáng-hay-tối bằng trung vị độ sáng cả vùng so
với ngưỡng Otsu. Sau chữ có cả giấy trắng lẫn bàn tay thì trung vị bị kéo sát
ngưỡng và luật lật ngược: mask phủ lên NỀN thay vì lên chữ, LaMa xoá nền rồi lấy
màu chữ trám vào. Đo trên slide 3 carousel TECHS 07/09/2026:

| Vùng | Ngưỡng | Trung vị | Biên | Kết quả |
|---|---|---|---|---|
| `AI COULD BECOME` (sau chữ có giấy trắng) | 94 | 100 | **6** | sai, ra dải xanh |
| `CERTIFIED FOR` (nền đen) | 95 | 29 | 66 | đúng |
| `HIGH-RISK PROFESSIONS` (nền đen) | 88 | 7 | 81 | đúng |

Luật "phía ít pixel hơn là chữ" cũng hỏng ở đây: phía sáng chiếm 52%. Cùng gốc
lỗi khiến brief báo màu vùng đó là `[23,22,22]` thay vì xanh `[159,197,97]`.
Chưa có cổng nào chặn — **thấy brief báo màu chữ tối trên một dòng rõ ràng đang
sáng thì đừng chạy nop, báo Ông Chủ.**

**Ảnh lớn từng làm LaMa chết vì hết bộ nhớ.** Đã sửa (`swap_image_text.MAX_PX_LAMA`):
trên 3 Mpx thì dựng nền ở độ phân giải thấp rồi ghép lại đúng vùng đã xoá. Đo
trên máy này (7GB RAM, CPU): 1536x1912 chạy 16s, 2048x2550 đòi 14.7GB và chết —
mà 2048x2550 là kích thước chuẩn của carousel Instagram.

`assets/fonts/` **không có font nghiêng nào**. Bản gốc dùng chữ nghiêng (body
carousel TECHS) thì chữ Việt vẽ ra sẽ đứng — sai kiểu chữ, và không có cổng nào
bắt. Cần thì báo Ông Chủ bổ sung một face italic vào `assets/fonts/`.

## Ranh giới

Logo và hình khối thương hiệu gốc: giữ (`null`) và báo Ông Chủ, không tự thay.
Không vẽ minh hoạ, không nền AI (retouch/blend chờ GPU). Tiếng Việt mất dấu ở
bất kỳ vùng nào thì nop dừng; `--bo-qua-dau` chỉ khi bản dịch thật sự là tiếng
Anh. Ảnh mà phần lớn chữ nằm trên nền ảnh thì Gin đừng làm nửa vời — chuyển cả
ảnh cho Itachi, vài dòng tiếng Anh sót lại giữa thẻ là kết quả không dùng được.
