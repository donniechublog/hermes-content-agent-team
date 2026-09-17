# Khoá manifest bản 2 — Việt không dấu → English (LOW-227)

**Ông Chủ duyệt 17/09/2026:** (1) `thuong_hieu → brand_match`; (2) `ma → id`;
(3) pha này chỉ đổi KHOÁ, giá trị liệt kê tiếng Việt tách ticket riêng sau pha 3;
(4) `state/golden/v0/samples.jsonl` và `drafts/<id>.img.json` đổi cùng pha 1.

Nguồn sự thật: [`manifest_keys_v2.json`](manifest_keys_v2.json). Script migrate
và phần sửa code sẽ đọc thẳng tệp đó, không chép tay lần hai.

## Cách đo (17/09/2026, máy chủ @1f8b432)

Quét **cả 188** `state/*/chuan_bi/*/xong.json` (110 bản 1 + 78 bản 0), gom mọi
khoá cấp manifest, cấp ảnh (2 615 ảnh) và khoá lồng; đọc code ghi từng khoá để đặt
tên theo **nghĩa**, không theo từng chữ. Khác với từ điển v0 (dịch từng chữ cho tên
hàm): ở đây khoá là hợp đồng dữ liệu nên nghĩa phải đúng — ví dụ `san` là tệp ảnh
**đã xử lý sẵn**, không phải "ready" chung chung; `roi` là **rối**, không phải "fall".

Kiểm máy: mọi khoá Việt trên máy chủ đều có tên mới; không hai khoá cũ nào về cùng
một tên trong cùng một cấp; không tên mới nào đè khoá English sẵn có.

## Cấp manifest (26 khoá đổi)

| cũ | mới | ghi chú |
|---|---|---|
| `phien_ban` | `version` | bản 2 |
| `anh` | `images` | |
| `toi_thieu` / `toi_thieu_co_ban` | `min_images` / `base_min_images` | khớp `role.min_images` đã có |
| `tieu_de_en` | `title_en` | |
| `tu_lieu` | `material` | khớp module `material.py` |
| `chu_bai` | `article_text` | |
| `so_mien` | `domains` | là **danh sách** miền, không phải số |
| `cap_ghep` / `ghep_hai_hang` | `stackable_pairs` / `two_company_pairs` | |
| `thu_tu_anh_theo_loai` | `image_order_by_story_type` | |
| `goi_y_bia` | `cover_suggestions` | |
| `chua_nhin` | `not_yet_seen` | từ điển v0 đã chốt |
| `so_dung_duoc` | `usable_count` | |
| `vai_anh` | `image_role` | |
| `tin_xep_hang` / `xep_hang` / `so_xep_hang` | `is_ranking_story` / `ranking` / `ranking_count` | |
| `tao_luc` / `ha_san_luc` | `created_at` / `min_lowered_at` | |
| `nguon_path` | `source_path` | |
| `thieu_anh` `{so, toi_thieu}` | `missing_images` `{count, min_images}` | |
| `chuyen_kite` / `hoi_kite` / `khong_kite` | `kite_task_id` / `kite_asked` / `kite_unavailable` | |
| `route_loi` | `route_error` | không có trong `schema.Manifest`, 4 tệp có |

`material` bên trong: `cau_co_so→number_sentences`, `doan_dau→lead_paragraph`,
`so_nguon→source_count`, `tu→source`, `tieu_de→title`, `nguon→sources`
(mỗi nguồn `nhan→label`, `tieu_de→title`, `doan→paragraphs`).

## Cấp ảnh (37 khoá đổi + 1 khoá cũ gộp)

| cũ | mới | | cũ | mới |
|---|---|---|---|---|
| `ma` | `id` | | `mo_ta` | `description` |
| `goc` | `original_path` | | `lien_quan` | `relevant` |
| `san` | `ready_path` | | `dung` | `uses` |
| `tu` | `source` | | `ghi_chu` | `notes` |
| `trang` | `page_url` | | `diem` / `ly_do` | `score` / `score_reason` |
| `mien` | `domain` | | `mat` | `faces` |
| `loai` | `kind` | | `ngang` | `landscape` |
| `ti_le` | `ratio` | | `canh_ngan` | `short_side` |
| `hint_chart` / `do_chart` | `chart_hint` / `chart_stats` | | `cat_ngang_ok` | `landscape_crop_ok` |
| `day_sang` | `bottom_brightness` | | `goc_trai_sang` | `bottom_left_brightness` |
| `du_tu_khoa` | `has_keywords` | | `tim_them` | `from_find_more` |
| `chup_nguon` / `kieu` | `capture_source` / `capture_kind` | | `tit_trang` | `page_title` |
| `mau_nen` / `dem_nen` | `background_color` / `padding_color` | | `paper_hinh` | `paper_figure` |
| `anh` (URL ứng viên) | `image_url` | | `du_phong` | `fallback` |
| `the` (thẻ HTML ứng viên) | `html_tag` | | `roi` (khoá cũ LOW-47) | gộp vào `cluttered` |

Khoá lồng:
- `khai_niem → concept {keyword, reason}`
- `thuong_hieu → brand_match {company, key, kind, keyword, person, person_role, board, background_tone, board_id}`
- `thuc_the → entity {name, article_name, source}`
- `xep_hang → ranking {file_path, kind, source, board, company, row, mentioned, has_logo}` — dùng chung cho `ranking` cấp manifest

## Cần Ông Chủ quyết

1. **`thuong_hieu → brand_match`, không phải `brand`** (từ điển v0 dịch `brand`).
   Manifest đã có khoá `brand` = slug tổ chức (`donniechublog`). Khi lên nhiều user,
   `brand` ở hai cấp mang hai nghĩa là đúng loại nhập nhằng ticket này muốn gỡ.
2. **`ma → id`**. Giá trị `A1`, `A2`… là mã ảnh trong một draft, không phải id toàn
   cục. Chọn `id` vì mọi nơi gọi nó là "mã ảnh"; nếu muốn rõ hơn thì `image_id`.
3. **Chỉ đổi KHOÁ, không đổi GIÁ TRỊ** trong pha này. Còn nhiều giá trị liệt kê tiếng
   Việt đang được code so sánh: `source` = `"khai_niem"`, `"thuong_hieu"`, `"gốc"`,
   `"báo khác"`; `kind` = `"anh"`; `capture_kind` = `"tit"`; `ranking.kind` = `"bang"`,
   `"danh-sach"`, `"the"`; `brand_match.kind` = `"nguoi"`; `background_tone` = `"sáng"`/`"tối"`;
   `uses` là câu hiển thị (`"bìa"`, `"thân"`). Đổi luôn thì phạm vi và rủi ro đổi hành vi
   tăng gấp đôi, nên đề xuất tách **ticket riêng sau pha 3**.
4. **Nằm ngoài `xong.json`** nhưng dùng chung tên: `vai_anh` trong
   `drafts/<id>.img.json`/`.meta.json`, dict ảnh trong `state/golden/v0/samples.jsonl`.
   Đề xuất: samples.jsonl **đổi cùng pha 1** (không thì phép đo baseline vô nghĩa);
   `.img.json` đổi cùng pha 1 để một khái niệm chỉ có một tên.

## Không đổi

Khoá đã English: `draft_id, brand, title, link, workdir, flagship, via, category,
summary, source_note, dropped, url, alt, w, h, cluttered, commons, og, site, model, logo`.
Giá trị đường dẫn (`original_path`, `workdir`… vẫn chứa `chuan_bi/…/goc/`) — việc của pha 2.
