## Thiếu bảng "Image Edit Arena" và tên mã biến thể (09/09/2026)

Ông Chủ gửi hai ảnh chụp Arena — "Image Edit Arena" và "Text-to-Image Arena",
cả hai đều xếp GPT-Image-2.5 hạng #1 (Sunburst) và #2 (Flare) — kèm một câu:
*"làm thông tin về model mà không đưa được 2 chart này vào là quá kém"*. Đúng,
và có hai lỗ hổng cộng dồn trong `xep_hang.py`, cả hai đều hỏng câm lặng:

1. **"Image Edit Arena" chưa từng có trong registry `NGUON`.** Chỉ có
   `arena-t2i` (Text-to-Image) — bảng chỉnh sửa ảnh là một board KHÁC, tách
   riêng trên arena.ai (`/leaderboard/image-edit`), và trước giờ registry chưa
   liệt kê. Xác nhận bằng WebFetch trước khi thêm (nguyên tắc đã ghi ngay
   trong `xep_hang.py`: "không thêm nguồn chưa chụp được"): trang thật, 55
   model, dữ liệu khớp hệt ảnh Ông Chủ gửi (sunburst 1520±9, flare 1491±9, gpt
   image 2 medium 1461±3...).
2. **`_DUOI` không có "Sunburst"/"Flare".** Hai cái tên đó là mã của **hai biến
   thể cùng họ, cùng đứng trên cùng một bảng** — thiếu chúng thì `tach_model`
   dừng ở "GPT Image 2.5", khớp NHẬP NHẰNG cả hai hàng. Engine khoanh hàng nào
   tìm thấy trước, bất kể tin đang nói về Sunburst hay Flare — sai ảnh cho
   đúng một nửa số tin về cặp model này.

**Sửa:** thêm `arena-image-edit` vào `NGUON` (ngay sau `arena-t2i`) và một
mục `CHU_DE` mới ưu tiên nó khi tiêu đề nói "chỉnh sửa ảnh" / "image edit";
mục `\bimage\b` chung giờ xét **cả hai** bảng — một model tạo ảnh mạnh
thường lên cả hai board cùng lúc, đúng như dữ liệu thật lần này. Thêm
`Sunburst|Flare` vào `_DUOI`. Test hồi quy ở `tests/test_xep_hang.py` khớp lại
đúng số liệu Ông Chủ gửi (không đoán URL — mọi test dùng dữ liệu đã xác nhận
qua WebFetch).

**Cập nhật cùng ngày — lấy được cả hai chart.** Đưa ra lo ngại "kiến trúc chỉ
mang được một bảng mỗi tin, đổi sang nhiều ảnh là thay đổi lớn hơn, cần chốt
trước" — Ông Chủ bác thẳng cả tiền đề: *"đã làm social media thì làm gì có
chuyện bị giới hạn ở nguồn tư liệu"*, và chỉ ra hai bảng đó *"một bảng là top
model tạo sinh, một bảng là top model chỉnh sửa, đâu có trùng lặp"* — tức
không có lý do tự giới hạn khi hai nguồn không hề overlap.

Sửa: `xep_hang.tim_va_chup_nhieu()` (hàm mới, **không sửa** `tim_va_chup()` cũ —
`_xep_hang_boi_canh` trong `anh_chuan_bi.py` và CLI `main()` vẫn gọi bản cũ,
đợi đúng MỘT dict) đọc cờ `doc_lap: True` gắn ngay tại khai báo NGUON của
`arena-t2i`/`arena-image-edit`: nguồn "độc lập" (đo năng lực riêng) không bao
giờ bị một thành công khác chặn lại; nguồn "thường" (4 biến thể đo cùng một
năng lực code — arena-code/swebench/aider/livecodebench) vẫn dừng ở thành công
đầu tiên như cũ, lấy thêm chỉ lặp lại bằng chứng. Luật chọn nằm trọn trong một
hàm thuần `_bo_qua_nguon(n, da_chup_thuong)`, tách riêng để test không cần
Playwright (không cài được trong môi trường này để mock trình duyệt thật).

`anh_chuan_bi.py` đổi `xh` (dict|None) → `xhs` (list, có thể rỗng) xuyên suốt
`_chup_xep_hang` → `_gom_va_tai_anh` → `dung_manifest`; mỗi bảng chụp được
mang mã riêng (`XH`, `XH2`...) qua `_anh_muc_xep_hang()` (hàm thuần, tách để
test không phải chạy `_gom_va_tai_anh` — hàm đó gọi mạng thật nên test trực
tiếp treo/timeout). `dung_manifest` nhận cả `None` (quy ước cũ, hai test có
sẵn của tính năng ảnh thương hiệu truyền `None` ở vị trí này) lẫn `[]` — không
đổi hành vi cho mọi tin chỉ có một bảng. `m["xep_hang"]` (bảng ĐẦU TIÊN, dùng
bởi cổng chặn `can_anh_xep_hang`) và mọi gate hiện có không đổi hợp đồng; thêm
`m["so_xep_hang"]` để `dong_brief_xep_hang` nói rõ cho vai biết có mã `XH2` khi
có, tránh bỏ phí tấm thứ hai vì brief không nhắc tới nó.

Không đổi những gì các file khác (đang sửa `anh_thuong_hieu.py`/
`anh_khai_niem.py` cùng lúc) không nhắc tới: mỗi ảnh xếp hạng vẫn mang
`"xep_hang": xh` của riêng nó nên mọi cổng đọc PER-IMAGE (`dre_nop.py`,
`ethan_nop.py`, `ethan_chuan_bi.py`) coi XH2 y hệt XH, không cần sửa gì.

---

