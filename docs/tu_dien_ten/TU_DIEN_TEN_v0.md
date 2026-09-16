# TỪ ĐIỂN TÊN — v0 (chưa đụng mã)

Sinh tự động bởi `gen.py` từ repo hiện tại: 114 module, 1243 def/class (1059 tên khác nhau), 791 hằng số. `?token` = chưa có trong bảng; ⚠️ = token mơ hồ, phải chọn tay theo nghĩa tại chỗ.

**Tiêu chí (Ông Chủ 12/09/2026):** nghĩa dịch không cần đúng từng chữ — chỉ cần KHÔNG hai hàm/lớp top-level nào trong cùng module trùng tên sau khi dịch. Xem mục F.

Luật: rename 1-1 giữ cấu trúc cụm; khoá JSON trên đĩa KHÔNG đổi; tên vai (ethan/dre/kite…) giữ nguyên; token đã là English giữ nguyên. Sửa `cum.json` / `don.json` / `moho.json` / `them.json` / `overrides.json` rồi chạy lại `python3 gen.py .` để bảng dưới cập nhật.

## A. Từ gốc — CỤM (khớp trước)

| Việt | English |
|---|---|
| `anh_bai` | `article_images` |
| `anh_bao_thuc_the` | `press_entity_images` |
| `anh_chuan_bi` | `image_prepare` |
| `anh_commons` | `commons_images` |
| `anh_hang` | `vendor_images` |
| `anh_khai_niem` | `image_concept` |
| `anh_khong_lien_quan` | `irrelevant_images` |
| `anh_thuc_the` | `entity_images` |
| `anh_thuong_hieu` | `image_brand` |
| `article_extract` | `article_extract` |
| `arxiv_bia` | `arxiv_cover` |
| `arxiv_hinh` | `arxiv_figures` |
| `ba_cham` | `ellipsis` |
| `ban_do` | `map` |
| `ban_giao` | `handoff` |
| `bang_chung` | `evidence` |
| `bang_den` | `blackboard` |
| `bang_du_lieu` | `table` |
| `bang_model` | `model_boards` |
| `bao_cao` | `report` |
| `bao_cao_manifest` | `manifest_report` |
| `bao_chet_lap` | `report_repeated_crash` |
| `bao_dam` | `ensure` |
| `bao_khac` | `other_outlets` |
| `bao_mat` | `security` |
| `bat_buoc` | `required` |
| `bat_dau` | `start` |
| `benchmark_trich` | `benchmark_excerpt` |
| `bi_mat` | `secret` |
| `binh_thuong` | `normal` |
| `bo_dem` | `buffer` |
| `bo_hau_to_site` | `strip_site_suffix` |
| `bo_qua` | `skip` |
| `bo_qua_nguon` | `skip_source` |
| `bo_sung` | `supplement` |
| `brief_chung` | `brief_common` |
| `cac_manh` | `fragments` |
| `cai_dat` | `setup` |
| `cam_ket` | `commit` |
| `can_anh_xep_hang` | `needs_ranking_image` |
| `canh_bao` | `warning` |
| `canh_dai` | `long_side` |
| `canh_ngan` | `short_side` |
| `cao_nhat` | `highest` |
| `cap_ghep` | `stackable_pairs` |
| `cap_ghep_hero` | `stackable_pairs_hero` |
| `cap_nhat` | `update` |
| `caption_check` | `caption_check` |
| `cau_bi_dung` | `killed_message` |
| `cau_chay_lau` | `long_run_message` |
| `cau_hinh` | `config` |
| `cham_khe` | `touch_slit` |
| `chat_luong` | `quality` |
| `chat_router` | `chat_router` |
| `chi_muc` | `index` |
| `chi_phi` | `cost` |
| `chi_ro` | `specify` |
| `chia_tin` | `split_message` |
| `chieu_cao` | `height` |
| `chieu_rong` | `width` |
| `cho_luot` | `wait_slot` |
| `cho_phep` | `allow` |
| `chon_so` | `pick_number` |
| `chu_de` | `topic` |
| `chu_de_topic` | `topic` |
| `chu_thich` | `annotation` |
| `chu_thuan` | `pure_text` |
| `chua_nhin` | `not_yet_seen` |
| `chuan_bi` | `prepare` |
| `chuc_nang` | `feature` |
| `chup_chart` | `capture_chart` |
| `chup_lai_man_hinh` | `screenshot` |
| `chup_lead` | `capture_lead` |
| `chup_man_hinh` | `screenshot` |
| `chup_nguon` | `capture_source` |
| `chup_trang` | `capture_page` |
| `co_cum` | `has_phrase` |
| `co_hoc` | `mechanical` |
| `co_so_du_lieu` | `database` |
| `co_tu` | `has_word` |
| `cong_bo` | `announcement` |
| `cong_chan` | `gate` |
| `cost_squeeze` | `cost_squeeze` |
| `crop_ti_le` | `crop_ratio` |
| `cum_anh` | `image_phrases` |
| `cung_tin` | `same_story` |
| `cuon_roi` | `scrolled` |
| `cuu_bai` | `rescue_article` |
| `da_dung` | `used` |
| `da_nhin` | `already_seen` |
| `dac_trung` | `distinctive` |
| `dat_ten` | `naming` |
| `dau_ra` | `output` |
| `dau_tien` | `first` |
| `dau_vao` | `input` |
| `dau_vet` | `trace` |
| `dau_xuat_xu` | `provenance_stamp` |
| `day_sang` | `bright_bottom` |
| `dem_chet` | `count_crashes` |
| `dem_lai` | `recount` |
| `dem_mat` | `count_faces` |
| `di_chuyen` | `migrate` |
| `dien_tich` | `area` |
| `dieu_kien` | `condition` |
| `dinh_dang` | `format` |
| `dinh_tuyen` | `route` |
| `do_hoa` | `graphic` |
| `do_phan_giai` | `resolution` |
| `do_tre` | `latency` |
| `do_uu_tien` | `priority` |
| `doc_gia` | `reader` |
| `doc_lap` | `independent` |
| `doi_chu_anh` | `swap_image_text` |
| `doi_khoa` | `wait_lock` |
| `dong_bo` | `sync` |
| `dong_dau` | `stamp` |
| `dong_gop` | `contribute` |
| `dong_thoi` | `concurrent` |
| `draft_write` | `draft_write` |
| `du_lieu` | `data` |
| `du_nguyen_lieu` | `has_enough_material` |
| `dung_sai` | `tolerance` |
| `duyet_bai` | `approve_post` |
| `duyet_chat` | `approve_chat` |
| `duyet_chon_tin` | `approve_pick` |
| `duyet_co_so` | `approve_base` |
| `duyet_giao_viec` | `approve_dispatch` |
| `duyet_lenh` | `approve_command` |
| `emoji_deck` | `emoji_deck` |
| `env_load` | `env_load` |
| `ghi_chu` | `notes` |
| `ghi_de` | `overwrite` |
| `ghi_log` | `write_log` |
| `ghim_manifest` | `pin_manifest` |
| `gia_moi_bai` | `price_per_item` |
| `gia_ra` | `price_out` |
| `gia_tri` | `value` |
| `gia_usd` | `price_usd` |
| `gia_vao` | `price_in` |
| `giai_don` | `resolve_single` |
| `giai_ghep` | `resolve_stack` |
| `giai_muc` | `resolve_item` |
| `giai_thich` | `explain` |
| `giao_dich` | `transaction` |
| `giao_dien` | `ui` |
| `giao_viec` | `dispatch` |
| `giay_phep` | `license` |
| `gio_han` | `time_limit` |
| `gioi_han` | `limit` |
| `goi_y_nguon` | `suggest_sources` |
| `gui_telegram` | `send_telegram` |
| `ha_cap` | `downgrade` |
| `ha_san_luc` | `lower_stage_time` |
| `ha_san_nut` | `lower_stage_button` |
| `hang_cua` | `rank_of` |
| `hang_doi` | `queue` |
| `hang_ngang` | `row` |
| `hang_trong_tin` | `vendors_in_story` |
| `hanh_vi` | `behavior` |
| `hau_to` | `suffix` |
| `hermes_adapter` | `hermes_adapter` |
| `hieu_nang` | `performance` |
| `ho_model` | `model_family` |
| `ho_so` | `profile` |
| `hoan_tac` | `rollback` |
| `hoan_tat` | `finish` |
| `hoan_thanh` | `complete` |
| `hoi_thoai` | `conversation` |
| `hop_dong` | `contract` |
| `hop_le` | `valid` |
| `hop_nhat` | `merge` |
| `im_lang` | `silent` |
| `in_executor` | `in_executor` |
| `in_progress` | `in_progress` |
| `in_use` | `in_use` |
| `it_dung_nhat` | `least_used` |
| `k_tho` | `k_raw` |
| `ke_tiep` | `next` |
| `ket_luan` | `conclusion` |
| `ket_noi` | `connection` |
| `ket_qua` | `result` |
| `ket_thuc` | `end` |
| `kha_nang` | `capability` |
| `khai_niem` | `concept` |
| `khe_tren` | `top_slit` |
| `kho_khoa` | `locked_format` |
| `kho_the` | `card_format` |
| `khoa_api` | `api_key` |
| `khoa_chinh` | `primary_key` |
| `khoanh_y` | `highlight_y` |
| `khoi_dong` | `start` |
| `khoi_phuc` | `restore` |
| `khong_browser` | `no_browser` |
| `khong_gui` | `no_send` |
| `khong_nhin` | `unseen` |
| `khung_anh` | `image_frame` |
| `khung_nhin` | `viewport` |
| `kich_thuoc` | `size` |
| `kiem_chu` | `check_text` |
| `kiem_da_dung_nhieu` | `check_reused` |
| `kiem_ghep` | `check_stack` |
| `kiem_hang_tren_the` | `check_rank_on_card` |
| `kiem_hermes` | `check_hermes` |
| `kiem_mat` | `check_faces` |
| `kiem_moi_truong` | `check_env` |
| `kiem_nhan_vat` | `check_subject` |
| `kiem_quote_dich` | `check_quote_translated` |
| `kiem_so_tren_anh` | `check_numbers_on_card` |
| `kiem_tra` | `check` |
| `kiem_truong` | `check_field` |
| `la_gi` | `what_is` |
| `la_hoac` | `is_or` |
| `la_tin_xep_hang` | `is_ranking_story` |
| `lam_lai` | `redo` |
| `lam_moi` | `fresh` |
| `lan_chay` | `run` |
| `lan_chay_cuoi` | `last_run` |
| `lap_cum` | `repeat_phrase` |
| `lap_day` | `fill` |
| `lenh_chon` | `pick_command` |
| `lien_quan` | `relevant` |
| `liet_ke` | `list` |
| `loai_tin` | `story_type` |
| `loc_commons` | `filter_commons` |
| `loi_nghiem` | `fatal` |
| `luat_anh` | `image_rules` |
| `luot_dung` | `usage` |
| `ly_do` | `reason` |
| `mac_dinh` | `default` |
| `man_hinh` | `screen` |
| `manifest_build` | `manifest_build` |
| `manifest_chung` | `manifest_common` |
| `manifest_ghi` | `manifest_write` |
| `mat_khau` | `password` |
| `mat_nguoi` | `face` |
| `mat_tho` | `raw_face` |
| `mau_sac` | `color` |
| `max_runtime_cua` | `max_runtime_for` |
| `may_chu` | `server` |
| `mo_coi` | `orphan` |
| `mo_hinh` | `model` |
| `mo_ta` | `description` |
| `moat_publish` | `moat_publish` |
| `moc_lan_chay` | `run_start` |
| `model_audition` | `model_audition` |
| `model_watch` | `model_watch` |
| `moi_` | `new` |
| `moi_nhat` | `latest` |
| `moi_truong` | `environment` |
| `mot_minh` | `alone` |
| `muc_do` | `level` |
| `muc_luc` | `index` |
| `muc_tieu` | `target` |
| `nang_cap` | `upgrade` |
| `nang_luc` | `capability` |
| `nen_chu` | `text_bg` |
| `nen_trang` | `white_bg` |
| `ngan_sach` | `budget` |
| `nguoi_doc` | `reader` |
| `nguoi_dung` | `user` |
| `nguon_bai` | `article_sources` |
| `nhac_nho` | `remind` |
| `nhan_dien` | `detect` |
| `nhan_ma` | `mark_code` |
| `nhan_vat` | `subject` |
| `nhan_viec` | `receive_job` |
| `nhan_vien` | `staff` |
| `nhat_ky` | `journal` |
| `nhat_ky_web` | `journal_web` |
| `nhip_cuoi` | `last_beat` |
| `nhip_tho` | `heartbeat` |
| `noi_dung` | `content` |
| `nop_chung` | `submit_common` |
| `ong_chu` | `boss` |
| `phan_giai` | `resolution` |
| `phan_loai` | `classify` |
| `phan_tich` | `analyze` |
| `phan_tram` | `percent` |
| `phat_hien` | `detect` |
| `phien_ban` | `version` |
| `phien_browser` | `browser_session` |
| `phien_hoac_moi` | `session_or_new` |
| `phien_lam_viec` | `session` |
| `phong_ban` | `department` |
| `pid_song` | `pid_alive` |
| `quan_trong` | `important` |
| `quet_chuan_bi` | `scan_prepare` |
| `quet_chung` | `scan_common` |
| `quet_nop` | `scan_submit` |
| `quy_uoc` | `convention` |
| `render_edu` | `render_edu` |
| `ro_handle` | `clear_handle` |
| `roi_du` | `fallback_enough` |
| `roi_duoi` | `fall_below` |
| `route_thieu_anh` | `route_missing_images` |
| `rut_gon` | `shorten` |
| `rut_van` | `shorten_text` |
| `san_pham` | `product` |
| `san_sang` | `ready` |
| `sao_luu` | `backup` |
| `sap_xep` | `sort` |
| `scan_business` | `scan_business` |
| `scan_models` | `scan_models` |
| `scan_sources` | `scan_sources` |
| `slug_that` | `canonical_slug` |
| `so_anh_toi_thieu` | `min_images` |
| `so_lan` | `count_of` |
| `so_lieu` | `figures` |
| `so_luong` | `quantity` |
| `so_sanh` | `compare` |
| `so_thu_tu` | `ordinal` |
| `soat_cron` | `audit_cron` |
| `social_post` | `social_post` |
| `soi_model` | `inspect_model` |
| `song_song` | `parallel` |
| `su_co` | `incident` |
| `suy_luan` | `reasoning` |
| `tac_gia` | `author` |
| `tach_hang` | `extract_rank` |
| `tach_model` | `extract_model` |
| `tach_roi` | `split` |
| `tai_lieu` | `docs` |
| `tai_loc` | `download_filter` |
| `tao_task` | `create_task` |
| `task_bodies` | `task_bodies` |
| `teaser_assemble` | `teaser_assemble` |
| `tele_util` | `tele_util` |
| `ten_hien` | `display_name` |
| `ten_rieng_dau` | `leading_proper_noun` |
| `thanh_cong` | `success` |
| `thanh_vien` | `member` |
| `thap_nhat` | `lowest` |
| `the_du_phong` | `fallback_card` |
| `theo_bac` | `by_tier` |
| `theo_doi` | `monitor` |
| `theo_doi_9router` | `monitor_9router` |
| `thiet_lap` | `settings` |
| `thoi_gian` | `time` |
| `thong_bao` | `notify` |
| `thong_luong` | `throughput` |
| `thu_muc` | `directory` |
| `thu_tu` | `order` |
| `thuat_ngu` | `term` |
| `thuc_the` | `entity` |
| `thuoc_tinh` | `attribute` |
| `thuong_hieu` | `brand` |
| `ti_le` | `ratio` |
| `ti_le_phan_tram` | `percentage` |
| `tich_luy` | `accumulate` |
| `tien_do` | `progress` |
| `tien_to` | `prefix` |
| `tieng_viet` | `vietnamese` |
| `tieu_chi` | `criteria` |
| `tieu_de` | `title` |
| `tim_anh_them` | `find_more_images` |
| `tim_rong` | `widen_search` |
| `tim_va_chup` | `find_and_capture` |
| `tin_nhan` | `message` |
| `tinh_nang` | `feature` |
| `to_chuc` | `organization` |
| `toa_soan` | `outlet` |
| `toan_bo` | `entire` |
| `toc_do` | `speed` |
| `toi_da` | `max` |
| `toi_thieu` | `min` |
| `tom_tat` | `summary` |
| `ton_nhat` | `most_expensive` |
| `tong_cong` | `total` |
| `tong_hop` | `aggregate` |
| `tra_ve` | `return` |
| `trang_cong_bo` | `announcement_page` |
| `trang_thai` | `status` |
| `tre_gio` | `late` |
| `trich_dan` | `citation` |
| `trinh_duyet` | `browser` |
| `tro_giup` | `help` |
| `trong_so` | `weight` |
| `trung_binh` | `average` |
| `trung_gan_giong` | `near_duplicate` |
| `truy_van` | `query` |
| `tu_choi` | `reject` |
| `tu_cung_tin` | `story_tokens` |
| `tu_dong` | `auto` |
| `tu_khoa` | `keyword` |
| `tu_lieu` | `material` |
| `tu_rac` | `junk_words` |
| `ung_vien` | `candidate` |
| `url_commons` | `commons_urls` |
| `uu_tien` | `priority` |
| `vai_tro` | `role` |
| `vai_viet_cua` | `writer_for` |
| `van_ban` | `text` |
| `vi_du` | `example` |
| `vi_sao` | `why` |
| `vi_tri` | `position` |
| `vong_bu` | `fallback_rounds` |
| `vong_lap` | `loop` |
| `website_hang` | `vendor_website` |
| `xa_bang` | `off_board` |
| `xa_hoi` | `social` |
| `xep_day_lai` | `refill` |
| `xep_hang` | `ranking` |
| `xep_hang_doi` | `enqueue` |
| `xu_ly` | `process` |
| `xuat_xu` | `provenance` |
| `yeu_cau` | `request` |

## A2. Từ gốc — TỪ ĐƠN

| Việt | English | Mơ hồ |
|---|---|---|
| `am` | `negative` |  |
| `an` | `hide` |  |
| `anh` | `image` |  |
| `ap` | `apply` |  |
| `au` | `eu` |  |
| `ba` | `three` |  |
| `bac` | `tier` |  |
| `bai` | `article` |  |
| `bam` | `press` |  |
| `ban` | `copy` | ⚠️ bản=copy / bàn=table / bán=sell |
| `bang` | `board` | ⚠️ bảng=board/table |
| `bao` | `report` |  |
| `bat` | `catch` | ⚠️ bắt=catch / bật=enable |
| `ben` | `side` |  |
| `bi` | `got` |  |
| `bia` | `cover` |  |
| `bien` | `variable` |  |
| `binh` | `normal` |  |
| `bo` | `drop` | ⚠️ bỏ=drop / bộ=set |
| `boc` | `extract` |  |
| `boi` | `context` |  |
| `bong` | `shadow` |  |
| `bu` | `fallback` |  |
| `buoc` | `step` |  |
| `ca` | `all` |  |
| `cac` | `each` |  |
| `cach` | `way` |  |
| `cai` | `item` |  |
| `cam` | `forbid` |  |
| `cang` | `tension` |  |
| `canh` | `edge` | ⚠️ cạnh=edge / cảnh=warning |
| `cao` | `height` |  |
| `cat` | `crop` |  |
| `cau` | `sentence` |  |
| `chac` | `sure` |  |
| `cham` | `touch` |  |
| `chan` | `block` |  |
| `chay` | `run` |  |
| `chep` | `copy` |  |
| `chet` | `crash` |  |
| `chi` | `only` | ⚠️ chỉ=only / chi=spend |
| `chia` | `split` |  |
| `chieu` | `dimension` |  |
| `chinh` | `main` |  |
| `chiu` | `bear` |  |
| `cho` | `wait` | ⚠️ chờ=wait / cho=for/give |
| `chon` | `pick` |  |
| `chong` | `anti` |  |
| `chot` | `finalize` |  |
| `chu` | `text` | ⚠️ chữ=text / chủ=owner |
| `chua` | `not_yet` |  |
| `chuan` | `standard` |  |
| `chuc` | `function` |  |
| `chung` | `common` |  |
| `chung2` | `common2` |  |
| `chuoi` | `string` |  |
| `chup` | `capture` |  |
| `chuyen` | `transfer` |  |
| `co` | `has` |  |
| `con` | `remaining` |  |
| `cong` | `gate` |  |
| `cot` | `column` |  |
| `cu` | `old` | ⚠️ cũ=old / cứ=keep-going |
| `cua` | `of` |  |
| `cum` | `phrase` |  |
| `cung` | `same` |  |
| `cuoi` | `last` |  |
| `cuon` | `scroll` |  |
| `cuu` | `rescue` |  |
| `da` | `already` |  |
| `dac` | `solid` |  |
| `dai` | `long` |  |
| `dam` | `bold` |  |
| `dan` | `guide` |  |
| `dang` | `form` |  |
| `danh` | `list` |  |
| `dao` | `invert` |  |
| `dat` | `set` |  |
| `dau` | `mark` | ⚠️ dấu=mark / đầu=head/first |
| `day` | `bottom` | ⚠️ đáy=bottom / dây=cable / dạy=teach / đầy=full |
| `de` | `for` | ⚠️ để=to / dễ=easy |
| `dem` | `count` |  |
| `dep` | `pretty` |  |
| `deu` | `all` |  |
| `di` | `go` |  |
| `dia` | `disk` |  |
| `dich` | `translate` |  |
| `diem` | `score` |  |
| `dien` | `aspect` |  |
| `dieu` | `control` |  |
| `dinh` | `fixed` |  |
| `do` | `measure` |  |
| `doan` | `guess` |  |
| `doc` | `read` | ⚠️ đọc=read / dọc=portrait |
| `doi` | `change` | ⚠️ đổi=change / đợi=wait (cụm doi_khoa=wait_lock) / đội=team |
| `don` | `single` |  |
| `dong` | `line` | ⚠️ dòng=line / đóng=close / động=motion |
| `du` | `enough` |  |
| `dua` | `pass` |  |
| `dung` | `use` | ⚠️ dùng=use / dừng=stop / đúng=correct / dựng=build |
| `duoc` | `ok` |  |
| `duoi` | `below` |  |
| `duong` | `path` |  |
| `duyet` | `approve` |  |
| `ep` | `force` |  |
| `gan` | `near` |  |
| `ghep` | `stack` |  |
| `ghi` | `write` |  |
| `ghim` | `pin` |  |
| `gi` | `what` |  |
| `gia` | `fake` | ⚠️ giả=fake (mặc định, stub test) / giá=price (cụm gia_vao/gia_ra/gia_usd/gia_moi_bai) |
| `giai` | `resolve` |  |
| `gian` | `space` |  |
| `giao` | `hand` |  |
| `giay` | `seconds` |  |
| `gio` | `hours` |  |
| `giong` | `voice` |  |
| `giu` | `keep` |  |
| `giua` | `middle` |  |
| `goc` | `original` |  |
| `goi` | `call` |  |
| `gom` | `gather` |  |
| `gon` | `compact` |  |
| `gon2` | `compact2` |  |
| `gop` | `merge` |  |
| `gui` | `send` |  |
| `ha` | `lower` |  |
| `hai` | `two` |  |
| `han` | `limit` |  |
| `hang` | `rank` | ⚠️ hạng=rank / hàng=row / hãng=vendor |
| `het` | `all_done` |  |
| `hien` | `show` |  |
| `hieu` | `understand` |  |
| `hinh` | `figure` |  |
| `ho` | `family` |  |
| `hoa` | `ify` |  |
| `hoac` | `or` |  |
| `hoi` | `ask` |  |
| `hon` | `than` |  |
| `hong` | `broken` |  |
| `hop` | `box` |  |
| `im` | `silent` |  |
| `in` | `print` | ⚠️ in=print (mặc định: in_log, in_bang) / English in (cụm in_progress/in_use/in_executor) |
| `kem` | `with` |  |
| `kenh` | `channel` |  |
| `keo` | `drag` |  |
| `ket` | `end` |  |
| `khac` | `other` |  |
| `khach` | `customer` |  |
| `khan` | `urgent` |  |
| `khe` | `slit` |  |
| `khi` | `when` |  |
| `khit` | `tight` |  |
| `kho` | `format` |  |
| `khoa` | `lock` | ⚠️ khoá=lock / khoá=key |
| `khoang` | `range` |  |
| `khoanh` | `highlight` |  |
| `khoi` | `block` |  |
| `khong` | `no` |  |
| `khop` | `match` |  |
| `khung` | `frame` |  |
| `kich` | `size` |  |
| `kiem` | `check` |  |
| `kieu` | `kind` |  |
| `kin` | `sealed` |  |
| `la` | `is` |  |
| `lai` | `again` |  |
| `lam` | `make` |  |
| `lan` | `attempt` | ⚠️ lần=time / lan=spread |
| `lap` | `repeat` |  |
| `lat` | `flip` |  |
| `lau` | `long_time` |  |
| `lay` | `take` |  |
| `le` | `odd` |  |
| `lech` | `offset` |  |
| `lenh` | `command` |  |
| `lich` | `schedule` |  |
| `lieu` | `material` |  |
| `lo` | `leak` |  |
| `loai` | `type` |  |
| `loc` | `filter` |  |
| `loi` | `error` |  |
| `lon` | `large` |  |
| `lop` | `layer` |  |
| `lot` | `pass` |  |
| `luan` | `reason` |  |
| `luat` | `rules` |  |
| `lui` | `back` |  |
| `luon` | `always` |  |
| `luong` | `flow` |  |
| `luot` | `turn` |  |
| `luu` | `save` |  |
| `ma` | `code` | ⚠️ mã=code / mà=but |
| `mac` | `default` |  |
| `man` | `screen` |  |
| `mang` | `network` |  |
| `manh` | `fragment` |  |
| `mat` | `face` |  |
| `mau` | `color` | ⚠️ màu=color / mẫu=sample |
| `may` | `machine` |  |
| `mien` | `domain` |  |
| `mieng` | `piece` |  |
| `minh` | `self` |  |
| `mo` | `open` |  |
| `moc` | `timestamp` |  |
| `moi` | `new` | ⚠️ mới=new / mỗi=each / mời=invite |
| `mong` | `thin` |  |
| `mot` | `one` |  |
| `muc` | `item` | ⚠️ mục=item / mức=level |
| `muon` | `late` |  |
| `nam` | `lie` |  |
| `nang` | `capability` |  |
| `nap` | `load` |  |
| `nay` | `this` |  |
| `nen` | `background` | ⚠️ nền=background / nên=should |
| `neu` | `if` |  |
| `ngan` | `short` |  |
| `ngang` | `landscape` |  |
| `ngat` | `break` |  |
| `ngay` | `date` |  |
| `nghich` | `reverse` |  |
| `nghiem` | `strict` |  |
| `ngoai` | `outside` |  |
| `nguoi` | `person` |  |
| `nguon` | `source` |  |
| `nguong` | `threshold` |  |
| `nguyen` | `raw` |  |
| `nhac` | `mention` |  |
| `nham` | `wrong` |  |
| `nhan` | `label` | ⚠️ nhãn=label / nhận=receive / nhân=multiply |
| `nhat` | `most` |  |
| `nhieu` | `many` |  |
| `nhin` | `seen` |  |
| `nhip` | `beat` |  |
| `nho` | `small` |  |
| `nhom` | `group` |  |
| `nhung` | `but` |  |
| `noi` | `say` |  |
| `nong` | `hot` |  |
| `nop` | `submit` |  |
| `nua` | `half` |  |
| `nuoc` | `country` |  |
| `nut` | `button` |  |
| `o` | `cell` |  |
| `pha` | `phase` |  |
| `phai` | `right` |  |
| `phan` | `part` | ⚠️ phần=part / phân=classify |
| `phang` | `flat` |  |
| `phat` | `emit` |  |
| `phep` | `permission` |  |
| `phia` | `side` |  |
| `phien` | `session` |  |
| `phieu` | `ballot` |  |
| `phong` | `room` |  |
| `phu` | `secondary` |  |
| `phut` | `minutes` |  |
| `qua` | `over` |  |
| `quan` | `manage` |  |
| `quet` | `scan` |  |
| `quy` | `rule` |  |
| `quyen` | `permission` |  |
| `quyet` | `decide` |  |
| `ra` | `out` |  |
| `rac` | `junk` |  |
| `rieng` | `own` |  |
| `ro` | `clear` |  |
| `roi` | `fall` |  |
| `rong` | `empty` | ⚠️ rỗng=empty / rộng=wide |
| `rut` | `shorten` |  |
| `sach` | `clean` |  |
| `sai` | `wrong` |  |
| `san` | `ready` |  |
| `sang` | `bright` | ⚠️ sáng=bright / sang=to |
| `sao` | `star` |  |
| `sap` | `sort` |  |
| `sau` | `after` |  |
| `sinh` | `generate` |  |
| `so` | `count` | ⚠️ số=number / so=compare |
| `soat` | `audit` |  |
| `soi` | `inspect` |  |
| `song` | `alive` |  |
| `sua` | `fix` |  |
| `suc` | `health` |  |
| `sung` | `supplement` |  |
| `tach` | `extract` |  |
| `tai` | `download` |  |
| `tam` | `temp` |  |
| `tan` | `spread` |  |
| `tang` | `layer` |  |
| `tao` | `create` |  |
| `tap` | `set` |  |
| `tat` | `all` |  |
| `tay` | `manual` |  |
| `ten` | `name` |  |
| `tep` | `file` |  |
| `tg` | `time` |  |
| `th` | `brand_` |  |
| `tha` | `drop` |  |
| `than` | `body` |  |
| `thang` | `straight` |  |
| `thanh` | `into` |  |
| `thap` | `low` |  |
| `that` | `real` |  |
| `thay` | `see` | ⚠️ thấy=see / thay=replace |
| `the` | `card` | ⚠️ thẻ=card / thế=so |
| `them` | `extra` |  |
| `theo` | `by` |  |
| `thi` | `then` |  |
| `thich` | `explain` |  |
| `thieu` | `missing` |  |
| `tho` | `raw` |  |
| `thoat` | `exit` |  |
| `thoi` | `time` |  |
| `thong` | `info` |  |
| `thu` | `try` | ⚠️ thử=try / thứ=order / thu=collect |
| `thua` | `excess` |  |
| `thuan` | `pure` |  |
| `thuat` | `technique` |  |
| `thuc` | `actual` |  |
| `thuong` | `regular` |  |
| `tich` | `accumulate` |  |
| `tien` | `money` |  |
| `tiep` | `next` |  |
| `tieu` | `consume` |  |
| `tim` | `find` |  |
| `tin` | `story` |  |
| `tinh` | `static` |  |
| `tit` | `headline` |  |
| `toan` | `whole` |  |
| `toi` | `dark` | ⚠️ tối=dark / tới=until |
| `tong` | `total` |  |
| `tot` | `good` |  |
| `tq` | `china` |  |
| `tra` | `return` | ⚠️ trả=return / tra=lookup |
| `trai` | `left` |  |
| `tran` | `ceiling` |  |
| `trang` | `page` |  |
| `tre` | `late` |  |
| `tren` | `on` |  |
| `treo` | `stalled` |  |
| `trich` | `excerpt` |  |
| `trinh` | `program` |  |
| `tro` | `point` |  |
| `tron` | `full` |  |
| `trong` | `within` |  |
| `trung` | `duplicate` |  |
| `truoc` | `before` |  |
| `truong` | `field` |  |
| `truy` | `trace` |  |
| `tu` | `from` | ⚠️ từ=from/word / tự=self |
| `tuan` | `week` |  |
| `tuc` | `instant` |  |
| `tung` | `each` |  |
| `tuoi` | `age` |  |
| `tuong` | `wall` |  |
| `ty` | `billion` |  |
| `ungvien` | `candidate` |  |
| `uu` | `prefer` |  |
| `va` | `and` |  |
| `vai` | `role` |  |
| `van` | `still` | ⚠️ vẫn=still / văn=text |
| `vang` | `gold` |  |
| `vao` | `into` |  |
| `ve` | `about` |  |
| `vet` | `trace` |  |
| `viec` | `job` |  |
| `vien` | `border` |  |
| `viet` | `write` |  |
| `vit` | `duck` |  |
| `voi` | `with` |  |
| `vong` | `round` |  |
| `vua` | `fit` |  |
| `vung` | `region` |  |
| `xa` | `far` |  |
| `xac` | `confirm` |  |
| `xau` | `ugly` |  |
| `xep` | `arrange` |  |
| `xet` | `consider` |  |
| `xoa` | `delete` |  |
| `xong` | `done` |  |
| `xuat` | `export` |  |
| `yeu` | `weak` |  |

## B. Module

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `about_text` | `about_text` |  |
| `ada_prepare` | `ada_prepare` |  |
| `ada_submit` | `ada_submit` |  |
| `approve_base` | `approve_base` |  |
| `approve_chat` | `approve_chat` |  |
| `approve_command` | `approve_command` |  |
| `approve_dispatch` | `approve_dispatch` |  |
| `approve_pick` | `approve_pick` |  |
| `approve_post` | `approve_post` |  |
| `approve_service` | `approve_service` |  |
| `article_extract` | `article_extract` |  |
| `article_images` | `article_images` |  |
| `article_sources` | `article_sources` |  |
| `arxiv_cover` | `arxiv_cover` |  |
| `arxiv_figures` | `arxiv_figures` |  |
| `audit_cron` | `audit_cron` |  |
| `blackboard` | `blackboard` |  |
| `bob_submit` | `bob_submit` |  |
| `brief_common` | `brief_common` |  |
| `browser_session` | `browser_session` |  |
| `cape_prepare` | `cape_prepare` |  |
| `cape_submit` | `cape_submit` |  |
| `caption_check` | `caption_check` |  |
| `capture_chart` | `capture_chart` |  |
| `capture_page` | `capture_page` |  |
| `card` | `card` |  |
| `carousel` | `carousel` |  |
| `chat_router` | `chat_router` |  |
| `check_env` | `check_env` |  |
| `check_hermes` | `check_hermes` |  |
| `cleanup` | `cleanup` |  |
| `cost_squeeze` | `cost_squeeze` |  |
| `crop_ratio` | `crop_ratio` |  |
| `deck` | `deck` |  |
| `draft_write` | `draft_write` |  |
| `dre_prepare` | `dre_prepare` |  |
| `dre_submit` | `dre_submit` |  |
| `emoji_deck` | `emoji_deck` |  |
| `entity_images` | `entity_images` |  |
| `env_load` | `env_load` |  |
| `ethan_prepare` | `ethan_prepare` |  |
| `ethan_submit` | `ethan_submit` |  |
| `find_image_web` | `find_image_web` |  |
| `find_more_images` | `find_more_images` |  |
| `gin_prepare` | `gin_prepare` |  |
| `gin_submit` | `gin_submit` |  |
| `hermes_adapter` | `hermes_adapter` |  |
| `image_brand` | `image_brand` |  |
| `image_concept` | `image_concept` |  |
| `image_frame` | `image_frame` |  |
| `image_prepare` | `image_prepare` |  |
| `image_provenance` | `image_provenance` |  |
| `image_rules_dre` | `image_rules_dre` |  |
| `image_rules_ethan` | `image_rules_ethan` |  |
| `image_rules_kite` | `image_rules_kite` |  |
| `itachi_prepare` | `itachi_prepare` |  |
| `itachi_submit` | `itachi_submit` |  |
| `jika_prepare` | `jika_prepare` |  |
| `jika_submit` | `jika_submit` |  |
| `journal` | `journal` |  |
| `journal_web` | `journal_web` |  |
| `kite_prepare` | `kite_prepare` |  |
| `kite_submit` | `kite_submit` |  |
| `manifest_build` | `manifest_build` |  |
| `manifest_common` | `manifest_common` |  |
| `manifest_report` | `manifest_report` |  |
| `manifest_write` | `manifest_write` |  |
| `material` | `material` |  |
| `miles_prepare` | `miles_prepare` |  |
| `miles_submit` | `miles_submit` |  |
| `moat_publish` | `moat_publish` |  |
| `model_audition` | `model_audition` |  |
| `model_boards` | `model_boards` |  |
| `model_watch` | `model_watch` |  |
| `monitor_9router` | `monitor_9router` |  |
| `prepare.__init__` | `prepare.__init__` |  |
| `prepare.browser` | `prepare.browser` |  |
| `prepare.common` | `prepare.common` |  |
| `prepare.download_filter` | `prepare.download_filter` |  |
| `prepare.fallback_rounds` | `prepare.fallback_rounds` |  |
| `prepare.manifest` | `prepare.manifest` |  |
| `prepare.source` | `prepare.source` |  |
| `prepare.vision` | `prepare.vision` |  |
| `press_entity_images` | `press_entity_images` |  |
| `publish` | `publish` |  |
| `ranking` | `ranking` |  |
| `render_edu` | `render_edu` |  |
| `required` | `required` |  |
| `role` | `role` |  |
| `route_missing_images` | `route_missing_images` |  |
| `scan_business` | `scan_business` |  |
| `scan_common` | `scan_common` |  |
| `scan_models` | `scan_models` |  |
| `scan_prepare` | `scan_prepare` |  |
| `scan_sources` | `scan_sources` |  |
| `scan_submit` | `scan_submit` |  |
| `scan_x` | `scan_x` |  |
| `schema` | `schema` |  |
| `send_telegram` | `send_telegram` |  |
| `skill_lesson_approve` | `skill_lesson_approve` |  |
| `skill_lesson_commit` | `skill_lesson_commit` |  |
| `skill_lesson_filter` | `skill_lesson_filter` |  |
| `social_post` | `social_post` |  |
| `story_type` | `story_type` |  |
| `submit_common` | `submit_common` |  |
| `swap_image_text` | `swap_image_text` |  |
| `sync_hermes` | `sync_hermes` |  |
| `task_bodies` | `task_bodies` |  |
| `teaser_assemble` | `teaser_assemble` |  |
| `tele_util` | `tele_util` |  |
| `text_bg` | `text_bg` |  |
| `vietnamese` | `vietnamese` |  |
| `worker_scope_sweep` | `worker_scope_sweep` |  |
| `write_log` | `write_log` |  |

## C. Hàm/lớp theo module

### `about_text`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `path_font` | `path_font` |  |
| `font_default` | `font_default` |  |
| `height_item` | `height_item` |  |
| `has_by_original` | `has_by_original` |  |
| `ratio_empty` | `ratio_empty` |  |
| `pick_font` | `pick_font` |  |
| `to_color` | `to_color` |  |
| `ceiling_box` | `ceiling_box` |  |
| `_space_line` | `_space_line` |  |
| `_slit` | `_slit` |  |
| `pick_has` | `pick_has` |  |
| `about_block` | `about_block` |  |

### `ada_prepare`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `workdir` | `workdir` |  |
| `_tier` | `_tier` |  |
| `gather_manifest` | `gather_manifest` |  |
| `gather_draft` | `gather_draft` |  |
| `gather_kanban` | `gather_kanban` |  |
| `gather_token` | `gather_token` |  |
| `gather_9router` | `gather_9router` |  |
| `write_brief` | `write_brief` |  |

### `ada_submit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `use_report` | `use_report` |  |

### `approve_base`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `load_secrets` | `load_secrets` |  |
| `call` | `call` |  |
| `call_upload` | `call_?upload` |  |
| `_write_json` | `_write_json` |  |
| `_lock_of` | `_lock_of` |  |
| `_run_background` | `_run_background` |  |
| `_boc` | `_extract` |  |
| `_send_text` | `_send_text` |  |
| `_reply_real` | `_reply_real` |  |
| `_extract_line` | `_extract_line` |  |
| `_load_json` | `_load_json` |  |
| `is_boss` | `is_boss` |  |

### `approve_chat`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `RankFIFCell` | `RankFIFCell` |  |
| `lay_so` | `take_count` | ⚠️ so |
| `doi` | `change` | ⚠️ doi |
| `release` | `release` |  |
| `_rank_of` | `_rank_of` |  |
| `_ai_form_run` | `_ai_form_run` |  |
| `context_edge_role` | `context_edge_role` |  |
| `_story_pass_job` | `_story_pass_job` |  |
| `_drop_gate_old_chat` | `_drop_gate_old_chat` |  |
| `handle_chat` | `handle_chat` |  |
| `_chat_has_lock` | `_chat_has_lock` |  |
| `_goi` | `_call` |  |

### `approve_command`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_standard_ify_url` | `_standard_ify_url` |  |
| `_url_valid` | `_url_valid` |  |
| `_read_page` | `_read_page` |  |
| `_read_social` | `_read_social` |  |
| `_line_role_help` | `_line_role_help` |  |
| `_command_article` | `_command_article` |  |
| `handle_command` | `handle_command` |  |
| `tra_loi` | `return_error` | ⚠️ tra |

### `approve_dispatch`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_report_receive_job` | `_report_receive_job` |  |
| `role_of_topic` | `role_of_topic` |  |
| `standard_assignee` | `standard_assignee` |  |
| `kanban_create` | `kanban_create` |  |
| `long_run_message` | `long_run_message` |  |
| `killed_message` | `killed_message` |  |
| `_blackboard_root` | `_blackboard_root` |  |
| `_blackboard_write` | `_blackboard_write` |  |
| `_status_task` | `_status_task` |  |
| `_summary_run` | `_summary_run` |  |
| `reason_task` | `reason_task` |  |
| `link_result` | `link_result` |  |
| `_done_code_no_hand` | `_done_code_no_hand` |  |
| `report_progress_kanban` | `report_progress_kanban` |  |
| `standard_label` | `standard_label` |  |

### `approve_pick`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `slugify` | `slugify` |  |
| `latest_manifest` | `latest_manifest` |  |
| `_mid_report` | `_mid_report` |  |
| `manifest_already_send` | `manifest_already_send` |  |
| `_is_reply_report` | `_is_reply_report` |  |
| `read_pick_command` | `read_pick_command` |  |
| `_xa` | `_far` |  |
| `write_meta` | `write_meta` |  |
| `_draft_id` | `_draft_id` |  |
| `_research_source` | `_research_source` |  |
| `_block_run_engine` | `_block_run_engine` |  |
| `_crop_sidecar` | `_crop_sidecar` |  |
| `create_pair` | `create_pair` |  |
| `_lock_manifest` | `_lock_manifest` |  |
| `_report_already_label` | `_report_already_label` |  |
| `_process_pick` | `_process_pick` |  |

### `approve_post`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_process_button` | `_process_button` |  |
| `keyboard` | `keyboard` |  |
| `_upload_timeout` | `_?upload_timeout` |  |
| `_media_timeout` | `_media_timeout` |  |
| `_compress_preview` | `_?compress_preview` |  |
| `_send_media_group` | `_send_media_group` |  |
| `draft_push` | `draft_push` |  |
| `_split_caption_html` | `_split_caption_html` |  |
| `already_len_channel` | `already_len_channel` |  |
| `_write_mark` | `_write_mark` |  |
| `_text_one_attempt` | `_text_one_attempt` |  |
| `publish` | `publish` |  |
| `_go_count_image` | `_go_count_image` |  |
| `mark_draft` | `mark_draft` |  |
| `_extract_reason_redo` | `_extract_reason_redo` |  |
| `_code_of_slide` | `_code_of_slide` |  |
| `_write_forbid_image_redo` | `_write_forbid_image_redo` |  |
| `_hand_redo` | `_hand_redo` |  |
| `_load_redo_wait` | `_load_redo_wait` |  |
| `_wait_within_topic` | `_wait_within_topic` |  |
| `_over_limit` | `_over_limit` |  |
| `_label_reason_redo` | `_label_reason_redo` |  |
| `_process_reason_redo` | `_process_reason_redo` |  |
| `_redo_all_done_limit` | `_redo_all_done_limit` |  |
| `_hand_all_done_limit` | `_hand_all_done_limit` |  |
| `create_task_kite` | `create_task_kite` |  |
| `_button_drop_limit` | `_button_drop_limit` |  |
| `_button_kite` | `_button_kite` |  |
| `_button_lower_ready` | `_button_lower_ready` |  |
| `_button_redo` | `_button_redo` |  |
| `_answer_callback` | `_?answer_callback` |  |
| `_button_approve` | `_button_approve` |  |
| `_writer_by_queue` | `_writer_by_queue` |  |
| `retarget_writer_body` | `?retarget_writer_body` |  |
| `parse_reply_approval` | `parse_reply_approval` |  |
| `find_album_draft` | `find_album_draft` |  |
| `handle_reply_approval` | `handle_reply_approval` |  |
| `_process_reply_approval` | `_process_reply_approval` |  |
| `_finalize_button` | `_finalize_button` |  |
| `handle_img_approval` | `handle_img_approval` |  |
| `handle_callback` | `handle_callback` |  |
| `_bottom_again_moat` | `_bottom_again_moat` |  |
| `chay` | `run` |  |
| `_read_draft` | `_read_draft` |  |
| `_form_background` | `_form_background` |  |
| `_fix_story_go_button` | `_fix_story_go_button` |  |

### `approve_service`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_download_image_fixed_with` | `_download_image_fixed_with` |  |
| `_report_no_family_point` | `_report_no_family_point` |  |
| `_pick_command_if_has` | `_pick_command_if_has` |  |
| `_report_no_right_reply` | `_report_no_right_reply` |  |
| `handle_message` | `handle_message` |  |
| `_write_offset` | `_write_offset` |  |
| `_read_offset` | `_read_offset` |  |
| `_audit_tirith` | `_audit_tirith` |  |
| `_rescue_article_end_publishing` | `_rescue_article_end_publishing` |  |
| `loop` | `loop` |  |
| `_finish_push_cli` | `_finish_push_cli` |  |

### `article_extract`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `fetch` | `fetch` |  |
| `_parser` | `_parser` |  |
| `extract` | `extract` |  |
| `meta` | `meta` |  |

### `article_images`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_download` | `_download` |  |
| `image_within_page` | `image_within_page` |  |
| `them` | `extra` |  |
| `other_outlets` | `other_outlets` |  |
| `_graphic` | `_graphic` |  |
| `measure_image` | `measure_image` |  |
| `touch` | `touch` |  |
| `find` | `find` |  |
| `_da_thu_nho` | `_already_try_small` | ⚠️ thu |

### `article_sources`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `strip_site_suffix` | `strip_site_suffix` |  |
| `story_tokens` | `story_tokens` |  |
| `same_story` | `same_story` |  |
| `_download` | `_download` |  |
| `resolve_code_gnews` | `resolve_code_gnews` |  |
| `has_vietnamese` | `has_vietnamese` |  |
| `_title_rss` | `_title_rss` |  |
| `_title_page` | `_title_page` |  |
| `_title_slug` | `_title_slug` |  |
| `_name_own_no_mark` | `_name_own_no_mark` |  |
| `title_find` | `title_find` |  |
| `_query_bing` | `_query_bing` |  |
| `other_outlets_bing` | `other_outlets_bing` |  |
| `report_about_keyword` | `report_about_keyword` |  |
| `find` | `find` |  |
| `_trong_feed` | `_within_feed` |  |

### `arxiv_cover`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `is_arxiv` | `is_arxiv` |  |
| `download_pdf` | `download_pdf` |  |
| `capture_cover` | `capture_cover` |  |
| `_dark_half_below` | `_dark_half_below` |  |

### `arxiv_figures`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `is_annotation` | `is_annotation` |  |
| `is_body_article` | `is_body_article` |  |
| `_hand` | `_hand` |  |
| `_merge` | `_merge` |  |
| `_anti_landscape` | `_anti_landscape` |  |
| `annotation_enough_line` | `annotation_enough_line` |  |
| `_drop_run_mark` | `_drop_run_mark` |  |
| `_graphic_within_long` | `_graphic_within_long` |  |
| `region_figure` | `region_figure` |  |
| `pdf_of_link` | `pdf_of_link` |  |
| `_graphic_page` | `_graphic_page` |  |
| `_no_page_full` | `_no_page_full` |  |
| `extract` | `extract` |  |
| `download_pdf` | `download_pdf` |  |
| `candidate` | `candidate` |  |

### `audit_cron`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_epoch` | `_epoch` |  |
| `_hours` | `_hours` |  |
| `_age` | `_age` |  |
| `format_cron` | `format_cron` |  |
| `audit_format` | `audit_format` |  |
| `audit` | `audit` |  |
| `lock_still_for` | `lock_still_for` |  |
| `read_mark` | `read_mark` |  |
| `use_story` | `use_story` |  |

### `blackboard`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_meta_path` | `_meta_path` |  |
| `_meta` | `_meta` |  |
| `_write_meta` | `_write_meta` |  |
| `_standard_home` | `_standard_home` |  |
| `_kb` | `_kb` |  |
| `root_of` | `root_of` |  |
| `create_root` | `create_root` |  |
| `write` | `write` |  |
| `write_background` | `write_background` |  |
| `read` | `read` |  |
| `_value` | `_value` |  |

### `bob_submit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `handle_channel` | `handle_channel` |  |
| `board_mood` | `board_mood` |  |
| `mood_from_vision` | `mood_from_vision` |  |
| `is_url` | `is_url` |  |
| `take_image` | `take_image` |  |
| `line_frame` | `line_frame` |  |
| `_env_clean` | `_env_clean` |  |
| `send` | `send` |  |

### `brief_common`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `mark` | `mark` |  |
| `block_redo` | `block_redo` |  |
| `block_material` | `block_material` |  |
| `below` | `below` |  |

### `browser_session`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `got_block` | `got_block` |  |
| `BrowserSession` | `BrowserSession` |  |
| `browser` | `browser` |  |
| `trang` | `page` |  |
| `dong` | `line` | ⚠️ dong |
| `session_or_new` | `session_or_new` |  |

### `cape_prepare`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `slug` | `slug` |  |
| `workdir` | `workdir` |  |
| `extract` | `extract` |  |
| `write_brief` | `write_brief` |  |

### `cape_submit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|

### `caption_check`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `billion_odd_mark` | `billion_odd_mark` |  |
| `_drop_card` | `_drop_card` |  |
| `_words` | `_words` |  |
| `repeat_phrase` | `repeat_phrase` |  |
| `count_within` | `count_within` |  |
| `count_is` | `count_is` |  |
| `_check_measure_long` | `_check_measure_long` |  |
| `_check_still_room` | `_check_still_room` |  |
| `_check_figures` | `_check_figures` |  |
| `check` | `check` |  |

### `capture_chart`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_block_empty` | `_block_empty` |  |
| `frame_can` | `frame_can` |  |
| `_is_image` | `_is_image` |  |
| `download_image` | `download_image` |  |
| `capture` | `capture` |  |

### `capture_page`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `capture` | `capture` |  |
| `_out_rgb` | `_out_rgb` |  |
| `_variable_text_card_x` | `_variable_text_card_x` |  |
| `count_background` | `count_background` |  |
| `capture_lead_mobile` | `capture_lead_mobile` |  |

### `card`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `set_brand` | `set_brand` |  |
| `_f` | `_f` |  |
| `_measure_bright` | `_measure_bright` |  |
| `_enough_bright` | `_enough_bright` |  |
| `_enough_dark` | `_enough_dark` |  |
| `_color_of_rank` | `_color_of_rank` |  |
| `_extract_label` | `_extract_label` |  |
| `_color_rank_within` | `_color_rank_within` |  |
| `_empty_line` | `_empty_line` |  |
| `_about_line` | `_about_line` |  |
| `_empty_tracked` | `_empty_tracked` |  |
| `_about_tracked` | `_about_tracked` |  |
| `_wrap` | `_wrap` |  |
| `_fit_text` | `_fit_text` |  |
| `_grow_title` | `_grow_title` |  |
| `_step_line` | `_step_line` |  |
| `stack_read` | `stack_read` |  |
| `_block_standard_image` | `_block_standard_image` |  |
| `_block_chart` | `_block_chart` |  |
| `_block_crop` | `_block_crop` |  |
| `_open_image` | `_open_image` |  |
| `_fit_cover` | `_fit_cover` |  |
| `_range` | `_range` |  |
| `_layer_image` | `_layer_image` |  |
| `_capability_flow_rank` | `_capability_flow_rank` |  |
| `_timestamp_background_solid` | `_timestamp_background_solid` |  |
| `_text_bg_strict` | `_text_bg_strict` |  |
| `_open_region_text` | `_open_region_text` |  |
| `_within_card` | `_within_card` |  |
| `_bright_region` | `_bright_region` |  |
| `_can_board_line` | `_can_board_line` |  |
| `_color_change_background_hide_whole` | `_color_change_background_hide_whole` |  |
| `_quote_mark` | `_quote_mark` |  |
| `_quote_frame` | `_quote_frame` |  |
| `_render_quote` | `_render_quote` |  |
| `_chip_neo` | `_chip_neo` |  |
| `_phase` | `_phase` |  |
| `build` | `build` |  |
| `_render_ceiling` | `_render_ceiling` |  |
| `_cao_tieu_de` | `_height_title` |  |
| `_cao_dau` | `_height_mark` | ⚠️ dau |
| `_box_min` | `_box_min` |  |
| `_x_chu` | `_x_text` | ⚠️ chu |

### `carousel`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `set_background` | `set_background` |  |
| `_line_h` | `_line_h` |  |
| `_fit_block` | `_fit_block` |  |
| `_draw_paragraphs` | `_draw_paragraphs` |  |
| `_cyan` | `_cyan` |  |
| `_net` | `_net` |  |
| `_color_mark` | `_color_mark` |  |
| `_chip_neo` | `_chip_neo` |  |
| `_watermark` | `_watermark` |  |
| `_open` | `_open` |  |
| `_stack_if_can` | `_stack_if_can` |  |
| `_ramp_mask` | `_ramp_mask` |  |
| `_measure_region_text` | `_measure_region_text` |  |
| `_background_solid_below_text` | `_background_solid_below_text` |  |
| `_layer_if_can` | `_layer_if_can` |  |
| `_body_image` | `_body_image` |  |
| `build_body` | `build_body` |  |
| `build_body_quote` | `build_body_quote` |  |
| `build_cover` | `build_cover` |  |
| `_is_flagship` | `_is_flagship` |  |
| `_gate_text` | `_gate_text` |  |
| `_gate_image` | `_gate_image` |  |
| `gom` | `gather` |  |
| `_gate_overflow` | `_gate_overflow` |  |

### `chat_router`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `chat_hint` | `chat_hint` |  |
| `route` | `route` |  |
| `_drop_line_junk` | `_drop_line_junk` |  |
| `use_argv` | `use_argv` |  |
| `ask` | `ask` |  |
| `clean` | `clean` |  |

### `check_env`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `check_cv2` | `check_cv2` |  |
| `check_yunet` | `check_yunet` |  |
| `check_chromium` | `check_chromium` |  |
| `check_variable_environment` | `check_variable_environment` |  |
| `check_openai_key` | `check_openai_key` |  |
| `check_telegram_token` | `check_telegram_token` |  |

### `check_hermes`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_home_kanban` | `_home_kanban` |  |
| `_check_board` | `_check_board` |  |
| `check_column` | `check_column` |  |
| `check_has_chat` | `check_has_chat` |  |
| `check_swarm` | `check_swarm` |  |

### `cleanup`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `get_state_dir` | `get_state_dir` |  |
| `cleanup_old_candidates` | `cleanup_old_candidates` |  |
| `trim_jsonl` | `trim_jsonl` |  |
| `cleanup_append_only_logs` | `cleanup_append_only_logs` |  |
| `cleanup_old_manifests` | `cleanup_old_manifests` |  |

### `cost_squeeze`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `reasoning_of_role` | `reasoning_of_role` |  |
| `soul` | `soul` |  |
| `job_teaser` | `job_teaser` |  |
| `job_writer` | `job_writer` |  |
| `nhac` | `mention` |  |
| `shorten_text` | `shorten_text` |  |
| `run` | `run` |  |

### `crop_ratio`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `crop` | `crop` |  |

### `deck`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_grow` | `_grow` |  |
| `_draw_lines` | `_draw_lines` |  |
| `_line_h` | `_line_h` |  |
| `_badge` | `_badge` |  |
| `_two_tone_title` | `_two_tone_title` |  |
| `_open_bg` | `_open_bg` |  |
| `take_statement` | `take_statement` |  |
| `take_list_steps` | `take_list_steps` |  |
| `take_checklist` | `take_checklist` |  |
| `take_grid3` | `take_grid3` |  |
| `take_cover` | `take_cover` |  |
| `_fit_size` | `_fit_size` |  |
| `_footer_burst` | `_footer_burst` |  |
| `_footer_two` | `_footer_two` |  |
| `_burst` | `_burst` |  |
| `_gate` | `_gate` |  |

### `draft_write`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|

### `dre_prepare`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `write_brief` | `write_brief` |  |

### `dre_submit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `Context` | `Context` |  |
| `nhan_ma` | `mark_code` |  |
| `kiem_lien_quan` | `check_relevant` |  |
| `kiem_mat` | `check_faces` |  |
| `_resolve_stack` | `_resolve_stack` |  |
| `_resolve_single` | `_resolve_single` |  |
| `_resolve_item` | `_resolve_item` |  |
| `resolve_spec` | `resolve_spec` |  |
| `single_slide_old` | `single_slide_old` |  |
| `use` | `use` |  |
| `handoff` | `handoff` |  |

### `emoji_deck`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_load` | `_load` |  |
| `_save` | `_save` |  |
| `next_emoji` | `next_emoji` |  |

### `entity_images`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `entity_within_title` | `entity_within_title` |  |
| `pageimages` | `pageimages` |  |
| `commons_by_phrase` | `commons_by_phrase` |  |
| `entity_images` | `entity_images` |  |
| `label_entity` | `label_entity` |  |

### `env_load`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `hermes_home` | `hermes_home` |  |
| `hermes_homes` | `hermes_homes` |  |
| `topics` | `topics` |  |
| `_brand` | `_brand` |  |
| `brand_long` | `brand_long` |  |
| `quantity` | `quantity` |  |
| `handle_channel` | `handle_channel` |  |
| `_file_env` | `_file_env` |  |
| `state_dir` | `state_dir` |  |
| `topics_path` | `topics_path` |  |
| `load` | `load` |  |
| `album_secondary` | `album_secondary` |  |
| `so` | `count` | ⚠️ so |
| `required` | `required` |  |
| `write_json` | `write_json` |  |

### `ethan_prepare`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `label_ethan` | `label_ethan` |  |
| `stackable_pairs_hero` | `stackable_pairs_hero` |  |
| `write_brief` | `write_brief` |  |

### `ethan_submit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_check_stack` | `_check_stack` |  |
| `_check_text` | `_check_text` |  |
| `resolve_spec` | `resolve_spec` |  |

### `find_image_web`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_use_ok` | `_use_ok` |  |
| `bing_murl` | `bing_murl` |  |
| `yandex_img_url` | `yandex_img_url` |  |
| `filter` | `filter` |  |
| `_bing` | `_bing` |  |
| `_yandex` | `_yandex` |  |
| `find_image_web` | `find_image_web` |  |

### `find_more_images`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `read_count_turn` | `read_count_turn` |  |
| `check_keyword` | `check_keyword` |  |
| `candidate_commons` | `candidate_commons` |  |
| `try_small_commons` | `try_small_commons` |  |
| `filter_openverse` | `filter_openverse` |  |
| `candidate_openverse` | `candidate_openverse` |  |
| `candidate_from_url` | `candidate_from_url` |  |
| `candidate_keyword` | `candidate_keyword` |  |
| `say_image_new` | `say_image_new` |  |
| `fresh_manifest` | `fresh_manifest` |  |
| `in_result` | `in_result` | ⚠️ in |

### `gin_prepare`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_download_link` | `_download_link` |  |
| `find_image` | `find_image` |  |
| `workdir` | `workdir` |  |
| `_extract_text` | `_extract_text` |  |
| `color_text` | `color_text` |  |
| `distinctive_text` | `distinctive_text` |  |
| `measure_background` | `measure_background` |  |
| `ocr_region` | `ocr_region` |  |
| `_read_can_odd` | `_read_can_odd` |  |
| `about_preview` | `about_preview` |  |
| `write_brief` | `write_brief` |  |

### `gin_submit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `single` | `single` |  |
| `_no_box` | `_no_box` |  |
| `_box_translate` | `_box_translate` |  |
| `make_card` | `make_card` |  |

### `hermes_adapter`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `kanban_db` | `kanban_db` |  |
| `has_kanban` | `has_kanban` |  |
| `_open` | `_open` |  |
| `_ask` | `_ask` |  |
| `state_db_each_profile` | `state_db_each_profile` |  |
| `use_by_model` | `use_by_model` |  |
| `summary_session` | `summary_session` |  |
| `create_task` | `create_task` |  |
| `job` | `job` |  |
| `one_job` | `one_job` |  |
| `status` | `status` |  |
| `count_form_run` | `count_form_run` |  |
| `writer_queue` | `writer_queue` |  |
| `last_run` | `last_run` |  |
| `_standard_ify_run` | `_standard_ify_run` |  |
| `run_start` | `run_start` |  |
| `heartbeat` | `heartbeat` |  |
| `pid_alive` | `pid_alive` |  |
| `worker_run_state` | `worker_run_state` |  |
| `count_done_by_role` | `count_done_by_role` |  |
| `last_run_many` | `last_run_many` |  |

### `image_brand`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_from_distinctive` | `_from_distinctive` |  |
| `_has_phrase` | `_has_phrase` |  |
| `_has_word` | `_has_word` |  |
| `_many` | `_many` |  |
| `vendors_in_story` | `vendors_in_story` | ⚠️ in |
| `query` | `query` |  |
| `filter_commons` | `filter_commons` |  |
| `_ask_api` | `_ask_api` |  |
| `_file_claim` | `_file_claim` |  |
| `_qid_claim` | `_qid_claim` |  |
| `qid_rank` | `qid_rank` |  |
| `material_wikidata` | `material_wikidata` |  |
| `_slug` | `_slug` |  |
| `_lock_model` | `_lock_model` |  |
| `vendor_website` | `vendor_website` |  |
| `_download_html` | `_download_html` |  |
| `announcement_page` | `announcement_page` |  |
| `commons_urls` | `commons_urls` |  |
| `card_logo` | `card_logo` |  |
| `_measure_bright_logo` | `_measure_bright_logo` |  |
| `image_wikidata` | `image_wikidata` |  |
| `_candidate` | `_candidate` |  |
| `image_person_landscape` | `image_person_landscape` |  |
| `image_has_ballot` | `image_has_ballot` |  |
| `vendor_images` | `vendor_images` |  |
| `rank_has_model` | `rank_has_model` |  |
| `sentence_ask_vision` | `sentence_ask_vision` |  |
| `_ask_commons` | `_ask_commons` |  |
| `label_by_type` | `label_by_type` |  |
| `label_brand` | `label_brand` |  |

### `image_concept`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_country_within` | `_country_within` |  |
| `keyword_heuristic` | `keyword_heuristic` |  |
| `keyword_llm` | `keyword_llm` |  |
| `read_return_error_llm` | `read_return_error_llm` |  |
| `keyword_concept` | `keyword_concept` |  |
| `_from_distinctive` | `_from_distinctive` |  |
| `filter_commons` | `filter_commons` |  |
| `image_concept` | `image_concept` |  |
| `sentence_ask_vision` | `sentence_ask_vision` |  |
| `label_concept` | `label_concept` |  |

### `image_frame`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_make_full` | `_make_full` |  |
| `_color` | `_color` |  |
| `_font` | `_font` |  |
| `avatar_wait_emoji` | `avatar_wait_emoji` |  |
| `_about_rgb` | `_about_rgb` |  |
| `line_frame` | `line_frame` |  |
| `_text_space` | `_text_space` |  |

### `image_prepare`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `prepare_article` | `prepare_article` |  |
| `workdir` | `workdir` |  |
| `load_meta` | `load_meta` |  |
| `_wait_for_slot` | `_wait_for_slot` |  |
| `_description_missing_image` | `_description_missing_image` |  |
| `_handle_lock` | `_handle_lock` |  |
| `count_crashes` | `count_crashes` |  |
| `_report_crash_loop` | `_report_crash_loop` |  |
| `run` | `run` |  |

### `image_provenance`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `stamp_provenance` | `stamp_provenance` |  |
| `stamp_file` | `stamp_file` |  |
| `_text` | `_text` |  |
| `read_crop_trace` | `read_crop_trace` |  |
| `allows_landscape_crop` | `allows_landscape_crop` |  |
| `is_ranking_image` | `is_ranking_image` |  |
| `is_stacked_composite` | `is_stacked_composite` |  |
| `_used_images_log` | `_used_images_log` |  |
| `story_key` | `story_key` |  |
| `remove_used_for_draft` | `remove_used_for_draft` |  |

### `image_rules_dre`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `ratio_after_stack` | `ratio_after_stack` |  |
| `stack_fit_frame` | `stack_fit_frame` |  |
| `stack_crop_note` | `stack_crop_?note` |  |
| `_is_title_case_headline` | `_is_title_?case_headline` |  |
| `subject_names` | `subject_names` |  |
| `subject_evidence` | `subject_evidence` |  |
| `measure_chart_signal` | `measure_chart_signal` |  |
| `is_chart` | `is_chart` |  |
| `_js_regex_literal` | `_js_regex_literal` |  |
| `js_junk_url_pattern` | `js_junk_url_pattern` |  |
| `js_junk_dom_pattern` | `js_junk_dom_pattern` |  |
| `dhash` | `dhash` |  |
| `is_near_duplicate` | `is_near_duplicate` |  |
| `_file_md5` | `_file_md5` |  |
| `dhash_threshold_for` | `dhash_threshold_for` |  |
| `record_used` | `record_used` |  |
| `check_not_reused` | `check_not_reused` |  |
| `tone_mismatch` | `tone_mismatch` |  |
| `_load_yunet` | `_load_yunet` |  |
| `count_faces` | `count_faces` |  |
| `is_blank_image` | `is_blank_image` |  |
| `check_blank_image` | `check_blank_image` |  |
| `check_chart_integrity` | `check_chart_integrity` |  |
| `check_chart_standalone` | `check_chart_standalone` |  |
| `check_aspect_ratio` | `check_aspect_ratio` |  |
| `check_crop_landscape` | `check_crop_landscape` |  |
| `check_resolution` | `check_resolution` |  |
| `check_unnamed_face` | `check_unnamed_face` |  |
| `check_duplicate` | `check_duplicate` |  |

### `image_rules_ethan`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `ratio_after_stack` | `ratio_after_stack` |  |
| `stack_fit_frame` | `stack_fit_frame` |  |
| `measure_chart_signal` | `measure_chart_signal` |  |
| `is_chart` | `is_chart` |  |
| `_js_regex_literal` | `_js_regex_literal` |  |
| `js_junk_url_pattern` | `js_junk_url_pattern` |  |
| `js_junk_dom_pattern` | `js_junk_dom_pattern` |  |
| `dhash` | `dhash` |  |
| `is_near_duplicate` | `is_near_duplicate` |  |
| `_file_md5` | `_file_md5` |  |
| `dhash_threshold_for` | `dhash_threshold_for` |  |
| `record_used` | `record_used` |  |
| `check_not_reused` | `check_not_reused` |  |
| `tone_mismatch` | `tone_mismatch` |  |
| `_load_yunet` | `_load_yunet` |  |
| `count_faces` | `count_faces` |  |
| `is_blank_image` | `is_blank_image` |  |
| `check_blank_image` | `check_blank_image` |  |
| `check_chart_integrity` | `check_chart_integrity` |  |
| `check_chart_standalone` | `check_chart_standalone` |  |
| `check_aspect_ratio` | `check_aspect_ratio` |  |
| `check_crop_landscape` | `check_crop_landscape` |  |
| `check_resolution` | `check_resolution` |  |
| `check_unnamed_face` | `check_unnamed_face` |  |
| `check_duplicate` | `check_duplicate` |  |

### `image_rules_kite`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `ratio_after_stack` | `ratio_after_stack` |  |
| `stack_fit_frame` | `stack_fit_frame` |  |
| `measure_chart_signal` | `measure_chart_signal` |  |
| `is_chart` | `is_chart` |  |
| `_js_regex_literal` | `_js_regex_literal` |  |
| `js_junk_url_pattern` | `js_junk_url_pattern` |  |
| `js_junk_dom_pattern` | `js_junk_dom_pattern` |  |
| `dhash` | `dhash` |  |
| `is_near_duplicate` | `is_near_duplicate` |  |
| `_file_md5` | `_file_md5` |  |
| `dhash_threshold_for` | `dhash_threshold_for` |  |
| `record_used` | `record_used` |  |
| `check_not_reused` | `check_not_reused` |  |
| `tone_mismatch` | `tone_mismatch` |  |
| `_load_yunet` | `_load_yunet` |  |
| `count_faces` | `count_faces` |  |
| `is_blank_image` | `is_blank_image` |  |
| `check_blank_image` | `check_blank_image` |  |
| `check_chart_integrity` | `check_chart_integrity` |  |
| `check_chart_standalone` | `check_chart_standalone` |  |
| `check_aspect_ratio` | `check_aspect_ratio` |  |
| `check_crop_landscape` | `check_crop_landscape` |  |
| `check_resolution` | `check_resolution` |  |
| `check_unnamed_face` | `check_unnamed_face` |  |
| `check_duplicate` | `check_duplicate` |  |

### `itachi_prepare`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `prepare_slide` | `prepare_slide` |  |
| `call_y_way` | `call_y_way` |  |
| `write_brief` | `write_brief` |  |

### `itachi_submit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_color_hide_whole` | `_color_hide_whole` |  |
| `about_download_wait` | `about_download_wait` |  |

### `journal`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_hours_vn` | `_hours_vn` |  |
| `_within_date` | `_within_date` |  |
| `_open` | `_open` |  |
| `_bear_error_db` | `_bear_error_db` |  |
| `bao` | `report` |  |
| `trong` | `within` |  |
| `_gather_by_job` | `_gather_by_job` |  |
| `part_cron` | `part_cron` |  |
| `part_kanban` | `part_kanban` |  |
| `part_finn` | `part_finn` |  |
| `_diem` | `_score` |  |
| `part_draft` | `part_draft` |  |
| `part_git` | `part_git` |  |
| `part_model` | `part_model` |  |
| `extra_notes` | `extra_notes` |  |
| `read_notes` | `read_notes` |  |
| `use_page` | `use_page` |  |

### `journal_web`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_page` | `_page` |  |
| `_bold` | `_bold` |  |
| `md_bright_html` | `md_bright_html` |  |
| `xa_bang` | `off_board` |  |
| `page_date` | `page_date` |  |
| `page_list_clean` | `page_list_clean` |  |
| `bai` | `article` |  |
| `Handler` | `Handler` |  |
| `log_message` | `log_message` |  |
| `_tra` | `_return` | ⚠️ tra |
| `do_GET` | `measure_get` |  |

### `kite_prepare`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `handle_channel` | `handle_channel` |  |
| `transfer_from_role` | `transfer_from_role` |  |
| `figure_real` | `figure_real` |  |
| `figure_open_mark` | `figure_open_mark` |  |
| `figure_hero` | `figure_hero` |  |
| `_hero_what_is` | `_hero_what_is` |  |
| `line_hero` | `line_hero` |  |
| `_force_raw` | `_force_raw` |  |
| `figure_right_use` | `figure_right_use` |  |
| `ensure_has_cover` | `ensure_has_cover` |  |
| `call_y_tone` | `call_y_tone` |  |
| `write_brief` | `write_brief` |  |

### `kite_submit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_check_figure_slide` | `_check_figure_slide` |  |
| `_resolve_slide` | `_resolve_slide` |  |
| `resolve_spec` | `resolve_spec` |  |

### `manifest_build`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_score` | `_score` |  |
| `_item_from_pick` | `_item_from_pick` |  |
| `gather_item` | `gather_item` |  |
| `crop_ceiling` | `crop_ceiling` |  |
| `extra_required` | `extra_required` |  |

### `manifest_common`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `pick_by_k` | `pick_by_k` |  |
| `single_summary` | `single_summary` |  |
| `list_count` | `list_count` |  |
| `path_out_new` | `path_out_new` |  |
| `write_manifest` | `write_manifest` |  |
| `finalize_required` | `finalize_required` |  |
| `write_report` | `write_report` |  |

### `manifest_report`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `use` | `use` |  |

### `manifest_write`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_count_report` | `_count_report` |  |
| `_item_from_submit` | `_item_from_submit` |  |
| `extra_required` | `extra_required` |  |

### `material`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `extract` | `extract` |  |
| `sentence_has_count` | `sentence_has_count` |  |
| `gather` | `gather` |  |
| `use_page` | `use_page` |  |

### `miles_prepare`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `write_brief` | `write_brief` |  |

### `miles_submit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `standard_ify` | `standard_ify` |  |

### `moat_publish`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `load_secrets` | `load_secrets` |  |
| `_wait_within` | `_wait_within` |  |
| `name_lock` | `name_lock` |  |
| `brand_container` | `brand_container` |  |
| `base_url` | `base_url` |  |
| `config` | `config` |  |
| `draft_path` | `draft_path` |  |
| `read_draft` | `read_draft` |  |
| `_write_json` | `_write_json` |  |
| `write_draft` | `write_draft` |  |
| `pure_text` | `pure_text` |  |
| `_background` | `_background` |  |
| `images_payload` | `images_payload` |  |
| `_body_intake` | `_body_intake` |  |
| `intake` | `intake` |  |
| `_read_queue` | `_read_queue` |  |
| `_write_queue` | `_write_queue` |  |
| `_form_try_again` | `_form_try_again` |  |
| `_list_mark_form_bottom` | `_list_mark_form_bottom` |  |
| `refill` | `refill` |  |
| `_drop_block_queue` | `_drop_block_queue` |  |
| `bottom_again` | `bottom_again` |  |
| `_fetch_status` | `_fetch_status` |  |
| `_poll_one_article` | `_poll_one_article` |  |
| `poll` | `poll` |  |
| `_exit` | `_exit` |  |
| `_tele` | `_tele` |  |
| `report_card` | `report_card` |  |
| `_notify` | `_notify` |  |

### `model_audition`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `call` | `call` |  |

### `model_boards`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `Board` | `Board` |  |
| `rank_and_date` | `rank_and_date` |  |

### `model_watch`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `models_in_use` | `models_in_use` |  |
| `probe` | `probe` |  |

### `monitor_9router`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_of_count_utc` | `_of_count_utc` |  |
| `_hours_vn` | `_hours_vn` |  |
| `_seconds` | `_seconds` |  |
| `_hhmm` | `_hhmm` |  |
| `_name_board` | `_name_board` |  |
| `_each_name` | `_each_name` |  |
| `string_already_config` | `string_already_config` |  |
| `cap_fallback` | `cap_fallback` | ⚠️ cap |
| `inspect_model` | `inspect_model` |  |
| `aggregate` | `aggregate` |  |
| `moi` | `new` | ⚠️ moi |
| `pct` | `pct` |  |
| `gon` | `compact` |  |
| `read_date` | `read_date` |  |
| `error_connection` | `error_connection` |  |
| `_standard_model` | `_standard_model` |  |
| `_single_fake` | `_single_fake` |  |
| `gather_role` | `gather_role` |  |
| `gia_cua` | `fake_of` | ⚠️ gia |
| `write_md` | `write_md` |  |
| `still_for` | `still_for` |  |
| `summary_tele` | `summary_tele` |  |
| `use` | `use` |  |
| `download` | `download` |  |

### `prepare.browser`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_js_browser` | `_js_browser` |  |
| `_take_image_page` | `_take_image_page` |  |
| `_open_page` | `_open_page` |  |
| `_find_report_gnews` | `_find_report_gnews` |  |
| `browser_pass` | `browser_pass` |  |
| `het_gio` | `all_done_hours` |  |

### `prepare.common`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_hdr` | `_hdr` |  |
| `_brand_of` | `_brand_of` |  |
| `_domain` | `_domain` |  |
| `_read_json` | `_read_json` |  |
| `_write_json` | `_write_json` |  |
| `_original_domain` | `_original_domain` |  |

### `prepare.download_filter`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_download_bytes` | `_download_bytes` |  |
| `_host_is_side_try_three` | `_host_is_side_try_three` |  |
| `_download_candidate` | `_download_candidate` |  |
| `download_and_filter` | `download_and_filter` |  |
| `_chart_by_figure` | `_chart_by_figure` |  |
| `_save_crop` | `_save_crop` |  |

### `prepare.fallback_rounds`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_supplement_source` | `_supplement_source` |  |
| `_extra_announcement_page` | `_extra_announcement_page` |  |
| `_take_from_browser` | `_take_from_browser` |  |
| `_capture_ranking` | `_capture_ranking` |  |
| `_image_item_ranking` | `_image_item_ranking` |  |
| `_gather_and_download_image` | `_gather_and_download_image` |  |
| `_round_widen_search` | `_round_widen_search` |  |
| `_ranking_context_edge` | `_ranking_context_edge` |  |
| `_report_brand_empty` | `_report_brand_empty` |  |
| `_round_brand` | `_round_brand` |  |
| `_round_capture_source` | `_round_capture_source` |  |
| `_ra` | `_out` |  |
| `capability_block_headline` | `capability_block_headline` |  |
| `_round_concept` | `_round_concept` |  |
| `_round_entity` | `_round_entity` |  |

### `prepare.manifest`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `describe_ranking_image` | `describe_ranking_image` |  |
| `ranking_brief_line` | `ranking_brief_line` |  |
| `pair_two_vendor_images` | `pair_two_vendor_images` |  |
| `stackable_pairs` | `stackable_pairs` |  |
| `contact_sheet` | `contact_sheet` |  |
| `gather_material` | `gather_material` |  |
| `_article_material` | `_article_material` |  |
| `compute_derived` | `compute_derived` |  |
| `build_manifest` | `build_manifest` |  |

### `prepare.source`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_summary_from_img_json` | `_summary_from_img_json` |  |
| `load_source` | `load_source` |  |
| `_title_page` | `_title_page` |  |
| `candidate_social` | `candidate_social` |  |
| `candidate_static` | `candidate_static` |  |
| `commons_images` | `commons_images` |  |
| `all_proper_nouns` | `all_proper_?nouns` |  |
| `_leading_proper_noun` | `_leading_proper_noun` |  |

### `prepare.vision`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `description_image` | `description_image` |  |
| `_mot_lan` | `_one_attempt` | ⚠️ lan |
| `_call_router` | `_call_router` |  |
| `_classify_hide_whole` | `_classify_hide_whole` |  |
| `classify` | `classify` |  |
| `_seen_image` | `_seen_image` |  |

### `press_entity_images`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `link_real` | `link_real` |  |
| `filter_article` | `filter_article` |  |
| `_rss` | `_rss` |  |
| `report_about` | `report_about` |  |
| `og_from_html` | `og_from_html` |  |
| `_og` | `_og` |  |
| `press_entity_images` | `press_entity_images` |  |

### `publish`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `load_secrets` | `load_secrets` |  |
| `single_pretty` | `single_pretty` |  |
| `_bo` | `_drop` | ⚠️ bo |
| `TelegramReject` | `TelegramReject` |  |
| `_check` | `_check` |  |
| `send_text_fragments` | `send_text_fragments` |  |
| `send_text` | `send_text` |  |
| `send_photo` | `send_photo` |  |
| `send_document` | `send_document` |  |
| `send_media_group` | `send_media_group` |  |
| `send_topic_with_keyboard` | `send_topic_with_keyboard` |  |
| `send_topic` | `send_topic` |  |
| `_main` | `_main` |  |

### `ranking`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `is_capture` | `is_capture` |  |
| `is_ranking_story` | `is_ranking_story` |  |
| `extract_model` | `extract_model` |  |
| `extract_rank` | `extract_rank` |  |
| `suggest_sources` | `suggest_sources` |  |
| `_change_board` | `_change_board` |  |
| `_hand` | `_hand` |  |
| `_capture` | `_capture` |  |
| `_highlight` | `_highlight` |  |
| `_of_count` | `_of_count` |  |
| `_capture_one_board` | `_capture_one_board` |  |
| `capture_board` | `capture_board` |  |
| `_capture_one_column` | `_capture_one_column` |  |
| `capture_list_clean` | `capture_list_clean` |  |
| `capture_svg` | `capture_svg` |  |
| `capture_logo` | `capture_logo` |  |
| `fallback_card` | `fallback_card` |  |
| `giua` | `middle` |  |
| `SessionCapture` | `SessionCapture` |  |
| `trang` | `page` |  |
| `thu` | `try` | ⚠️ thu |
| `_try_source` | `_try_source` |  |
| `find_and_capture` | `find_and_capture` |  |
| `_rank_of` | `_rank_of` |  |
| `source_proves_story` | `source_?proves_story` |  |
| `_sources_proving_story` | `_sources_?proving_story` |  |
| `_skip_source` | `_skip_source` |  |
| `find_and_capture_many` | `find_and_capture_many` |  |

### `render_edu`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_font_face_css` | `_font_face_css` |  |
| `_ff` | `_ff` |  |
| `base_css` | `base_css` |  |
| `rgba` | `rgba` |  |
| `hero_svg` | `hero_svg` |  |
| `_small` | `_small` |  |
| `_measure_image` | `_measure_image` |  |
| `_measure_image_real` | `_measure_image_real` |  |
| `_image_data_uri` | `_image_data_uri` |  |
| `lam` | `make` |  |
| `_bright` | `_bright` |  |
| `read_background` | `read_background` |  |
| `_read_background_real` | `_read_background_real` |  |
| `set_image` | `set_image` |  |
| `esc` | `esc` |  |
| `accent_html` | `accent_html` |  |
| `glow` | `glow` |  |
| `masthead` | `masthead` |  |
| `eyebrow` | `eyebrow` |  |
| `folio` | `folio` |  |
| `s_cover` | `s_cover` |  |
| `_cover_image` | `_cover_image` |  |
| `s_statement` | `s_statement` |  |
| `s_steps` | `s_steps` |  |
| `s_loop` | `s_loop` |  |
| `_color_dark` | `_color_dark` |  |
| `_css_mast_dark` | `_css_mast_dark` |  |
| `_css_text_dark_region` | `_css_text_dark_region` |  |
| `image_make_background` | `image_make_background` |  |
| `s_figure` | `s_figure` |  |
| `_count` | `_count` |  |
| `_value` | `_value` |  |
| `s_bars` | `s_bars` |  |
| `s_cta` | `s_cta` |  |
| `slide_read` | `slide_read` |  |
| `check_field` | `check_field` |  |
| `gate_slides` | `gate_slides` |  |
| `_gate_content` | `_gate_content` |  |
| `_texts` | `_texts` |  |
| `_journal_theme` | `_journal_theme` |  |
| `_theme_near_bottom` | `_theme_near_bottom` |  |
| `_write_theme` | `_write_theme` |  |
| `color_say_catch` | `color_say_catch` |  |
| `offset_hue` | `offset_hue` |  |
| `theme_near_color` | `theme_near_color` |  |
| `color_rank_within_spec` | `color_rank_within_spec` |  |
| `pick_theme_auto` | `pick_theme_auto` |  |
| `it_dung_nhat` | `least_used` |  |
| `_route_font` | `_route_font` |  |
| `_tra` | `_return` | ⚠️ tra |
| `_check_title_line` | `_check_title_line` |  |
| `_capture_each_slide` | `_capture_each_slide` |  |
| `render` | `render` |  |
| `dung_doc` | `use_read` | ⚠️ doc dung |

### `required`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `file` | `file` |  |
| `read` | `read` |  |
| `_write` | `_write` |  |
| `extra` | `extra` |  |
| `extra_many` | `extra_many` |  |
| `_standard` | `_standard` |  |
| `match` | `match` |  |
| `link_call_y` | `link_call_y` |  |
| `check` | `check` |  |
| `delete` | `delete` |  |
| `in_list_clean` | `in_list_clean` | ⚠️ in |

### `role`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `Role` | `Role` |  |
| `writers_for_brand` | `?writers_for_brand` |  |
| `pick_by_queue` | `pick_by_queue` |  |
| `writer_for` | `writer_for` |  |
| `display_name` | `display_name` |  |
| `rules_module` | `rules_?module` |  |
| `set_active_role` | `set_active_role` |  |
| `active_rules` | `active_rules` |  |
| `canonical_slug` | `canonical_slug` |  |
| `max_runtime_for` | `max_runtime_for` |  |
| `min_images` | `min_images` |  |
| `person_names_in_alt` | `person_names_in_alt` | ⚠️ in |
| `has_label_cover` | `has_label_cover` |  |
| `face_no_clear_ai` | `face_no_clear_ai` |  |
| `can_be_hero` | `can_be_hero` |  |
| `search_target_for` | `search_target_for` |  |
| `has_enough_material` | `has_enough_material` |  |
| `product_unit_for` | `product_unit_for` |  |
| `_build_go_map` | `_build_go_map` |  |

### `route_missing_images`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_time_send` | `_time_send` |  |
| `after_prepare` | `after_prepare` |  |
| `_hoi` | `_ask` |  |

### `scan_business`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `name_watchlist` | `name_watchlist` |  |
| `within_watchlist` | `within_watchlist` |  |
| `standard_ify` | `standard_ify` |  |
| `outlet` | `outlet` |  |
| `scan_gnews` | `scan_gnews` |  |
| `scan_report` | `scan_report` |  |
| `_keyword` | `_keyword` |  |
| `_amounts` | `_?amounts` |  |
| `_deal_keywords` | `_?deal_?keywords` |  |
| `_same_amount` | `_same_?amount` |  |
| `_is_follow_up` | `_is_?follow_?up` |  |
| `_capitalized` | `_?capitalized` |  |
| `gather_duplicate` | `gather_duplicate` |  |
| `is_deal_name` | `is_?deal_name` |  |
| `root` | `root` |  |
| `already_see` | `already_see` |  |
| `write_timestamp` | `write_timestamp` |  |

### `scan_common`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `host_say_drop` | `host_say_drop` |  |
| `check_url` | `check_url` |  |
| `url_hide_whole` | `url_hide_whole` |  |
| `standard_link` | `standard_link` |  |
| `ask_commons` | `ask_commons` |  |
| `get` | `get` |  |
| `timestamp_time` | `timestamp_time` |  |
| `from_distinctive` | `from_distinctive` |  |

### `scan_models`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `region_of` | `region_of` |  |
| `fetch_catalog` | `fetch_catalog` |  |
| `_arena_board` | `_arena_board` |  |
| `fetch_arena` | `fetch_arena` |  |
| `fetch_swebench` | `fetch_swebench` |  |
| `fetch_livebench` | `fetch_livebench` |  |
| `_original_by_name` | `_original_by_name` |  |
| `fetch_tbench` | `fetch_tbench` |  |
| `fetch_arcagi` | `fetch_arcagi` |  |
| `fetch_hle` | `fetch_hle` |  |
| `fetch_epoch` | `fetch_epoch` |  |
| `fetch_opencompass` | `fetch_opencompass` |  |
| `fetch_aa_media` | `fetch_aa_media` |  |
| `fetch_hf_trending` | `fetch_hf_trending` |  |
| `fetch_anthropic` | `fetch_anthropic` |  |
| `_rsc` | `_rsc` |  |
| `fetch_aa` | `fetch_aa` |  |
| `filter_aa` | `filter_aa` |  |
| `gon` | `compact` |  |
| `gon2` | `compact2` |  |
| `name_original` | `name_original` |  |
| `_board_original` | `_board_original` |  |
| `_make_full` | `_make_full` |  |
| `fetch_story_rank` | `fetch_story_rank` |  |
| `_t` | `_t` |  |
| `fetch_github` | `fetch_github` |  |
| `read_state` | `read_state` |  |
| `already_see` | `already_see` |  |
| `rank_old` | `rank_old` |  |
| `aa_already_report` | `aa_already_report` |  |
| `write_timestamp` | `write_timestamp` |  |
| `write_required` | `write_required` |  |
| `count_rank` | `count_rank` |  |
| `_try` | `_try` |  |
| `_in_board` | `_in_board` | ⚠️ in |
| `_in_report` | `_in_report` | ⚠️ in |

### `scan_prepare`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_crop` | `_crop` |  |
| `turn` | `turn` |  |
| `workdir` | `workdir` |  |
| `_new` | `_new` |  |
| `_run` | `_run` |  |
| `_required` | `_required` |  |
| `_supplement_required` | `_supplement_required` |  |
| `brief_scout` | `brief_scout` |  |
| `brief_nova` | `brief_nova` |  |
| `brief_market` | `brief_market` |  |
| `brief_qinn` | `brief_qinn` |  |

### `scan_sources`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `source_original` | `source_original` |  |
| `_is_ai_ish` | `_is_ai_ish` |  |
| `_age_hours` | `_age_hours` |  |
| `score_recency` | `score_recency` |  |
| `score_spread` | `score_spread` |  |
| `fetch_hn` | `fetch_hn` |  |
| `fetch_reddit` | `fetch_reddit` |  |
| `fetch_arxiv` | `fetch_arxiv` |  |
| `seen_keys` | `seen_keys` |  |
| `_image_of` | `_image_of` |  |
| `near_image` | `near_image` |  |

### `scan_submit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `error_block_send` | `error_block_send` |  |
| `path_manifest` | `path_manifest` |  |
| `pin_manifest` | `pin_manifest` |  |
| `filter_warning` | `filter_warning` |  |
| `_run` | `_run` |  |
| `_in_error` | `_in_error` | ⚠️ in |
| `send` | `send` |  |

### `scan_x`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `read_tweets` | `read_tweets` |  |
| `already_see` | `already_see` |  |
| `write_timestamp` | `write_timestamp` |  |
| `one_line` | `one_line` |  |
| `score_mechanical` | `score_mechanical` |  |
| `so` | `count` | ⚠️ so |
| `filter` | `filter` |  |
| `out_story` | `out_story` |  |

### `schema`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `Manifest` | `Manifest` |  |
| `Meta` | `Meta` |  |
| `SidecarImage` | `SidecarImage` |  |
| `SidecarWrite` | `SidecarWrite` |  |
| `LineImageUsed` | `LineImageUsed` |  |
| `_only_stack_ok` | `_only_stack_ok` |  |
| `_count_stackable_pairs_real` | `_count_stackable_pairs_real` |  |
| `_tot` | `_good` |  |
| `count_image_use_ok` | `count_image_use_ok` |  |
| `read_manifest` | `read_manifest` |  |
| `merge_meta` | `merge_meta` |  |
| `_kind` | `_kind` |  |

### `send_telegram`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `SendError` | `SendError` |  |
| `_topic` | `_topic` |  |
| `_md5` | `_md5` |  |
| `_telegram_post` | `_telegram_post` |  |
| `_write_journal` | `_write_journal` |  |
| `_mark_button_sent` | `_mark_button_?sent` |  |
| `_send_button` | `_send_button` |  |
| `_already_send_near_bottom` | `_already_send_near_bottom` |  |
| `_kb_approve` | `_kb_approve` |  |
| `post` | `post` |  |
| `near_bottom` | `near_bottom` |  |

### `skill_lesson_approve`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `verdict_path` | `?verdict_path` |  |
| `decide` | `decide` |  |
| `_drop_row` | `_drop_row` |  |
| `handle_button` | `handle_button` |  |

### `skill_lesson_commit`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `ApplyError` | `ApplyError` |  |
| `branch_name` | `branch_name` |  |
| `metadata_comment` | `?metadata_?comment` |  |
| `build_worktree` | `build_?worktree` |  |
| `remove_worktree` | `remove_?worktree` |  |
| `apply_lesson` | `apply_lesson` |  |
| `commit_lesson` | `commit_lesson` |  |
| `format_pr_body` | `format_?pr_body` |  |
| `default_open_pr` | `default_open_?pr` |  |
| `default_enable_auto_merge` | `default_?enable_auto_merge` |  |
| `default_pr_state` | `default_?pr_state` |  |
| `discard_pending` | `?discard_?pending` |  |
| `run` | `run` |  |

### `skill_lesson_filter`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `RepoIndex` | `RepoIndex` |  |
| `_read` | `_read` |  |
| `_defines` | `_?defines` |  |
| `has_identifier` | `has_?identifier` |  |
| `_suggest` | `_suggest` |  |
| `check_symbol` | `check_?symbol` |  |
| `commits_since` | `?commits_?since` |  |
| `extract_symbols` | `extract_?symbols` |  |
| `_line_diff` | `_line_diff` |  |
| `_paragraphs` | `_paragraphs` |  |
| `judge` | `?judge` |  |
| `flag` | `flag` |  |
| `collect_pending` | `?collect_?pending` |  |
| `find_task` | `find_task` |  |
| `keyboard_for` | `keyboard_for` |  |
| `format_message` | `format_message` |  |
| `run` | `run` |  |

### `social_post`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `is_social` | `is_social` |  |
| `title_from_text` | `title_from_text` |  |
| `read` | `read` |  |

### `story_type`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `standard_type` | `standard_type` |  |
| `order_image` | `order_image` |  |
| `late` | `late` |  |
| `score_by_type` | `score_by_type` |  |
| `country_of` | `country_of` |  |
| `code_has_ballot` | `code_has_ballot` |  |
| `line_brief` | `line_brief` |  |

### `submit_common`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `normalize` | `normalize` |  |
| `load_draft_context` | `load_draft_context` |  |
| `writer_for_article` | `writer_for_article` |  |
| `writer_persona_name` | `writer_persona_name` |  |
| `count_of_redo` | `count_of_redo` |  |
| `check_redo_reused` | `check_redo_reused` |  |
| `count_round_error` | `count_round_error` |  |
| `article_text_for` | `article_text_for` |  |
| `_strip_diacritics` | `_strip_diacritics` |  |
| `_words` | `_words` |  |
| `_name_in_article` | `_name_in_article` | ⚠️ in |
| `check_subject_named` | `check_subject_named` |  |
| `check_numbers_on_card` | `check_numbers_on_card` |  |
| `needs_ranking_image` | `needs_ranking_image` |  |
| `only_ranking_choice` | `only_ranking_?choice` |  |
| `irrelevant_images` | `irrelevant_images` |  |
| `check_not_reused_across_runs` | `check_not_reused_across_runs` |  |
| `_clean_use_alone` | `_clean_use_alone` |  |
| `check_image_fall` | `check_image_fall` |  |
| `check_quote_translated` | `check_quote_translated` |  |
| `check_no_repeat_image_redo` | `check_no_repeat_image_redo` |  |
| `check_guide_source_compact` | `check_guide_source_compact` |  |
| `check_rank_matches_image` | `check_rank_matches_image` |  |
| `_recently_posted` | `_recently_posted` |  |
| `send_album` | `send_album` |  |
| `_ghi_so` | `_write_count` | ⚠️ so |
| `write_blackboard` | `write_blackboard` |  |

### `swap_image_text`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_read_keep` | `_read_keep` |  |
| `_within_keep` | `_within_keep` |  |
| `find_region_text` | `find_region_text` |  |
| `use_mask` | `use_mask` |  |
| `_lama` | `_lama` |  |
| `_lama_run` | `_lama_run` |  |
| `inpaint` | `inpaint` |  |
| `delete_text` | `delete_text` |  |

### `sync_hermes`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_slug` | `_slug` |  |
| `plugin_home` | `plugin_home` |  |
| `_config_profile` | `_config_profile` |  |
| `_read_all` | `_read_all` |  |
| `_write_all` | `_write_all` |  |
| `sync_all_gate_old` | `sync_all_gate_old` |  |
| `cap_file` | `cap_file` | ⚠️ cap |
| `them_profile` | `extra_profile` |  |
| `_file_plugin` | `_file_plugin` |  |
| `missing_trace` | `missing_trace` |  |
| `two_home_offset` | `two_home_offset` |  |
| `hash_upstream` | `hash_upstream` |  |
| `read_upstream` | `read_upstream` |  |
| `write_upstream` | `write_upstream` |  |
| `check_upstream` | `check_upstream` |  |
| `kanban_already_catch` | `kanban_already_catch` |  |
| `mention_catch_plugin` | `mention_catch_plugin` |  |
| `mention_single_copy_item` | `mention_single_copy_item` |  |
| `read` | `read` |  |
| `standard` | `standard` |  |
| `_filter_secret` | `_filter_secret` |  |
| `_take` | `_take` |  |
| `capture_config` | `capture_config` |  |

### `task_bodies`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `end_role_image` | `end_role_image` |  |

### `teaser_assemble`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_drop_mark` | `_drop_mark` |  |
| `find_voice_wall_technique` | `find_voice_wall_technique` |  |
| `_item_no_ok_mention` | `_item_no_ok_mention` |  |
| `assemble` | `assemble` |  |

### `tele_util`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `drop_ansi` | `drop_ansi` |  |
| `_score_crop_hide_whole` | `_score_crop_hide_whole` |  |
| `split_message` | `split_message` |  |

### `text_bg`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `measure_bright_offset` | `measure_bright_offset` |  |
| `color_average` | `color_average` |  |
| `_luminance` | `_luminance` |  |
| `kenh` | `channel` |  |
| `_ratio_wall_part` | `_ratio_wall_part` |  |
| `threshold_wall_part` | `threshold_wall_part` |  |
| `ratio_wall_part` | `ratio_wall_part` |  |

### `vietnamese`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `drop_mark_forbid` | `drop_mark_forbid` |  |
| `find_face_mark` | `find_face_mark` |  |

### `worker_scope_sweep`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `kanban_homes` | `kanban_homes` |  |
| `list_scopes` | `list_?scopes` |  |
| `decide` | `decide` |  |
| `stop` | `?stop` |  |

### `write_log`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_block_create` | `_block_create` |  |
| `_block_create_real` | `_block_create_real` |  |
| `log` | `log` |  |
| `shorten` | `shorten` |  |
| `brand` | `brand` |  |

## D. Hằng số module

| Module | Hiện tại | Đề xuất | Cờ |
|---|---|---|---|
| `about_text` | `FONT` | `FONT` |  |
| `about_text` | `FONTS` | `FONTS` |  |
| `about_text` | `HAS_MEASURE` | `HAS_MEASURE` |  |
| `about_text` | `HAS_MIN` | `HAS_MIN` |  |
| `about_text` | `ROOT` | `ROOT` |  |
| `ada_prepare` | `DRAFTS` | `DRAFTS` |  |
| `ada_prepare` | `HERMES` | `HERMES` |  |
| `ada_prepare` | `ROOT` | `ROOT` |  |
| `ada_prepare` | `VN` | `VN` |  |
| `ada_submit` | `ROOT` | `ROOT` |  |
| `approve_base` | `API` | `API` |  |
| `approve_base` | `BOSS_IDS` | `BOSS_IDS` |  |
| `approve_base` | `BRAND` | `BRAND` |  |
| `approve_base` | `DRAFTS` | `DRAFTS` |  |
| `approve_base` | `HERMES_HOME` | `HERMES_HOME` |  |
| `approve_base` | `HERMES_PY` | `HERMES_PY` |  |
| `approve_base` | `OFFSET` | `OFFSET` |  |
| `approve_base` | `ROOT` | `ROOT` |  |
| `approve_base` | `STATE_DIR` | `STATE_DIR` |  |
| `approve_base` | `TELEGRAM_INCOMING` | `TELEGRAM_INCOMING` |  |
| `approve_base` | `UPLOAD_RETRY_DELAYS` | `?UPLOAD_RETRY_?DELAYS` |  |
| `approve_chat` | `ROLE_CHAT_MAKE_JOB` | `ROLE_CHAT_MAKE_JOB` |  |
| `approve_command` | `COMMAND_HELP` | `COMMAND_HELP` |  |
| `approve_command` | `SET_ARTICLE_COUNT` | `SET_ARTICLE_COUNT` |  |
| `approve_dispatch` | `AGAIN_REPORT_STALLED_MINUTES` | `AGAIN_REPORT_STALLED_MINUTES` |  |
| `approve_dispatch` | `ALREADY_REPORT_PROGRESS` | `ALREADY_REPORT_PROGRESS` |  |
| `approve_dispatch` | `ALREADY_REPORT_STALLED` | `ALREADY_REPORT_STALLED` |  |
| `approve_dispatch` | `BEAT_SILENT_MINUTES` | `BEAT_SILENT_MINUTES` |  |
| `approve_dispatch` | `BLACKBOARD_ASSIGNEE` | `BLACKBOARD_ASSIGNEE` |  |
| `approve_dispatch` | `BLACKBOARD_BRANDS` | `BLACKBOARD_BRANDS` |  |
| `approve_dispatch` | `BLACKBOARD_MENTION` | `BLACKBOARD_MENTION` |  |
| `approve_dispatch` | `DEFAULT_IMAGE` | `DEFAULT_IMAGE` |  |
| `approve_dispatch` | `DEFAULT_WRITE` | `DEFAULT_WRITE` |  |
| `approve_dispatch` | `LABEL_STANDARD` | `LABEL_STANDARD` |  |
| `approve_dispatch` | `NAME_BRIGHT_CAP` | `NAME_BRIGHT_CAP` | ⚠️ cap |
| `approve_dispatch` | `NAME_ROLE_IMAGE` | `NAME_ROLE_IMAGE` |  |
| `approve_dispatch` | `NAME_ROLE_WRITE` | `NAME_ROLE_WRITE` |  |
| `approve_dispatch` | `ROLE_CAROUSEL` | `ROLE_CAROUSEL` |  |
| `approve_dispatch` | `ROLE_EDU` | `ROLE_EDU` |  |
| `approve_dispatch` | `ROLE_IMAGE` | `ROLE_IMAGE` |  |
| `approve_dispatch` | `SLUG_OLD` | `SLUG_OLD` |  |
| `approve_dispatch` | `STORY_RESULT` | `STORY_RESULT` |  |
| `approve_dispatch` | `THRESHOLD_STALLED_MINUTES` | `THRESHOLD_STALLED_MINUTES` |  |
| `approve_pick` | `MANIFEST_BY_TOPIC` | `MANIFEST_BY_TOPIC` |  |
| `approve_post` | `ALBUM_SUFFIX_PATTERN` | `ALBUM_SUFFIX_PATTERN` |  |
| `approve_post` | `BACKGROUND_LAYER_BUTTON` | `BACKGROUND_LAYER_BUTTON` |  |
| `approve_post` | `CAPTION_LIMIT` | `CAPTION_LIMIT` |  |
| `approve_post` | `MARK_LEN_CHANNEL` | `MARK_LEN_CHANNEL` |  |
| `approve_post` | `PREVIEW_MAX_BYTES` | `PREVIEW_MAX_BYTES` |  |
| `approve_post` | `PREVIEW_MAX_DIM` | `PREVIEW_MAX_DIM` |  |
| `approve_post` | `REDO_LIMIT` | `REDO_LIMIT` |  |
| `approve_post` | `REDO_WAIT` | `REDO_WAIT` |  |
| `approve_post` | `REPLY_APPROVE_PATTERN` | `REPLY_APPROVE_PATTERN` |  |
| `approve_post` | `REPLY_QUEUE_PATTERN` | `REPLY_QUEUE_PATTERN` |  |
| `approve_post` | `UPLOAD_BASE_SECONDS` | `?UPLOAD_BASE_SECONDS` |  |
| `approve_post` | `UPLOAD_FLOOR_BYTES_PER_SEC` | `?UPLOAD_?FLOOR_BYTES_PER_SEC` |  |
| `approve_post` | `UPLOAD_WRITE_CEILING` | `?UPLOAD_WRITE_CEILING` |  |
| `approve_service` | `END_PUBLISHING_SECONDS` | `END_PUBLISHING_SECONDS` |  |
| `article_extract` | `SKIP_IMG_HINTS` | `SKIP_IMG_HINTS` |  |
| `article_extract` | `UA` | `UA` |  |
| `article_images` | `HAS_AI_GENERATE` | `HAS_AI_GENERATE` |  |
| `article_images` | `HDR` | `HDR` |  |
| `article_images` | `IMAGE_NEW_PAGE` | `IMAGE_NEW_PAGE` |  |
| `article_images` | `IS_STORY_MODEL` | `IS_STORY_MODEL` |  |
| `article_images` | `LONG_MAX` | `LONG_MAX` |  |
| `article_images` | `RULE` | `RULE` |  |
| `article_images` | `RULE_MODEL` | `RULE_MODEL` |  |
| `article_images` | `UA` | `UA` |  |
| `article_sources` | `BING_RSS` | `BING_RSS` |  |
| `article_sources` | `COUNT_SOURCE` | `COUNT_SOURCE` |  |
| `article_sources` | `DROP_DOMAIN` | `DROP_DOMAIN` |  |
| `article_sources` | `FROM_EMPTY` | `FROM_EMPTY` |  |
| `article_sources` | `FROM_EMPTY_QUERY` | `FROM_EMPTY_QUERY` |  |
| `article_sources` | `GNEWS` | `GNEWS` |  |
| `article_sources` | `GNEWS_ARTICLE` | `GNEWS_ARTICLE` |  |
| `article_sources` | `HDR` | `HDR` |  |
| `article_sources` | `RSS_GUESS` | `RSS_GUESS` |  |
| `article_sources` | `UA` | `UA` |  |
| `arxiv_cover` | `DARK` | `DARK` |  |
| `arxiv_cover` | `EMPTY` | `EMPTY` |  |
| `arxiv_cover` | `HEIGHT` | `HEIGHT` |  |
| `arxiv_cover` | `RATIO` | `RATIO` |  |
| `arxiv_cover` | `SOLID` | `SOLID` |  |
| `arxiv_cover` | `SOLID_FROM` | `SOLID_FROM` |  |
| `arxiv_cover` | `START_DARK` | `START_DARK` |  |
| `arxiv_cover` | `UA` | `UA` |  |
| `arxiv_figures` | `ANNOTATION` | `ANNOTATION` |  |
| `arxiv_figures` | `COUNT` | `COUNT` |  |
| `arxiv_figures` | `COUNT_PAGE` | `COUNT_PAGE` |  |
| `arxiv_figures` | `EMPTY_ITEM` | `EMPTY_ITEM` |  |
| `arxiv_figures` | `MAX` | `MAX` |  |
| `arxiv_figures` | `ODD_RUN_MARK` | `ODD_RUN_MARK` |  |
| `arxiv_figures` | `ODD_SAME` | `ODD_SAME` |  |
| `arxiv_figures` | `RATIO_MAX` | `RATIO_MAX` |  |
| `arxiv_figures` | `SHORT_SIDE_ITEM` | `SHORT_SIDE_ITEM` |  |
| `arxiv_figures` | `SLIT_TEXT` | `SLIT_TEXT` |  |
| `arxiv_figures` | `ZOOM_MAX` | `ZOOM_MAX` |  |
| `arxiv_figures` | `ZOOM_MIN` | `ZOOM_MIN` |  |
| `audit_cron` | `ITEM` | `ITEM` |  |
| `audit_cron` | `LATE_SECONDS` | `LATE_SECONDS` |  |
| `audit_cron` | `MARK` | `MARK` |  |
| `audit_cron` | `TICK_OLD` | `TICK_OLD` |  |
| `blackboard` | `DRAFTS` | `DRAFTS` |  |
| `blackboard` | `HERMES_DIR` | `HERMES_DIR` |  |
| `blackboard` | `PREFIX_ARTICLE` | `PREFIX_ARTICLE` |  |
| `blackboard` | `ROOT` | `ROOT` |  |
| `blackboard` | `ROOT_ASSIGNEE` | `ROOT_ASSIGNEE` |  |
| `bob_submit` | `EMOJI_DEFAULT` | `EMOJI_DEFAULT` |  |
| `bob_submit` | `GET_SOURCE` | `GET_SOURCE` |  |
| `bob_submit` | `RC_NO_HAS_IMAGE` | `RC_NO_HAS_IMAGE` |  |
| `bob_submit` | `ROOT` | `ROOT` |  |
| `bob_submit` | `SKILL` | `SKILL` |  |
| `browser_session` | `ARGS_DEFAULT` | `ARGS_DEFAULT` |  |
| `browser_session` | `CODE_BLOCK` | `CODE_BLOCK` |  |
| `browser_session` | `MOBILE_DPR` | `MOBILE_DPR` |  |
| `browser_session` | `MOBILE_UA` | `MOBILE_UA` |  |
| `browser_session` | `MOBILE_VIEWPORT` | `MOBILE_VIEWPORT` |  |
| `cape_prepare` | `ROOT` | `ROOT` |  |
| `cape_prepare` | `TEXT_MAX` | `TEXT_MAX` |  |
| `cape_submit` | `ROOT` | `ROOT` |  |
| `caption_check` | `BACKGROUND_SET` | `BACKGROUND_SET` |  |
| `caption_check` | `CARD_ALLOW` | `CARD_ALLOW` |  |
| `caption_check` | `CEILING_BACKGROUND_LAYER` | `CEILING_BACKGROUND_LAYER` |  |
| `caption_check` | `COUNT` | `COUNT` |  |
| `caption_check` | `FROM_ANNOUNCEMENT` | `FROM_ANNOUNCEMENT` |  |
| `caption_check` | `LIMIT` | `LIMIT` |  |
| `caption_check` | `MARK` | `MARK` |  |
| `caption_check` | `PHRASE_COUNT` | `PHRASE_COUNT` |  |
| `caption_check` | `STAR_EMPTY` | `STAR_EMPTY` |  |
| `caption_check` | `THRESHOLD_MARK` | `THRESHOLD_MARK` |  |
| `caption_check` | `TIME_ROOM` | `TIME_ROOM` |  |
| `capture_chart` | `DPR` | `DPR` |  |
| `capture_chart` | `EMPTY_MARK` | `EMPTY_MARK` |  |
| `capture_chart` | `EMPTY_MAX` | `EMPTY_MAX` |  |
| `capture_chart` | `HEIGHT_WARNING` | `HEIGHT_WARNING` |  |
| `capture_chart` | `MEASURE_JS` | `MEASURE_JS` |  |
| `capture_chart` | `PICK_DEFAULT` | `PICK_DEFAULT` |  |
| `capture_page` | `CROP_MAX` | `CROP_MAX` |  |
| `capture_page` | `CROP_RATIO_TRANSLATE` | `CROP_RATIO_TRANSLATE` |  |
| `capture_page` | `DPR` | `DPR` |  |
| `capture_page` | `FRAME` | `FRAME` |  |
| `capture_page` | `LEAD_TRY` | `LEAD_TRY` |  |
| `capture_page` | `MIN` | `MIN` |  |
| `capture_page` | `PICK` | `PICK` |  |
| `capture_page` | `THRESHOLD_OTHER_BACKGROUND` | `THRESHOLD_OTHER_BACKGROUND` |  |
| `capture_page` | `TIME_LIMIT` | `TIME_LIMIT` |  |
| `capture_page` | `UA` | `UA` |  |
| `capture_page` | `WAIT_LANG` | `WAIT_LANG` |  |
| `capture_page` | `WAIT_LAZY` | `WAIT_LAZY` |  |
| `card` | `ACCENT` | `ACCENT` |  |
| `card` | `ACCENT_DIM` | `ACCENT_DIM` |  |
| `card` | `ASSETS` | `ASSETS` |  |
| `card` | `BG` | `BG` |  |
| `card` | `BG_CARD` | `BG_CARD` |  |
| `card` | `BRAND` | `BRAND` |  |
| `card` | `BRAND_FROM` | `BRAND_FROM` |  |
| `card` | `BRAND_PHRASE` | `BRAND_PHRASE` |  |
| `card` | `BRAND_SIZE` | `BRAND_SIZE` |  |
| `card` | `CEILING_FRAME_LW` | `CEILING_FRAME_LW` |  |
| `card` | `CEILING_FRAME_PAD` | `CEILING_FRAME_PAD` |  |
| `card` | `CEILING_FRAME_R` | `CEILING_FRAME_R` |  |
| `card` | `CEILING_FRAME_X` | `CEILING_FRAME_X` |  |
| `card` | `CEILING_TEXTBOX` | `CEILING_TEXTBOX` |  |
| `card` | `CEILING_TEXT_X` | `CEILING_TEXT_X` |  |
| `card` | `CEILING_TITLE_LINES` | `CEILING_TITLE_LINES` |  |
| `card` | `CEILING_TITLE_MAX` | `CEILING_TITLE_MAX` |  |
| `card` | `CLUTTERED_BG_CEILING` | `?CLUTTERED_BG_CEILING` |  |
| `card` | `CLUTTERED_BG_LANG` | `?CLUTTERED_BG_LANG` |  |
| `card` | `CLUTTERED_BG_LONG_LANG` | `?CLUTTERED_BG_LONG_LANG` |  |
| `card` | `CLUTTERED_BG_ODD` | `?CLUTTERED_BG_ODD` |  |
| `card` | `CLUTTERED_BG_SPREAD` | `?CLUTTERED_BG_SPREAD` |  |
| `card` | `CLUTTERED_BG_SPREAD_SAME` | `?CLUTTERED_BG_SPREAD_SAME` |  |
| `card` | `CLUTTERED_BG_TEXT` | `?CLUTTERED_BG_TEXT` |  |
| `card` | `CLUTTERED_BG_VISION` | `?CLUTTERED_BG_VISION` |  |
| `card` | `COLOR_PHRASE` | `COLOR_PHRASE` |  |
| `card` | `COLOR_RANK` | `COLOR_RANK` |  |
| `card` | `CYAN` | `CYAN` |  |
| `card` | `DARK_MAX_LINE` | `DARK_MAX_LINE` |  |
| `card` | `FG` | `FG` |  |
| `card` | `FONTS` | `FONTS` |  |
| `card` | `F_BOLD` | `F_BOLD` |  |
| `card` | `F_HERO` | `F_HERO` |  |
| `card` | `F_MARK` | `F_MARK` |  |
| `card` | `F_MONO` | `F_MONO` |  |
| `card` | `F_QUOTE` | `F_QUOTE` |  |
| `card` | `F_QUOTE_REG` | `F_QUOTE_REG` |  |
| `card` | `F_REG` | `F_REG` |  |
| `card` | `F_SUB` | `F_SUB` |  |
| `card` | `F_UI` | `F_UI` |  |
| `card` | `HERO_WEIGHT` | `HERO_WEIGHT` |  |
| `card` | `KICKER_FAMILY` | `KICKER_FAMILY` |  |
| `card` | `KICKER_GAP` | `KICKER_GAP` |  |
| `card` | `KICKER_PHRASE` | `KICKER_PHRASE` |  |
| `card` | `KICKER_SIZE` | `KICKER_SIZE` |  |
| `card` | `KICKER_TRACK` | `KICKER_TRACK` |  |
| `card` | `LINE` | `LINE` |  |
| `card` | `MARK_SIZE` | `MARK_SIZE` |  |
| `card` | `MUTED` | `MUTED` |  |
| `card` | `PAD` | `PAD` |  |
| `card` | `QUOTE_BLUR` | `QUOTE_BLUR` |  |
| `card` | `QUOTE_BLUR_COUNT` | `QUOTE_BLUR_COUNT` |  |
| `card` | `QUOTE_LEAD` | `QUOTE_LEAD` |  |
| `card` | `QUOTE_MAX_LINES` | `QUOTE_MAX_LINES` |  |
| `card` | `QUOTE_PAD` | `QUOTE_PAD` |  |
| `card` | `RATIOS` | `RATIOS` |  |
| `card` | `SUB_SIZE` | `SUB_SIZE` |  |
| `card` | `THRESHOLD_BACKGROUND_BRIGHT` | `THRESHOLD_BACKGROUND_BRIGHT` |  |
| `card` | `THRESHOLD_FALL_LINE` | `THRESHOLD_FALL_LINE` |  |
| `card` | `TITLE_GROW_LINES` | `TITLE_GROW_LINES` |  |
| `card` | `TITLE_GROW_MAX` | `TITLE_GROW_MAX` |  |
| `card` | `TRANSLATE_FALL_LINE` | `TRANSLATE_FALL_LINE` |  |
| `card` | `VIA_SIZE` | `VIA_SIZE` |  |
| `carousel` | `BACKGROUND` | `BACKGROUND` |  |
| `carousel` | `BACKGROUND_SHOW` | `BACKGROUND_SHOW` |  |
| `carousel` | `BG` | `BG` |  |
| `carousel` | `BG_BLUR` | `BG_BLUR` |  |
| `carousel` | `BLUR_RADIUS` | `BLUR_RADIUS` |  |
| `carousel` | `BODY_LEAD` | `BODY_LEAD` |  |
| `carousel` | `CATEGORY_CALL_Y` | `CATEGORY_CALL_Y` |  |
| `carousel` | `CLUTTERED_BG_ODD` | `?CLUTTERED_BG_ODD` |  |
| `carousel` | `CLUTTERED_BG_SPREAD` | `?CLUTTERED_BG_SPREAD` |  |
| `carousel` | `DARK_MAX` | `DARK_MAX` |  |
| `carousel` | `FG` | `FG` |  |
| `carousel` | `FLAGSHIP_MIN` | `FLAGSHIP_MIN` |  |
| `carousel` | `F_MONO_CH` | `F_MONO_CH` |  |
| `carousel` | `F_UI_CH` | `F_UI_CH` |  |
| `carousel` | `HOOK_LEAD` | `HOOK_LEAD` |  |
| `carousel` | `HOOK_WEIGHT` | `HOOK_WEIGHT` |  |
| `carousel` | `LABEL_SIZE` | `LABEL_SIZE` |  |
| `carousel` | `MIN_SLIDE` | `MIN_SLIDE` |  |
| `carousel` | `OPEN` | `OPEN` |  |
| `carousel` | `PAD` | `PAD` |  |
| `carousel` | `PARA_GAP` | `PARA_GAP` |  |
| `carousel` | `Q_AVAIL` | `Q_AVAIL` |  |
| `carousel` | `Q_BOTTOM` | `Q_BOTTOM` |  |
| `carousel` | `Q_FRAME_X` | `Q_FRAME_X` |  |
| `carousel` | `Q_LEAD` | `Q_LEAD` |  |
| `carousel` | `Q_LINES` | `Q_LINES` |  |
| `carousel` | `Q_TEXT_X` | `Q_TEXT_X` |  |
| `carousel` | `TEXT_BASE` | `TEXT_BASE` |  |
| `carousel` | `TEXT_MAX_H` | `TEXT_MAX_H` |  |
| `carousel` | `THRESHOLD_BRIGHT_BRIGHT` | `THRESHOLD_BRIGHT_BRIGHT` |  |
| `carousel` | `THRESHOLD_BRIGHT_DARK` | `THRESHOLD_BRIGHT_DARK` |  |
| `carousel` | `THRESHOLD_VARIANCE_NEEDS_LAYER` | `THRESHOLD_?VARIANCE_NEEDS_LAYER` |  |
| `carousel` | `VEIL_EASE` | `VEIL_EASE` |  |
| `carousel` | `VEIL_SPAN` | `VEIL_SPAN` |  |
| `carousel` | `WM` | `WM` |  |
| `carousel` | `WM_BOTTOM` | `WM_BOTTOM` |  |
| `carousel` | `WM_SIZE` | `WM_SIZE` |  |
| `chat_router` | `CHAT_HINT` | `CHAT_HINT` |  |
| `chat_router` | `DROP_ONLY_READ` | `DROP_ONLY_READ` |  |
| `chat_router` | `HERMES_DIR` | `HERMES_DIR` |  |
| `chat_router` | `HERMES_HOME` | `HERMES_HOME` |  |
| `chat_router` | `HERMES_PY` | `HERMES_PY` |  |
| `chat_router` | `REPLY_LIMIT` | `REPLY_LIMIT` |  |
| `chat_router` | `TIMEOUT_SEC` | `TIMEOUT_SEC` |  |
| `chat_router` | `TOPIC_PROFILE` | `TOPIC_PROFILE` |  |
| `check_env` | `ITEM_CHECK` | `ITEM_CHECK` |  |
| `check_env` | `NAME_MODEL_YUNET` | `NAME_MODEL_YUNET` |  |
| `check_hermes` | `COLUMN_CAN` | `COLUMN_CAN` |  |
| `check_hermes` | `COLUMN_CAN_STATE` | `COLUMN_CAN_STATE` |  |
| `check_hermes` | `HAS_CHAT` | `HAS_CHAT` |  |
| `check_hermes` | `HERMES_PY` | `HERMES_PY` |  |
| `check_hermes` | `ROOT` | `ROOT` |  |
| `cleanup` | `ROOT` | `ROOT` |  |
| `cost_squeeze` | `CANDIDATE` | `CANDIDATE` |  |
| `cost_squeeze` | `FAKE` | `FAKE` |  |
| `cost_squeeze` | `HERMES` | `HERMES` |  |
| `cost_squeeze` | `JOB` | `JOB` |  |
| `cost_squeeze` | `ROOT` | `ROOT` |  |
| `cost_squeeze` | `ROUTER` | `ROUTER` |  |
| `cost_squeeze` | `STORY_WRITER` | `STORY_WRITER` |  |
| `crop_ratio` | `RATIO` | `RATIO` |  |
| `deck` | `ASSETS` | `ASSETS` |  |
| `deck` | `BG_CREAM` | `BG_CREAM` |  |
| `deck` | `BG_DARK` | `BG_DARK` |  |
| `deck` | `BLUE` | `BLUE` |  |
| `deck` | `CORAL` | `CORAL` |  |
| `deck` | `CREAM` | `CREAM` |  |
| `deck` | `FONTS` | `FONTS` |  |
| `deck` | `F_BODY` | `F_BODY` |  |
| `deck` | `F_COND` | `F_COND` |  |
| `deck` | `F_SANS` | `F_SANS` |  |
| `deck` | `F_SERIF` | `F_SERIF` |  |
| `deck` | `GREY` | `GREY` |  |
| `deck` | `INK` | `INK` |  |
| `deck` | `LAYOUTS` | `LAYOUTS` |  |
| `deck` | `PAD` | `PAD` |  |
| `deck` | `WHITE` | `WHITE` |  |
| `draft_write` | `DRAFTS` | `DRAFTS` |  |
| `dre_prepare` | `DRAFTS` | `DRAFTS` |  |
| `dre_prepare` | `ROOT` | `ROOT` |  |
| `dre_submit` | `DRAFTS` | `DRAFTS` |  |
| `dre_submit` | `ROOT` | `ROOT` |  |
| `dre_submit` | `TEXT_KEEP` | `TEXT_KEEP` |  |
| `emoji_deck` | `DECK` | `DECK` |  |
| `emoji_deck` | `FLAG_HINTS` | `FLAG_HINTS` |  |
| `emoji_deck` | `STATE_PATH` | `STATE_PATH` |  |
| `entity_images` | `MAX_ENTITY` | `MAX_ENTITY` |  |
| `entity_images` | `MAX_NEW_ENTITY` | `MAX_NEW_ENTITY` |  |
| `entity_images` | `SHORT_SIDE_MIN` | `SHORT_SIDE_MIN` |  |
| `entity_images` | `WIKI_API` | `WIKI_API` |  |
| `env_load` | `BRAND_LONG` | `BRAND_LONG` |  |
| `env_load` | `HERMES_DIR` | `HERMES_DIR` |  |
| `env_load` | `HERMES_PY` | `HERMES_PY` |  |
| `env_load` | `ROOT` | `ROOT` |  |
| `env_load` | `ROUTER_URL` | `ROUTER_URL` |  |
| `env_load` | `UA_BROWSER` | `UA_BROWSER` |  |
| `env_load` | `UA_WIKI` | `UA_WIKI` |  |
| `env_load` | `VISION_MODEL` | `VISION_MODEL` |  |
| `ethan_prepare` | `RATIO_HERO_MAX` | `RATIO_HERO_MAX` |  |
| `ethan_prepare` | `ROOT` | `ROOT` |  |
| `ethan_prepare` | `TAGLINE_CALL_Y` | `TAGLINE_CALL_Y` |  |
| `ethan_submit` | `DRAFTS` | `DRAFTS` |  |
| `ethan_submit` | `ROOT` | `ROOT` |  |
| `find_image_web` | `DROP_DOMAIN_WEB` | `DROP_DOMAIN_WEB` |  |
| `find_image_web` | `SOURCE` | `SOURCE` |  |
| `find_image_web` | `UA` | `UA` |  |
| `find_more_images` | `COUNT_COMMONS_NEW_TURN` | `COUNT_COMMONS_NEW_TURN` |  |
| `find_more_images` | `COUNT_REPORT_NEW_TURN` | `COUNT_REPORT_NEW_TURN` |  |
| `find_more_images` | `LICENSE_OK` | `LICENSE_OK` |  |
| `find_more_images` | `MAX_IMAGE_EXTRA` | `MAX_IMAGE_EXTRA` |  |
| `find_more_images` | `OPENVERSE` | `OPENVERSE` |  |
| `find_more_images` | `ROOT` | `ROOT` |  |
| `find_more_images` | `SHORT_SIDE_OPENVERSE` | `SHORT_SIDE_OPENVERSE` |  |
| `find_more_images` | `THUMB_COMMONS` | `THUMB_COMMONS` |  |
| `gin_prepare` | `BOLD_ITEM` | `BOLD_ITEM` |  |
| `gin_prepare` | `FLAT_STD` | `FLAT_STD` |  |
| `gin_prepare` | `ROOT` | `ROOT` |  |
| `gin_prepare` | `SOCIAL` | `SOCIAL` |  |
| `gin_submit` | `BAN_KINH_TRAM` | `COPY_?KINH_?TRAM` | ⚠️ ban |
| `gin_submit` | `RATIO_HAS_MIN` | `RATIO_HAS_MIN` |  |
| `gin_submit` | `ROOT` | `ROOT` |  |
| `image_brand` | `COMMONS` | `COMMONS` |  |
| `image_brand` | `DISPLAY_NAME` | `DISPLAY_NAME` |  |
| `image_brand` | `FROM_COMMON_NAME` | `FROM_COMMON_NAME` |  |
| `image_brand` | `HAS_BALLOT_URL` | `HAS_BALLOT_URL` |  |
| `image_brand` | `HAS_BALLOT_WAIT` | `HAS_BALLOT_WAIT` |  |
| `image_brand` | `MANY` | `MANY` |  |
| `image_brand` | `MANY_COMMON` | `MANY_COMMON` |  |
| `image_brand` | `MAX_ANNOUNCEMENT_PAGE` | `MAX_ANNOUNCEMENT_PAGE` |  |
| `image_brand` | `MAX_NEW_RANK` | `MAX_NEW_RANK` |  |
| `image_brand` | `MAX_PERSON` | `MAX_PERSON` |  |
| `image_brand` | `MAX_PERSON_LANDSCAPE` | `MAX_PERSON_LANDSCAPE` |  |
| `image_brand` | `MAX_QUERY` | `MAX_QUERY` |  |
| `image_brand` | `MAX_RANK` | `MAX_RANK` |  |
| `image_brand` | `NAME_EXTRA` | `NAME_EXTRA` |  |
| `image_brand` | `PATH_FEED` | `PATH_FEED` |  |
| `image_brand` | `PATH_STORY` | `PATH_STORY` |  |
| `image_brand` | `P_GATE_BILLION` | `P_GATE_BILLION` |  |
| `image_brand` | `P_WEBSITE` | `P_WEBSITE` |  |
| `image_brand` | `SHORT_SIDE_MIN` | `SHORT_SIDE_MIN` |  |
| `image_brand` | `SUFFIX` | `SUFFIX` |  |
| `image_brand` | `WIKIDATA` | `WIKIDATA` |  |
| `image_concept` | `COUNTRY` | `COUNTRY` |  |
| `image_concept` | `COUNTRY_WRITE_ALL` | `COUNTRY_WRITE_ALL` |  |
| `image_concept` | `FROM_DROP` | `FROM_DROP` |  |
| `image_concept` | `MAX_KEYWORD` | `MAX_KEYWORD` |  |
| `image_concept` | `NAME_TYPE` | `NAME_TYPE` |  |
| `image_concept` | `TOPIC` | `TOPIC` |  |
| `image_concept` | `UA` | `UA` |  |
| `image_frame` | `AVATARS` | `AVATARS` |  |
| `image_frame` | `BG` | `BG` |  |
| `image_frame` | `BORDER` | `BORDER` |  |
| `image_frame` | `COLOR_HANDLE` | `COLOR_HANDLE` |  |
| `image_frame` | `COLOR_PROMPT` | `COLOR_PROMPT` |  |
| `image_frame` | `DOTS` | `DOTS` |  |
| `image_frame` | `FONT_DIR` | `FONT_DIR` |  |
| `image_frame` | `FOOTER` | `FOOTER` |  |
| `image_frame` | `K_DROP_FULL_CARD` | `K_DROP_FULL_CARD` |  |
| `image_frame` | `K_DROP_FULL_OUTSIDE` | `K_DROP_FULL_OUTSIDE` |  |
| `image_frame` | `K_SHADOW` | `K_SHADOW` |  |
| `image_frame` | `MAXW` | `MAXW` |  |
| `image_frame` | `ROOT` | `ROOT` |  |
| `image_frame` | `SKILL` | `SKILL` |  |
| `image_prepare` | `COUNT_ENGINE_PARALLEL` | `COUNT_ENGINE_PARALLEL` |  |
| `image_prepare` | `MAX_CRASH` | `MAX_CRASH` |  |
| `image_prepare` | `NAME_CT` | `NAME_CT` |  |
| `image_prepare` | `WAIT_LOCK_SECONDS` | `WAIT_LOCK_SECONDS` |  |
| `image_prepare` | `WAIT_SLOT_SECONDS` | `WAIT_SLOT_SECONDS` |  |
| `image_provenance` | `MARK_PNG` | `MARK_PNG` |  |
| `image_rules_dre` | `AREA_DOWNLOAD` | `AREA_DOWNLOAD` |  |
| `image_rules_dre` | `BRIGHT_BOTTOM_MAX` | `BRIGHT_BOTTOM_MAX` |  |
| `image_rules_dre` | `CHART_COUNT_COLOR` | `CHART_COUNT_COLOR` |  |
| `image_rules_dre` | `CHART_FLAT` | `CHART_FLAT` |  |
| `image_rules_dre` | `DATE_SMALL_IMAGE` | `DATE_SMALL_IMAGE` |  |
| `image_rules_dre` | `EMPTY_COLOR` | `EMPTY_COLOR` |  |
| `image_rules_dre` | `EMPTY_FLAT` | `EMPTY_FLAT` |  |
| `image_rules_dre` | `FACE_EDGE_MAX` | `FACE_EDGE_MAX` |  |
| `image_rules_dre` | `JUNK` | `JUNK` |  |
| `image_rules_dre` | `JUNK_WORDS_DOM` | `JUNK_WORDS_DOM` |  |
| `image_rules_dre` | `JUNK_WORDS_URL` | `JUNK_WORDS_URL` |  |
| `image_rules_dre` | `LANDSCAPE_CLEAR` | `LANDSCAPE_CLEAR` |  |
| `image_rules_dre` | `SHORT_SIDE_DOWNLOAD` | `SHORT_SIDE_DOWNLOAD` |  |
| `image_rules_dre` | `SHORT_SIDE_MIN` | `SHORT_SIDE_MIN` |  |
| `image_rules_dre` | `STACK_FLOOR` | `STACK_?FLOOR` |  |
| `image_rules_dre` | `THRESHOLD_GRAPHIC` | `THRESHOLD_GRAPHIC` |  |
| `image_rules_dre` | `TOLERANCE_RATIO` | `TOLERANCE_RATIO` |  |
| `image_rules_ethan` | `AREA_DOWNLOAD` | `AREA_DOWNLOAD` |  |
| `image_rules_ethan` | `BRIGHT_BOTTOM_MAX` | `BRIGHT_BOTTOM_MAX` |  |
| `image_rules_ethan` | `CHART_COUNT_COLOR` | `CHART_COUNT_COLOR` |  |
| `image_rules_ethan` | `CHART_FLAT` | `CHART_FLAT` |  |
| `image_rules_ethan` | `DATE_SMALL_IMAGE` | `DATE_SMALL_IMAGE` |  |
| `image_rules_ethan` | `EMPTY_COLOR` | `EMPTY_COLOR` |  |
| `image_rules_ethan` | `EMPTY_FLAT` | `EMPTY_FLAT` |  |
| `image_rules_ethan` | `FACE_EDGE_MAX` | `FACE_EDGE_MAX` |  |
| `image_rules_ethan` | `JUNK` | `JUNK` |  |
| `image_rules_ethan` | `JUNK_WORDS_DOM` | `JUNK_WORDS_DOM` |  |
| `image_rules_ethan` | `JUNK_WORDS_URL` | `JUNK_WORDS_URL` |  |
| `image_rules_ethan` | `LANDSCAPE_CLEAR` | `LANDSCAPE_CLEAR` |  |
| `image_rules_ethan` | `SHORT_SIDE_DOWNLOAD` | `SHORT_SIDE_DOWNLOAD` |  |
| `image_rules_ethan` | `SHORT_SIDE_MIN` | `SHORT_SIDE_MIN` |  |
| `image_rules_ethan` | `THRESHOLD_GRAPHIC` | `THRESHOLD_GRAPHIC` |  |
| `image_rules_ethan` | `TOLERANCE_RATIO` | `TOLERANCE_RATIO` |  |
| `image_rules_kite` | `AREA_DOWNLOAD` | `AREA_DOWNLOAD` |  |
| `image_rules_kite` | `BRIGHT_BOTTOM_MAX` | `BRIGHT_BOTTOM_MAX` |  |
| `image_rules_kite` | `CHART_COUNT_COLOR` | `CHART_COUNT_COLOR` |  |
| `image_rules_kite` | `CHART_FLAT` | `CHART_FLAT` |  |
| `image_rules_kite` | `DATE_SMALL_IMAGE` | `DATE_SMALL_IMAGE` |  |
| `image_rules_kite` | `EMPTY_COLOR` | `EMPTY_COLOR` |  |
| `image_rules_kite` | `EMPTY_FLAT` | `EMPTY_FLAT` |  |
| `image_rules_kite` | `FACE_EDGE_MAX` | `FACE_EDGE_MAX` |  |
| `image_rules_kite` | `JUNK` | `JUNK` |  |
| `image_rules_kite` | `JUNK_WORDS_DOM` | `JUNK_WORDS_DOM` |  |
| `image_rules_kite` | `JUNK_WORDS_URL` | `JUNK_WORDS_URL` |  |
| `image_rules_kite` | `LANDSCAPE_CLEAR` | `LANDSCAPE_CLEAR` |  |
| `image_rules_kite` | `SHORT_SIDE_DOWNLOAD` | `SHORT_SIDE_DOWNLOAD` |  |
| `image_rules_kite` | `SHORT_SIDE_MIN` | `SHORT_SIDE_MIN` |  |
| `image_rules_kite` | `THRESHOLD_GRAPHIC` | `THRESHOLD_GRAPHIC` |  |
| `image_rules_kite` | `TOLERANCE_RATIO` | `TOLERANCE_RATIO` |  |
| `itachi_prepare` | `LAYOUT_HELP` | `LAYOUT_HELP` |  |
| `itachi_prepare` | `ROOT` | `ROOT` |  |
| `itachi_submit` | `ROOT` | `ROOT` |  |
| `itachi_submit` | `THRESHOLD_WALL_PART` | `THRESHOLD_WALL_PART` |  |
| `journal` | `DIRECTORY` | `DIRECTORY` |  |
| `journal` | `ERROR_READ` | `ERROR_READ` |  |
| `journal` | `EXCESS` | `EXCESS` |  |
| `journal` | `FORM_RUN` | `FORM_RUN` |  |
| `journal` | `HERMES` | `HERMES` |  |
| `journal` | `NOTES` | `NOTES` |  |
| `journal` | `ROOT` | `ROOT` |  |
| `journal` | `TYPE` | `TYPE` |  |
| `journal` | `VN` | `VN` |  |
| `journal_web` | `CSS` | `CSS` |  |
| `journal_web` | `HOST` | `HOST` |  |
| `journal_web` | `PORT` | `PORT` |  |
| `journal_web` | `ROOT` | `ROOT` |  |
| `kite_prepare` | `FIG_EMPTY_MIN` | `FIG_EMPTY_MIN` |  |
| `kite_prepare` | `MAX_FORCE_FIGURE` | `MAX_FORCE_FIGURE` |  |
| `kite_prepare` | `ROOT` | `ROOT` |  |
| `kite_submit` | `DRAFTS` | `DRAFTS` |  |
| `kite_submit` | `LIMIT` | `LIMIT` |  |
| `kite_submit` | `REQUIRED` | `REQUIRED` |  |
| `kite_submit` | `ROOT` | `ROOT` |  |
| `kite_submit` | `SLIDE_NEW_IMAGE_REAL` | `SLIDE_NEW_IMAGE_REAL` |  |
| `manifest_build` | `MAX_PICK` | `MAX_PICK` |  |
| `manifest_build` | `ROOT` | `ROOT` |  |
| `manifest_build` | `STATE` | `STATE` |  |
| `manifest_build` | `VALID_CATEGORIES` | `VALID_CATEGORIES` |  |
| `manifest_common` | `MAX_FROM_SUMMARY` | `MAX_FROM_SUMMARY` |  |
| `manifest_report` | `MENTION` | `MENTION` |  |
| `manifest_report` | `NAME_ROLE` | `NAME_ROLE` |  |
| `manifest_report` | `VN` | `VN` |  |
| `manifest_write` | `LABEL_DEFAULT` | `LABEL_DEFAULT` |  |
| `manifest_write` | `PREFIX` | `PREFIX` |  |
| `manifest_write` | `ROOT` | `ROOT` |  |
| `manifest_write` | `STATE` | `STATE` |  |
| `material` | `COUNT_ARTICLE_OTHER` | `COUNT_ARTICLE_OTHER` |  |
| `material` | `HAS_COUNT` | `HAS_COUNT` |  |
| `material` | `ROOT` | `ROOT` |  |
| `material` | `TEXT_MAX` | `TEXT_MAX` |  |
| `miles_prepare` | `DRAFTS` | `DRAFTS` |  |
| `miles_prepare` | `ROOT` | `ROOT` |  |
| `miles_prepare` | `VOICE` | `VOICE` |  |
| `miles_submit` | `DRAFTS` | `DRAFTS` |  |
| `miles_submit` | `ROOT` | `ROOT` |  |
| `moat_publish` | `BACKGROUND_IMAGE` | `BACKGROUND_IMAGE` |  |
| `moat_publish` | `CEILING_BACKGROUND_LAYER` | `CEILING_BACKGROUND_LAYER` |  |
| `moat_publish` | `CEILING_TOTAL` | `CEILING_TOTAL` |  |
| `moat_publish` | `CODE_BUTTON_FORM_AGAIN` | `CODE_BUTTON_FORM_AGAIN` |  |
| `moat_publish` | `DEFAULT_BRAND` | `DEFAULT_BRAND` |  |
| `moat_publish` | `DRAFTS` | `DRAFTS` |  |
| `moat_publish` | `LOCK_BY_BRAND` | `LOCK_BY_BRAND` |  |
| `moat_publish` | `LOCK_DEFAULT` | `LOCK_DEFAULT` |  |
| `moat_publish` | `MAX_IMAGE` | `MAX_IMAGE` |  |
| `moat_publish` | `MAX_TRACK_DAYS` | `MAX_TRACK_DAYS` |  |
| `moat_publish` | `MIME_BY_SUFFIX` | `MIME_BY_SUFFIX` |  |
| `moat_publish` | `PLATFORMS` | `PLATFORMS` |  |
| `moat_publish` | `PLATFORM_LABEL` | `PLATFORM_LABEL` |  |
| `moat_publish` | `QUALITY_BACKGROUND` | `QUALITY_BACKGROUND` |  |
| `moat_publish` | `QUEUE` | `QUEUE` |  |
| `moat_publish` | `ROOT` | `ROOT` |  |
| `moat_publish` | `SCHEDULE_BACK` | `SCHEDULE_BACK` |  |
| `moat_publish` | `SPOOL` | `SPOOL` |  |
| `moat_publish` | `STATE_DIR` | `STATE_DIR` |  |
| `moat_publish` | `TERMINAL` | `TERMINAL` |  |
| `moat_publish` | `THRESHOLD_BACKGROUND` | `THRESHOLD_BACKGROUND` |  |
| `moat_publish` | `TIER_QUALITY` | `TIER_QUALITY` |  |
| `moat_publish` | `TIMEOUT` | `TIMEOUT` |  |
| `moat_publish` | `TIMEOUT_BOTTOM` | `TIMEOUT_BOTTOM` |  |
| `model_audition` | `CANDIDATE` | `CANDIDATE` |  |
| `model_audition` | `COUNT` | `COUNT` |  |
| `model_audition` | `ROUTER` | `ROUTER` |  |
| `model_audition` | `STORY` | `STORY` |  |
| `model_audition` | `SYS` | `SYS` |  |
| `model_audition` | `THRESHOLD_MARK` | `THRESHOLD_MARK` |  |
| `model_audition` | `TOOLS` | `TOOLS` |  |
| `model_boards` | `AA` | `AA` |  |
| `model_boards` | `ARENA` | `ARENA` |  |
| `model_boards` | `ARENA_BOARDS` | `ARENA_BOARDS` |  |
| `model_boards` | `BOARD` | `BOARD` |  |
| `model_boards` | `COUNT_BOARD` | `COUNT_BOARD` |  |
| `model_boards` | `LABEL_BOARD` | `LABEL_BOARD` |  |
| `model_boards` | `LINK_BOARD` | `LINK_BOARD` |  |
| `model_boards` | `LOCK_BOARD` | `LOCK_BOARD` |  |
| `model_boards` | `SWE` | `SWE` |  |
| `model_watch` | `PROBE` | `PROBE` |  |
| `model_watch` | `REASONS` | `REASONS` |  |
| `model_watch` | `ROUTER` | `ROUTER` |  |
| `model_watch` | `TIMEOUT` | `TIMEOUT` |  |
| `monitor_9router` | `DB` | `DB` |  |
| `monitor_9router` | `DIRECTORY` | `DIRECTORY` |  |
| `monitor_9router` | `DRAFTS` | `DRAFTS` |  |
| `monitor_9router` | `EMPTY_OUT_MAX` | `EMPTY_OUT_MAX` |  |
| `monitor_9router` | `EMPTY_PROMPT_MIN` | `EMPTY_PROMPT_MIN` |  |
| `monitor_9router` | `FALLBACK_REAL` | `FALLBACK_REAL` |  |
| `monitor_9router` | `HERMES_HOMES` | `HERMES_HOMES` |  |
| `monitor_9router` | `JOURNAL` | `JOURNAL` |  |
| `monitor_9router` | `PROMPT_MIN_CACHE` | `PROMPT_MIN_CACHE` |  |
| `monitor_9router` | `ROOT` | `ROOT` |  |
| `monitor_9router` | `SECONDS_FLIP` | `SECONDS_FLIP` |  |
| `monitor_9router` | `THRESHOLD_CACHE` | `THRESHOLD_CACHE` |  |
| `monitor_9router` | `VN` | `VN` |  |
| `monitor_9router` | `WEB_URL` | `WEB_URL` |  |
| `prepare.common` | `DRAFTS` | `DRAFTS` |  |
| `prepare.common` | `GNEWS` | `GNEWS` |  |
| `prepare.common` | `HDR` | `HDR` |  |
| `prepare.common` | `MAX_IMAGE` | `MAX_IMAGE` |  |
| `prepare.common` | `ROOT` | `ROOT` |  |
| `prepare.common` | `UA` | `UA` |  |
| `prepare.download_filter` | `DOWNLOAD_MAX_BYTE` | `DOWNLOAD_MAX_BYTE` |  |
| `prepare.download_filter` | `MAX_DOWNLOAD` | `MAX_DOWNLOAD` |  |
| `prepare.fallback_rounds` | `MAX_ARTICLE_SOURCES` | `MAX_ARTICLE_SOURCES` |  |
| `prepare.fallback_rounds` | `MAX_EXTRA_BRAND_` | `MAX_EXTRA_BRAND_?` |  |
| `prepare.fallback_rounds` | `MAX_PAGE_CAPTURE` | `MAX_PAGE_CAPTURE` |  |
| `prepare.fallback_rounds` | `XH_CONTEXT_EDGE_SOURCE` | `XH_CONTEXT_EDGE_SOURCE` |  |
| `prepare.source` | `FROM_COMMON_MARK_SENTENCE` | `FROM_COMMON_MARK_SENTENCE` |  |
| `prepare.vision` | `SENTENCE_CLUTTERED` | `SENTENCE_?CLUTTERED` |  |
| `prepare.vision` | `SENTENCE_KEYWORD` | `SENTENCE_KEYWORD` |  |
| `prepare.vision` | `VISION_MODEL` | `VISION_MODEL` |  |
| `prepare.vision` | `VISION_URL` | `VISION_URL` |  |
| `press_entity_images` | `BING_RSS` | `BING_RSS` |  |
| `press_entity_images` | `MAX_ARTICLE` | `MAX_ARTICLE` |  |
| `press_entity_images` | `MAX_NEW_DOMAIN` | `MAX_NEW_DOMAIN` |  |
| `press_entity_images` | `MKT` | `MKT` |  |
| `publish` | `API` | `API` |  |
| `publish` | `CAPTION_LIMIT` | `CAPTION_LIMIT` |  |
| `publish` | `CARD_VALID` | `CARD_VALID` |  |
| `ranking` | `ARGS_CAPTURE` | `ARGS_CAPTURE` |  |
| `ranking` | `DPR` | `DPR` |  |
| `ranking` | `GOLD` | `GOLD` |  |
| `ranking` | `HEIGHT_MAX_CSS` | `HEIGHT_MAX_CSS` |  |
| `ranking` | `KIND_CAPTURE` | `KIND_CAPTURE` |  |
| `ranking` | `MAX_XH` | `MAX_XH` |  |
| `ranking` | `ON_MODEL` | `ON_MODEL` |  |
| `ranking` | `RATIO_FIT` | `RATIO_FIT` |  |
| `ranking` | `ROOT` | `ROOT` |  |
| `ranking` | `SOURCE` | `SOURCE` |  |
| `ranking` | `TIME_LIMIT` | `TIME_LIMIT` |  |
| `ranking` | `TOPIC` | `TOPIC` |  |
| `ranking` | `TOP_DEFAULT` | `TOP_DEFAULT` |  |
| `ranking` | `UA` | `UA` |  |
| `render_edu` | `BASE_CSS_TPL` | `BASE_CSS_TPL` |  |
| `render_edu` | `BUILDERS` | `BUILDERS` |  |
| `render_edu` | `DARK_MAX_OPEN` | `DARK_MAX_OPEN` |  |
| `render_edu` | `DIM` | `DIM` |  |
| `render_edu` | `FALLBACK` | `FALLBACK` |  |
| `render_edu` | `FIG_BOTTOM_FLAT` | `FIG_BOTTOM_FLAT` |  |
| `render_edu` | `FIG_EMPTY_MIN` | `FIG_EMPTY_MIN` |  |
| `render_edu` | `FIG_FIXED` | `FIG_FIXED` |  |
| `render_edu` | `FIG_TITLE_LINE` | `FIG_TITLE_LINE` |  |
| `render_edu` | `FONTS` | `FONTS` |  |
| `render_edu` | `FONTS_DIR` | `FONTS_DIR` |  |
| `render_edu` | `FONT_URL` | `FONT_URL` |  |
| `render_edu` | `HEROES` | `HEROES` |  |
| `render_edu` | `HERO_GRAPH` | `HERO_GRAPH` |  |
| `render_edu` | `HERO_GRID` | `HERO_GRID` |  |
| `render_edu` | `HERO_ORBIT` | `HERO_ORBIT` |  |
| `render_edu` | `HERO_RINGS` | `HERO_RINGS` |  |
| `render_edu` | `HERO_TPL` | `HERO_TPL` |  |
| `render_edu` | `HERO_WAVE` | `HERO_WAVE` |  |
| `render_edu` | `IMAGE_MIME` | `IMAGE_MIME` |  |
| `render_edu` | `MUTED` | `MUTED` |  |
| `render_edu` | `RATIO_COLOR_APPLY_INVERT` | `RATIO_COLOR_APPLY_INVERT` |  |
| `render_edu` | `RATIO_FLAT_MIN` | `RATIO_FLAT_MIN` |  |
| `render_edu` | `RATIO_IMAGE_HAS_COLOR` | `RATIO_IMAGE_HAS_COLOR` |  |
| `render_edu` | `REQUIRED_KIND` | `REQUIRED_KIND` |  |
| `render_edu` | `ROOT` | `ROOT` |  |
| `render_edu` | `SOFT` | `SOFT` |  |
| `render_edu` | `THEMES` | `THEMES` |  |
| `render_edu` | `THRESHOLD_BRIGHT_TEXT_DARK` | `THRESHOLD_BRIGHT_TEXT_DARK` |  |
| `render_edu` | `THRESHOLD_HUE_OFFSET_COLOR` | `THRESHOLD_HUE_OFFSET_COLOR` |  |
| `render_edu` | `THRESHOLD_OFFSET_BORDER` | `THRESHOLD_OFFSET_BORDER` |  |
| `render_edu` | `VEIL_SPAN` | `VEIL_SPAN` |  |
| `render_edu` | `WHITE` | `WHITE` |  |
| `required` | `LINK_BOARD` | `LINK_BOARD` |  |
| `role` | `DEFAULT_IMAGE` | `DEFAULT_IMAGE` |  |
| `role` | `DEFAULT_WRITE` | `DEFAULT_WRITE` |  |
| `role` | `DISPLAY_NAME` | `DISPLAY_NAME` |  |
| `role` | `MAX_RUNTIME` | `MAX_RUNTIME` |  |
| `role` | `MAX_RUNTIME_IMAGE` | `MAX_RUNTIME_IMAGE` |  |
| `role` | `NAME_BRIGHT_CAP` | `NAME_BRIGHT_CAP` | ⚠️ cap |
| `role` | `NAME_ROLE_IMAGE` | `NAME_ROLE_IMAGE` |  |
| `role` | `NAME_ROLE_WRITE` | `NAME_ROLE_WRITE` |  |
| `role` | `ROLE` | `ROLE` |  |
| `role` | `ROLE_CAROUSEL` | `ROLE_CAROUSEL` |  |
| `role` | `ROLE_EDU` | `ROLE_EDU` |  |
| `role` | `ROLE_IMAGE` | `ROLE_IMAGE` |  |
| `role` | `SLUG_OLD` | `SLUG_OLD` |  |
| `role` | `WRITERS_BY_BRAND` | `?WRITERS_BY_BRAND` |  |
| `role` | `WRITE_BY_BRAND` | `WRITE_BY_BRAND` |  |
| `role` | `WRITE_BY_SCAN` | `WRITE_BY_SCAN` |  |
| `route_missing_images` | `DRAFTS` | `DRAFTS` |  |
| `scan_business` | `AMOUNT_PATTERN` | `?AMOUNT_PATTERN` |  |
| `scan_business` | `AMOUNT_UNIT` | `?AMOUNT_UNIT` |  |
| `scan_business` | `CROSS_CURRENCY_TOLERANCE` | `?CROSS_?CURRENCY_TOLERANCE` |  |
| `scan_business` | `CURRENCY_OF_MARK` | `?CURRENCY_OF_MARK` |  |
| `scan_business` | `DEAL_WORDS` | `?DEAL_WORDS` |  |
| `scan_business` | `FOLLOW_UP_BEFORE_AMOUNT` | `?FOLLOW_?UP_BEFORE_?AMOUNT` |  |
| `scan_business` | `FOLLOW_UP_WINDOW` | `?FOLLOW_?UP_?WINDOW` |  |
| `scan_business` | `FROM_EMPTY` | `FROM_EMPTY` |  |
| `scan_business` | `GNEWS` | `GNEWS` |  |
| `scan_business` | `MIN_SHARED_DEAL_KEYWORDS` | `MIN_?SHARED_?DEAL_?KEYWORDS` |  |
| `scan_business` | `QUERY` | `QUERY` |  |
| `scan_business` | `RANK_ERROR` | `RANK_ERROR` |  |
| `scan_business` | `RANK_OF_NAME` | `RANK_OF_NAME` |  |
| `scan_business` | `REPORT_LARGE` | `REPORT_LARGE` |  |
| `scan_business` | `RSS_REPORT` | `RSS_REPORT` |  |
| `scan_business` | `SAME_AMOUNT_TOLERANCE` | `SAME_?AMOUNT_TOLERANCE` |  |
| `scan_business` | `STATE` | `STATE` |  |
| `scan_business` | `UA` | `UA` |  |
| `scan_business` | `WATCHLIST` | `WATCHLIST` |  |
| `scan_business` | `WATCHLIST_WORDS` | `WATCHLIST_WORDS` |  |
| `scan_common` | `FROM_EMPTY` | `FROM_EMPTY` |  |
| `scan_common` | `NAME_ROLE` | `NAME_ROLE` |  |
| `scan_common` | `UA` | `UA` |  |
| `scan_common` | `VN` | `VN` |  |
| `scan_models` | `AA` | `AA` |  |
| `scan_models` | `AA_MEDIA` | `AA_MEDIA` |  |
| `scan_models` | `ANTHROPIC_CL` | `ANTHROPIC_CL` |  |
| `scan_models` | `ARCAGI` | `ARCAGI` |  |
| `scan_models` | `ARENA` | `ARENA` |  |
| `scan_models` | `ARENA_BOARDS` | `ARENA_BOARDS` |  |
| `scan_models` | `ARENA_WEBDEV` | `ARENA_WEBDEV` |  |
| `scan_models` | `BIG` | `BIG` |  |
| `scan_models` | `CATALOG` | `CATALOG` |  |
| `scan_models` | `CEILING_BOARD` | `CEILING_BOARD` |  |
| `scan_models` | `CEILING_GH` | `CEILING_GH` |  |
| `scan_models` | `CEILING_HF` | `CEILING_HF` |  |
| `scan_models` | `COUNT_BOARD` | `COUNT_BOARD` |  |
| `scan_models` | `ECI` | `ECI` |  |
| `scan_models` | `GITHUB_REPOS` | `GITHUB_REPOS` |  |
| `scan_models` | `HF_API` | `HF_API` |  |
| `scan_models` | `HF_JUNK` | `HF_JUNK` |  |
| `scan_models` | `HF_READY` | `HF_READY` |  |
| `scan_models` | `HLE` | `HLE` |  |
| `scan_models` | `HLE_PAT` | `HLE_PAT` |  |
| `scan_models` | `I2V_PAT` | `I2V_PAT` |  |
| `scan_models` | `KEYWORD_STORY` | `KEYWORD_STORY` |  |
| `scan_models` | `LABEL_BOARD` | `LABEL_BOARD` |  |
| `scan_models` | `LIVEBENCH` | `LIVEBENCH` |  |
| `scan_models` | `LOCK_BOARD` | `LOCK_BOARD` |  |
| `scan_models` | `OC_API` | `OC_API` |  |
| `scan_models` | `RANK_CHINA` | `RANK_CHINA` |  |
| `scan_models` | `RANK_MY` | `RANK_MY` |  |
| `scan_models` | `REGION_LABEL` | `REGION_LABEL` |  |
| `scan_models` | `RSS_RANK` | `RSS_RANK` |  |
| `scan_models` | `STATE` | `STATE` |  |
| `scan_models` | `STT_PAT` | `STT_PAT` |  |
| `scan_models` | `SWEBENCH` | `SWEBENCH` |  |
| `scan_models` | `SWE_BASH` | `SWE_BASH` |  |
| `scan_models` | `SWE_SPLIT` | `SWE_SPLIT` |  |
| `scan_models` | `TBENCH` | `TBENCH` |  |
| `scan_models` | `TBENCH_BOARD` | `TBENCH_BOARD` |  |
| `scan_models` | `TTS_PAT` | `TTS_PAT` |  |
| `scan_models` | `UA` | `UA` |  |
| `scan_prepare` | `CACHE_HOURS` | `CACHE_HOURS` |  |
| `scan_prepare` | `CEILING_REPORT` | `CEILING_REPORT` |  |
| `scan_prepare` | `FRAME_HOURS` | `FRAME_HOURS` |  |
| `scan_prepare` | `MANY_ATTEMPT_WITHIN_DATE` | `MANY_ATTEMPT_WITHIN_DATE` |  |
| `scan_prepare` | `ROOT` | `ROOT` |  |
| `scan_prepare` | `TOPIC` | `TOPIC` |  |
| `scan_prepare` | `VN` | `VN` |  |
| `scan_sources` | `AI_HINTS` | `AI_HINTS` |  |
| `scan_sources` | `ARXIV_CATS` | `ARXIV_CATS` |  |
| `scan_sources` | `IMAGE_JUNK` | `IMAGE_JUNK` |  |
| `scan_sources` | `KEYWORD_AI` | `KEYWORD_AI` |  |
| `scan_sources` | `MAX_AGE_HOURS` | `MAX_AGE_HOURS` |  |
| `scan_sources` | `NAME_ORGANIZATION` | `NAME_ORGANIZATION` |  |
| `scan_sources` | `NO_HAS_IMAGE` | `NO_HAS_IMAGE` |  |
| `scan_sources` | `RANK_FRONTIER` | `RANK_FRONTIER` |  |
| `scan_sources` | `ROOT` | `ROOT` |  |
| `scan_sources` | `STATE` | `STATE` |  |
| `scan_sources` | `SUBS` | `SUBS` |  |
| `scan_sources` | `UA` | `UA` |  |
| `scan_submit` | `BLOCK_SEND` | `BLOCK_SEND` |  |
| `scan_submit` | `LABEL_WARNING` | `LABEL_WARNING` |  |
| `scan_submit` | `NAME` | `NAME` |  |
| `scan_submit` | `ROOT` | `ROOT` |  |
| `scan_x` | `CEILING_OLD_HOURS` | `CEILING_OLD_HOURS` |  |
| `scan_x` | `DEFAULT_URL` | `DEFAULT_URL` |  |
| `scan_x` | `KEEP_DATE` | `KEEP_DATE` |  |
| `scan_x` | `LINK_CAPABILITY` | `LINK_CAPABILITY` |  |
| `scan_x` | `LINK_CATCH_KY` | `LINK_CATCH_KY` |  |
| `scan_x` | `MIN_KY_FROM` | `MIN_KY_FROM` |  |
| `scan_x` | `STATE` | `STATE` |  |
| `schema` | `HEIGHT_MIN_CROP_LANDSCAPE` | `HEIGHT_MIN_CROP_LANDSCAPE` |  |
| `schema` | `VERSION_MANIFEST` | `VERSION_MANIFEST` |  |
| `send_telegram` | `API` | `API` |  |
| `send_telegram` | `RETRY_DELAYS` | `RETRY_?DELAYS` |  |
| `send_telegram` | `STATE` | `STATE` |  |
| `send_telegram` | `TOPICS` | `TOPICS` |  |
| `skill_lesson_approve` | `DECISION_NOTE` | `?DECISION_?NOTE` |  |
| `skill_lesson_approve` | `SAFE_KEY` | `?SAFE_KEY` |  |
| `skill_lesson_approve` | `STATE` | `STATE` |  |
| `skill_lesson_commit` | `BRANCH_PREFIX` | `BRANCH_PREFIX` |  |
| `skill_lesson_commit` | `REPO` | `REPO` |  |
| `skill_lesson_commit` | `STATE` | `STATE` |  |
| `skill_lesson_filter` | `AVOID_WORDS` | `?AVOID_WORDS` |  |
| `skill_lesson_filter` | `BACKTICK` | `?BACKTICK` |  |
| `skill_lesson_filter` | `BRAND_WORDS` | `BRAND_WORDS` |  |
| `skill_lesson_filter` | `BUG_WORDS` | `?BUG_WORDS` |  |
| `skill_lesson_filter` | `DATA_SUFFIXES` | `DATA_?SUFFIXES` |  |
| `skill_lesson_filter` | `DOTTED` | `?DOTTED` |  |
| `skill_lesson_filter` | `DUPLICATE_RATIO` | `DUPLICATE_RATIO` |  |
| `skill_lesson_filter` | `IDENTIFIER` | `?IDENTIFIER` |  |
| `skill_lesson_filter` | `MAX_ADDED_LINES` | `MAX_?ADDED_LINES` |  |
| `skill_lesson_filter` | `MAX_SKILL_LINES` | `MAX_SKILL_LINES` |  |
| `skill_lesson_filter` | `MAX_SKILL_SECTIONS` | `MAX_SKILL_?SECTIONS` |  |
| `skill_lesson_filter` | `PY_FILE` | `PY_FILE` |  |
| `skill_lesson_filter` | `RENAME_COMMIT` | `RENAME_COMMIT` |  |
| `skill_lesson_filter` | `RENAME_DICTS` | `RENAME_?DICTS` |  |
| `skill_lesson_filter` | `REPO` | `REPO` |  |
| `skill_lesson_filter` | `RULE_LABELS` | `RULE_LABELS` |  |
| `skill_lesson_filter` | `SOURCE_OF_TRUTH` | `SOURCE_OF_?TRUTH` |  |
| `skill_lesson_filter` | `STATE` | `STATE` |  |
| `skill_lesson_filter` | `TASK_END_GRACE_SECONDS` | `TASK_END_?GRACE_SECONDS` |  |
| `skill_lesson_filter` | `TELEGRAM_BUDGET` | `TELEGRAM_BUDGET` |  |
| `social_post` | `HOSTS` | `HOSTS` |  |
| `social_post` | `ROOT` | `ROOT` |  |
| `social_post` | `SCRIPT` | `SCRIPT` |  |
| `story_type` | `BOARD_IMAGE_BY_TYPE` | `BOARD_IMAGE_BY_TYPE` |  |
| `story_type` | `CODE_HAS_BALLOT` | `CODE_HAS_BALLOT` |  |
| `story_type` | `COUNTRY_OF_RANK` | `COUNTRY_OF_RANK` |  |
| `story_type` | `DEFAULT` | `DEFAULT` |  |
| `story_type` | `KEYWORD_LOWER_LAYER` | `KEYWORD_LOWER_LAYER` |  |
| `submit_common` | `MAX_ROUND` | `MAX_ROUND` |  |
| `submit_common` | `MINUTES_ALBUM_FIT_LEN` | `MINUTES_ALBUM_FIT_LEN` |  |
| `submit_common` | `ROOT` | `ROOT` |  |
| `swap_image_text` | `AREA_TO_SEALED` | `AREA_TO_SEALED` |  |
| `swap_image_text` | `DILATE_PX` | `DILATE_PX` |  |
| `swap_image_text` | `MAX_PX_LAMA` | `MAX_PX_LAMA` |  |
| `sync_hermes` | `ALL_GATE_OLD` | `ALL_GATE_OLD` |  |
| `sync_hermes` | `COLOR_UPSTREAM` | `COLOR_UPSTREAM` |  |
| `sync_hermes` | `FILE_CONFIG` | `FILE_CONFIG` |  |
| `sync_hermes` | `FILE_UPSTREAM` | `FILE_UPSTREAM` |  |
| `sync_hermes` | `HERMES_AGENT` | `HERMES_AGENT` |  |
| `sync_hermes` | `HOMES` | `HOMES` |  |
| `sync_hermes` | `IS_PLUGIN` | `IS_PLUGIN` |  |
| `sync_hermes` | `LOCK_PROMPT` | `LOCK_PROMPT` |  |
| `sync_hermes` | `LOCK_SECRET` | `LOCK_SECRET` |  |
| `sync_hermes` | `PLUGIN_FILE` | `PLUGIN_FILE` |  |
| `sync_hermes` | `PLUGIN_REPO` | `PLUGIN_REPO` |  |
| `sync_hermes` | `REPO` | `REPO` |  |
| `sync_hermes` | `ROOT` | `ROOT` |  |
| `sync_hermes` | `SCRIPT` | `SCRIPT` |  |
| `sync_hermes` | `TRACE` | `TRACE` |  |
| `task_bodies` | `CAROUSEL_BODY` | `CAROUSEL_BODY` |  |
| `task_bodies` | `EDU_BODY` | `EDU_BODY` |  |
| `task_bodies` | `END_ROLE_IMAGE` | `END_ROLE_IMAGE` |  |
| `task_bodies` | `ILLU_BODY` | `ILLU_BODY` |  |
| `task_bodies` | `WRITER_BODY` | `WRITER_BODY` |  |
| `teaser_assemble` | `CLOSING` | `CLOSING` |  |
| `teaser_assemble` | `LONG_BROKEN` | `LONG_BROKEN` |  |
| `teaser_assemble` | `LONG_THIN_LATE` | `LONG_THIN_LATE` |  |
| `teaser_assemble` | `PHRASE_WALL_TECHNIQUE` | `PHRASE_WALL_TECHNIQUE` |  |
| `tele_util` | `LIMIT` | `LIMIT` |  |
| `vietnamese` | `MARK_FORBID` | `MARK_FORBID` |  |
| `vietnamese` | `NEGATIVE_FACE_MARK` | `NEGATIVE_FACE_MARK` |  |
| `vietnamese` | `PHRASE_FACE_MARK` | `PHRASE_FACE_MARK` |  |
| `worker_scope_sweep` | `SCOPE_PATTERN` | `SCOPE_PATTERN` |  |

## E. Token chưa có trong bảng

| token | lần | ví dụ module |
|---|---|---|
| `cluttered` | 11 | card, carousel, prepare.vision |
| `upload` | 6 | approve_base, approve_post |
| `amount` | 5 | scan_business |
| `deal` | 4 | scan_business |
| `follow` | 3 | scan_business |
| `up` | 3 | scan_business |
| `pr` | 3 | manifest_build, skill_lesson_commit |
| `note` | 2 | approve_command, approve_post, image_rules_dre |
| `writers` | 2 | role |
| `keywords` | 2 | scan_business |
| `worktree` | 2 | skill_lesson_commit |
| `pending` | 2 | moat_publish, skill_lesson_commit, skill_lesson_filter |
| `identifier` | 2 | skill_lesson_filter |
| `delays` | 2 | approve_base, send_telegram |
| `floor` | 2 | approve_post, image_rules_dre |
| `currency` | 2 | scan_business |
| `compress` | 1 | approve_post |
| `answer` | 1 | approve_post |
| `retarget` | 1 | approve_post |
| `case` | 1 | image_rules_dre |
| `nouns` | 1 | prepare.source |
| `proves` | 1 | ranking |
| `proving` | 1 | ranking |
| `module` | 1 | role, skill_lesson_filter |
| `amounts` | 1 | scan_business |
| `capitalized` | 1 | scan_business |
| `sent` | 1 | cleanup, send_telegram, skill_lesson_filter |
| `verdict` | 1 | skill_lesson_approve, skill_lesson_commit, skill_lesson_filter |
| `metadata` | 1 | skill_lesson_commit |
| `comment` | 1 | skill_lesson_commit |
| `enable` | 1 | skill_lesson_commit |
| `discard` | 1 | skill_lesson_commit |
| `defines` | 1 | skill_lesson_filter |
| `symbol` | 1 | skill_lesson_commit, skill_lesson_filter |
| `commits` | 1 | skill_lesson_filter |
| `since` | 1 | skill_lesson_filter |
| `symbols` | 1 | skill_lesson_commit, skill_lesson_filter |
| `judge` | 1 | skill_lesson_filter |
| `collect` | 1 | skill_lesson_filter |
| `choice` | 1 | submit_common |
| `scopes` | 1 | worker_scope_sweep |
| `stop` | 1 | worker_scope_sweep |
| `variance` | 1 | carousel |
| `kinh` | 1 | gin_submit |
| `tram` | 1 | gin_submit |
| `` | 1 |  |
| `cross` | 1 | scan_business |
| `window` | 1 | scan_business |
| `shared` | 1 | scan_business |
| `decision` | 1 | skill_lesson_approve, skill_lesson_commit |
| `safe` | 1 | skill_lesson_approve |
| `avoid` | 1 | skill_lesson_filter |
| `backtick` | 1 | skill_lesson_filter |
| `bug` | 1 | skill_lesson_filter |
| `suffixes` | 1 | skill_lesson_filter |
| `dotted` | 1 | skill_lesson_filter |
| `added` | 1 | skill_lesson_filter |
| `sections` | 1 | skill_lesson_filter |
| `dicts` | 1 | skill_lesson_filter |
| `truth` | 1 | skill_lesson_filter |
| `grace` | 1 | skill_lesson_filter, worker_scope_sweep |

## F. Va chạm tên — PHẢI SỬA trước khi rename

Hai hàm/lớp top-level khác nhau trong CÙNG module mà dịch ra CÙNG một tên — rename thẳng sẽ ghi đè, gây lỗi gọi thật. Sửa bằng `overrides.json` (`"module.ten_goc": "ten_moi"`), không cần đụng bảng từ điển chung.

**Không còn va chạm nào** — đo trên 114 module / 1169 hàm-lớp top-level.

## F2. Tên module mới đè lên tên đã dùng — PHẢI SỬA trước khi đổi tên tệp

Tên tệp mới trùng một biến/tham số/def/alias đang có ở tệp khác (kể cả tests): sau rename tên đó SHADOW module → `UnboundLocalError`/pyflakes đỏ. Sửa: đổi tên module trong `cum.json` (khoá = tên tệp cũ), hoặc đổi biến cục bộ đó.

**Không có.**