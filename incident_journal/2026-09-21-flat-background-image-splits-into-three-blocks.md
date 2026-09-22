# Ảnh nền phẳng tách thành 3 khối: ảnh sắc / dải mờ xám / overlay tối — 21/09/2026

Ticket theo dõi: LOW-341 (gộp LOW-339 — Kite, ticket con).

Hai slide quote bài MiniMax-H3 (donniechublog): hình Figure 1 / Figure 3 của paper, nền giấy
trắng. Slide ra ba mảng tách rời:

```
y    0– 779  ảnh sắc (giấy trắng 254)          55% khung
y  779– 900  dải cover-blur xám (TB 199)       11% — bản mờ phóng to của chính hình
y  960–1350  overlay tối + chữ trắng (TB 78)   29%
mép ảnh sắc: 254 -> 191 trong MỘT hàng
```

Ông Chủ, nguyên văn: *"ko nên làm thế này, hình sẽ bị tách thành 3 khối. luôn ưu tiên đặt
chữ màu tương phản với màu nền trước khi phải dùng tới nền chữ. ví dụ trường hợp này chỉ cần
phóng lớn main image ra để hiển thị full 90% width rồi đặt quote màu đen lên nền trắng là
được"*. Cùng ngày: *"bìa cũng áp dụng"*; ảnh nền phẳng thì *"kéo màu mép ra kín hai bên"*;
và sau bản dựng đầu (bìa SoL-Pi ghép 2 hình bị thu còn ~55% bề ngang): *"luôn ưu tiên hiển
thị full chiều rộng, phần nội dung ảnh bị chèn vào text, chúng ta phủ lên một layer cùng màu
với màu nền rồi đặt quote của chúng ta lên"*.

Ba chỗ:

1. **Nền slide luôn là bản cover-blur của ảnh** (`carousel._body_image`). Đúng cho ảnh chụp,
   sai cho ảnh nền phẳng: phần mờ lộ ra dưới hình là một dải xám đục, dán thẳng không dải
   chuyển.
2. **Dre không bao giờ đổi màu chữ.** `FG` cố định cho cả bộ nên hễ nền sáng là overlay tối
   (`_layer_if_can`). Đường "đổi màu chữ theo nền" chỉ có ở slide logo (LOW-295) và chỉ
   cho ảnh logo, không có ở slide quote hay bìa.
3. **Cổng không hỏi đúng câu.** `_gate_text_background` (LOW-286) đo độ đặc/diện tích nền
   chữ: 5 slide dựng lại đều PASS (0.31–0.38 / 0.60–0.81). Không cổng nào hỏi "có cần nền
   chữ không".

Sửa (Dre):

- `logo_card.flat_background` / `content_box`: ảnh có viền bốn cạnh một màu phẳng. Đo viền
  1%, dung sai 12: hình paper ≥ 0.927 / 0.757, ảnh chụp ≤ 0.694 / 0.304 → ngưỡng 0.90 / 0.70.
  Viền 2% ăn vào dòng chữ bị cắt ở mép của hình (cặp ghép bìa SoL-Pi 0.906); dung sai 20 để
  lọt nền một màu có chấm (ảnh giả `_ve` của test_spec_dre 0.908).
- `carousel._flat_layout`: khung = màu nền của ảnh, nội dung 90% bề ngang, chữ/nét/chip đổi
  màu tương phản — ở slide thân, slide quote và bìa. Ảnh cao hơn phần trên chữ: KHÔNG thu,
  phần lấn vào vùng chữ phủ đúng màu nền (tan 120px, đặc từ 24px trên dòng chữ đầu).
- `dre_submit`: ảnh nền phẳng dùng ảnh GỐC, không áp luật "ảnh ngang phải ghép / chart không
  làm bìa".
- Cổng `carousel._gate_flat`: ảnh nguồn nền phẳng mà slide không phải một mặt phẳng màu nền
  ngoài ảnh và trong vùng chữ → dừng, không gửi album.

Dựng lại HAI ALBUM THẬT trên máy chủ (`dc-group`, spec trong state, ra `/tmp/low341`) lộ
thêm 4 slide cùng loại mà bản đầu bỏ sót: MiniMax slide 2 (sơ đồ chạm mép, viền 0.71), SoL-Pi
slide 5 (hình + bảng cắt sát lề, viền 0.43), SoL-Pi slide 4 và 6 (ghép hai ảnh KHÁC màu nền).
Ông Chủ chọn làm luôn trước khi deploy. Nới theo tỉ lệ màu nền toàn ảnh cho MỌI ảnh là sai —
đo trên 5429 ảnh gốc, ở 0.55/0.60 nó kéo chân dung nền xám/đen (Musk, Altman) vào. Nên:

- Ngưỡng nới (viền ≥ 0.40, cả ảnh ≥ 0.45) CHỈ cho ảnh vision xếp `chart` — gom 151/276 chart
  đang trượt (bảng, UI, sơ đồ).
- Ảnh ghép xét từng tấm (`carousel._flat_plan`; `dre_submit` ghi `image_kinds`): cùng nền →
  nền phẳng; khác nền → giữ full bề ngang, vùng chữ phủ màu nền của tấm dưới.

Kết quả trên máy chủ: MiniMax slide 2–4 và cả 6 slide SoL-Pi đổi; 4 slide ảnh chụp của
MiniMax (bìa, 5, 6, 7) giống hệt từng pixel.

Chưa làm: Kite (`render_edu.set_image` cắt mép dưới ảnh phẳng cao thay vì thu — LOW-339,
cần đo slide Pirate Face trên máy chủ), thẻ Ethan (LOW-287).

Ghi chú vận hành: production đã chuyển sang máy `dc-group` từ 20/09; remote `deploy` trên máy
Windows vẫn trỏ `donniechu-01` (thư mục `content-team` ở đó đã bị xoá 21/09), và máy Windows
không thấy `dc-group` trong mạng NetBird — vào được bằng ProxyJump qua `donniechu-01` theo IP
`100.87.212.236` (host key đã có trong known_hosts của `donniechu-01`; gọi bằng tên máy thì
"Host key verification failed").
