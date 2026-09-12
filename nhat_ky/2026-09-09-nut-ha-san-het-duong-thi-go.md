## Nút "hạ sàn" hết đường thì gỡ luôn bàn phím (09/09/2026)

Ông Chủ bấm "🖼 Dre làm với 4 ảnh" (imgtiep) trên một tin chỉ có 4/8 ảnh thật.
Engine trả lời đúng: *"Chỉ 4 ảnh thật mà carousel cần tối thiểu 5 slide — bấm
tiếp cũng không dựng được. Chuyển Kite vẽ vector, hoặc bỏ tin."* — nhưng **gỡ
luôn bàn phím ngay sau đó**. Hai đường vừa nêu không còn nút nào bấm được nữa;
Ông Chủ phải tự gõ lệnh.

Nguyên nhân: `_chot_nut()` (đuôi chung của mọi nút duyệt ảnh trong
`duyet_bai.py`) gỡ bàn phím **vô điều kiện**, không phân biệt "tương tác đã kết
thúc" (đã tạo task, đã ghi quyết định) với "vẫn còn đường phải chọn tiếp".
`_nut_ha_san()` — xử lý imgtiep — có ba nhánh: hạ sàn thành công (kết thúc),
sàn đã ở mức tối thiểu (kết thúc), và **hết đường vì số ảnh thật còn dưới cả
sàn cứng** `carousel.MIN_SLIDE` — nhánh cuối này KHÔNG kết thúc, nó đang hỏi
tiếp, nhưng trả về y hệt hai nhánh kia (chỉ một chuỗi `note`) nên `_chot_nut`
không có cách nào biết mà giữ bàn phím lại.

**Sửa:** `_nut_ha_san()` giờ trả `(note, keyboard)`; nhánh hết đường build lại
bàn phím "🎨 Gửi Kite vẽ vector" + "❌ Bỏ hẳn tin" (bỏ nút Kite nếu brand chưa
có Kite — cùng nguyên tắc "không hứa suông" đã áp cho nhánh `khong_kite` của
`anh_chuan_bi._route_thieu_anh`). `_chot_nut()` nhận thêm tham số `keyboard`
tuỳ chọn: có thì gắn lại đúng bàn phím đó, không thì gỡ trắng như cũ — mọi nút
khác (imgok/imgno/imgkite/imgredo) không đổi hành vi.

---

