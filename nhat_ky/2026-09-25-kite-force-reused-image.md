# Kite dừng vì bộ ép đòi ảnh đã lên bài khác — 25/09/2026

Ticket theo dõi: LOW-415.

Ông Chủ gửi hai tin ⛔ trong topic Kite: *Carousel deck: OpenEvidence đạt định giá 15 tỷ USD*
(blog) và *Thẩm phán Mỹ chất vấn ByteDance trong phiên xử* (dcgr). Cả hai cùng một kiểu:

```
figure_right_use ép A3 trên slide thân
[LOI] slide 5 (A3): TRUNG anh da dung o bai 'byteplus-cua-bytedance-ra-mat-nen-tang-p-kite-dcgr' (kite, 22/09 11:41)
```

Bộ ép (`kite_prepare._force_raw`) không hỏi cổng `check_not_reused`, còn cổng nộp của
Kite thì hỏi. Tấm đã lên bài khác trong 14 ngày nằm ở cả hai danh sách: dùng thì dính trùng,
bỏ thì thiếu mã ép. Cặp cổng đá nhau thứ ba, sau hai cặp của LOW-337 (trùng trong bài, ảnh
trống).

Hai tấm bị chặn đều là **ảnh thực thể từ Commons**: chân dung Sam Altman, toà nhà
ByteDance. Loại ảnh này tự nhiên lặp lại giữa các tin về cùng một hãng/người, nên lỗi không
phải hiếm. Tin nhắn chặn của Kite còn gợi ý A11 làm "ảnh thay thế sẵn", mà A11 (biển hiệu
ByteDance) cũng đã lên bài khác. Vai sửa theo gợi ý đó thì vẫn bị chặn lần nữa.

Đo trên dc-group, cùng script trước/sau:

| Bài | Bộ ép trước | Bộ ép sau |
|---|---|---|
| openevidence-…-dre-donniechublog | A8 A9 A12 A13 **A14** A15 | A8 A9 A12 A13 A15 A21 |
| tham-phan-my-…-dre-dcgr | A2 **A3** A4 A5 A6 | A2 A4 A5 A6 A7 |

Vá: `_force_raw` và `figure_hero` bỏ tấm mà `reused_elsewhere` (chính cổng
`image_rules_kite.check_not_reused`) chặn; brief ghi ⛔ cạnh tấm đó. Không nới cổng, vì luật
"mỗi tin một ảnh" (06/09) vẫn đúng.

Bài học: mỗi lần thêm một cổng chặn ở `kite_submit`, phải hỏi xem bộ ép và bìa có đọc
cùng luật đó không. Tới nay đã ba lần một cổng mới chặn đúng thứ mà bộ ép đòi.
