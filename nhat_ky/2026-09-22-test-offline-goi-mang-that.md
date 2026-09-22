# Test "không mạng" gọi mạng thật, treo cả bộ test trên máy chủ — 22/09/2026

Ticket theo dõi: LOW-365.

`tests/test_round_brand_always_run.py` tự nhận "khong mang, khong browser, khong
vision", nhưng trên máy chủ chạm trần 180s: log cuối là `[thuc the] Samsung`
(Wikipedia/Commons) và `[vision] A3.png: ... TimeoutError`. Một `tests/run.sh` chạy
nền chết ở tệp 119/187, không in dòng kết. Sáng cùng ngày cả bộ vẫn qua 186/186 —
test xanh hay treo tuỳ tốc độ mạng lúc chạy.

Nguyên nhân: harness thay pha nặng của `prepare_article()` bằng stub theo một danh
sách tên (`PHA_NANG`). Hai vòng thêm sau — `_round_capture_source`, `_round_entity` —
không ai thêm vào danh sách, nên chạy thật. Lỗi mạng bị chính vòng đó nuốt, test
vẫn xanh, chỉ chậm; và vì `_round_entity` thật sự thêm ảnh khi có mạng, câu hỏi
"vòng khái niệm có chạy không" còn phụ thuộc mạng. Lần thứ ba cùng một lỗi:
`test_find_image_by_role.py` đã vá đúng chỗ này ngày 13/09 (6 phút 34), nhưng chỉ vá
ở tệp đó.

Sửa (chỉ test, không đụng mã sản phẩm):

- Stub hai vòng bị quên trong `test_round_brand_always_run.py`.
- `tests/tam.py: block_network()` — chặn getaddrinfo/connect ở mức socket, ghi lại mọi
  lần thử. Hai harness `prepare_article()` `assert not tried`: pha lọt stub giờ là ĐỎ
  trong ~2s (thử bỏ stub `_round_entity`: 3 test FAIL, nêu `en.wikipedia.org`,
  `commons.wikimedia.org`), không còn là xanh-chậm.
- Cổng mã nguồn: mọi `_round_*` trong `prepare_article()` phải có trong `PHA_NANG` —
  bắt cả vòng mới nằm sau điều kiện mà kịch bản test chưa đi tới.
- `tests/run.sh`: trần mỗi tệp `TEST_TIMEOUT` (mặc định 300s, `0` = tắt). Tệp treo báo
  `HONG (qua 300s, ...)` và lượt chạy đi tiếp tới dòng N/M.

Số đo (máy dev): 68s → <1s. Máy chủ: xem LOW-365 mục 6.

Nhìn ở đâu: dòng `test_round_brand_always_run.py` trong `bash tests/run.sh`; bất kỳ
dòng `HONG (qua ...s` nào về sau là một tệp test treo — mở tệp đó trước.
