# Hướng dẫn gán nhãn bộ ảnh chuẩn (LOW-224)

Nhãn là **sự thật** mà mọi thay đổi engine ảnh được đo theo: loại oan (ảnh dùng được mà engine bỏ) và lọt rác (ảnh không dùng được mà engine giữ). Mọi tiêu chí dưới đây lấy từ luật Ông Chủ đã chốt; không tự thêm tiêu chí.

## Gán mù

Người gán chỉ xem: ảnh, tin (tiêu đề, tóm tắt, đoạn đầu), và nguồn gốc ảnh (`tu`, `mien`, `url`, `trang`, `alt`, `tit_trang`, đánh dấu khái niệm/thương hiệu/thực thể). **Không xem** quyết định hay mô tả của engine (`lien_quan`, `dung`, `ghi_chu`, `mo_ta`), để nhãn không bị kéo theo engine.

## Trường nhãn (một dòng JSON mỗi ảnh)

```json
{"id": "...", "usable": "yes|no", "relevant": "yes|concept|no|unknown",
 "subject": "...", "defect": "none|...", "confidence": "high|low", "note": "..."}
```

### `relevant`: ảnh có thể hiện chủ thể của tin không

- `yes`: ảnh thể hiện **bất kỳ** chủ thể hay keyword nào của tin: hãng, sản phẩm, model, người của hãng, trụ sở/văn phòng, logo, sự kiện của hãng, địa điểm hay công trình trong tin.
  - Không chỉ tên đứng đầu tiêu đề, và không bắt phải đúng sự kiện của tin (luật LOW-164: "keyword gì trong bài thì MỌI ảnh liên quan keyword đó dùng được"; LOW-176: mọi chủ thể đều tính). Ảnh CEO Anthropic ở một hội nghị khác vẫn `yes` cho tin Anthropic ký hợp đồng trung tâm dữ liệu.
  - Bằng chứng có thể là hình (logo, tên trên ảnh) hoặc chữ (alt, tên tệp Commons, tít trang, url) nêu đúng chủ thể.
- `concept`: ảnh không phải của chủ thể nào, nhưng minh hoạ đúng **nội dung** tin: datacenter/rack cho tin trung tâm dữ liệu, chip/wafer cho tin chip, cờ nước của hãng. Bảng loại tin của Ông Chủ (12/09) cho phép sàn giao dịch/cổ phiếu với tin BUSINESS/FUNDING; ca này ghi `confidence: low` để Ông Chủ soát.
- `no`: chủ đề khác, hoặc **trùng tên khác nghĩa** (tranh Claude Monet cho tin Claude, ca sĩ Banks cho tin ngân hàng, xương "anthropic cut marks").
- `unknown`: không đủ bằng chứng để nói.

### `defect`: lỗi khiến ảnh không dùng được

| Mã | Khi nào |
|---|---|
| `none` | không lỗi |
| `wrong_meaning` | trùng tên khác nghĩa (xem trên) |
| `blank_placeholder` | trống, xám, khung chờ tải, placeholder |
| `broken_capture` | chụp trang hỏng: banner cookie/popup che, cắt cụt nội dung chính, spinner "Loading" |
| `blurry` | mờ/nhoè thật (không phải chỉ độ phân giải thấp) |
| `ad_widget` | quảng cáo, widget giá, nút đăng ký, khối "bài liên quan" |
| `publisher_logo` | logo/avatar của chính tờ báo hay trang, không phải chủ thể |
| `chart_not_proving_claim` | chart/bảng không chứng minh đúng claim của tin (sai model, sai bảng, sai thứ đang đo; luật 16/09) |
| `unidentified_person` | ảnh chính là người, mà **không có chữ nào** (alt, caption, tên tệp, tít trang, url) nêu tên người đó |
| `off_topic` | chủ đề khác, không trùng tên |

**Không nhận diện người qua khuôn mặt.** Chỉ dùng chữ đi kèm ảnh. Không có chữ nêu tên thì là `unidentified_person`, dù nhìn giống ai.

### Không phải lỗi (đừng trừ)

- Tỉ lệ, bố cục, ảnh ngang thấp, độ phân giải hơi thấp: lỗi nhỏ, luật 12/09.
- Ảnh rối, có chữ in sẵn (luật 13/09: vẫn dùng, script tự đặt nền chữ đặc).
- Ảnh minh hoạ biên tập, screenshot sạch, ảnh chụp lại màn hình (luật 16/09, LOW-201).
- Ảnh chụp khối tít/ảnh hero của chính bài báo về tin này (`tu: chup_nguon`), miễn không trống/hỏng.

### `usable`

`yes` khi `relevant ∈ {yes, concept}` và `defect = none`. Ngược lại `no`.

### `confidence`

`low` khi phân vân: ảnh khái niệm theo loại tin, bằng chứng chữ mơ hồ, ảnh nhỏ khó nhìn. Ông Chủ soát các ca `low` trước.

### `subject` và `note`

- `subject`: ảnh thể hiện gì, gọi theo chủ thể của tin (ví dụ "Anthropic – Jack Clark (alt)", "datacenter concept", "Claude Monet painting").
- `note`: tiếng Việt, ngắn, nêu bằng chứng quyết định ("alt nêu Jack Clark, co-founder Anthropic").
