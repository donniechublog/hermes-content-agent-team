# Ảnh rối vẫn được chọn, nền chữ trên ảnh rối nham nhở — 13/09/2026

Ticket theo dõi: LOW-47.

Bộ carousel Anthropic/Nvidia IPO (dcgr, draft
`anthropic-ipo-nvidia-c-n-nh-c-r-t-10-t-u-dre-dcgr`) lên topic với ba ảnh
"rối" dù kho có nhiều ảnh trụ sở Nvidia sạch hơn hẳn:

```
slide 2  A5   chụp màn hình splash "Claude", còn dòng "loading chart..."
slide 5  A9   đồ hoạ "Nvidia Weighs $10B Investment as Anthropic IPO..." — chữ in
              chìm lộ lem nhem sau câu quote Việt
slide 7  A8+A10  tiêu đề báo Nga RBC + logo báo, toàn chữ tiếng Nga
```

Ông Chủ, nguyên văn: *"không ưu tiên sử dụng tất cả những ảnh nhìn rối, trong
trường hợp buộc phải dùng, thì lớp nền của text phải làm cho nghiêm chỉnh, đừng
nham nhở"*.

Ba lỗi, ba chỗ:

1. **Không ai biết ảnh nào rối.** Vision chỉ hỏi `LIEN_QUAN`. Cả ba ảnh trên
   đều đúng chủ đề nên qua cổng; nhánh chụp trang nguồn còn không hỏi lại chủ
   đề. Không có trường nào trong manifest nói "ảnh này nhìn rối", nên brief và
   cổng chặn không có gì để dựa.
   Sửa: `chuan_bi/nhin.py` hỏi thêm dòng `ROI` ở MỌI nhánh (`CAU_ROI`), trả qua
   tham số `ket_qua` để tuple trả về giữ nguyên 2/3 phần tử (Bob và test mở gói
   cố định). `phan_loai` ghi `roi`; ảnh rối bị gỡ nhãn bìa và có ghi chú đầu
   dòng "⚠️ ẢNH RỐI".

2. **Không có gì chặn chọn ảnh rối khi còn ảnh sạch.** Ghi chú trong brief chỉ
   là lời mềm — đúng bài học của LOW-45/LOW-46 hôm nay.
   Sửa: `nop_chung.kiem_anh_roi`, gọi từ `dre_nop.giai_spec` và
   `ethan_nop.giai_spec`. Chỉ báo lỗi khi CÒN ảnh sạch thật sự thay được: vision
   nói rõ `roi is False`, liên quan, ảnh chụp không phải chart, không mặt người,
   không ngang, chưa dùng trong bài này và chưa lên bài khác
   (`luat_anh.kiem_da_dung`). Hết ảnh sạch thì ảnh rối vẫn được dùng.

3. **Nền chữ trên ảnh rối là lớp mờ 55%.** `carousel._lop_neu_can` trần
   `TOI_TOI_DA=140`, mờ `BLUR_RADIUS=14` — đủ cho ảnh chụp thường, nhưng chữ in
   sẵn trong đồ hoạ vẫn lộ ra sau câu quote. Thẻ Ethan (`card._mo_vung_chu`)
   chỉ làm mờ, cùng lỗi.
   Sửa: slide/thẻ dùng ảnh rối nhận cờ `roi` (dre_nop → carousel.spec, ethan_nop
   → `card.py --roi`) và vẽ nền ĐẶC màu BG (`carousel._nen_dac_duoi_chu`,
   `card._nen_chu_nghiem`). Ghi thành ngoại lệ có chủ đích ở `LUAT_ANH.md` mục 7.1.

   Chỗ bắt đầu nền đặc phải ĐO, không đặt cố định. Ba lần dựng thử trên đúng
   ảnh A9, mỗi lần một cách hỏng:

   ```
   lan 1  nen dac tu ngay tren chu cua ta   -> tieu de in san (hang 690-989) lo nguyen,
                                               dai chuyen 180px cat nua dong "Markets Near Record"
   lan 2  leo len khoang lang gan nhat       -> the Ethan: khe 1110-1136 ngay duoi chu in san
                                               cung la "lang", dung o do thi tieu de lo nguyen
   lan 3  bo khoang lang con chu in san tren -> slide quote: leo cham tran 40% (540), dai chuyen
                                               cat nua chu "INVESTMENT" (hang 520-539)
   ```

   `card._moc_nen_dac` (dùng chung carousel + thẻ): đo chi tiết ngang từng hàng
   pixel, từ trên chữ của ta leo lên tìm ≥24 hàng lặng liền nhau; chỉ nhận khoảng
   lặng khi 160px phía trên nó không còn khối chữ in sẵn (TB 15 hàng ≥ 25 — đo:
   chữ 25–47, ảnh chụp 8–21); chạm trần 40% thì quay về khoảng lặng cao nhất đã
   gặp chứ không dừng ở trần. Ngưỡng "lặng" là 7, không phải 6: khe 620–689 của
   slide quote dao động 3–6, ngưỡng 6 làm chuỗi đứt. Kết quả đo trên A9:

   ```
   slide quote   nen dac tu hang 676, dai chuyen 621-676
   slide than    nen dac tu hang 688, dai chuyen 621-688
   the Ethan     nen dac tu hang 765, dai chuyen 690-765
   ```

Giới hạn còn lại, ghi rõ để khỏi tưởng đã xong:

- Manifest chuẩn bị TRƯỚC bản vá không có `roi` → cổng im lặng cho tới khi
  chạy lại chuẩn bị ảnh. Không tự vá ngược manifest cũ.
- Ảnh ngang không được tính là "ảnh sạch thay được" vì trên `main` chưa có
  `cat_ngang_ok` (nằm ở `feat/org-id-multitenant`, 64e35c4). Cổng vì thế chặn
  ít hơn mức có thể, không chặn oan.
- Kite và Bob chưa áp. Bob vẫn nhận câu hỏi có dòng ROI nhưng không dùng.

Phát hiện phụ lúc làm ticket này: 09:19 UTC thư mục chạy thật trên máy chủ bị
chuyển từ `feat/org-id-multitenant` sang `main`. Hai nhánh lệch nhau 22 commit
mỗi bên; toàn bộ phần tìm ảnh (`tim_anh_them`, Yandex, chụp nhiều báo, loại trùng
dHash, ngưỡng slide 6/7) và ba bản vá sáng nay (8709bf3, 23c5087, b16f250) không
có trên `main`. Ticket này dựng trên `main` vì đó là nhánh đang chạy; chọn nhánh
nào là nguồn sự thật là việc của Ông Chủ.

Bài học: "đúng chủ đề" và "nhìn được" là hai câu hỏi khác nhau, và cổng nào
cũng chỉ hỏi câu thứ nhất. Một ảnh đúng tin 100% vẫn có thể là ảnh xấu nhất
kho. Mỗi lần thêm một tiêu chí thẩm mỹ, phải thêm cả ba: con mắt nhận ra, cổng
chặn chọn sai, và cách vẽ khi buộc phải dùng — thiếu một thì lời dặn lại thành
lời mềm.

---
