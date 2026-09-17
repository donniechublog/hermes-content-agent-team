# Hướng dẫn gán nhãn bộ ảnh chuẩn (LOW-224) — bản 2.2

Bản 2 (17/09/2026): bổ sung **luật Ông Chủ chốt** sau vòng soát 60 nhãn đầu tiên (đồng ý 52/60). Khi luật chốt dưới đây khác các mục phía sau, **luật chốt thắng**.

## Luật Ông Chủ chốt 17/09

| # | Ca | Chốt |
|---|---|---|
| 1 | Alt/tít chỉ nêu **chức danh** ("Anthropic CEO", "OpenAI policy chief") | Đủ, coi như đã nêu người → dùng được |
| 2 | Ảnh **nhiều người**, chữ chỉ nêu một người hoặc chỉ nêu hãng ("Peter Kyle visits Anthropic") | Dùng được |
| 3 | Ảnh người mà chữ đi kèm (alt, tít bài chứa ảnh) nêu **hãng/chủ thể của tin** nhưng không nêu tên người (ảnh ghép, alt "Safety push sparks infighting at OpenAI, Anthropic") | Dùng được. `unidentified_person` chỉ khi **không chữ nào** gắn ảnh với chủ thể của tin |
| 4 | **Địa danh/quốc gia/thành phố** có trong tin (Brisbane, Queensland, Malaysia) | Dùng được (ví dụ toàn cảnh Brisbane) |
| 5 | Từ chỉ dùng làm **phép so sánh** trong tít ("gấp 5 lần ngân sách **Olympic**") | KHÔNG phải chủ thể → `off_topic` |
| 6 | Ảnh có chữ/số **lỗi thời hoặc gây hiểu sai** so với tin (năm 2024 trên ảnh cho tin 2026, sự kiện khác đè chữ lên) | Không dùng → `outdated_or_misleading_text` |
| 7 | **Ảnh khái niệm chung chung** (sàn chứng khoán, rack server, trình soạn code, chồng giấy) | Dùng được → `relevant: concept` |
| 8 | Ảnh tìm web (`tu: web_yandex`/`web_bing`) mà **alt chính là từ khoá tìm** | **Tin alt đó như bằng chứng chữ** (engine đã tìm đúng từ khoá) |
| 9 | **Biểu đồ giá cổ phiếu** của hãng trong tin | Dùng được |
| 10 | **Bảng xếp hạng** đúng model/hãng của tin nhưng là **bảng con khác** (Multi-Image Edit thay vì Image Edit) | Dùng được. `chart_not_proving_claim` chỉ khi chart về model/hãng KHÁC, hoặc không liên quan gì tới tin |
| 11 | **Ảnh hero trừu tượng/nghệ thuật** của chính bài gốc | Dùng được |
| 12 | Chụp trang nguồn **dính quảng cáo, banner, khối đăng ký, thông tin không liên quan** | **TUYỆT ĐỐI không dùng** → `ad_widget`. Nguyên văn: "nội dung chất lượng rất nhiều, ko việc gì phải đưa những thứ trash này vào" |
| 13 | Chụp màn hình có **viền đen hai bên dày** làm thẩm mỹ kém | Không dùng → `poor_capture_layout` (nhưng code nên CẮT viền: "chỉ cần bỏ viền đen hai bên đi là dùng được"). **Dải đen PHÍA DƯỚI không phải lỗi** — "quá lý tưởng để chúng ta chèn text lên" (vòng 2) |
| 14 | **Khung video** có nút play / lớp tối đè lên | Không dùng → `video_player_overlay` |
| 15 | **Logo báo / watermark** nhỏ ở góc ảnh đúng chủ thể | Không phải lỗi |

### Luật chốt vòng 2 (17/09)

| # | Ca | Chốt |
|---|---|---|
| 16 | **Bảng xếp hạng đúng hãng**, tin không có claim xếp hạng | Dùng được khi chart cùng **dòng sản phẩm/model** của tin (chart Claude cho tin Claude). KHÔNG khi tin về mảng khác mà hãng có nhiều ảnh tốt hơn — "quá nhiều ảnh của google trên internet, không cần phải đưa ảnh của gemini vào" (#250) |
| 17 | **Watermark lớn / phủ khắp ảnh** (Bigstock, chữ NEWS to giữa ảnh) | Không dùng → `ad_widget` |
| 18 | Ảnh đúng hãng nhưng **chữ trên ảnh nói chuyện khác** (banner khoá học, logo "CENSORED", wafer ghi hãng pin mặt trời) | Không dùng → `outdated_or_misleading_text` |
| 19 | Alt nêu đúng hãng nhưng **hình rõ ràng là thứ khác** (xe cảnh sát, cửa hàng Gucci, đám đông không dấu hiệu gì) | **Theo hình** → không dùng → `off_topic`. Luật 8 (tin alt từ khoá) chỉ áp khi hình không mâu thuẫn |

### Giới hạn rút từ câu trả lời soát của Ông Chủ (bản 2.1)

Không phải luật mới. Đây là cách Ông Chủ đã chấm chính các ảnh mẫu, ghi lại để người gán sau không lệch:

| Luật | Giới hạn | Ảnh mẫu Ông Chủ chấm |
|---|---|---|
| 7 khái niệm | Phải **cùng lĩnh vực nội dung** tin: rack cho tin datacenter được, rack cho tin ra mắt model phần mềm thì **không** | #135 không |
| 4 địa danh | Ảnh phải là **chính địa danh** (toàn cảnh, biểu tượng). Ảnh một sự kiện/công trình khác ở đó thì không (sân bay Ai Cập cho tin datacenter Ai Cập) | #130 không; toàn cảnh Brisbane được |
| 6 chữ gây hiểu sai | Chữ **tự nhiên trong cảnh** (bảng điện sàn NYSE) không tính | #69 được |
| 13 chụp xấu | Dải đen dưới (1/4 → hơn nửa khung) **dùng được**, là chỗ chèn chữ. Chỉ viền hai bên dày chưa cắt mới lỗi; nội dung còn quá ít (~1/3 khung) thì không | #220, #37, #92, #94, #119, #157, #244 được; #172 không; #132 (~65% đen) không |
| 3 ảnh người | Chỉ có **URL trang** nêu chủ thể, alt rỗng → **không đủ** | #76 không |
| 7 khái niệm | Sản phẩm/người của **hãng khác không có trong tin** (máy trạm AMD cho tin không nhắc AMD) → `off_topic` | #115 không |


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
- `concept`: ảnh không phải của chủ thể nào, nhưng minh hoạ đúng **nội dung** tin: datacenter/rack cho tin trung tâm dữ liệu, chip/wafer cho tin chip, cờ nước của hãng. Ảnh khái niệm chung chung cũng tính (luật chốt 7).
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
| `unidentified_person` | ảnh chính là người, mà **không có chữ nào** (alt, caption, tên tệp, tít trang, url) nêu tên, chức danh, hay hãng/chủ thể của tin (luật chốt 1–3) |
| `outdated_or_misleading_text` | chữ/số trên ảnh lỗi thời hoặc nói sự kiện khác (luật chốt 6) |
| `poor_capture_layout` | chụp màn hình viền quá dày, nửa đen, bố cục xấu (luật chốt 13) |
| `video_player_overlay` | khung video có nút play/lớp tối (luật chốt 14) |
| `off_topic` | chủ đề khác, không trùng tên |

**Không nhận diện người qua khuôn mặt.** Chỉ dùng chữ đi kèm ảnh (tên, chức danh, hoặc hãng/chủ thể của tin — luật chốt 1–3). Không có chữ nào như vậy thì là `unidentified_person`, dù nhìn giống ai.

### Không phải lỗi (đừng trừ)

- Tỉ lệ, bố cục, ảnh ngang thấp, độ phân giải hơi thấp: lỗi nhỏ, luật 12/09.
- Ảnh rối, có chữ in sẵn (luật 13/09: vẫn dùng, script tự đặt nền chữ đặc).
- Ảnh minh hoạ biên tập, screenshot sạch, ảnh chụp lại màn hình (luật 16/09, LOW-201).
- Ảnh chụp khối tít/ảnh hero của chính bài báo về tin này (`tu: chup_nguon`), miễn không trống/hỏng, không dính quảng cáo/khối lạ, không viền dày (luật chốt 12–13).

### `usable`

`yes` khi `relevant ∈ {yes, concept}` và `defect = none`. Ngược lại `no`.

### `confidence`

`low` khi phân vân: ảnh khái niệm theo loại tin, bằng chứng chữ mơ hồ, ảnh nhỏ khó nhìn. Ông Chủ soát các ca `low` trước.

### `subject` và `note`

- `subject`: ảnh thể hiện gì, gọi theo chủ thể của tin (ví dụ "Anthropic – Jack Clark (alt)", "datacenter concept", "Claude Monet painting").
- `note`: tiếng Việt, ngắn, nêu bằng chứng quyết định ("alt nêu Jack Clark, co-founder Anthropic").
