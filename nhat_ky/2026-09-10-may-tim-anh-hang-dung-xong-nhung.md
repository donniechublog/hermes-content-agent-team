## Máy tìm ảnh hãng dựng xong nhưng treo sau chữ "nếu thiếu ảnh" (10/09/2026)

Ông Chủ, kèm hai link task: *"Dre vẫn ko chịu đi tìm các hình liên quan như logo,
brand, founder, trụ sở... của chủ đề được nhắc tới"* — **đúng câu đã nói hôm
09/09**, sau khi bản sửa 09/09 đã chạy được một ngày.

Bản 09/09 không sai chỗ nào nó làm: UA Wikimedia, hỏi nhiều hãng, Wikidata
`P18`/`P154`/`P112`, câu hỏi vision riêng cho từng loại tư liệu — đo lại vẫn ra
ảnh thật. Sai ở chỗ **nối nó vào dây chuyền**: `anh_chuan_bi.chuan_bi()` gọi
`_vong_thuong_hieu` bên trong một `if len(dung_duoc) < muc_tieu_tim or not
_co_bia(...)`. Tức nó là **vòng bù khi thiếu ảnh**, không phải một vòng đi tìm.

Đo bằng cách thay mọi pha nặng bằng stub rồi đếm vòng nào thật sự chạy (tin
`Samsung opens new chip plant in Texas`, ngưỡng Dre = 5):

```
2 ảnh của chính bài dùng được -> ['thuong_hieu', 'khai_niem']
4 ảnh                          -> ['thuong_hieu', 'khai_niem']
5 ảnh                          -> KHÔNG VÒNG NÀO
9 ảnh                          -> KHÔNG VÒNG NÀO
```

Bài viết về một hãng lớn mà báo gốc có sẵn 5 ảnh thì **không một request nào**
tới Commons/Wikidata — không logo, không chân dung founder, không trụ sở. Mà vai
thì bị brief cấm tự tải thêm ("chỉ dùng MÃ ẢNH, không tải/crop/mở gì thêm") và
từ kiến trúc 3 lớp cũng không còn công cụ tìm ảnh. Nên nhìn từ phía Ông Chủ nó
hiện ra đúng như *"Dre không chịu đi tìm"*, còn thật ra Dre không có gì để chọn.

**Bài học**: một tính năng "đi tìm thêm tư liệu" mà đặt sau điều kiện *thiếu* thì
nó chỉ là lưới an toàn, không phải tính năng. Hai thứ đó khác nhau ở chỗ ai được
hưởng: lưới cứu bài nghèo ảnh, tính năng làm giàu **mọi** bài. Câu của Ông Chủ cả
hai lần đều là loại thứ hai; lần đầu đọc thành loại thứ nhất vì câu 09/09 mở đầu
bằng *"ko thấy ảnh liên quan thì..."*.

Sửa: gọi thẳng, không `if`. Giá phải trả có trần sẵn — tối đa +4 ảnh một bộ,
tổng không quá `TOI_DA_ANH + 4`, và tin không nhắc hãng nào trong watchlist thì
`hang_trong_tin` trả rỗng nên vòng thoát ngay, không tốn request. Riêng nhánh
**mở browser đi chụp bảng xếp hạng** vẫn giữ điều kiện thiếu ảnh — đó mới là
phần đắt (một Chromium + `xep_hang.tim_va_chup`). Vòng **ảnh khái niệm** (cờ,
rack) cũng giữ nguyên điều kiện cũ: nó là ảnh chung chung, không phải ảnh của
chủ đề được nhắc tới.

**Vế thứ hai — "task này thì ko chịu dùng hình của Founder".** Brief của Dre thật
ra gắn nhãn đủ (`👤 CHÂN DUNG NHÀ SÁNG LẬP — <tên>, ... phải khai "nhan_vat"`),
nên với Dre nguyên nhân vẫn quy về lỗi trên: không có ảnh để mà dùng. Nhưng cùng
bộ ảnh đó, `ethan_chuan_bi.nhan_ethan` **dựng lại `ghi_chu` từ đầu** nên vứt mất
ghi chú `anh_thuong_hieu.nhan_thuong_hieu` đã cài, và thay bằng một câu *"trụ
sở/campus/biển hiệu"* dán chung cho **mọi** loại tư liệu. Một tấm chân dung tới
tay Ethan vì thế không có cái **tên** để khai `nhan_vat` — mà `kiem_nhan_vat`
chặn ảnh có mặt người không khai tên, nên Ethan buộc phải bỏ ảnh founder. Câu
nhãn tách thành `anh_thuong_hieu.nhan_theo_loai(th)`, một bản cho cả hai brief.

**Cổng chặn**: `tests/test_vong_thuong_hieu_luon_chay.py`. Ba test hành vi chạy
thật `chuan_bi()` với stub, cộng một cổng ở mức **mã nguồn** — đọc AST của
`chuan_bi()` và bắt lỗi nếu lời gọi `_vong_thuong_hieu` lại nằm trong một `if`.
Cổng AST cần thiết vì test hành vi dùng stub: ai đó treo lại điều kiện bằng một
biến khác thì con số có thể tình cờ thuận và test vẫn xanh. Đối chứng ngược trên
bản `git HEAD`: hai test đó hỏng đúng như mong đợi, hai test giữ hành vi cũ xanh
cả hai bên.

---

