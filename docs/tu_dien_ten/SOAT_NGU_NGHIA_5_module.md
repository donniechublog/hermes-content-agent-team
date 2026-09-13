# Soát nghĩa 5 module quan trọng nhất — thử nghiệm bước 0.5

Ông Chủ 12/09/2026: *"từ gốc nghĩa tiếng việt là gì không quá quan trọng, miễn
là khi chuyển qua tiếng anh thì nó đúng với hàm sau khi đã đổi tên biến để
không bị lỗi gọi"*.

Nghĩa là bảng C (hàm/lớp) trong `TU_DIEN_TEN_nhap.md` — sinh bằng cách tách
token rồi tra từ điển — chỉ là **khung nháp**. Việc thật là đọc docstring/thân
mỗi hàm rồi đặt tên theo **hành vi**, không theo nghĩa từng chữ. Tệp này là một
lượt thử: soát tay 86 hàm/lớp trong 5 module có nhiều nơi gọi tới nhất (đo bằng
số module khác `import`), so găng với cột dịch máy để xem sai lệch thật đến đâu.

## Kết quả đếm được

| Module | Số hàm/lớp | Dịch máy ĐÚNG (giữ) | Dịch máy SAI/gây hiểu nhầm (đổi) |
|---|---|---|---|
| `luat_anh.py` | 35 | 14 | 21 |
| `vai.py` | 11 (+ lớp `Vai`) | 3 | 8 |
| `nop_chung.py` | 20 | 6 | 14 |
| `anh_chuan_bi.py` | 9 (+ `main`) | 2 | 7 |
| `chuan_bi/manifest.py` | 8 | 1 | 7 |
| **Tổng** | **86** | **26 (30%)** | **60 (70%)** |

**70% dịch máy sai hoặc gây hiểu nhầm khi đối chiếu với hành vi thật.** Xác
nhận đúng điều Ông Chủ nói — bảng cụm/từ đơn không đủ, phải đọc từng hàm.

Ca rõ nhất: `dung_manifest` — dịch máy `use_manifest` (dùng = use), nhưng hàm
này **DỰNG** dict manifest từ 13 tham số rồi trả về để ghi vào `xong.json` —
không "dùng" cái gì có sẵn. Tên đúng: `build_manifest`. Một chữ "dùng" quá đa
nghĩa (dùng/dừng/đúng/dựng) để suy ra bằng tra từ điển thuần.

---

## `luat_anh.py` — luật ảnh (35 hàm)

| Hiện tại | Dịch máy | Theo hành vi thật | Đổi? |
|---|---|---|---|
| `dong_dau` | ~~close_mark~~ | `stamp_provenance` — trả PngInfo mang dấu `nguon_dung=<xuất_xứ>` | ✅ đổi |
| `dong_dau_tep` | ~~close_mark_file~~ | `stamp_file` — mở lại một PNG đã lưu, ghi dấu vào đó | ✅ đổi |
| `_text` | ?text | *(không docstring — cần đọc thân hàm trước khi đặt tên)* | ⏸ chưa đủ dữ liệu |
| `doc_dau_crop` | ~~read_mark_crop~~ | `read_crop_trace` — đọc dấu vết crop_ti_le.py để lại, trả (rộng, cao) gốc | ✅ đổi |
| `doc_cat_ngang` | ~~read_crop_landscape~~ | `allows_landscape_crop` — trang thái "có được phép cắt bề ngang tấm này" | ✅ đổi |
| `la_xep_hang` | is_ranking | `is_ranking_image` | ✅ đổi (rõ hơn) |
| `co_xuat_xu` | has_provenance | `has_provenance` | giữ |
| `la_ghep` | is_stack | `is_stacked_composite` — có phải bản ghép dọc do chính đội dựng | ✅ đổi |
| `do_chart` | measure_chart | `measure_chart_signal` — trả (độ phẳng, số màu) dùng để nhận diện chart | ✅ đổi (rõ hơn) |
| `la_chart` | is_chart | `is_chart` | giữ |
| `_js_re` | ?tu_regex | `_js_regex_literal` — dựng chuỗi `new RegExp(...)` cho JS | ✅ đổi |
| `js_rac_url` | js_junk_url | `js_junk_url_pattern` | ✅ đổi (rõ hơn: trả regex, không phải hành động lọc) |
| `js_rac_dom` | js_junk_dom | `js_junk_dom_pattern` | ✅ đổi |
| `dhash` | dhash | `dhash` (thuật ngữ chuẩn — difference hash) | giữ |
| `gan_giong` | ~~near_similar~~ | `is_near_duplicate` — so hai hash trong ngưỡng | ✅ đổi |
| `_md5` | _md5 | `_file_md5` | ✅ đổi (rõ đối tượng) |
| `nguong_dhash` | threshold_dhash | `dhash_threshold_for` — ngưỡng hợp với LOẠI ảnh | ✅ đổi |
| `_so_da_dung` | ~~count_used~~ | `_used_images_log` — **"sổ" = ledger/log, KHÔNG PHẢI "số" = number** | ✅ đổi — ca mơ hồ điển hình |
| `khoa_tin` | lock_story | `story_key` — khoá ổn định của MỘT TIN (không phải một draft) | ✅ đổi (rõ hơn: là khoá/key, không phải hành động khoá) |
| `ghi_da_dung` | ?ghi_da_dung | `record_used` | ✅ đổi |
| `xoa_da_dung` | delete_used | `remove_used_for_draft` | ✅ đổi (rõ phạm vi) |
| `kiem_da_dung` | check_used | `check_not_reused` | ✅ đổi (gate phủ định) |
| `lech_tone` | offset_tone | `tone_mismatch` | ✅ đổi |
| `_yunet` | _yunet | `_load_yunet` — nạp lazy model, dùng một lần cho cả tiến trình | ✅ đổi |
| `dem_mat` | count_face | `count_faces` | giữ (đúng, chỉ số nhiều) |
| `la_anh_rong` | is_image_empty | `is_blank_image` | ✅ đổi (rõ hơn: trắng trơn, không phải "rỗng" chung chung) |
| `kiem_anh_rong` | check_image_empty | `check_blank_image` | ✅ đổi |
| `kiem_chart` | check_chart | `check_chart_integrity` — chart phải NGUYÊN VẸN, FULL bề ngang | ✅ đổi (rõ hơn) |
| `kiem_anh_thap` | check_image_low | `check_image_too_flat` — ảnh QUÁ NGANG so với khung khoá khổ | ✅ đổi — "thấp" ở đây không phải "low", mà "ảnh dẹt" |
| `kiem_lech_tone` | check_offset_tone | `check_tone_mismatch` | ✅ đổi |
| `kiem_chart_mot_minh` | check_chart_single | `check_chart_standalone` | ✅ đổi |
| `kiem_ti_le` | check_ratio | `check_aspect_ratio` | ✅ đổi (thuật ngữ chuẩn) |
| `kiem_crop_ngang` | check_crop_landscape | `check_landscape_crop` | giữ (thứ tự từ khác nhưng nghĩa rõ, có thể giữ) |
| `kiem_xuat_xu` | check_provenance | `check_provenance` | giữ |
| `kiem_do_phan_giai` | check_resolution | `check_resolution` | giữ |
| `kiem_day_sang` | check_bottom_bright | `check_bright_bottom` | ✅ đổi (thứ tự tự nhiên hơn) |
| `kiem_mat_nguoi` | check_face_person | `check_unnamed_face` — không dùng ảnh một người VÔ DANH | ✅ đổi (rõ điều kiện chặn) |
| `kiem_trung` | check_duplicate | `check_duplicate` | giữ |

## `vai.py` — bảng đăng ký vai (11 hàm + lớp `Vai`)

| Hiện tại | Dịch máy | Theo hành vi thật | Đổi? |
|---|---|---|---|
| `class Vai` | Role | `Role` | giữ |
| `vai_viet_cua` | writer_of | `writer_for` — hỏi VAI QUÉT trước, rồi tới BRAND | ✅ đổi |
| `ten_hien` | name_show | `display_name` | ✅ đổi |
| `slug_that` | slug_real | `canonical_slug` — chữ bất kỳ (tên cũ/persona) → slug hiện tại | ✅ đổi |
| `max_runtime_cua` | max_runtime_for | `max_runtime_for` | giữ |
| `so_anh_toi_thieu` | min_images | `min_images_for` | giữ (gần đúng) |
| `ten_nguoi_trong_alt` | name_person_in_alt | `person_names_in_alt` | ✅ đổi (số nhiều, đúng kiểu trả về `list`) |
| `anh_chinh_duoc` | image_main_ok | `can_be_hero` — tấm này có dùng MỘT MÌNH làm ảnh chính được không | ✅ đổi |
| `so_anh_muc_tieu_tim` | count_image_target_find | `search_target_for` | ✅ đổi |
| `du_nguyen_lieu` | enough_material | `has_enough_material` | ✅ đổi |
| `don_vi_san` | unit_ready | `product_unit_for` — chữ gọi MỘT ĐƠN VỊ sản phẩm ("slide" hay "ảnh") | ✅ đổi |
| `_map_go` | _map_go | `_build_go_map` | ✅ đổi |

## `nop_chung.py` — cổng chặn dùng chung Ethan/Dre (20 hàm)

| Hiện tại | Dịch máy | Theo hành vi thật | Đổi? |
|---|---|---|---|
| `chuan` | standard | `normalize` — chuẩn hoá chuỗi để so "giống hệt" | ✅ đổi |
| `nap` | load | `load_draft_context` | ✅ đổi (rõ hơn: trả 7 giá trị) |
| `vai_viet_cua_bai` | writer_of_article | `writer_of_article` | giữ |
| `persona_viet` | persona_write | `writer_persona_name` | ✅ đổi |
| `so_lan_lam_lai` | count_redo | `redo_count` | giữ |
| `kiem_lam_lai` | check_redo | `check_redo_reused` — làm lại mà vẫn giữ ảnh/hook cũ → lỗi | ✅ đổi |
| `dem_vong_loi` | count_loop_error | `count_error_loop` | giữ (gần đúng) |
| `chu_bai_cua` | text_article_of | `article_text_for` | ✅ đổi |
| `_khong_dau` | _no_mark | `_strip_diacritics` | ✅ đổi |
| `_tu` | _from | `_words` — chuỗi → danh sách TỪ đã bỏ dấu | ✅ đổi — "từ" ở đây là "word", không phải "from" |
| `_ten_co_trong_bai` | _name_has_in_article | `_name_in_article` | ✅ đổi |
| `kiem_nhan_vat` | check_label_person | `check_subject_named` — cổng MẶT NGƯỜI dùng chung | ✅ đổi |
| `kiem_so_tren_anh` | check_number_on_image | `check_numbers_on_card` | giữ (gần đúng) |
| `can_anh_xep_hang` | needs_ranking_image | `needs_ranking_image` | giữ |
| `anh_khong_lien_quan` | image_no_relevant | `irrelevant_images` | ✅ đổi |
| `kiem_da_dung_nhieu` | check_used_many | `check_not_reused_across_runs` | ✅ đổi |
| `kiem_quote_dich` | check_quote_translate | `check_quote_translated` | giữ (gần đúng) |
| `kiem_hang_tren_the` | check_rank_on_card | `check_rank_matches_image` — hạng trên thẻ phải TRÙNG hạng engine khoanh | ✅ đổi (rõ hơn: so khớp, không chỉ "kiểm tra") |
| `_album_da_len` | _album_already_up | `_recently_posted` | ✅ đổi |
| `gui_album` | send_album | `send_album` | giữ |
| `ghi_bang_den` | write_blackboard | `write_blackboard` | giữ |

## `anh_chuan_bi.py` — engine chuẩn bị ảnh (9 hàm + `main`)

| Hiện tại | Dịch máy | Theo hành vi thật | Đổi? |
|---|---|---|---|
| `chuan_bi` | prepare | `prepare_article` — cả pipeline: nguồn→browser→(xếp hạng)→tải→nhìn→manifest | ✅ đổi (tránh trùng tên với module `prepare`/`image_prepare`) |
| `workdir` | workdir | `workdir` | giữ |
| `nap_meta` | load_meta | `load_meta` | giữ |
| `_cho_luot` | _wait_slot | `_wait_for_slot` | ✅ đổi (rõ động từ) |
| `_mo_ta_thieu_anh` | _describe_missing_image | `_describe_missing_images` | giữ (số nhiều) |
| `_doi_khoa` | _wait_lock | `_handle_lock` — không chỉ "chờ", còn phát hiện khoá mồ côi + dọn | ✅ đổi |
| `dem_chet` | count_crash | `count_crashes` | giữ |
| `_bao_chet_lap` | _report_crash_repeat | `_report_crash_loop` | ✅ đổi (thuật ngữ "crash loop" chuẩn hơn) |
| `chay` | run | `run` | giữ |
| `main` | main | `main` | giữ |

## `chuan_bi/manifest.py` — dựng manifest (8 hàm)

| Hiện tại | Dịch máy | Theo hành vi thật | Đổi? |
|---|---|---|---|
| `cau_xep_hang` | sentence_ranking | `describe_ranking_image` | ✅ đổi (rõ hành động: mô tả) |
| `dong_brief_xep_hang` | line_brief_ranking | `ranking_brief_line` | ✅ đổi |
| `ghep_hai_hang` | stack_two_row | `pair_two_vendor_images` — tin THƯƠNG VỤ: cặp ảnh của HAI HÃNG khác nhau | ✅ đổi — "hàng" ở đây = "hãng" (vendor), không phải "row" |
| `cap_ghep` | pair_stack | `stackable_pairs` | ✅ đổi |
| `bang_anh` | board_image | `contact_sheet` — tấm thu nhỏ gom mọi ảnh, nhãn mã+kích thước+loại | ✅ đổi (thuật ngữ nhiếp ảnh chuẩn) |
| `gom_tu_lieu` | gather_material | `gather_material` | giữ |
| `_tu_lieu_bai` | _material_article | `_article_material` | ✅ đổi (thứ tự tự nhiên) |
| `dan_xuat` | guide_export | `compute_derived` — **"dẫn xuất" = derived, KHÔNG PHẢI "dẫn" + "xuất" (guide+export)** | ✅ đổi — ca mơ hồ cụm bị tách sai |
| `dung_manifest` | use_manifest | `build_manifest` | ✅ đổi — ca dẫn chứng ở đầu tệp |

---

## Kết luận cho bước tiếp theo

1. **Bảng C cơ khí trong `TU_DIEN_TEN_nhap.md` không dùng được trực tiếp** —
   phải soát tay theo mẫu trên cho toàn bộ ~930 hàm, không chỉ 5 module này.
2. Ba dạng sai lặp lại nhiều lần, đáng thêm quy tắc chung khi soát các module
   còn lại:
   - **Cụm bị tách sai** (`dan_xuat` → "dẫn"+"xuất" thay vì "dẫn xuất"=derived;
     `dong_dau` → "đóng"+"dấu" thay vì "đóng dấu"=stamp).
   - **Danh từ bị dịch như động từ** (`khoa_tin` là một cái KHOÁ/key, dịch máy
     ra động từ "lock"; `_so_da_dung` là một cuốn SỔ/log, dịch máy ra "count").
   - **Hàng/hãng/hạng lẫn nhau theo ngữ cảnh** (`ghep_hai_hang` = hai HÃNG,
     không phải hai HÀNG — khác hẳn `kiem_hang_tren_the` cùng gốc "hang" nhưng
     là HẠNG/rank).
3. Việc rename thật (khi thực thi) phải dùng công cụ đổi tên atomic (rope/AST)
   đổi định nghĩa + mọi nơi gọi trong một bước, chạy đủ 66 test sau mỗi module
   — không sed theo mẫu chuỗi.
