# Người đếm slide lạc quan hơn cổng chặn: cặp ghép lệch khung, mặt người lạ — 13/09/2026

Ticket theo dõi: LOW-46.

Tin TSMC doanh thu tháng 8, lần làm lại thứ ba (task `t_2d546375`, dcgr). Engine
đếm đủ 6 slide nên ngừng tìm ảnh. Dre dựng thật thì block, nguyên văn log:

```
- Cổng chặn loại ghép A5+A10 (tỉ lệ 0.75, lệch tone), nên chỉ còn A6, A7, A8, A9
- 4 ảnh < 6 slide tối thiểu, không được dùng lại mã
- Đã kanban_block kind=capability, chưa gửi album
```

Ông Chủ phải tự vào tìm thêm ảnh. Lần thứ ba trong hai ngày công thức đếm và
cổng chặn nói hai điều khác nhau về cùng một bộ ảnh (xem t_a8ffd2f6 ở
`schema._chi_ghep_duoc`).

Hai chỗ đếm sai, hai chỗ sửa:

1. **Cặp ghép đếm theo phép chia, không theo luật ghép.** `so_anh_dung_duoc`
   cộng `len(chi_ghep) // 2` — coi bất kỳ hai tấm chỉ-ghép nào cũng thành một
   slide. Cổng thật (`dre_nop._giai_ghep`) chỉ nhận cặp có tỉ lệ sau ghép trong
   dải 4:5..1:1. Hai tấm 3:2 như A5, A10 ra `1 / (1/1.5 + 1/1.5) = 0.75` — trượt.
   Cùng công thức tỉ lệ lại được chép ở ba nơi: `manifest.cap_ghep`,
   `dre_nop._giai_ghep`, và (ngầm) người đếm.
   Sửa: `luat_anh.ghep_vua_khung(r1, r2)` là bản duy nhất, cả ba nơi gọi. Người
   đếm tính **số cặp rời nhau lớn nhất** thật sự ghép vừa khung
   (`schema._so_cap_ghep_that`) — ghép tối ưu, không tham lam: bốn tấm C-A-B-D
   mà chỉ A-C, A-B, B-D vừa khung thì nhặt A-B trước ra 1 cặp, đúng là 2.
   Dùng `ti_le` đã đo trong manifest, không mở tệp ảnh.
   "Lệch tone" trong log không còn là luật: cổng tone đã bỏ khỏi hệ thống cùng
   ngày (`luat_anh.lech_tone` không còn gọi ở cổng nào), nên không đưa vào đếm.

2. **Mặt người không rõ ai vẫn được đếm.** Theo lời Dre ở cùng task, A3 có mặt
   người không rõ ai. `nop_chung.kiem_nhan_vat` chặn tấm như thế (vai không được
   bịa tên), `vai.anh_chinh_duoc` cũng đã loại, riêng người đếm vẫn tính.
   Sửa: `vai.mat_khong_ro_ai(a)` — một điều kiện cho cả `anh_chinh_duoc` lẫn
   `so_anh_dung_duoc`; áp cho cả tấm đứng một mình lẫn tấm trong cặp ghép (cổng
   ghép cũng kiểm mặt).

Test: `tests/test_dem_ghep_mat_nguoi.py` tái hiện đúng bộ của t_2d546375 (ra 4,
`du_nguyen_lieu("dre")` là False nên engine tìm tiếp). Hai test cũ khoá công thức
`// 2` bằng dữ liệu không có tỉ lệ đã sửa: `test_tim_anh_them` giờ khẳng định hai
tấm 3:2 thấp KHÔNG ghép được, hai tấm 16:9 thì được; `test_schema` (bộ
t_a8ffd2f6) ghi rõ tỉ lệ A7/A12 là giả định 16:9 vì bộ gốc không lưu.

Giới hạn còn lại:

- Mặt người có tên trong alt vẫn được đếm, dù `kiem_nhan_vat` còn đòi tên đó
  xuất hiện trong chữ bài — người đếm không có chữ bài trong tay.
- `ti_le` của manifest là tỉ lệ ảnh gốc; cổng ghép đo lại trên tệp. Hai số lệch
  nhau chỉ khi ảnh bị thay sau khi chuẩn bị.

Bài học: một con số "đủ/thiếu" mà không hỏi cùng luật với cổng chặn thì chỉ là
lời hứa. Mỗi lần cổng chặn thêm một điều kiện, người đếm phải gọi đúng hàm đó —
không chép công thức, không xấp xỉ bằng phép chia.

---
