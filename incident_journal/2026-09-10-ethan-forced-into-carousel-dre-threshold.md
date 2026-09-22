## Ethan bị bắt làm carousel: engine áp ngưỡng của Dre cho mọi vai (10/09/2026)

Ông Chủ hỏi: *"việc của Ethan là làm single image, sao hôm nay Ethan lại báo
không thể tạo slide?"*. Giả thuyết đầu tiên — giao nhầm task — **sai**. Phân
công vẫn đúng: `duyet_chon_tin` tạo task tiêu đề `"Anh: …"` cho `designer` và
`"Carousel: …"` cho `carousel`, kanban của cả hai brand không có task nào lệch.

Bằng chứng thật nằm ở `state/blog/approve.log`:

```
09-10 00:42:02 [nut] draft=muse-spark-1-3-max-meta-m-i-v-o-8-designer-donniechubl:
  ⚠️ Chỉ 2 ảnh thật mà carousel cần tối thiểu 5 slide — bấm tiếp cũng không
  dựng được. Chuyển Kite vẽ vector, hoặc bỏ tin.
09-10 00:42:17 [nut] draft=nex-agi-nex-n2-5-pro-th-tr-ng-s-hu-designer-donniechubl:  (y hệt)
```

Đuôi draft là `-designer-…` — bài của **Ethan**, mà hệ thống nói bằng tiếng của
carousel. Ông Chủ đọc đúng như nó hiện ra: Ethan đang loay hoay với slide.

**Nguyên nhân:** `anh_chuan_bi.chuan_bi()` chạy CHUNG cho cả ba vai dùng ảnh
nhưng tính ngưỡng bằng `carousel.FLAGSHIP_MIN if flagship else
carousel.MIN_SLIDE` — luôn 5, hoặc 8 với tin flagship — bất kể vai nào sẽ dùng
bộ ảnh. `card.py` của Ethan chỉ cần **một** tấm. Nên mọi bài giao Ethan có dưới
5 ảnh khả dụng (rất thường gặp với tin không phải benchmark) đều bị kẹt ở bước
"thiếu ảnh", rồi `route_thieu_anh` gửi lên topic của Ethan câu hỏi carousel kèm
nút "Gửi Kite vẽ vector". `chuan_bi/manifest.py` ghi tiếp
`toi_thieu_co_ban = carousel.MIN_SLIDE` nên nút "hạ sàn" cũng lấy sàn 5.

Lỗi sống được lâu vì với Dre **hai con số trùng nhau**: mỗi slide một ảnh riêng,
nên "số ảnh tối thiểu" và "số slide tối thiểu" là một — `dre_nop` đọc
`m["toi_thieu"]` theo nghĩa slide, engine ghi nó theo nghĩa ảnh, không ai thấy
sự khác. Chỉ Ethan mới làm hai nghĩa đó tách ra.

**Sửa:** ngưỡng thành thuộc tính của vai trong bản đăng ký (`vai.py`:
`anh_toi_thieu`, `anh_toi_thieu_flagship`; Ethan 1, Dre 5/8, Kite 1 vì vẽ
vector), engine hỏi `vai.so_anh_toi_thieu(vai_anh, flagship)`. Vai lấy từ
`tom["vai_anh"]` — `_tom_tat_tu_img_json` đã đọc sẵn khoá đó từ sidecar
`.img.json` từ lâu, chỉ là chưa ai dùng tới.

**Cái bẫy khi sửa:** hạ thẳng ngưỡng xuống 1 cho Ethan thì hỏng theo chiều
ngược lại. Một con số đang gánh **hai việc**: nó vừa là ngưỡng CHẶN, vừa là mốc
để vòng tìm ảnh biết khi nào dừng. Ethan chỉ cần 1 tấm để *dựng*, nhưng cần
nhiều tấm để *chọn* — `card.py` chặn chart và ảnh ngang >1.6 đi một mình, vision
còn loại thêm ảnh không liên quan. Cho engine dừng tìm ở tấm đầu tiên là đúng
kiểu block đã thấy ở `t_618244d2` sáng nay ("chuẩn bị chỉ có 1 ảnh A1, A1 là
chart, hết đường"). Nên tách hẳn: `toi_thieu` (chặn, theo vai) và
`muc_tieu_tim` (dừng tìm, giữ nguyên số cũ 5/8 cho **mọi** vai). Phần tìm ảnh
chạy y hệt trước, chỉ phần chặn là đổi. Kèm ba thứ nhỏ:

- `create_pair` ghi sidecar **trước** khi chạy engine nền. Trước đó ngược lại,
  tức engine đọc một tệp chưa ai ghi — trước giờ chỉ mất tóm tắt (im lặng), từ
  nay mất cả ngưỡng.
- Nút "hạ sàn" gọi sản phẩm đúng tên: "slide" cho Dre/Kite, "ảnh" cho Ethan.
- `test_nguong_anh_theo_vai.py`: 10 test, trong đó **hai cổng đọc mã nguồn** —
  dòng thật sự hỏng nằm trong hàm mở Chromium + gọi vision, không unit test
  được. Một cổng giữ "ngưỡng chặn phải hỏi bản đăng ký vai", cổng kia giữ "vòng
  tìm ảnh không được đo bằng ngưỡng chặn". Đã thử làm hỏng lại từng chiều để
  chắc cả hai cổng thật sự đỏ, không phải test rỗng.

**Bài học:** một hằng số mượn từ module của vai khác thì sớm muộn cũng áp sai
cho vai không liên quan. Thứ thuộc về vai phải nằm trong bản đăng ký vai — đúng
lý do `vai.py` ra đời (audit A4/F1), chỉ là lần đó mới gom bảng tên, chưa gom
luật. Và khi một biến đang gánh hai nghĩa mà chỉ một nghĩa sai, tách hai nghĩa
ra trước, đừng sửa con số.

---

