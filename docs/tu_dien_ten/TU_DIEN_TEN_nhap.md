# TỪ ĐIỂN TÊN — bản nháp bước 0 (chưa đụng mã)

Nguồn: 103 module, 1058 def/class (930 tên khác nhau), 680 hằng số. Đề xuất sinh máy từ bảng A; `?token` = chưa có trong bảng; ⚠️ = token mơ hồ, phải chọn tay theo nghĩa tại chỗ.

Luật: rename 1-1 giữ cấu trúc cụm; khoá JSON trên đĩa KHÔNG đổi; tên vai (ethan/dre/kite…) giữ; token đã là English giữ nguyên.

## A. Từ gốc — CỤM (khớp trước)

| Việt | English |
|---|---|
| `anh_bai` | `article_images` |
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
| `ban_do` | `map` |
| `ban_giao` | `handoff` |
| `bang_chung` | `evidence` |
| `bang_den` | `blackboard` |
| `bang_du_lieu` | `table` |
| `bang_model` | `model_boards` |
| `bao_cao` | `report` |
| `bao_cao_manifest` | `manifest_report` |
| `bao_chet_lap` | `report_repeated_crash` |
| `bao_khac` | `other_outlets` |
| `bao_mat` | `security` |
| `bat_buoc` | `required` |
| `bat_dau` | `start` |
| `bi_mat` | `secret` |
| `binh_thuong` | `normal` |
| `bo_dem` | `buffer` |
| `bo_hau_to_site` | `strip_site_suffix` |
| `bo_qua` | `skip` |
| `bo_qua_nguon` | `skip_source` |
| `brief_chung` | `brief_common` |
| `cai_dat` | `setup` |
| `cam_ket` | `commit` |
| `can_anh_xep_hang` | `needs_ranking_image` |
| `canh_bao` | `warning` |
| `canh_dai` | `long_side` |
| `canh_ngan` | `short_side` |
| `cao_nhat` | `highest` |
| `caption_check` | `caption_check` |
| `cau_bi_dung` | `killed_message` |
| `cau_chay_lau` | `long_run_message` |
| `cau_hinh` | `config` |
| `chat_luong` | `quality` |
| `chat_router` | `chat_router` |
| `chi_muc` | `index` |
| `chi_phi` | `cost` |
| `chieu_cao` | `height` |
| `chieu_rong` | `width` |
| `cho_luot` | `wait_slot` |
| `chon_so` | `pick_number` |
| `chu_de` | `topic` |
| `chu_de_topic` | `topic` |
| `chu_thich` | `annotation` |
| `chuan_bi` | `prepare` |
| `chup_chart` | `capture_chart` |
| `chup_lead` | `capture_lead` |
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
| `cung_tin` | `same_story` |
| `da_dung` | `used` |
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
| `dieu_kien` | `condition` |
| `dinh_dang` | `format` |
| `dinh_tuyen` | `route` |
| `do_tre` | `latency` |
| `do_uu_tien` | `priority` |
| `doc_gia` | `reader` |
| `doi_chu_anh` | `swap_image_text` |
| `doi_khoa` | `wait_lock` |
| `dong_bo` | `sync` |
| `dong_dau` | `stamp` |
| `dong_thoi` | `concurrent` |
| `draft_write` | `draft_write` |
| `du_lieu` | `data` |
| `du_nguyen_lieu` | `has_enough_material` |
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
| `ghi_log` | `log` |
| `gia_tri` | `value` |
| `giai_don` | `resolve_single` |
| `giai_ghep` | `resolve_stack` |
| `giai_muc` | `resolve_item` |
| `giai_thich` | `explain` |
| `giao_dich` | `transaction` |
| `giao_viec` | `dispatch` |
| `gio_han` | `time_limit` |
| `gioi_han` | `limit` |
| `goi_y_nguon` | `suggest_sources` |
| `gui_telegram` | `send_telegram` |
| `ha_cap` | `downgrade` |
| `hang_cua` | `rank_of` |
| `hang_doi` | `queue` |
| `hang_ngang` | `row` |
| `hang_trong_tin` | `vendors_in_story` |
| `hau_to` | `suffix` |
| `hermes_adapter` | `hermes_adapter` |
| `hieu_nang` | `performance` |
| `hoan_tac` | `rollback` |
| `hoan_tat` | `finish` |
| `hoan_thanh` | `complete` |
| `hoi_thoai` | `conversation` |
| `hop_dong` | `contract` |
| `hop_le` | `valid` |
| `hop_nhat` | `merge` |
| `im_lang` | `silent` |
| `ke_tiep` | `next` |
| `ket_noi` | `connection` |
| `ket_qua` | `result` |
| `ket_thuc` | `end` |
| `kha_nang` | `capability` |
| `khai_niem` | `concept` |
| `kho_khoa` | `locked_format` |
| `kho_the` | `card_format` |
| `khoa_api` | `api_key` |
| `khoa_chinh` | `primary_key` |
| `khoi_dong` | `start` |
| `khoi_phuc` | `restore` |
| `khong_browser` | `no_browser` |
| `khong_gui` | `no_send` |
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
| `la_tin_xep_hang` | `is_ranking_story` |
| `lam_lai` | `redo` |
| `lam_moi` | `fresh` |
| `lan_chay` | `run` |
| `lan_chay_cuoi` | `last_run` |
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
| `manifest_build` | `manifest_build` |
| `manifest_chung` | `manifest_common` |
| `manifest_ghi` | `manifest_write` |
| `mat_khau` | `password` |
| `mat_nguoi` | `face` |
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
| `moi_truong` | `environment` |
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
| `nhip_tho` | `heartbeat` |
| `noi_dung` | `content` |
| `nop_chung` | `submit_common` |
| `ong_chu` | `boss` |
| `phan_loai` | `classify` |
| `phan_tich` | `analyze` |
| `phan_tram` | `percent` |
| `phat_hien` | `detect` |
| `phien_ban` | `version` |
| `phien_browser` | `browser_session` |
| `phien_lam_viec` | `session` |
| `phong_ban` | `department` |
| `pid_song` | `pid_alive` |
| `quan_trong` | `important` |
| `quet_chuan_bi` | `scan_prepare` |
| `quet_chung` | `scan_common` |
| `quet_nop` | `scan_submit` |
| `quy_uoc` | `convention` |
| `render_edu` | `render_edu` |
| `route_thieu_anh` | `route_missing_images` |
| `san_pham` | `product` |
| `san_sang` | `ready` |
| `sao_luu` | `backup` |
| `sap_xep` | `sort` |
| `scan_business` | `scan_business` |
| `scan_models` | `scan_models` |
| `scan_sources` | `scan_sources` |
| `slug_that` | `canonical_slug` |
| `so_anh_toi_thieu` | `min_images` |
| `so_lieu` | `figures` |
| `so_luong` | `quantity` |
| `so_sanh` | `compare` |
| `so_thu_tu` | `ordinal` |
| `soat_cron` | `audit_cron` |
| `social_post` | `social_post` |
| `song_song` | `parallel` |
| `su_co` | `incident` |
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
| `thap_nhat` | `lowest` |
| `the_du_phong` | `fallback_card` |
| `theo_doi` | `monitor` |
| `theo_doi_9router` | `monitor_9router` |
| `thiet_lap` | `settings` |
| `thong_bao` | `notify` |
| `thong_luong` | `throughput` |
| `thu_muc` | `directory` |
| `thu_tu` | `order` |
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
| `toa_soan` | `outlet` |
| `toan_bo` | `entire` |
| `toc_do` | `speed` |
| `toi_da` | `max` |
| `toi_thieu` | `min` |
| `tom_tat` | `summary` |
| `tong_cong` | `total` |
| `tong_hop` | `aggregate` |
| `tra_ve` | `return` |
| `trang_cong_bo` | `announcement_page` |
| `trang_thai` | `status` |
| `trong_so` | `weight` |
| `trung_binh` | `average` |
| `trung_gan_giong` | `near_duplicate` |
| `truy_van` | `queries` |
| `tu_choi` | `reject` |
| `tu_cung_tin` | `story_tokens` |
| `tu_dong` | `auto` |
| `tu_khoa` | `keyword` |
| `tu_lieu` | `material` |
| `ung_vien` | `candidate` |
| `url_commons` | `commons_urls` |
| `uu_tien` | `priority` |
| `vai_tro` | `role` |
| `vai_viet_cua` | `writer_for` |
| `van_ban` | `text` |
| `vi_tri` | `position` |
| `vong_bu` | `fallback_rounds` |
| `vong_lap` | `loop` |
| `website_hang` | `vendor_website` |
| `xa_hoi` | `social` |
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
| `bai` | `article` |  |
| `bam` | `press` |  |
| `ban` | `copy` | ⚠️ bản=copy / bàn=table / bán=sell |
| `bang` | `board` | ⚠️ bảng=board/table |
| `bao` | `outlet` |  |
| `bat` | `catch` | ⚠️ bắt=catch / bật=enable |
| `bi` | `got` |  |
| `bia` | `cover` |  |
| `bien` | `variable` |  |
| `binh` | `normal` |  |
| `bo` | `drop` | ⚠️ bỏ=drop / bộ=set |
| `boc` | `extract` |  |
| `boi` | `context` |  |
| `brand` | `brand` |  |
| `brief` | `brief` |  |
| `bu` | `fallback` |  |
| `buoc` | `step` |  |
| `ca` | `all` |  |
| `cac` | `each` |  |
| `cach` | `way` |  |
| `cai` | `item` |  |
| `cang` | `tension` |  |
| `canh` | `edge` | ⚠️ cạnh=edge / cảnh=warning |
| `cao` | `height` |  |
| `cap` | `pair` |  |
| `cat` | `crop` |  |
| `cau` | `sentence` |  |
| `chac` | `sure` |  |
| `cham` | `touch` |  |
| `chan` | `block` |  |
| `chay` | `run` |  |
| `chep` | `copy` |  |
| `chet` | `crash` |  |
| `chi` | `only` | ⚠️ chỉ=only / chi=spend |
| `chieu` | `dimension` |  |
| `chinh` | `main` |  |
| `cho` | `wait` | ⚠️ chờ=wait / cho=for/give |
| `chon` | `pick` |  |
| `chot` | `finalize` |  |
| `chu` | `text` | ⚠️ chữ=text / chủ=owner |
| `chua` | `not_yet` |  |
| `chuan` | `standard` |  |
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
| `da` | `already` |  |
| `dai` | `long` |  |
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
| `dia` | `disk` |  |
| `dich` | `translate` |  |
| `diem` | `score` |  |
| `dieu` | `control` |  |
| `dinh` | `fixed` |  |
| `do` | `measure` |  |
| `doan` | `guess` |  |
| `doc` | `read` | ⚠️ đọc=read / dọc=portrait |
| `doi` | `change` |  |
| `don` | `single` |  |
| `dong` | `line` | ⚠️ dòng=line / đóng=close / động=motion |
| `draft` | `draft` |  |
| `du` | `enough` |  |
| `dung` | `use` | ⚠️ dùng=use / dừng=stop / đúng=correct / dựng=build |
| `duoc` | `ok` |  |
| `duoi` | `under` |  |
| `duong` | `path` |  |
| `duyet` | `approve` |  |
| `ep` | `force` |  |
| `gan` | `near` |  |
| `gap` | `meet` |  |
| `ghep` | `stack` |  |
| `ghi` | `write` |  |
| `gia` | `fake` | ⚠️ giả=fake / giá=price |
| `giai` | `resolve` |  |
| `giao` | `hand` |  |
| `giay` | `seconds` |  |
| `gio` | `hours` |  |
| `giong` | `voice` |  |
| `giu` | `keep` |  |
| `giua` | `middle` |  |
| `goc` | `original` |  |
| `goi` | `call` |  |
| `gom` | `gather` |  |
| `gui` | `send` |  |
| `hai` | `two` |  |
| `han` | `limit` |  |
| `hang` | `rank` | ⚠️ hạng=rank / hàng=row / hãng=vendor |
| `het` | `all_done` |  |
| `hien` | `show` |  |
| `hieu` | `understand` |  |
| `hinh` | `figure` |  |
| `hoa` | `ify` |  |
| `hoi` | `ask` |  |
| `hong` | `broken` |  |
| `hop` | `box` |  |
| `id` | `id` |  |
| `im` | `silent` |  |
| `in` | `print` |  |
| `kem` | `with` |  |
| `kenh` | `channel` |  |
| `keo` | `drag` |  |
| `ket` | `end` |  |
| `khac` | `other` |  |
| `khach` | `customer` |  |
| `khan` | `urgent` |  |
| `kho` | `size` |  |
| `khoa` | `lock` | ⚠️ khoá=lock / khoá=key |
| `khoang` | `range` |  |
| `khoi` | `block` |  |
| `khong` | `no` |  |
| `khop` | `match` |  |
| `khung` | `frame` |  |
| `kich` | `size` |  |
| `kiem` | `check` |  |
| `kieu` | `kind` |  |
| `la` | `is` |  |
| `lai` | `again` |  |
| `lam` | `make` |  |
| `lan` | `attempt` | ⚠️ lần=time / lan=spread |
| `lat` | `flip` |  |
| `lau` | `long_time` |  |
| `lay` | `take` |  |
| `le` | `odd` |  |
| `lech` | `offset` |  |
| `lenh` | `command` |  |
| `lich` | `schedule` |  |
| `lieu` | `material` |  |
| `link` | `link` |  |
| `lo` | `leak` |  |
| `loai` | `type` |  |
| `loc` | `filter` |  |
| `loi` | `error` |  |
| `lon` | `large` |  |
| `lop` | `layer` |  |
| `luat` | `rules` |  |
| `luon` | `always` |  |
| `luot` | `slot` |  |
| `luu` | `save` |  |
| `ma` | `code` | ⚠️ mã=code / mà=but |
| `mac` | `default` |  |
| `man` | `screen` |  |
| `mang` | `network` |  |
| `manifest` | `manifest` |  |
| `mat` | `face` |  |
| `mau` | `color` | ⚠️ màu=color / mẫu=sample |
| `may` | `machine` |  |
| `mien` | `domain` |  |
| `mieng` | `piece` |  |
| `mo` | `open` |  |
| `moc` | `timestamp` |  |
| `model` | `model` |  |
| `moi` | `new` | ⚠️ mới=new / mỗi=each / mời=invite |
| `mot` | `one` |  |
| `muc` | `item` | ⚠️ mục=item / mức=level |
| `nam` | `lie` |  |
| `nap` | `load` |  |
| `nay` | `this` |  |
| `nen` | `background` | ⚠️ nền=background / nên=should |
| `neu` | `if` |  |
| `ngan` | `short` |  |
| `ngang` | `landscape` |  |
| `ngat` | `break` |  |
| `ngay` | `date` |  |
| `nghich` | `reverse` |  |
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
| `phai` | `right` |  |
| `phan` | `part` | ⚠️ phần=part / phân=classify |
| `phang` | `flat` |  |
| `phat` | `emit` |  |
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
| `rong` | `empty` | ⚠️ rỗng=empty / rộng=wide |
| `sach` | `clean` |  |
| `sai` | `wrong` |  |
| `san` | `ready` |  |
| `sang` | `bright` | ⚠️ sáng=bright / sang=to |
| `sap` | `sort` |  |
| `sau` | `after` |  |
| `sinh` | `generate` |  |
| `slide` | `slide` |  |
| `slug` | `slug` |  |
| `so` | `count` | ⚠️ số=number / so=compare |
| `soat` | `audit` |  |
| `song` | `alive` |  |
| `spec` | `spec` |  |
| `sua` | `fix` |  |
| `suc` | `health` |  |
| `tach` | `extract` |  |
| `tai` | `download` |  |
| `tam` | `temp` |  |
| `tang` | `layer` |  |
| `tao` | `create` |  |
| `tap` | `set` |  |
| `task` | `task` |  |
| `tat` | `all` |  |
| `tay` | `manual` |  |
| `ten` | `name` |  |
| `tep` | `file` |  |
| `text` | `text` |  |
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
| `thich` | `explain` |  |
| `thieu` | `missing` |  |
| `thoat` | `exit` |  |
| `thoi` | `time` |  |
| `thong` | `info` |  |
| `thu` | `try` | ⚠️ thử=try / thứ=order / thu=collect |
| `thua` | `excess` |  |
| `thuc` | `actual` |  |
| `thuong` | `regular` |  |
| `tien` | `money` |  |
| `tiep` | `next` |  |
| `tieu` | `consume` |  |
| `tim` | `find` |  |
| `tin` | `story` |  |
| `tinh` | `static` |  |
| `title` | `title` |  |
| `toan` | `whole` |  |
| `toi` | `dark` | ⚠️ tối=dark / tới=until |
| `tong` | `total` |  |
| `tot` | `good` |  |
| `tra` | `return` | ⚠️ trả=return / tra=lookup |
| `trai` | `left` |  |
| `tran` | `ceiling` |  |
| `trang` | `page` |  |
| `tren` | `on` |  |
| `treo` | `stalled` |  |
| `tron` | `full` |  |
| `trong` | `within` |  |
| `trung` | `duplicate` |  |
| `truoc` | `before` |  |
| `truy` | `trace` |  |
| `tu` | `from` | ⚠️ từ=from/word / tự=self |
| `tuan` | `week` |  |
| `tuc` | `instant` |  |
| `tuong` | `wall` |  |
| `ty` | `billion` |  |
| `url` | `url` |  |
| `uu` | `prefer` |  |
| `va` | `and` |  |
| `vai` | `role` |  |
| `van` | `still` | ⚠️ vẫn=still / văn=text |
| `vao` | `into` |  |
| `ve` | `about` |  |
| `vet` | `trace` |  |
| `vi` | `because` |  |
| `viec` | `job` |  |
| `viet` | `write` |  |
| `vong` | `round` |  |
| `vua` | `fit` |  |
| `vung` | `region` |  |
| `xac` | `confirm` |  |
| `xau` | `ugly` |  |
| `xet` | `consider` |  |
| `xoa` | `delete` |  |
| `xong` | `done` |  |
| `xuat` | `export` |  |
| `yeu` | `weak` |  |

## B. Module (103)

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `ada_chuan_bi` | `ada_prepare` |  |
| `ada_nop` | `ada_submit` |  |
| `anh_bai` | `article_images` |  |
| `anh_chuan_bi` | `image_prepare` |  |
| `anh_khai_niem` | `image_concept` |  |
| `anh_thuc_the` | `entity_images` |  |
| `anh_thuong_hieu` | `image_brand` |  |
| `approve_service` | `?approve_?service` |  |
| `article_extract` | `article_extract` |  |
| `arxiv_bia` | `arxiv_cover` |  |
| `arxiv_hinh` | `arxiv_figures` |  |
| `bang_den` | `blackboard` |  |
| `bang_model` | `model_boards` |  |
| `bao_cao_manifest` | `manifest_report` |  |
| `bat_buoc` | `required` |  |
| `bob_nop` | `bob_submit` |  |
| `brief_chung` | `brief_common` |  |
| `cape_chuan_bi` | `cape_prepare` |  |
| `cape_nop` | `cape_submit` |  |
| `caption_check` | `caption_check` |  |
| `card` | `card` |  |
| `carousel` | `?carousel` |  |
| `chat_router` | `chat_router` |  |
| `chuan_bi.__init__` | `prepare.?_?_init_?_?` |  |
| `chuan_bi.browser` | `prepare.browser` |  |
| `chuan_bi.chung` | `prepare.?chung` |  |
| `chuan_bi.manifest` | `prepare.manifest` |  |
| `chuan_bi.nguon` | `prepare.source` |  |
| `chuan_bi.nhin` | `prepare.vision` |  |
| `chuan_bi.tai_loc` | `prepare.download_filter` |  |
| `chuan_bi.vong_bu` | `prepare.fallback_rounds` |  |
| `chup_chart` | `capture_chart` |  |
| `chup_trang` | `capture_page` |  |
| `cleanup` | `cleanup` |  |
| `cost_squeeze` | `cost_squeeze` |  |
| `crop_ti_le` | `crop_ratio` |  |
| `deck` | `deck` |  |
| `doi_chu_anh` | `swap_image_text` |  |
| `dong_bo_hermes` | `sync_hermes` |  |
| `draft_write` | `draft_write` |  |
| `dre_chuan_bi` | `dre_prepare` |  |
| `dre_nop` | `dre_submit` |  |
| `duyet_bai` | `approve_post` |  |
| `duyet_chat` | `approve_chat` |  |
| `duyet_chon_tin` | `approve_pick` |  |
| `duyet_co_so` | `approve_base` |  |
| `duyet_giao_viec` | `approve_dispatch` |  |
| `duyet_lenh` | `approve_command` |  |
| `emoji_deck` | `emoji_deck` |  |
| `env_load` | `env_load` |  |
| `ethan_chuan_bi` | `ethan_prepare` |  |
| `ethan_nop` | `ethan_submit` |  |
| `ghi_log` | `log` |  |
| `gin_chuan_bi` | `gin_prepare` |  |
| `gin_nop` | `gin_submit` |  |
| `gui_telegram` | `send_telegram` |  |
| `hermes_adapter` | `hermes_adapter` |  |
| `itachi_chuan_bi` | `itachi_prepare` |  |
| `itachi_nop` | `itachi_submit` |  |
| `jika_chuan_bi` | `jika_prepare` |  |
| `jika_nop` | `jika_submit` |  |
| `khung_anh` | `image_frame` |  |
| `kiem_hermes` | `check_hermes` |  |
| `kiem_moi_truong` | `check_env` |  |
| `kite_chuan_bi` | `kite_prepare` |  |
| `kite_nop` | `kite_submit` |  |
| `loai_tin` | `story_type` |  |
| `luat_anh` | `image_rules` |  |
| `manifest_build` | `manifest_build` |  |
| `manifest_chung` | `manifest_common` |  |
| `manifest_ghi` | `manifest_write` |  |
| `miles_chuan_bi` | `miles_prepare` |  |
| `miles_nop` | `miles_submit` |  |
| `moat_publish` | `moat_publish` |  |
| `model_audition` | `model_audition` |  |
| `model_watch` | `model_watch` |  |
| `nen_chu` | `text_bg` |  |
| `nguon_bai` | `article_sources` |  |
| `nhat_ky` | `journal` |  |
| `nhat_ky_web` | `journal_web` |  |
| `nop_chung` | `submit_common` |  |
| `phien_browser` | `browser_session` |  |
| `publish` | `?publish` |  |
| `quet_chuan_bi` | `scan_prepare` |  |
| `quet_chung` | `scan_common` |  |
| `quet_nop` | `scan_submit` |  |
| `render_edu` | `render_edu` |  |
| `route_thieu_anh` | `route_missing_images` |  |
| `scan_business` | `scan_business` |  |
| `scan_models` | `scan_models` |  |
| `scan_sources` | `scan_sources` |  |
| `schema` | `?schema` |  |
| `soat_cron` | `audit_cron` |  |
| `social_post` | `social_post` |  |
| `task_bodies` | `task_bodies` |  |
| `teaser_assemble` | `teaser_assemble` |  |
| `tele_util` | `tele_util` |  |
| `theo_doi_9router` | `monitor_9router` |  |
| `tieng_viet` | `vietnamese` |  |
| `tim_anh_them` | `find_more_images` |  |
| `tu_lieu` | `material` |  |
| `vai` | `role` |  |
| `xep_hang` | `ranking` |  |

## C. Hàm/lớp theo module

### `ada_chuan_bi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `workdir` | `workdir` |  |
| `_bac` | `_?bac` |  |
| `gom_manifest` | `gather_manifest` |  |
| `gom_draft` | `gather_draft` |  |
| `gom_kanban` | `gather_kanban` |  |
| `gom_token` | `gather_token` |  |
| `gom_9router` | `gather_?9router` |  |
| `viet_brief` | `write_brief` |  |

### `ada_nop`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `dung_bao_cao` | `use_report` | ⚠️ dung |

### `anh_bai`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_tai` | `_download` |  |
| `anh_trong_trang` | `image_within_page` |  |
| `them` | `extra` |  |
| `bao_khac` | `other_outlets` |  |
| `_do_hoa` | `_measure_ify` |  |
| `do_anh` | `measure_image` |  |
| `cham` | `touch` |  |
| `tim` | `find` |  |
| `_da_thu_nho` | `_already_try_small` | ⚠️ thu |

### `anh_chuan_bi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `chuan_bi` | `prepare` |  |
| `workdir` | `workdir` |  |
| `nap_meta` | `load_meta` |  |
| `_cho_luot` | `_wait_slot` |  |
| `_mo_ta_thieu_anh` | `_description_missing_image` |  |
| `_doi_khoa` | `_wait_lock` |  |
| `dem_chet` | `count_crashes` |  |
| `_bao_chet_lap` | `_report_repeated_crash` |  |
| `chay` | `run` |  |

### `anh_khai_niem`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_nuoc_trong` | `_country_within` |  |
| `tu_khoa_heuristic` | `keyword_?heuristic` |  |
| `tu_khoa_llm` | `keyword_?llm` |  |
| `doc_tra_loi_llm` | `read_return_error_?llm` | ⚠️ doc tra |
| `tu_khoa_khai_niem` | `keyword_concept` |  |
| `_tu_dac_trung` | `_from_distinctive` | ⚠️ tu |
| `loc_commons` | `filter_commons` |  |
| `anh_khai_niem` | `image_concept` |  |
| `cau_hoi_vision` | `sentence_ask_vision` |  |
| `nhan_khai_niem` | `label_concept` | ⚠️ nhan |

### `anh_thuc_the`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `thuc_the_trong_tieu_de` | `actual_card_within_title` | ⚠️ the |
| `pageimages` | `?pageimages` |  |
| `commons_theo_cum` | `commons_by_phrase` |  |
| `anh_thuc_the` | `entity_images` |  |
| `nhan_thuc_the` | `label_actual_card` | ⚠️ nhan the |

### `anh_thuong_hieu`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_tu_dac_trung` | `_from_distinctive` | ⚠️ tu |
| `_co_cum` | `_has_phrase` |  |
| `_co_tu` | `_has_word` |  |
| `_nhieu` | `_many` |  |
| `hang_trong_tin` | `vendors_in_story` |  |
| `truy_van` | `queries` |  |
| `loc_commons` | `filter_commons` |  |
| `_hoi_api` | `_ask_api` |  |
| `_tep_claim` | `_file_claim` |  |
| `_qid_claim` | `_qid_claim` |  |
| `qid_hang` | `qid_rank` | ⚠️ hang |
| `tu_lieu_wikidata` | `material_wikidata` |  |
| `_slug` | `_slug` |  |
| `_khoa_model` | `_lock_model` | ⚠️ khoa |
| `website_hang` | `vendor_website` |  |
| `_tai_html` | `_download_html` |  |
| `trang_cong_bo` | `announcement_page` |  |
| `url_commons` | `commons_urls` |  |
| `the_logo` | `card_logo` | ⚠️ the |
| `_do_sang_logo` | `_measure_bright_logo` | ⚠️ sang |
| `anh_wikidata` | `image_wikidata` |  |
| `_ung_vien` | `_candidate` |  |
| `anh_nguoi_ngang` | `image_person_landscape` |  |
| `anh_co_phieu` | `image_has_ballot` |  |
| `anh_hang` | `vendor_images` |  |
| `hang_co_model` | `rank_has_model` | ⚠️ hang |
| `cau_hoi_vision` | `sentence_ask_vision` |  |
| `_hoi_commons` | `_ask_commons` |  |
| `nhan_theo_loai` | `label_by_type` | ⚠️ nhan |
| `nhan_thuong_hieu` | `label_brand` | ⚠️ nhan |

### `approve_service`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_tai_anh_dinh_kem` | `_download_image_fixed_with` |  |
| `_bao_khong_ho_tro` | `_outlet_no_?ho_?tro` |  |
| `_lenh_chon_neu_co` | `_pick_command_if_has` |  |
| `_bao_khong_phai_reply` | `_outlet_no_right_reply` |  |
| `handle_message` | `handle_?message` |  |
| `_ghi_offset` | `_write_offset` |  |
| `_doc_offset` | `_read_offset` | ⚠️ doc |
| `_soat_tirith` | `_audit_?tirith` |  |
| `_cuu_bai_ket_publishing` | `_?cuu_article_end_?publishing` |  |
| `loop` | `loop` |  |

### `article_extract`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `fetch` | `fetch` |  |
| `_parser` | `_parser` |  |
| `extract` | `?extract` |  |
| `meta` | `meta` |  |

### `arxiv_bia`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `la_arxiv` | `is_arxiv` |  |
| `tai_pdf` | `download_pdf` |  |
| `chup_bia` | `capture_cover` |  |
| `_toi_nua_duoi` | `_dark_half_under` | ⚠️ toi |

### `arxiv_hinh`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `la_chu_thich` | `is_annotation` |  |
| `la_than_bai` | `is_body_article` |  |
| `_giao` | `_hand` |  |
| `_gop` | `_?gop` |  |
| `_chong_ngang` | `_?chong_landscape` |  |
| `chu_thich_du_dong` | `annotation_enough_line` | ⚠️ dong |
| `_bo_chay_dau` | `_drop_run_mark` | ⚠️ bo dau |
| `_do_hoa_trong_dai` | `_measure_ify_within_long` |  |
| `vung_hinh` | `region_figure` |  |
| `pdf_cua_link` | `pdf_of_link` |  |
| `_do_hoa_trang` | `_measure_ify_page` |  |
| `_khong_trang_tron` | `_no_page_full` |  |
| `boc` | `extract` |  |
| `tai_pdf` | `download_pdf` |  |
| `ung_vien` | `candidate` |  |

### `bang_den`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_meta_path` | `_meta_path` |  |
| `_meta` | `_meta` |  |
| `_ghi_meta` | `_write_meta` |  |
| `_chuan_home` | `_standard_home` |  |
| `_kb` | `_?kb` |  |
| `root_of` | `root_?of` |  |
| `tao_root` | `create_root` |  |
| `ghi` | `write` |  |
| `ghi_nen` | `write_background` | ⚠️ nen |
| `doc` | `read` | ⚠️ doc |
| `_gia_tri` | `_value` |  |

### `bang_model`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `Bang` | `Board` | ⚠️ bang |
| `hang_va_ngay` | `rank_and_date` | ⚠️ hang |

### `bao_cao_manifest`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `dung` | `use` | ⚠️ dung |

### `bat_buoc`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `tep` | `file` |  |
| `doc` | `read` | ⚠️ doc |
| `_ghi` | `_write` |  |
| `them` | `extra` |  |
| `them_nhieu` | `extra_many` |  |
| `_chuan` | `_standard` |  |
| `khop` | `match` |  |
| `link_goi_y` | `link_call_y` |  |
| `kiem` | `check` |  |
| `xoa` | `delete` |  |
| `in_danh_sach` | `in_list_clean` |  |

### `bob_nop`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `handle_kenh` | `handle_channel` |  |
| `bang_mood` | `board_?mood` | ⚠️ bang |
| `mood_tu_vision` | `?mood_from_vision` | ⚠️ tu |
| `la_url` | `is_url` |  |
| `lay_anh` | `take_image` |  |
| `dong_khung` | `line_frame` | ⚠️ dong |
| `_env_sach` | `_env_clean` |  |
| `gui` | `send` |  |

### `brief_chung`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `dau` | `mark` | ⚠️ dau |
| `khoi_lam_lai` | `block_redo` |  |
| `khoi_tu_lieu` | `block_material` |  |
| `duoi` | `under` |  |

### `cape_chuan_bi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `slug` | `slug` |  |
| `workdir` | `workdir` |  |
| `boc` | `extract` |  |
| `viet_brief` | `write_brief` |  |

### `cape_nop`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|

### `caption_check`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `ty_le_dau` | `billion_odd_mark` | ⚠️ dau |
| `_bo_the` | `_drop_card` | ⚠️ bo the |
| `_tu` | `_from` | ⚠️ tu |
| `lap_cum` | `?lap_phrase` |  |
| `so_trong` | `count_within` | ⚠️ so |
| `so_la` | `count_is` | ⚠️ so |
| `_kiem_do_dai` | `_check_measure_long` |  |
| `_kiem_van_phong` | `_check_still_room` | ⚠️ van |
| `_kiem_so_lieu` | `_check_figures` |  |
| `kiem` | `check` |  |

### `card`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `dat_thuong_hieu` | `set_brand` |  |
| `_f` | `_f` |  |
| `_do_sang` | `_measure_bright` | ⚠️ sang |
| `_du_sang` | `_enough_bright` | ⚠️ sang |
| `_du_toi` | `_enough_dark` | ⚠️ toi |
| `_mau_cua_hang` | `_color_of_rank` | ⚠️ hang mau |
| `_tach_nhan` | `_extract_label` | ⚠️ nhan |
| `_mau_hang_trong` | `_color_rank_within` | ⚠️ hang mau |
| `_rong_dong` | `_empty_line` | ⚠️ dong rong |
| `_ve_dong` | `_about_line` | ⚠️ dong |
| `_rong_tracked` | `_empty_?tracked` | ⚠️ rong |
| `_ve_tracked` | `_about_?tracked` |  |
| `_wrap` | `_?wrap` |  |
| `_fit_text` | `_fit_text` |  |
| `_grow_title` | `_grow_title` |  |
| `_buoc_dong` | `_step_line` | ⚠️ dong |
| `ghep_doc` | `stack_read` | ⚠️ doc |
| `_chan_anh_thap` | `_block_image_low` |  |
| `_chan_chuan_anh` | `_block_standard_image` |  |
| `_chan_chart` | `_block_chart` |  |
| `_chan_crop` | `_block_crop` |  |
| `_mo_anh` | `_open_image` |  |
| `_fit_cover` | `_fit_cover` |  |
| `_khoang` | `_range` |  |
| `_lop_anh` | `_layer_image` |  |
| `_mo_vung_chu` | `_open_region_text` | ⚠️ chu |
| `_trong_the` | `_within_card` | ⚠️ the |
| `_sang_vung` | `_bright_region` | ⚠️ sang |
| `_mau_doi_nen` | `_color_change_background` | ⚠️ mau nen |
| `_can_bang_dong` | `_can_board_line` | ⚠️ bang dong |
| `_mau_doi_nen_an_toan` | `_color_change_background_hide_whole` | ⚠️ mau nen |
| `_quote_mark` | `_quote_mark` |  |
| `_quote_frame` | `_quote_frame` |  |
| `_render_quote` | `_render_quote` |  |
| `_chip_neo` | `_?chip_?neo` |  |
| `_pha` | `_?pha` |  |
| `build` | `build` |  |
| `_render_tran` | `_render_ceiling` |  |
| `_cao_tieu_de` | `_height_title` |  |
| `_cao_dau` | `_height_mark` | ⚠️ dau |
| `_box_min` | `_box_min` |  |
| `_x_chu` | `_x_text` | ⚠️ chu |

### `carousel`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `dat_nen` | `set_background` | ⚠️ nen |
| `_line_h` | `_line_h` |  |
| `_fit_block` | `_fit_?block` |  |
| `_draw_paragraphs` | `_?draw_?paragraphs` |  |
| `_cyan` | `_?cyan` |  |
| `_net` | `_?net` |  |
| `_mau_dau` | `_color_mark` | ⚠️ dau mau |
| `_chip_neo` | `_?chip_?neo` |  |
| `_watermark` | `_?watermark` |  |
| `_open` | `_open` |  |
| `_ghep_neu_can` | `_stack_if_can` |  |
| `_ramp_mask` | `_?ramp_mask` |  |
| `_do_vung_chu` | `_measure_region_text` | ⚠️ chu |
| `_lop_neu_can` | `_layer_if_can` |  |
| `_body_image` | `_body_image` |  |
| `build_body` | `build_body` |  |
| `build_body_quote` | `build_body_quote` |  |
| `build_cover` | `build_cover` |  |
| `_la_flagship` | `_is_flagship` |  |
| `_gate_text` | `_gate_text` |  |
| `_gate_anh` | `_gate_image` |  |
| `gom` | `gather` |  |
| `_gate_chu` | `_gate_text` | ⚠️ chu |

### `chat_router`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `chat_hint` | `chat_hint` |  |
| `route` | `?route` |  |
| `_bo_dong_rac` | `_drop_line_junk` | ⚠️ bo dong |
| `dung_argv` | `use_?argv` | ⚠️ dung |
| `ask` | `?ask` |  |
| `clean` | `?clean` |  |

### `chuan_bi.browser`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_js_browser` | `_js_browser` |  |
| `_lay_anh_trang` | `_take_image_page` |  |
| `_mo_trang` | `_open_page` |  |
| `_tim_bao_gnews` | `_find_outlet_gnews` |  |
| `browser_pass` | `browser_?pass` |  |
| `het_gio` | `all_done_hours` |  |

### `chuan_bi.chung`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_hdr` | `_hdr` |  |
| `_brand_cua` | `_brand_of` |  |
| `_mien` | `_domain` |  |
| `_doc_json` | `_read_json` | ⚠️ doc |
| `_ghi_json` | `_write_json` |  |
| `_goc_mien` | `_original_domain` |  |

### `chuan_bi.manifest`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `cau_xep_hang` | `sentence_ranking` |  |
| `dong_brief_xep_hang` | `line_brief_ranking` | ⚠️ dong |
| `ghep_hai_hang` | `stack_two_rank` | ⚠️ hang |
| `cap_ghep` | `cap_stack` |  |
| `bang_anh` | `board_image` | ⚠️ bang |
| `gom_tu_lieu` | `gather_material` |  |
| `_tu_lieu_bai` | `_material_article` |  |
| `dan_xuat` | `guide_export` |  |
| `dung_manifest` | `use_manifest` | ⚠️ dung |

### `chuan_bi.nguon`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_tom_tat_tu_img_json` | `_summary_from_img_json` | ⚠️ tu |
| `nap_nguon` | `load_source` |  |
| `_tieu_de_trang` | `_title_page` |  |
| `ung_vien_social` | `candidate_social` |  |
| `ung_vien_tinh` | `candidate_static` |  |
| `anh_commons` | `commons_images` |  |
| `_ten_rieng_dau` | `_leading_proper_noun` |  |

### `chuan_bi.nhin`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `mo_ta_anh` | `description_image` |  |
| `_goi_router` | `_call_router` |  |
| `_phan_loai_an_toan` | `_classify_hide_whole` |  |
| `phan_loai` | `classify` |  |
| `_nhin_anh` | `_?nhin_image` |  |

### `chuan_bi.tai_loc`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_tai_bytes` | `_download_bytes` |  |
| `_host_la_ben_thu_ba` | `_host_is_?ben_try_?ba` | ⚠️ thu |
| `_tai_ung_vien` | `_download_candidate` |  |
| `tai_va_loc` | `download_and_filter` |  |
| `_chart_theo_hinh` | `_chart_by_figure` |  |
| `_luu_crop` | `_save_crop` |  |

### `chuan_bi.vong_bu`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_bo_sung_nguon` | `_drop_?sung_source` | ⚠️ bo |
| `_them_trang_cong_bo` | `_extra_announcement_page` |  |
| `_lay_tu_browser` | `_take_from_browser` | ⚠️ tu |
| `_chup_xep_hang` | `_capture_ranking` |  |
| `_anh_muc_xep_hang` | `_image_item_ranking` | ⚠️ muc |
| `_gom_va_tai_anh` | `_gather_and_download_image` |  |
| `_vong_tim_rong` | `_round_widen_search` |  |
| `_xep_hang_boi_canh` | `_ranking_context_edge` | ⚠️ canh |
| `_vong_thuong_hieu` | `_round_brand` |  |
| `_vong_chup_nguon` | `_round_capture_source` |  |
| `_ra` | `_out` |  |
| `_vong_khai_niem` | `_round_concept` |  |
| `_vong_thuc_the` | `_round_actual_card` | ⚠️ the |

### `chup_chart`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_chan_rong` | `_block_empty` | ⚠️ rong |
| `khung_can` | `frame_can` |  |
| `_la_anh` | `_is_image` |  |
| `tai_anh` | `download_image` |  |
| `chup` | `capture` |  |

### `chup_trang`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `chup` | `capture` |  |
| `chup_lead_mobile` | `capture_lead_mobile` |  |

### `cleanup`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `get_state_dir` | `get_state_dir` |  |
| `cleanup_old_candidates` | `cleanup_old_?candidates` |  |
| `trim_jsonl` | `?trim_?jsonl` |  |
| `cleanup_append_only_logs` | `cleanup_append_?only_logs` |  |
| `cleanup_old_manifests` | `cleanup_old_?manifests` |  |

### `cost_squeeze`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `suy_luan_cua_vai` | `?suy_?luan_of_role` |  |
| `soul` | `?soul` |  |
| `viec_teaser` | `job_?teaser` |  |
| `viec_writer` | `job_writer` |  |
| `nhac` | `mention` |  |
| `rut_van` | `?rut_still` | ⚠️ van |
| `chay` | `run` |  |

### `crop_ti_le`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `cat` | `crop` |  |

### `deck`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_grow` | `_grow` |  |
| `_draw_lines` | `_?draw_lines` |  |
| `_line_h` | `_line_h` |  |
| `_badge` | `_?badge` |  |
| `_two_tone_title` | `_?two_tone_title` |  |
| `_open_bg` | `_open_bg` |  |
| `lay_statement` | `take_?statement` |  |
| `lay_list_steps` | `take_list_?steps` |  |
| `lay_checklist` | `take_?checklist` |  |
| `lay_grid3` | `take_?grid3` |  |
| `lay_cover` | `take_cover` |  |
| `_fit_size` | `_fit_size` |  |
| `_footer_burst` | `_footer_?burst` |  |
| `_footer_two` | `_footer_?two` |  |
| `_burst` | `_?burst` |  |
| `_gate` | `_gate` |  |

### `doi_chu_anh`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_doc_giu` | `_read_keep` | ⚠️ doc |
| `_trong_giu` | `_within_keep` |  |
| `tim_vung_chu` | `find_region_text` | ⚠️ chu |
| `dung_mask` | `use_mask` | ⚠️ dung |
| `_lama` | `_lama` |  |
| `inpaint` | `?inpaint` |  |
| `xoa_chu` | `delete_text` | ⚠️ chu |

### `dong_bo_hermes`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_slug` | `_slug` |  |
| `plugin_home` | `plugin_home` |  |
| `_cau_hinh_profile` | `_config_profile` |  |
| `_doc_tat` | `_read_all` | ⚠️ doc |
| `_ghi_tat` | `_write_all` |  |
| `dong_bo_tat_cong_cu` | `sync_all_gate_old` | ⚠️ cu |
| `cap_tep` | `cap_file` |  |
| `them_profile` | `extra_profile` |  |
| `_tep_plugin` | `_file_plugin` |  |
| `thieu_dau_vet` | `missing_trace` |  |
| `hai_home_lech` | `two_home_offset` |  |
| `hash_upstream` | `hash_upstream` |  |
| `doc_upstream` | `read_upstream` | ⚠️ doc |
| `ghi_upstream` | `write_upstream` |  |
| `kiem_upstream` | `check_upstream` |  |
| `kanban_da_bat` | `kanban_already_catch` | ⚠️ bat |
| `nhac_bat_plugin` | `mention_catch_plugin` | ⚠️ bat |
| `nhac_don_ban_cai` | `mention_single_copy_item` | ⚠️ ban |
| `doc` | `read` | ⚠️ doc |
| `chuan` | `standard` |  |
| `_loc_bi_mat` | `_filter_secret` |  |
| `_lay` | `_take` |  |
| `chup_cau_hinh` | `capture_config` |  |

### `draft_write`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|

### `dre_chuan_bi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `viet_brief` | `write_brief` |  |

### `dre_nop`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_Boi` | `_Context` |  |
| `nhan_ma` | `mark_code` |  |
| `kiem_lien_quan` | `check_relevant` |  |
| `kiem_mat` | `check_faces` |  |
| `_giai_ghep` | `_resolve_stack` |  |
| `_giai_don` | `_resolve_single` |  |
| `_giai_muc` | `_resolve_item` |  |
| `giai_spec` | `resolve_spec` |  |
| `don_slide_cu` | `single_slide_old` | ⚠️ cu |
| `dung` | `use` | ⚠️ dung |
| `ban_giao` | `handoff` |  |

### `duyet_bai`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_xu_ly_nut` | `_process_button` |  |
| `keyboard` | `?keyboard` |  |
| `_send_media_group` | `_send_media_group` |  |
| `draft_push` | `draft_push` |  |
| `da_len_channel` | `already_len_channel` |  |
| `_ghi_dau` | `_write_mark` | ⚠️ dau |
| `_chu_mot_lan` | `_text_one_attempt` | ⚠️ chu lan |
| `publish` | `?publish` |  |
| `_go_so_anh` | `_go_count_image` | ⚠️ so |
| `mark_draft` | `mark_draft` |  |
| `_tach_ly_do_lam_lai` | `_extract_reason_redo` |  |
| `_giao_lam_lai` | `_hand_redo` |  |
| `_nap_lam_lai_cho` | `_load_redo_wait` | ⚠️ cho |
| `_cho_trong_topic` | `_wait_within_topic` | ⚠️ cho |
| `_qua_han` | `_over_limit` |  |
| `_nhan_ly_do_lam_lai` | `_label_reason_redo` | ⚠️ nhan |
| `_xu_ly_ly_do_lam_lai` | `_process_reason_redo` |  |
| `_lam_lai_het_han` | `_redo_all_done_limit` |  |
| `_giao_het_han` | `_hand_all_done_limit` |  |
| `tao_task_kite` | `create_task_kite` |  |
| `_nut_bo_han` | `_button_drop_limit` | ⚠️ bo |
| `_nut_kite` | `_button_kite` |  |
| `_nut_ha_san` | `_button_?ha_ready` |  |
| `_nut_lam_lai` | `_button_redo` |  |
| `_nut_duyet` | `_button_approve` |  |
| `_chot_nut` | `_finalize_button` |  |
| `handle_img_approval` | `handle_img_?approval` |  |
| `handle_callback` | `handle_callback` |  |
| `_day_lai_moat` | `_bottom_again_?moat` | ⚠️ day |
| `chay` | `run` |  |
| `_doc_draft` | `_read_draft` | ⚠️ doc |
| `_dang_nen` | `_form_background` | ⚠️ nen |
| `_sua_tin_go_nut` | `_fix_story_go_button` |  |

### `duyet_chat`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_HangFIFO` | `_RankFIFCell` | ⚠️ hang |
| `lay_so` | `take_count` | ⚠️ so |
| `doi` | `change` |  |
| `release` | `release` |  |
| `_hang_cua` | `_rank_of` |  |
| `_ai_dang_chay` | `_ai_form_run` |  |
| `boi_canh_vai` | `context_edge_role` | ⚠️ canh |
| `_tin_dua_viec` | `_story_?dua_job` |  |
| `_bo_cong_cu_chat` | `_drop_gate_old_chat` | ⚠️ bo cu |
| `handle_chat` | `handle_chat` |  |
| `_chat_co_khoa` | `_chat_has_lock` | ⚠️ khoa |
| `_goi` | `_call` |  |

### `duyet_chon_tin`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `slugify` | `slugify` |  |
| `latest_manifest` | `?latest_manifest` |  |
| `_mid_bao_cao` | `_mid_report` |  |
| `manifest_da_gui` | `manifest_already_send` |  |
| `_la_reply_bao_cao` | `_is_reply_report` |  |
| `doc_lenh_chon` | `read_pick_command` | ⚠️ doc |
| `_xa` | `_?xa` |  |
| `write_meta` | `write_meta` |  |
| `_draft_id` | `_draft_id` |  |
| `_research_nguon` | `_?research_source` |  |
| `_khoi_chay_engine` | `_block_run_?engine` |  |
| `_cat_sidecar` | `_crop_?sidecar` |  |
| `create_pair` | `?create_?pair` |  |
| `_khoa_manifest` | `_lock_manifest` | ⚠️ khoa |
| `_bao_da_nhan` | `_outlet_already_label` | ⚠️ nhan |
| `_xu_ly_chon` | `_process_pick` |  |

### `duyet_co_so`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `load_secrets` | `load_secrets` |  |
| `call` | `?call` |  |
| `_ghi_json` | `_write_json` |  |
| `_khoa_cua` | `_lock_of` | ⚠️ khoa |
| `_chay_nen` | `_run_background` | ⚠️ nen |
| `_boc` | `_extract` |  |
| `_gui_chu` | `_send_text` | ⚠️ chu |
| `_reply_that` | `_reply_real` |  |
| `_boc_dong` | `_extract_line` | ⚠️ dong |
| `_nap_json` | `_load_json` |  |
| `la_ong_chu` | `is_boss` |  |

### `duyet_giao_viec`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_bao_nhan_viec` | `_outlet_receive_job` |  |
| `vai_cua_topic` | `role_of_topic` |  |
| `chuan_assignee` | `standard_assignee` |  |
| `kanban_create` | `kanban_?create` |  |
| `cau_chay_lau` | `long_run_message` |  |
| `cau_bi_dung` | `killed_message` |  |
| `_bang_den_root` | `_blackboard_root` |  |
| `_bang_den_ghi` | `_blackboard_write` |  |
| `_trang_thai_task` | `_status_task` |  |
| `_tom_tat_run` | `_summary_run` |  |
| `ly_do_task` | `reason_task` |  |
| `link_ket_qua` | `link_result` |  |
| `_xong_ma_khong_giao` | `_done_code_no_hand` | ⚠️ ma |
| `bao_tien_do_kanban` | `outlet_progress_kanban` |  |
| `chuan_nhan` | `standard_label` | ⚠️ nhan |

### `duyet_lenh`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_chuan_hoa_url` | `_standard_ify_url` |  |
| `_url_hop_le` | `_url_valid` |  |
| `_doc_trang` | `_read_page` | ⚠️ doc |
| `_doc_social` | `_read_social` | ⚠️ doc |
| `_dong_vai_help` | `_line_role_help` | ⚠️ dong |
| `_lenh_bai` | `_command_article` |  |
| `handle_command` | `handle_?command` |  |
| `tra_loi` | `return_error` | ⚠️ tra |

### `emoji_deck`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_load` | `_load` |  |
| `_save` | `_?save` |  |
| `next_emoji` | `next_emoji` |  |

### `env_load`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `hermes_home` | `hermes_home` |  |
| `hermes_homes` | `hermes_homes` |  |
| `topics` | `topics` |  |
| `_brand` | `_brand` |  |
| `brand_dai` | `brand_long` |  |
| `so_luong` | `quantity` |  |
| `handle_kenh` | `handle_channel` |  |
| `_tep_env` | `_file_env` |  |
| `state_dir` | `state_dir` |  |
| `topics_path` | `topics_path` |  |
| `nap` | `load` |  |
| `album_phu` | `album_secondary` |  |
| `so` | `count` | ⚠️ so |
| `bat_buoc` | `required` |  |
| `ghi_json` | `write_json` |  |

### `ethan_chuan_bi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `nhan_ethan` | `label_ethan` | ⚠️ nhan |
| `cap_ghep_hero` | `cap_stack_hero` |  |
| `viet_brief` | `write_brief` |  |

### `ethan_nop`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_kiem_ghep` | `_check_stack` |  |
| `_kiem_chu` | `_check_text` |  |
| `giai_spec` | `resolve_spec` |  |

### `ghi_log`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_khoi_tao` | `_block_create` |  |
| `_khoi_tao_that` | `_block_create_real` |  |
| `log` | `log` |  |
| `rut` | `?rut` |  |
| `brand` | `brand` |  |

### `gin_chuan_bi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `tim_anh` | `find_image` |  |
| `workdir` | `workdir` |  |
| `mau_chu` | `color_text` | ⚠️ chu mau |
| `ocr_vung` | `ocr_region` |  |
| `ve_preview` | `about_?preview` |  |
| `viet_brief` | `write_brief` |  |

### `gin_nop`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `don` | `single` |  |

### `gui_telegram`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `GuiLoi` | `SendError` |  |
| `_topic` | `_topic` |  |
| `_md5` | `_md5` |  |
| `_ghi_nhat_ky` | `_write_journal` |  |
| `_da_gui_gan_day` | `_already_send_near_bottom` | ⚠️ day |
| `_kb_duyet` | `_?kb_approve` |  |
| `post` | `post` |  |
| `gan_day` | `near_bottom` | ⚠️ day |

### `hermes_adapter`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `kanban_db` | `kanban_db` |  |
| `co_kanban` | `has_kanban` |  |
| `_mo` | `_open` |  |
| `_hoi` | `_ask` |  |
| `state_db_cac_profile` | `state_db_each_profile` |  |
| `dung_theo_model` | `use_by_model` | ⚠️ dung |
| `tom_tat_phien` | `summary_session` |  |
| `tao_task` | `create_task` |  |
| `viec` | `job` |  |
| `mot_viec` | `one_job` |  |
| `trang_thai` | `status` |  |
| `dem_dang_chay` | `count_form_run` |  |
| `lan_chay_cuoi` | `last_run` |  |
| `_chuan_hoa_lan_chay` | `_standard_ify_run` |  |
| `moc_lan_chay` | `run_start` |  |
| `nhip_tho` | `heartbeat` |  |
| `pid_song` | `pid_alive` |  |
| `dem_xong_theo_vai` | `count_done_by_role` |  |
| `lan_chay_cuoi_nhieu` | `last_run_many` |  |

### `itachi_chuan_bi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `chuan_bi_slide` | `prepare_slide` |  |
| `goi_y_cach` | `call_y_way` |  |
| `viet_brief` | `write_brief` |  |

### `itachi_nop`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_font_mac_dinh` | `_font_default` |  |
| `_ve_khoi` | `_about_block` |  |
| `_tran_hop` | `_ceiling_box` |  |
| `_mau` | `_color` | ⚠️ mau |
| `_mau_an_toan` | `_color_hide_whole` | ⚠️ mau |
| `ve_tai_cho` | `about_download_wait` | ⚠️ cho |

### `khung_anh`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_lam_tron` | `_make_full` |  |
| `_mau` | `_color` | ⚠️ mau |
| `_font` | `_font` |  |
| `avatar_cho_emoji` | `?avatar_wait_emoji` | ⚠️ cho |
| `_ve_rgb` | `_about_rgb` |  |
| `dong_khung` | `line_frame` | ⚠️ dong |
| `_chu_gian` | `_text_?gian` | ⚠️ chu |

### `kiem_hermes`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_home_kanban` | `_home_kanban` |  |
| `_kiem_bang` | `_check_board` | ⚠️ bang |
| `kiem_cot` | `check_column` |  |
| `kiem_co_chat` | `check_has_chat` |  |
| `kiem_swarm` | `check_?swarm` |  |

### `kiem_moi_truong`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `kiem_cv2` | `check_cv2` |  |
| `kiem_yunet` | `check_yunet` |  |
| `kiem_chromium` | `check_chromium` |  |
| `kiem_bien_moi_truong` | `check_variable_environment` |  |
| `kiem_openai_key` | `check_?openai_key` |  |
| `kiem_telegram_token` | `check_telegram_token` |  |

### `kite_chuan_bi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `handle_kenh` | `handle_channel` |  |
| `chuyen_tu_vai` | `transfer_from_role` | ⚠️ tu |
| `hinh_that` | `figure_real` |  |
| `hinh_mo_dau` | `figure_open_mark` | ⚠️ dau |
| `hinh_hero` | `figure_hero` |  |
| `_hero_la_gi` | `_hero_is_?gi` |  |
| `dong_hero` | `line_hero` | ⚠️ dong |
| `_ep_tho` | `_force_?tho` |  |
| `hinh_phai_dung` | `figure_right_use` | ⚠️ dung |
| `bao_dam_co_bia` | `outlet_?dam_has_cover` |  |
| `goi_y_tone` | `call_y_tone` |  |
| `viet_brief` | `write_brief` |  |

### `kite_nop`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_kiem_hinh_slide` | `_check_figure_slide` |  |
| `_giai_slide` | `_resolve_slide` |  |
| `giai_spec` | `resolve_spec` |  |

### `loai_tin`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `chuan_loai` | `standard_type` |  |
| `thu_tu_anh` | `order_image` |  |
| `muon` | `?muon` |  |
| `diem_theo_loai` | `score_by_type` |  |
| `nuoc_cua` | `country_of` |  |
| `ma_co_phieu` | `code_has_ballot` | ⚠️ ma |
| `dong_brief` | `line_brief` | ⚠️ dong |

### `luat_anh`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `dong_dau` | `stamp` |  |
| `dong_dau_tep` | `stamp_file` |  |
| `_text` | `_text` |  |
| `doc_dau_crop` | `read_mark_crop` | ⚠️ dau doc |
| `doc_cat_ngang` | `read_crop_landscape` | ⚠️ doc |
| `la_xep_hang` | `is_ranking` |  |
| `co_xuat_xu` | `has_provenance` |  |
| `la_ghep` | `is_stack` |  |
| `do_chart` | `measure_chart` |  |
| `la_chart` | `is_chart` |  |
| `_js_re` | `_js_re` |  |
| `js_rac_url` | `js_junk_url` |  |
| `js_rac_dom` | `js_junk_dom` |  |
| `dhash` | `dhash` |  |
| `gan_giong` | `near_voice` |  |
| `_md5` | `_md5` |  |
| `nguong_dhash` | `threshold_dhash` |  |
| `_so_da_dung` | `_count_used` | ⚠️ so |
| `khoa_tin` | `lock_story` | ⚠️ khoa |
| `ghi_da_dung` | `write_used` |  |
| `xoa_da_dung` | `delete_used` |  |
| `kiem_da_dung` | `check_used` |  |
| `lech_tone` | `offset_tone` |  |
| `_yunet` | `_yunet` |  |
| `dem_mat` | `count_faces` |  |
| `la_anh_rong` | `is_image_empty` | ⚠️ rong |
| `kiem_anh_rong` | `check_image_empty` | ⚠️ rong |
| `kiem_chart` | `check_chart` |  |
| `kiem_anh_thap` | `check_image_low` |  |
| `kiem_lech_tone` | `check_offset_tone` |  |
| `kiem_chart_mot_minh` | `check_chart_one_?minh` |  |
| `kiem_ti_le` | `check_ratio` |  |
| `kiem_crop_ngang` | `check_crop_landscape` |  |
| `kiem_xuat_xu` | `check_provenance` |  |
| `kiem_do_phan_giai` | `check_measure_part_resolve` | ⚠️ phan |
| `kiem_day_sang` | `check_bright_bottom` |  |
| `kiem_mat_nguoi` | `check_faces_person` |  |
| `kiem_trung` | `check_duplicate` |  |

### `manifest_build`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_diem` | `_score` |  |
| `_muc_tu_pick` | `_item_from_?pick` | ⚠️ muc tu |
| `gom_muc` | `gather_item` | ⚠️ muc |
| `cat_tran` | `crop_ceiling` |  |
| `them_bat_buoc` | `extra_required` |  |

### `manifest_chung`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `chon_theo_k` | `pick_by_k` |  |
| `don_tom_tat` | `single_summary` |  |
| `danh_so` | `list_count` | ⚠️ so |
| `duong_ra_moi` | `path_out_new` | ⚠️ moi |
| `ghi_manifest` | `write_manifest` |  |
| `chot_bat_buoc` | `finalize_required` |  |
| `viet_bao_cao` | `write_report` |  |

### `manifest_ghi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_so_bao` | `_count_outlet` | ⚠️ so |
| `_muc_tu_nop` | `_item_from_submit` | ⚠️ muc tu |
| `them_bat_buoc` | `extra_required` |  |

### `miles_chuan_bi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `viet_brief` | `write_brief` |  |

### `miles_nop`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `chuan_hoa` | `standard_ify` |  |

### `moat_publish`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `load_secrets` | `load_secrets` |  |
| `_cho_trong` | `_wait_within` | ⚠️ cho |
| `ten_khoa` | `name_lock` | ⚠️ khoa |
| `brand_container` | `brand_?container` |  |
| `base_url` | `base_url` |  |
| `config` | `config` |  |
| `draft_path` | `draft_path` |  |
| `read_draft` | `read_draft` |  |
| `_ghi_json` | `_write_json` |  |
| `write_draft` | `write_draft` |  |
| `chu_thuan` | `text_?thuan` | ⚠️ chu |
| `_nen` | `_background` | ⚠️ nen |
| `images_payload` | `images_payload` |  |
| `_body_intake` | `_body_?intake` |  |
| `intake` | `?intake` |  |
| `_doc_hang_doi` | `_read_queue` | ⚠️ doc |
| `_ghi_hang_doi` | `_write_queue` |  |
| `_dang_thu_lai` | `_form_try_again` | ⚠️ thu |
| `_danh_dau_dang_day` | `_list_mark_form_bottom` | ⚠️ dau day |
| `xep_day_lai` | `?xep_bottom_again` | ⚠️ day |
| `_bo_khoi_hang_doi` | `_drop_block_queue` | ⚠️ bo |
| `day_lai` | `bottom_again` | ⚠️ day |
| `_fetch_status` | `_fetch_status` |  |
| `_poll_mot_bai` | `_?poll_one_article` |  |
| `poll` | `?poll` |  |
| `_thoat` | `_exit` |  |
| `_tele` | `_?tele` |  |
| `bao_the` | `outlet_card` | ⚠️ the |
| `_notify` | `_?notify` |  |

### `model_audition`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `goi` | `call` |  |

### `model_watch`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `models_in_use` | `models_in_?use` |  |
| `probe` | `?probe` |  |

### `nen_chu`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `do_sang_lech` | `measure_bright_offset` | ⚠️ sang |
| `mau_trung_binh` | `color_average` | ⚠️ mau |
| `_luminance` | `_?luminance` |  |
| `kenh` | `channel` |  |
| `_ti_le_tuong_phan` | `_ratio_wall_part` | ⚠️ phan |
| `nguong_tuong_phan` | `threshold_wall_part` | ⚠️ phan |
| `ti_le_tuong_phan` | `ratio_wall_part` | ⚠️ phan |

### `nguon_bai`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `bo_hau_to_site` | `strip_site_suffix` |  |
| `tu_cung_tin` | `story_tokens` |  |
| `cung_tin` | `same_story` |  |
| `_tai` | `_download` |  |
| `giai_ma_gnews` | `resolve_code_gnews` | ⚠️ ma |
| `co_tieng_viet` | `has_vietnamese` |  |
| `_tieu_de_rss` | `_title_rss` |  |
| `_tieu_de_trang` | `_title_page` |  |
| `_ten_rieng_khong_dau` | `_name_own_no_mark` | ⚠️ dau |
| `tieu_de_tim` | `title_find` |  |
| `_truy_van_bing` | `_queries_bing` |  |
| `bao_khac_bing` | `other_outlets_bing` |  |
| `tim` | `find` |  |
| `_trong_feed` | `_within_?feed` |  |

### `nhat_ky`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_gio_vn` | `_hours_vn` |  |
| `_trong_ngay` | `_within_date` |  |
| `_mo` | `_open` |  |
| `_chiu_loi_db` | `_?chiu_error_db` |  |
| `bao` | `outlet` |  |
| `trong` | `within` |  |
| `_gom_theo_viec` | `_gather_by_job` |  |
| `phan_cron` | `part_cron` | ⚠️ phan |
| `phan_kanban` | `part_kanban` | ⚠️ phan |
| `phan_finn` | `part_finn` | ⚠️ phan |
| `_diem` | `_score` |  |
| `phan_draft` | `part_draft` | ⚠️ phan |
| `phan_git` | `part_git` | ⚠️ phan |
| `phan_model` | `part_model` | ⚠️ phan |
| `them_ghi_chu` | `extra_notes` |  |
| `doc_ghi_chu` | `read_notes` | ⚠️ doc |
| `dung_trang` | `use_page` | ⚠️ dung |

### `nhat_ky_web`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_trang` | `_page` |  |
| `_dam` | `_?dam` |  |
| `md_sang_html` | `md_bright_html` | ⚠️ sang |
| `xa_bang` | `?xa_board` | ⚠️ bang |
| `trang_ngay` | `page_date` |  |
| `trang_danh_sach` | `page_list_clean` |  |
| `bai` | `article` |  |
| `Handler` | `?handler` |  |
| `log_message` | `log_?message` |  |
| `_tra` | `_return` | ⚠️ tra |
| `do_GET` | `measure_get` |  |

### `nop_chung`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `chuan` | `standard` |  |
| `nap` | `load` |  |
| `vai_viet_cua_bai` | `writer_for_article` |  |
| `persona_viet` | `?persona_write` |  |
| `so_lan_lam_lai` | `count_attempt_redo` | ⚠️ lan so |
| `kiem_lam_lai` | `check_redo` |  |
| `dem_vong_loi` | `count_round_error` |  |
| `chu_bai_cua` | `text_article_of` | ⚠️ chu |
| `_khong_dau` | `_no_mark` | ⚠️ dau |
| `_tu` | `_from` | ⚠️ tu |
| `_ten_co_trong_bai` | `_name_has_within_article` |  |
| `kiem_nhan_vat` | `check_subject` |  |
| `kiem_so_tren_anh` | `check_numbers_on_card` |  |
| `can_anh_xep_hang` | `needs_ranking_image` |  |
| `anh_khong_lien_quan` | `irrelevant_images` |  |
| `kiem_da_dung_nhieu` | `check_reused` |  |
| `kiem_quote_dich` | `check_quote_translated` |  |
| `kiem_hang_tren_the` | `check_rank_on_card` |  |
| `_album_da_len` | `_album_already_len` |  |
| `gui_album` | `send_album` |  |
| `_ghi_so` | `_write_count` | ⚠️ so |
| `ghi_bang_den` | `write_blackboard` |  |

### `phien_browser`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `bi_chan` | `got_block` |  |
| `PhienBrowser` | `BrowserSession` |  |
| `browser` | `browser` |  |
| `trang` | `page` |  |
| `dong` | `line` | ⚠️ dong |
| `phien_hoac_moi` | `session_?hoac_new` | ⚠️ moi |

### `publish`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `load_secrets` | `load_secrets` |  |
| `don_dep` | `single_pretty` |  |
| `_bo` | `_drop` | ⚠️ bo |
| `TelegramTuChoi` | `TelegramReject` |  |
| `_check` | `_?check` |  |
| `send_text_cac_manh` | `send_text_each_?manh` |  |
| `send_text` | `send_text` |  |
| `send_photo` | `send_?photo` |  |
| `send_document` | `send_?document` |  |
| `send_media_group` | `send_media_group` |  |
| `gui_topic` | `send_topic` |  |
| `_main` | `_main` |  |

### `quet_chuan_bi`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_cat` | `_crop` |  |
| `workdir` | `workdir` |  |
| `_moi` | `_new` | ⚠️ moi |
| `_chay` | `_run` |  |
| `_bat_buoc` | `_required` |  |
| `_bo_sung_bat_buoc` | `_drop_?sung_required` | ⚠️ bo |
| `brief_scout` | `brief_?scout` |  |
| `brief_nova` | `brief_nova` |  |
| `brief_market` | `brief_?market` |  |

### `quet_chung`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `host_noi_bo` | `host_say_drop` | ⚠️ bo |
| `kiem_url` | `check_url` |  |
| `url_an_toan` | `url_hide_whole` |  |
| `chuan_link` | `standard_link` |  |
| `hoi_commons` | `ask_commons` |  |
| `get` | `get` |  |
| `moc_thoi_gian` | `timestamp_time_?gian` |  |
| `tu_dac_trung` | `from_distinctive` | ⚠️ tu |

### `quet_nop`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `loi_chan_gui` | `error_block_send` |  |
| `duong_manifest` | `path_manifest` |  |
| `ghim_manifest` | `?ghim_manifest` |  |
| `loc_canh_bao` | `filter_warning` |  |
| `_chay` | `_run` |  |
| `_in_loi` | `_in_error` |  |
| `gui` | `send` |  |

### `render_edu`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_font_face_css` | `_font_?face_css` |  |
| `_ff` | `_?ff` |  |
| `base_css` | `base_css` |  |
| `rgba` | `rgba` |  |
| `hero_svg` | `hero_svg` |  |
| `_nho` | `_small` |  |
| `_do_anh` | `_measure_image` |  |
| `_do_anh_that` | `_measure_image_real` |  |
| `_anh_data_uri` | `_image_?data_?uri` |  |
| `lam` | `make` |  |
| `_sang` | `_bright` | ⚠️ sang |
| `doc_nen` | `read_background` | ⚠️ doc nen |
| `_doc_nen_that` | `_read_background_real` | ⚠️ doc nen |
| `dat_anh` | `set_image` |  |
| `esc` | `?esc` |  |
| `accent_html` | `accent_html` |  |
| `glow` | `?glow` |  |
| `masthead` | `?masthead` |  |
| `eyebrow` | `?eyebrow` |  |
| `folio` | `?folio` |  |
| `s_cover` | `s_cover` |  |
| `_cover_anh` | `_cover_image` |  |
| `s_statement` | `s_?statement` |  |
| `s_steps` | `s_?steps` |  |
| `s_loop` | `s_loop` |  |
| `_mau_toi` | `_color_dark` | ⚠️ mau toi |
| `_css_mast_toi` | `_css_?mast_dark` | ⚠️ toi |
| `_css_chu_toi_vung` | `_css_text_dark_region` | ⚠️ chu toi |
| `anh_lam_nen` | `image_make_background` | ⚠️ nen |
| `s_figure` | `s_figure` |  |
| `_so` | `_count` | ⚠️ so |
| `_gia_tri` | `_value` |  |
| `s_bars` | `s_?bars` |  |
| `s_cta` | `s_?cta` |  |
| `slide_doc` | `slide_read` | ⚠️ doc |
| `kiem_truong` | `check_?truong` |  |
| `gate_slides` | `gate_slides` |  |
| `_gate_noi_dung` | `_gate_content` |  |
| `_texts` | `_texts` |  |
| `_nhat_ky_theme` | `_journal_theme` |  |
| `_theme_gan_day` | `_theme_near_bottom` | ⚠️ day |
| `_ghi_theme` | `_write_theme` |  |
| `mau_noi_bat` | `color_say_catch` | ⚠️ bat mau |
| `lech_hue` | `offset_?hue` |  |
| `theme_gan_mau` | `theme_near_color` | ⚠️ mau |
| `mau_hang_trong_spec` | `color_rank_within_spec` | ⚠️ hang mau |
| `chon_theme_tu_dong` | `pick_theme_auto` |  |
| `it_dung_nhat` | `?it_use_nhat` | ⚠️ dung |
| `_route_font` | `_?route_font` |  |
| `_tra` | `_return` | ⚠️ tra |
| `_kiem_tieu_de_dong` | `_check_title_line` | ⚠️ dong |
| `_chup_cac_slide` | `_capture_each_slide` |  |
| `render` | `render` |  |
| `dung_doc` | `use_read` | ⚠️ doc dung |

### `route_thieu_anh`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_tg_gui` | `_?tg_send` |  |
| `sau_chuan_bi` | `after_prepare` |  |
| `_hoi` | `_ask` |  |

### `scan_business`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `ten_watchlist` | `name_watchlist` |  |
| `trong_watchlist` | `within_watchlist` |  |
| `chuan_hoa` | `standard_ify` |  |
| `toa_soan` | `outlet` |  |
| `quet_gnews` | `scan_gnews` |  |
| `quet_bao` | `scan_outlet` |  |
| `_tu_khoa` | `_keyword` |  |
| `gom_trung` | `gather_duplicate` |  |
| `da_thay` | `already_see` | ⚠️ thay |
| `ghi_moc` | `write_timestamp` |  |

### `scan_models`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `vung_cua` | `region_of` |  |
| `fetch_openrouter` | `fetch_openrouter` |  |
| `_usd_1m` | `_?usd_?1m` |  |
| `fetch_catalog` | `fetch_?catalog` |  |
| `_arena_board` | `_arena_board` |  |
| `fetch_arena` | `fetch_arena` |  |
| `fetch_swebench` | `fetch_?swebench` |  |
| `fetch_livebench` | `fetch_?livebench` |  |
| `fetch_openrouter_usage` | `fetch_openrouter_?usage` |  |
| `_goc_theo_ten` | `_original_by_name` |  |
| `fetch_tbench` | `fetch_?tbench` |  |
| `fetch_arcagi` | `fetch_?arcagi` |  |
| `fetch_hle` | `fetch_?hle` |  |
| `fetch_epoch` | `fetch_?epoch` |  |
| `fetch_opencompass` | `fetch_?opencompass` |  |
| `fetch_aa_media` | `fetch_aa_media` |  |
| `fetch_hf_trending` | `fetch_hf_?trending` |  |
| `fetch_anthropic` | `fetch_?anthropic` |  |
| `_rsc` | `_?rsc` |  |
| `fetch_aa` | `fetch_aa` |  |
| `loc_aa` | `filter_aa` |  |
| `gon` | `?gon` |  |
| `gon2` | `?gon2` |  |
| `ten_goc` | `name_original` |  |
| `_bang_goc` | `_board_original` | ⚠️ bang |
| `_lam_tron` | `_make_full` |  |
| `fetch_tin_hang` | `fetch_story_rank` | ⚠️ hang |
| `_t` | `_t` |  |
| `fetch_github` | `fetch_github` |  |
| `_lam_sach` | `_make_clean` |  |
| `trich_benchmark` | `?trich_?benchmark` |  |
| `doc_state` | `read_state` | ⚠️ doc |
| `da_thay` | `already_see` | ⚠️ thay |
| `hang_cu` | `rank_old` | ⚠️ cu hang |
| `aa_da_bao` | `aa_already_outlet` |  |
| `ghi_moc` | `write_timestamp` |  |
| `ghi_bat_buoc` | `write_required` |  |
| `so_hang` | `count_rank` | ⚠️ hang so |
| `_thu` | `_try` | ⚠️ thu |
| `_in_bang` | `_in_board` | ⚠️ bang |
| `_in_bao_cao` | `_in_report` |  |

### `scan_sources`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `nguon_goc` | `source_original` |  |
| `_is_ai_ish` | `_is_ai_?ish` |  |
| `_age_hours` | `_?age_?hours` |  |
| `score_recency` | `score_?recency` |  |
| `score_spread` | `score_?spread` |  |
| `fetch_hn` | `fetch_?hn` |  |
| `fetch_reddit` | `fetch_reddit` |  |
| `fetch_arxiv` | `fetch_arxiv` |  |
| `seen_keys` | `?seen_keys` |  |
| `_anh_cua` | `_image_of` |  |
| `gan_anh` | `near_image` |  |

### `schema`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `Manifest` | `Manifest` |  |
| `Meta` | `Meta` |  |
| `SidecarAnh` | `?sidecarImage` |  |
| `SidecarViet` | `?sidecarWrite` |  |
| `DongAnhDaDung` | `LineImageUsed` | ⚠️ dong |
| `_chi_ghep_duoc` | `_only_stack_ok` | ⚠️ chi |
| `so_anh_dung_duoc` | `count_image_use_ok` | ⚠️ dung so |
| `doc_manifest` | `read_manifest` | ⚠️ doc |
| `hop_nhat_meta` | `merge_meta` |  |
| `_kieu` | `_kind` |  |

### `soat_cron`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_epoch` | `_?epoch` |  |
| `_gio` | `_hours` |  |
| `_tuoi` | `_?tuoi` |  |
| `kho_cron` | `size_cron` |  |
| `soat_kho` | `audit_size` |  |
| `soat` | `audit` |  |
| `khoa_van_de` | `lock_still_for` | ⚠️ de khoa van |
| `doc_dau` | `read_mark` | ⚠️ dau doc |
| `dung_tin` | `use_story` | ⚠️ dung |

### `social_post`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `la_social` | `is_social` |  |
| `tieu_de_tu_text` | `title_from_text` | ⚠️ tu |
| `doc` | `read` | ⚠️ doc |

### `task_bodies`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `ket_thuc_vai_anh` | `end_role_image` |  |

### `teaser_assemble`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_bo_dau` | `_drop_mark` | ⚠️ bo dau |
| `tim_giong_tuong_thuat` | `find_voice_wall_?thuat` |  |
| `_muc_khong_duoc_nhac` | `_item_no_ok_mention` | ⚠️ muc |
| `assemble` | `?assemble` |  |

### `tele_util`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `bo_ansi` | `drop_?ansi` | ⚠️ bo |
| `_diem_cat_an_toan` | `_score_crop_hide_whole` |  |
| `chia_tin` | `?chia_story` |  |

### `theo_doi_9router`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `_cua_so_utc` | `_of_count_utc` | ⚠️ so |
| `_gio_vn` | `_hours_vn` |  |
| `_giay` | `_seconds` |  |
| `_hhmm` | `_?hhmm` |  |
| `_ten_bang` | `_name_board` | ⚠️ bang |
| `_cac_ten` | `_each_name` |  |
| `chuoi_da_cau_hinh` | `string_already_config` |  |
| `cap_fallback` | `cap_fallback` |  |
| `soi_model` | `?soi_model` |  |
| `tong_hop` | `aggregate` |  |
| `moi` | `new` | ⚠️ moi |
| `pct` | `?pct` |  |
| `gon` | `?gon` |  |
| `doc_ngay` | `read_date` | ⚠️ doc |
| `loi_ket_noi` | `error_connection` |  |
| `_chuan_model` | `_standard_model` |  |
| `_don_gia` | `_single_gia` | ⚠️ gia |
| `gom_vai` | `gather_role` |  |
| `gia_cua` | `gia_of` | ⚠️ gia |
| `viet_md` | `write_md` |  |
| `van_de` | `still_for` | ⚠️ de van |
| `tom_tat_tele` | `summary_?tele` |  |
| `dung` | `use` | ⚠️ dung |
| `tai` | `download` |  |

### `tieng_viet`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `bo_dau_cam` | `drop_mark_?cam` | ⚠️ bo dau |
| `tim_mat_dau` | `find_face_mark` | ⚠️ dau |

### `tim_anh_them`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `doc_so_luot` | `read_count_slot` | ⚠️ doc so |
| `kiem_tu_khoa` | `check_keyword` |  |
| `ung_vien_commons` | `candidate_commons` |  |
| `thu_nho_commons` | `try_small_commons` | ⚠️ thu |
| `loc_openverse` | `filter_openverse` |  |
| `ung_vien_openverse` | `candidate_openverse` |  |
| `ung_vien_tu_url` | `candidate_from_url` | ⚠️ tu |
| `ung_vien_tu_khoa` | `candidate_keyword` |  |
| `noi_anh_moi` | `say_image_new` | ⚠️ moi |
| `lam_moi_manifest` | `fresh_manifest` |  |
| `in_ket_qua` | `in_result` |  |

### `tu_lieu`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `boc` | `extract` |  |
| `cau_co_so` | `sentence_has_count` | ⚠️ so |
| `gom` | `gather` |  |
| `dung_trang` | `use_page` | ⚠️ dung |

### `vai`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `Vai` | `Role` |  |
| `vai_viet_cua` | `writer_for` |  |
| `ten_hien` | `display_name` |  |
| `slug_that` | `canonical_slug` |  |
| `max_runtime_cua` | `max_runtime_for` |  |
| `so_anh_toi_thieu` | `min_images` |  |
| `ten_nguoi_trong_alt` | `name_person_within_alt` |  |
| `anh_chinh_duoc` | `image_main_ok` |  |
| `so_anh_muc_tieu_tim` | `count_image_target_find` | ⚠️ so |
| `du_nguyen_lieu` | `has_enough_material` |  |
| `don_vi_san` | `single_vi_ready` |  |
| `_map_go` | `_map_go` |  |

### `xep_hang`

| Hiện tại | Đề xuất | Cờ |
|---|---|---|
| `la_chup` | `is_capture` |  |
| `la_tin_xep_hang` | `is_ranking_story` |  |
| `tach_model` | `extract_model` |  |
| `tach_hang` | `extract_rank` |  |
| `goi_y_nguon` | `suggest_sources` |  |
| `_doi_bang` | `_change_board` | ⚠️ bang |
| `_giao` | `_hand` |  |
| `_chup` | `_capture` |  |
| `_khoanh` | `_?khoanh` |  |
| `_cua_so` | `_of_count` | ⚠️ so |
| `_chup_mot_bang` | `_capture_one_board` | ⚠️ bang |
| `chup_bang` | `capture_board` | ⚠️ bang |
| `_chup_mot_cot` | `_capture_one_column` |  |
| `chup_danh_sach` | `capture_list_clean` |  |
| `chup_svg` | `capture_svg` |  |
| `chup_logo` | `capture_logo` |  |
| `the_du_phong` | `fallback_card` |  |
| `giua` | `middle` |  |
| `_PhienChup` | `_SessionCapture` |  |
| `trang` | `page` |  |
| `thu` | `try` | ⚠️ thu |
| `_thu_nguon` | `_try_source` | ⚠️ thu |
| `tim_va_chup` | `find_and_capture` |  |
| `_hang_cua` | `_rank_of` |  |
| `_bo_qua_nguon` | `_skip_source` |  |
| `tim_va_chup_nhieu` | `find_and_capture_many` |  |

## D. Hằng số module

| Module | Hiện tại | Đề xuất | Cờ |
|---|---|---|---|
| `ada_chuan_bi` | `DRAFTS` | `DRAFTS` |  |
| `ada_chuan_bi` | `HERMES` | `HERMES` |  |
| `ada_chuan_bi` | `ROOT` | `ROOT` |  |
| `ada_chuan_bi` | `VN` | `VN` |  |
| `ada_nop` | `ROOT` | `ROOT` |  |
| `anh_bai` | `ANH_MOI_TRANG` | `IMAGE_NEW_PAGE` | ⚠️ moi |
| `anh_bai` | `CO_AI_SINH` | `HAS_AI_GENERATE` |  |
| `anh_bai` | `DAI_TOI_DA` | `LONG_MAX` |  |
| `anh_bai` | `DIEN_TICH_TOI_THIEU` | `?DIEN_?TICH_MIN` |  |
| `anh_bai` | `HDR` | `HDR` |  |
| `anh_bai` | `LA_TIN_MODEL` | `IS_STORY_MODEL` |  |
| `anh_bai` | `QUY` | `RULE` |  |
| `anh_bai` | `QUY_MODEL` | `RULE_MODEL` |  |
| `anh_bai` | `RAC` | `JUNK` |  |
| `anh_bai` | `UA` | `UA` |  |
| `anh_chuan_bi` | `CHO_KHOA_GIAY` | `WAIT_LOCK_SECONDS` | ⚠️ cho khoa |
| `anh_chuan_bi` | `CHO_LUOT_GIAY` | `WAIT_SLOT_SECONDS` |  |
| `anh_chuan_bi` | `SO_ENGINE_SONG_SONG` | `COUNT_?ENGINE_PARALLEL` | ⚠️ so |
| `anh_chuan_bi` | `TEN_CT` | `NAME_?CT` |  |
| `anh_chuan_bi` | `TOI_DA_CHET` | `MAX_CRASH` |  |
| `anh_khai_niem` | `CHU_DE` | `TOPIC` |  |
| `anh_khai_niem` | `NUOC` | `COUNTRY` |  |
| `anh_khai_niem` | `NUOC_VIET_TAT` | `COUNTRY_WRITE_ALL` |  |
| `anh_khai_niem` | `TEN_LOAI` | `NAME_TYPE` |  |
| `anh_khai_niem` | `TOI_DA_TU_KHOA` | `MAX_KEYWORD` |  |
| `anh_khai_niem` | `TU_BO` | `FROM_DROP` | ⚠️ bo tu |
| `anh_khai_niem` | `UA` | `UA` |  |
| `anh_thuc_the` | `CANH_NGAN_MIN` | `SHORT_SIDE_MIN` |  |
| `anh_thuc_the` | `TOI_DA_MOI_THUC_THE` | `MAX_NEW_ACTUAL_CARD` | ⚠️ moi the |
| `anh_thuc_the` | `TOI_DA_THUC_THE` | `MAX_ACTUAL_CARD` | ⚠️ the |
| `anh_thuc_the` | `WIKI_API` | `WIKI_API` |  |
| `anh_thuong_hieu` | `CANH_NGAN_MIN` | `SHORT_SIDE_MIN` |  |
| `anh_thuong_hieu` | `COMMONS` | `COMMONS` |  |
| `anh_thuong_hieu` | `CO_PHIEU_CHO` | `HAS_BALLOT_WAIT` | ⚠️ cho |
| `anh_thuong_hieu` | `CO_PHIEU_URL` | `HAS_BALLOT_URL` |  |
| `anh_thuong_hieu` | `DUONG_FEED` | `PATH_?FEED` |  |
| `anh_thuong_hieu` | `DUONG_TIN` | `PATH_STORY` |  |
| `anh_thuong_hieu` | `HAU_TO` | `SUFFIX` |  |
| `anh_thuong_hieu` | `NHIEU` | `MANY` |  |
| `anh_thuong_hieu` | `NHIEU_CHUNG` | `MANY_?CHUNG` |  |
| `anh_thuong_hieu` | `P_CONG_TY` | `P_GATE_BILLION` |  |
| `anh_thuong_hieu` | `P_WEBSITE` | `P_?WEBSITE` |  |
| `anh_thuong_hieu` | `TEN_HIEN` | `DISPLAY_NAME` |  |
| `anh_thuong_hieu` | `TEN_THEM` | `NAME_EXTRA` |  |
| `anh_thuong_hieu` | `TOI_DA_HANG` | `MAX_RANK` | ⚠️ hang |
| `anh_thuong_hieu` | `TOI_DA_MOI_HANG` | `MAX_NEW_RANK` | ⚠️ hang moi |
| `anh_thuong_hieu` | `TOI_DA_NGUOI` | `MAX_PERSON` |  |
| `anh_thuong_hieu` | `TOI_DA_NGUOI_NGANG` | `MAX_PERSON_LANDSCAPE` |  |
| `anh_thuong_hieu` | `TOI_DA_TRANG_CONG_BO` | `MAX_ANNOUNCEMENT_PAGE` |  |
| `anh_thuong_hieu` | `TOI_DA_TRUY_VAN` | `MAX_QUERIES` |  |
| `anh_thuong_hieu` | `TU_CHUNG_TEN` | `FROM_?CHUNG_NAME` | ⚠️ tu |
| `anh_thuong_hieu` | `WIKIDATA` | `WIKIDATA` |  |
| `approve_service` | `KET_PUBLISHING_GIAY` | `END_?PUBLISHING_SECONDS` |  |
| `article_extract` | `SKIP_IMG_HINTS` | `?SKIP_IMG_HINTS` |  |
| `article_extract` | `UA` | `UA` |  |
| `arxiv_bia` | `BAT_DAU_TOI` | `START_DARK` | ⚠️ toi |
| `arxiv_bia` | `CAO` | `HEIGHT` |  |
| `arxiv_bia` | `DAC` | `?DAC` |  |
| `arxiv_bia` | `DAC_TU` | `?DAC_FROM` | ⚠️ tu |
| `arxiv_bia` | `RONG` | `EMPTY` | ⚠️ rong |
| `arxiv_bia` | `TI_LE` | `RATIO` |  |
| `arxiv_bia` | `TOI` | `DARK` | ⚠️ toi |
| `arxiv_bia` | `UA` | `UA` |  |
| `arxiv_hinh` | `CANH_NGAN_MUC` | `SHORT_SIDE_ITEM` | ⚠️ muc |
| `arxiv_hinh` | `CHU_THICH` | `ANNOTATION` |  |
| `arxiv_hinh` | `DEM` | `COUNT` |  |
| `arxiv_hinh` | `KHE_CHU` | `?KHE_TEXT` | ⚠️ chu |
| `arxiv_hinh` | `LE_CHAY_DAU` | `ODD_RUN_MARK` | ⚠️ dau |
| `arxiv_hinh` | `LE_CUNG` | `ODD_SAME` |  |
| `arxiv_hinh` | `RONG_MUC` | `EMPTY_ITEM` | ⚠️ muc rong |
| `arxiv_hinh` | `SO_TRANG` | `COUNT_PAGE` | ⚠️ so |
| `arxiv_hinh` | `TI_LE_MAX` | `RATIO_MAX` |  |
| `arxiv_hinh` | `TOI_DA` | `MAX` |  |
| `arxiv_hinh` | `ZOOM_MAX` | `ZOOM_MAX` |  |
| `arxiv_hinh` | `ZOOM_MIN` | `ZOOM_MIN` |  |
| `bang_den` | `DRAFTS` | `DRAFTS` |  |
| `bang_den` | `HERMES_DIR` | `HERMES_DIR` |  |
| `bang_den` | `ROOT` | `ROOT` |  |
| `bang_den` | `ROOT_ASSIGNEE` | `ROOT_ASSIGNEE` |  |
| `bang_den` | `TIEN_TO_BAI` | `PREFIX_ARTICLE` |  |
| `bang_model` | `AA` | `AA` |  |
| `bang_model` | `ARENA` | `ARENA` |  |
| `bang_model` | `ARENA_BOARDS` | `ARENA_BOARDS` |  |
| `bang_model` | `BANG` | `BOARD` | ⚠️ bang |
| `bang_model` | `KHOA_BANG` | `LOCK_BOARD` | ⚠️ bang khoa |
| `bang_model` | `LINK_BANG` | `LINK_BOARD` | ⚠️ bang |
| `bang_model` | `NHAN_BANG` | `LABEL_BOARD` | ⚠️ bang nhan |
| `bang_model` | `SO_BANG` | `COUNT_BOARD` | ⚠️ bang so |
| `bang_model` | `SWE` | `?SWE` |  |
| `bao_cao_manifest` | `NHAC` | `MENTION` |  |
| `bao_cao_manifest` | `TEN_VAI` | `NAME_ROLE` |  |
| `bao_cao_manifest` | `VN` | `VN` |  |
| `bat_buoc` | `LINK_BANG` | `LINK_BOARD` | ⚠️ bang |
| `bob_nop` | `EMOJI_MAC_DINH` | `EMOJI_DEFAULT` |  |
| `bob_nop` | `GET_SOURCE` | `GET_?SOURCE` |  |
| `bob_nop` | `RC_KHONG_CO_ANH` | `RC_NO_HAS_IMAGE` |  |
| `bob_nop` | `ROOT` | `ROOT` |  |
| `bob_nop` | `SKILL` | `?SKILL` |  |
| `cape_chuan_bi` | `CHU_TOI_DA` | `TEXT_MAX` | ⚠️ chu |
| `cape_chuan_bi` | `ROOT` | `ROOT` |  |
| `cape_nop` | `ROOT` | `ROOT` |  |
| `caption_check` | `CUM_SO` | `PHRASE_COUNT` | ⚠️ so |
| `caption_check` | `DAU` | `MARK` | ⚠️ dau |
| `caption_check` | `GIOI_HAN` | `LIMIT` |  |
| `caption_check` | `NEN_DAT` | `BACKGROUND_SET` | ⚠️ nen |
| `caption_check` | `NGUONG_DAU` | `THRESHOLD_MARK` | ⚠️ dau |
| `caption_check` | `SAO_RONG` | `?SAO_EMPTY` | ⚠️ rong |
| `caption_check` | `SO` | `COUNT` | ⚠️ so |
| `caption_check` | `THE_CHO_PHEP` | `CARD_WAIT_?PHEP` | ⚠️ cho the |
| `caption_check` | `THOI_PHONG` | `TIME_ROOM` |  |
| `caption_check` | `TRAN_NEN_TANG` | `CEILING_BACKGROUND_LAYER` | ⚠️ nen |
| `caption_check` | `TU_CONG_BO` | `FROM_ANNOUNCEMENT` | ⚠️ tu |
| `card` | `ACCENT` | `ACCENT` |  |
| `card` | `ACCENT_DIM` | `ACCENT_DIM` |  |
| `card` | `ASSETS` | `?ASSETS` |  |
| `card` | `BG` | `BG` |  |
| `card` | `BG_CARD` | `BG_CARD` |  |
| `card` | `BRAND_CUM` | `BRAND_PHRASE` |  |
| `card` | `BRAND_SIZE` | `BRAND_SIZE` |  |
| `card` | `BRAND_TU` | `BRAND_FROM` | ⚠️ tu |
| `card` | `CYAN` | `?CYAN` |  |
| `card` | `DICH_ROI_DONG` | `TRANSLATE_?ROI_LINE` | ⚠️ dong |
| `card` | `FG` | `?FG` |  |
| `card` | `FONTS` | `FONTS` |  |
| `card` | `F_BOLD` | `F_?BOLD` |  |
| `card` | `F_HERO` | `F_HERO` |  |
| `card` | `F_MARK` | `F_MARK` |  |
| `card` | `F_MONO` | `F_?MONO` |  |
| `card` | `F_QUOTE` | `F_QUOTE` |  |
| `card` | `F_QUOTE_REG` | `F_QUOTE_?REG` |  |
| `card` | `F_REG` | `F_?REG` |  |
| `card` | `F_SUB` | `F_SUB` |  |
| `card` | `F_UI` | `F_?UI` |  |
| `card` | `HERO_WEIGHT` | `HERO_?WEIGHT` |  |
| `card` | `KICKER_CUM` | `KICKER_PHRASE` |  |
| `card` | `KICKER_GAP` | `KICKER_GAP` |  |
| `card` | `KICKER_HO` | `KICKER_?HO` |  |
| `card` | `KICKER_SIZE` | `KICKER_SIZE` |  |
| `card` | `KICKER_TRACK` | `KICKER_?TRACK` |  |
| `card` | `LINE` | `LINE` |  |
| `card` | `MARK_SIZE` | `MARK_SIZE` |  |
| `card` | `MAU_CUM` | `COLOR_PHRASE` | ⚠️ mau |
| `card` | `MAU_HANG` | `COLOR_RANK` | ⚠️ hang mau |
| `card` | `MUTED` | `?MUTED` |  |
| `card` | `NGUONG_NEN_SANG` | `THRESHOLD_BACKGROUND_BRIGHT` | ⚠️ nen sang |
| `card` | `NGUONG_ROI_DONG` | `THRESHOLD_?ROI_LINE` | ⚠️ dong |
| `card` | `PAD` | `PAD` |  |
| `card` | `QUOTE_BLUR` | `QUOTE_BLUR` |  |
| `card` | `QUOTE_BLUR_DEM` | `QUOTE_BLUR_COUNT` |  |
| `card` | `QUOTE_LEAD` | `QUOTE_LEAD` |  |
| `card` | `QUOTE_MAX_LINES` | `QUOTE_MAX_LINES` |  |
| `card` | `QUOTE_PAD` | `QUOTE_PAD` |  |
| `card` | `RATIOS` | `?RATIOS` |  |
| `card` | `SUB_SIZE` | `SUB_SIZE` |  |
| `card` | `THUONG_HIEU` | `BRAND` |  |
| `card` | `TITLE_GROW_LINES` | `TITLE_GROW_LINES` |  |
| `card` | `TITLE_GROW_MAX` | `TITLE_GROW_MAX` |  |
| `card` | `TOI_TOI_DA_DONG` | `DARK_MAX_LINE` | ⚠️ dong toi |
| `card` | `TRAN_FRAME_LW` | `CEILING_FRAME_?LW` |  |
| `card` | `TRAN_FRAME_PAD` | `CEILING_FRAME_PAD` |  |
| `card` | `TRAN_FRAME_R` | `CEILING_FRAME_R` |  |
| `card` | `TRAN_FRAME_X` | `CEILING_FRAME_X` |  |
| `card` | `TRAN_TEXTBOX` | `CEILING_?TEXTBOX` |  |
| `card` | `TRAN_TEXT_X` | `CEILING_TEXT_X` |  |
| `card` | `TRAN_TITLE_LINES` | `CEILING_TITLE_LINES` |  |
| `card` | `TRAN_TITLE_MAX` | `CEILING_TITLE_MAX` |  |
| `card` | `VIA_SIZE` | `?VIA_SIZE` |  |
| `carousel` | `BG` | `BG` |  |
| `carousel` | `BG_BLUR` | `BG_BLUR` |  |
| `carousel` | `BLUR_RADIUS` | `BLUR_RADIUS` |  |
| `carousel` | `BODY_LEAD` | `BODY_LEAD` |  |
| `carousel` | `CATEGORY_GOI_Y` | `CATEGORY_CALL_Y` |  |
| `carousel` | `FG` | `?FG` |  |
| `carousel` | `FLAGSHIP_MIN` | `FLAGSHIP_MIN` |  |
| `carousel` | `F_MONO_CH` | `F_?MONO_?CH` |  |
| `carousel` | `F_UI_CH` | `F_?UI_?CH` |  |
| `carousel` | `HOOK_LEAD` | `HOOK_LEAD` |  |
| `carousel` | `HOOK_WEIGHT` | `HOOK_?WEIGHT` |  |
| `carousel` | `LABEL_SIZE` | `LABEL_SIZE` |  |
| `carousel` | `MIN_SLIDE` | `MIN_SLIDE` |  |
| `carousel` | `MO` | `OPEN` |  |
| `carousel` | `NEN` | `BACKGROUND` | ⚠️ nen |
| `carousel` | `NEN_HIEN` | `BACKGROUND_SHOW` | ⚠️ nen |
| `carousel` | `NGUONG_ROI_CAN_LOP` | `THRESHOLD_?ROI_CAN_LAYER` |  |
| `carousel` | `NGUONG_SANG_SANG` | `THRESHOLD_BRIGHT_BRIGHT` | ⚠️ sang |
| `carousel` | `NGUONG_SANG_TOI` | `THRESHOLD_BRIGHT_DARK` | ⚠️ sang toi |
| `carousel` | `PAD` | `PAD` |  |
| `carousel` | `PARA_GAP` | `?PARA_GAP` |  |
| `carousel` | `Q_AVAIL` | `Q_?AVAIL` |  |
| `carousel` | `Q_BOTTOM` | `Q_BOTTOM` |  |
| `carousel` | `Q_FRAME_X` | `Q_FRAME_X` |  |
| `carousel` | `Q_LEAD` | `Q_LEAD` |  |
| `carousel` | `Q_LINES` | `Q_LINES` |  |
| `carousel` | `Q_TEXT_X` | `Q_TEXT_X` |  |
| `carousel` | `TEXT_BASE` | `TEXT_BASE` |  |
| `carousel` | `TEXT_MAX_H` | `TEXT_MAX_H` |  |
| `carousel` | `TOI_TOI_DA` | `DARK_MAX` | ⚠️ toi |
| `carousel` | `VEIL_EASE` | `?VEIL_?EASE` |  |
| `carousel` | `VEIL_SPAN` | `?VEIL_?SPAN` |  |
| `carousel` | `WM` | `?WM` |  |
| `carousel` | `WM_BOTTOM` | `?WM_BOTTOM` |  |
| `carousel` | `WM_SIZE` | `?WM_SIZE` |  |
| `chat_router` | `BO_CHI_DOC` | `DROP_ONLY_READ` | ⚠️ bo chi doc |
| `chat_router` | `CHAT_HINT` | `CHAT_HINT` |  |
| `chat_router` | `HERMES_DIR` | `HERMES_DIR` |  |
| `chat_router` | `HERMES_HOME` | `HERMES_HOME` |  |
| `chat_router` | `HERMES_PY` | `HERMES_PY` |  |
| `chat_router` | `REPLY_LIMIT` | `REPLY_LIMIT` |  |
| `chat_router` | `TIMEOUT_SEC` | `TIMEOUT_?SEC` |  |
| `chat_router` | `TOPIC_PROFILE` | `TOPIC_PROFILE` |  |
| `chuan_bi.chung` | `DRAFTS` | `DRAFTS` |  |
| `chuan_bi.chung` | `GNEWS` | `GNEWS` |  |
| `chuan_bi.chung` | `HDR` | `HDR` |  |
| `chuan_bi.chung` | `ROOT` | `ROOT` |  |
| `chuan_bi.chung` | `TOI_DA_ANH` | `MAX_IMAGE` |  |
| `chuan_bi.chung` | `UA` | `UA` |  |
| `chuan_bi.nguon` | `TU_CHUNG_DAU_CAU` | `FROM_?CHUNG_MARK_SENTENCE` | ⚠️ dau tu |
| `chuan_bi.nhin` | `VISION_MODEL` | `VISION_MODEL` |  |
| `chuan_bi.nhin` | `VISION_URL` | `VISION_URL` |  |
| `chuan_bi.tai_loc` | `CANH_NGAN_BO` | `SHORT_SIDE_DROP` | ⚠️ bo |
| `chuan_bi.tai_loc` | `TAI_TOI_DA_BYTE` | `DOWNLOAD_MAX_?BYTE` |  |
| `chuan_bi.tai_loc` | `TOI_DA_TAI` | `MAX_DOWNLOAD` |  |
| `chuan_bi.tai_loc` | `URL_RAC` | `URL_JUNK` |  |
| `chuan_bi.vong_bu` | `TOI_DA_THEM_TH` | `MAX_EXTRA_?TH` |  |
| `chuan_bi.vong_bu` | `TOI_DA_TRANG_CHUP` | `MAX_PAGE_CAPTURE` |  |
| `chuan_bi.vong_bu` | `XH_BOI_CANH_NGUON` | `?XH_CONTEXT_EDGE_SOURCE` | ⚠️ canh |
| `chup_chart` | `CAO_CANH_BAO` | `HEIGHT_WARNING` |  |
| `chup_chart` | `CHON_MAC_DINH` | `PICK_DEFAULT` |  |
| `chup_chart` | `DO_JS` | `MEASURE_JS` |  |
| `chup_chart` | `DPR` | `DPR` |  |
| `chup_chart` | `RONG_DAU` | `EMPTY_MARK` | ⚠️ dau rong |
| `chup_chart` | `RONG_TOI_DA` | `EMPTY_MAX` | ⚠️ rong |
| `chup_trang` | `CHON` | `PICK` |  |
| `chup_trang` | `CHO_LANG` | `WAIT_LANG` | ⚠️ cho |
| `chup_trang` | `CHO_LAZY` | `WAIT_?LAZY` | ⚠️ cho |
| `chup_trang` | `DPR` | `DPR` |  |
| `chup_trang` | `GIO_HAN` | `TIME_LIMIT` |  |
| `chup_trang` | `KHUNG` | `FRAME` |  |
| `chup_trang` | `LEAD_THU` | `LEAD_TRY` | ⚠️ thu |
| `chup_trang` | `TOI_THIEU` | `MIN` |  |
| `chup_trang` | `UA` | `UA` |  |
| `cleanup` | `ROOT` | `ROOT` |  |
| `cost_squeeze` | `GIA` | `GIA` | ⚠️ gia |
| `cost_squeeze` | `HERMES` | `HERMES` |  |
| `cost_squeeze` | `ROOT` | `ROOT` |  |
| `cost_squeeze` | `ROUTER` | `ROUTER` |  |
| `cost_squeeze` | `TIN_WRITER` | `STORY_WRITER` |  |
| `cost_squeeze` | `UNG_VIEN` | `CANDIDATE` |  |
| `cost_squeeze` | `VIEC` | `JOB` |  |
| `crop_ti_le` | `TI_LE` | `RATIO` |  |
| `deck` | `ASSETS` | `?ASSETS` |  |
| `deck` | `BG_CREAM` | `BG_?CREAM` |  |
| `deck` | `BG_DARK` | `BG_DARK` |  |
| `deck` | `BLUE` | `?BLUE` |  |
| `deck` | `CORAL` | `?CORAL` |  |
| `deck` | `CREAM` | `?CREAM` |  |
| `deck` | `FONTS` | `FONTS` |  |
| `deck` | `F_BODY` | `F_BODY` |  |
| `deck` | `F_COND` | `F_?COND` |  |
| `deck` | `F_SANS` | `F_?SANS` |  |
| `deck` | `F_SERIF` | `F_?SERIF` |  |
| `deck` | `GREY` | `?GREY` |  |
| `deck` | `INK` | `?INK` |  |
| `deck` | `LAYOUTS` | `?LAYOUTS` |  |
| `deck` | `PAD` | `PAD` |  |
| `deck` | `WHITE` | `?WHITE` |  |
| `doi_chu_anh` | `DIEN_TICH_TO_KIN` | `?DIEN_?TICH_?TO_?KIN` |  |
| `doi_chu_anh` | `DILATE_PX` | `DILATE_PX` |  |
| `dong_bo_hermes` | `DAU_VET` | `TRACE` |  |
| `dong_bo_hermes` | `HERMES_AGENT` | `HERMES_?AGENT` |  |
| `dong_bo_hermes` | `HOMES` | `HOMES` |  |
| `dong_bo_hermes` | `KHOA_BI_MAT` | `LOCK_SECRET` | ⚠️ khoa |
| `dong_bo_hermes` | `KHOA_PROMPT` | `LOCK_PROMPT` | ⚠️ khoa |
| `dong_bo_hermes` | `LA_PLUGIN` | `IS_PLUGIN` |  |
| `dong_bo_hermes` | `MAU_UPSTREAM` | `COLOR_UPSTREAM` | ⚠️ mau |
| `dong_bo_hermes` | `PLUGIN_REPO` | `PLUGIN_REPO` |  |
| `dong_bo_hermes` | `PLUGIN_TEP` | `PLUGIN_FILE` |  |
| `dong_bo_hermes` | `REPO` | `REPO` |  |
| `dong_bo_hermes` | `ROOT` | `ROOT` |  |
| `dong_bo_hermes` | `SCRIPT` | `?SCRIPT` |  |
| `dong_bo_hermes` | `TAT_CONG_CU` | `ALL_GATE_OLD` | ⚠️ cu |
| `dong_bo_hermes` | `TEP_CAU_HINH` | `FILE_CONFIG` |  |
| `dong_bo_hermes` | `TEP_UPSTREAM` | `FILE_UPSTREAM` |  |
| `draft_write` | `DRAFTS` | `DRAFTS` |  |
| `dre_chuan_bi` | `DRAFTS` | `DRAFTS` |  |
| `dre_chuan_bi` | `ROOT` | `ROOT` |  |
| `dre_nop` | `CHU_GIU` | `TEXT_KEEP` | ⚠️ chu |
| `dre_nop` | `DRAFTS` | `DRAFTS` |  |
| `dre_nop` | `ROOT` | `ROOT` |  |
| `duyet_bai` | `CAPTION_LIMIT` | `CAPTION_LIMIT` |  |
| `duyet_bai` | `DAU_LEN_CHANNEL` | `MARK_LEN_CHANNEL` | ⚠️ dau |
| `duyet_bai` | `LAM_LAI_CHO` | `REDO_WAIT` | ⚠️ cho |
| `duyet_bai` | `LAM_LAI_HAN` | `REDO_LIMIT` |  |
| `duyet_bai` | `NEN_TANG_NUT` | `BACKGROUND_LAYER_BUTTON` | ⚠️ nen |
| `duyet_chat` | `VAI_CHAT_LAM_VIEC` | `ROLE_CHAT_MAKE_JOB` |  |
| `duyet_chon_tin` | `MANIFEST_THEO_TOPIC` | `MANIFEST_BY_TOPIC` |  |
| `duyet_co_so` | `API` | `API` |  |
| `duyet_co_so` | `BRAND` | `BRAND` |  |
| `duyet_co_so` | `DRAFTS` | `DRAFTS` |  |
| `duyet_co_so` | `HERMES_HOME` | `HERMES_HOME` |  |
| `duyet_co_so` | `HERMES_PY` | `HERMES_PY` |  |
| `duyet_co_so` | `OFFSET` | `OFFSET` |  |
| `duyet_co_so` | `ONG_CHU_IDS` | `BOSS_IDS` |  |
| `duyet_co_so` | `ROOT` | `ROOT` |  |
| `duyet_co_so` | `STATE_DIR` | `STATE_DIR` |  |
| `duyet_co_so` | `TELEGRAM_INCOMING` | `TELEGRAM_?INCOMING` |  |
| `duyet_giao_viec` | `BANG_DEN_ASSIGNEE` | `BLACKBOARD_ASSIGNEE` |  |
| `duyet_giao_viec` | `BANG_DEN_BRANDS` | `BLACKBOARD_?BRANDS` |  |
| `duyet_giao_viec` | `BANG_DEN_NHAC` | `BLACKBOARD_MENTION` |  |
| `duyet_giao_viec` | `DA_BAO_TIEN_DO` | `ALREADY_OUTLET_PROGRESS` |  |
| `duyet_giao_viec` | `DA_BAO_TREO` | `ALREADY_OUTLET_STALLED` |  |
| `duyet_giao_viec` | `LAI_BAO_TREO_PHUT` | `AGAIN_OUTLET_STALLED_MINUTES` |  |
| `duyet_giao_viec` | `MAC_DINH_ANH` | `DEFAULT_IMAGE` |  |
| `duyet_giao_viec` | `MAC_DINH_VIET` | `DEFAULT_WRITE` |  |
| `duyet_giao_viec` | `NGUONG_TREO_PHUT` | `THRESHOLD_STALLED_MINUTES` |  |
| `duyet_giao_viec` | `NHAN_CHUAN` | `LABEL_STANDARD` | ⚠️ nhan |
| `duyet_giao_viec` | `NHIP_IM_PHUT` | `?NHIP_SILENT_MINUTES` |  |
| `duyet_giao_viec` | `SLUG_CU` | `SLUG_OLD` | ⚠️ cu |
| `duyet_giao_viec` | `TEN_SANG_CAP` | `NAME_BRIGHT_CAP` | ⚠️ sang |
| `duyet_giao_viec` | `TEN_VAI_ANH` | `NAME_ROLE_IMAGE` |  |
| `duyet_giao_viec` | `TEN_VAI_VIET` | `NAME_ROLE_WRITE` |  |
| `duyet_giao_viec` | `TIN_KET_QUA` | `STORY_RESULT` |  |
| `duyet_giao_viec` | `VAI_ANH` | `ROLE_IMAGE` |  |
| `duyet_giao_viec` | `VAI_CAROUSEL` | `ROLE_?CAROUSEL` |  |
| `duyet_giao_viec` | `VAI_EDU` | `ROLE_EDU` |  |
| `duyet_lenh` | `DAT_BAI_SO` | `SET_ARTICLE_COUNT` | ⚠️ so |
| `duyet_lenh` | `LENH_HELP` | `COMMAND_HELP` |  |
| `emoji_deck` | `DECK` | `DECK` |  |
| `emoji_deck` | `FLAG_HINTS` | `FLAG_HINTS` |  |
| `emoji_deck` | `STATE_PATH` | `STATE_PATH` |  |
| `env_load` | `BRAND_DAI` | `BRAND_LONG` |  |
| `env_load` | `HERMES_DIR` | `HERMES_DIR` |  |
| `env_load` | `HERMES_PY` | `HERMES_PY` |  |
| `env_load` | `ROOT` | `ROOT` |  |
| `env_load` | `ROUTER_URL` | `ROUTER_URL` |  |
| `env_load` | `UA_TRINH_DUYET` | `UA_?TRINH_APPROVE` |  |
| `env_load` | `UA_WIKI` | `UA_WIKI` |  |
| `env_load` | `VISION_MODEL` | `VISION_MODEL` |  |
| `ethan_chuan_bi` | `ROOT` | `ROOT` |  |
| `ethan_chuan_bi` | `TAGLINE_GOI_Y` | `TAGLINE_CALL_Y` |  |
| `ethan_chuan_bi` | `TI_LE_HERO_MAX` | `RATIO_HERO_MAX` |  |
| `ethan_nop` | `DRAFTS` | `DRAFTS` |  |
| `ethan_nop` | `ROOT` | `ROOT` |  |
| `gin_chuan_bi` | `ROOT` | `ROOT` |  |
| `gin_nop` | `ROOT` | `ROOT` |  |
| `gui_telegram` | `API` | `API` |  |
| `gui_telegram` | `STATE` | `STATE` |  |
| `gui_telegram` | `TOPICS` | `TOPICS` |  |
| `itachi_chuan_bi` | `LAYOUT_HELP` | `LAYOUT_HELP` |  |
| `itachi_chuan_bi` | `ROOT` | `ROOT` |  |
| `itachi_nop` | `CO_MIN` | `HAS_MIN` |  |
| `itachi_nop` | `FONT` | `FONT` |  |
| `itachi_nop` | `FONTS` | `FONTS` |  |
| `itachi_nop` | `NGUONG_TUONG_PHAN` | `THRESHOLD_WALL_PART` | ⚠️ phan |
| `itachi_nop` | `ROOT` | `ROOT` |  |
| `khung_anh` | `AVATARS` | `?AVATARS` |  |
| `khung_anh` | `BG` | `BG` |  |
| `khung_anh` | `DOTS` | `?DOTS` |  |
| `khung_anh` | `FONT_DIR` | `FONT_DIR` |  |
| `khung_anh` | `FOOTER` | `FOOTER` |  |
| `khung_anh` | `K_BONG` | `K_?BONG` |  |
| `khung_anh` | `K_BO_TRON_NGOAI` | `K_DROP_FULL_OUTSIDE` | ⚠️ bo |
| `khung_anh` | `K_BO_TRON_THE` | `K_DROP_FULL_CARD` | ⚠️ bo the |
| `khung_anh` | `MAU_HANDLE` | `COLOR_HANDLE` | ⚠️ mau |
| `khung_anh` | `MAU_PROMPT` | `COLOR_PROMPT` | ⚠️ mau |
| `khung_anh` | `MAXW` | `?MAXW` |  |
| `khung_anh` | `ROOT` | `ROOT` |  |
| `khung_anh` | `SKILL` | `?SKILL` |  |
| `khung_anh` | `VIEN` | `?VIEN` |  |
| `kiem_hermes` | `COT_CAN` | `COLUMN_CAN` |  |
| `kiem_hermes` | `COT_CAN_STATE` | `COLUMN_CAN_STATE` |  |
| `kiem_hermes` | `CO_CHAT` | `HAS_CHAT` |  |
| `kiem_hermes` | `HERMES_PY` | `HERMES_PY` |  |
| `kiem_hermes` | `ROOT` | `ROOT` |  |
| `kiem_moi_truong` | `MUC_KIEM` | `ITEM_CHECK` | ⚠️ muc |
| `kiem_moi_truong` | `TEN_MODEL_YUNET` | `NAME_MODEL_YUNET` |  |
| `kite_chuan_bi` | `FIG_RONG_TOI_THIEU` | `FIG_EMPTY_MIN` | ⚠️ rong |
| `kite_chuan_bi` | `ROOT` | `ROOT` |  |
| `kite_chuan_bi` | `TOI_DA_EP_HINH` | `MAX_FORCE_FIGURE` |  |
| `kite_nop` | `BAT_BUOC` | `REQUIRED` |  |
| `kite_nop` | `DRAFTS` | `DRAFTS` |  |
| `kite_nop` | `GIOI_HAN` | `LIMIT` |  |
| `kite_nop` | `ROOT` | `ROOT` |  |
| `loai_tin` | `BANG_ANH_THEO_LOAI` | `BOARD_IMAGE_BY_TYPE` | ⚠️ bang |
| `loai_tin` | `MAC_DINH` | `DEFAULT` |  |
| `loai_tin` | `MA_CO_PHIEU` | `CODE_HAS_BALLOT` | ⚠️ ma |
| `loai_tin` | `NUOC_CUA_HANG` | `COUNTRY_OF_RANK` | ⚠️ hang |
| `loai_tin` | `TU_KHOA_HA_TANG` | `KEYWORD_?HA_LAYER` |  |
| `luat_anh` | `CANH_NGAN_MIN` | `SHORT_SIDE_MIN` |  |
| `luat_anh` | `CANH_NGAN_TAI` | `SHORT_SIDE_DOWNLOAD` |  |
| `luat_anh` | `CAO_TOI_THIEU` | `HEIGHT_MIN` |  |
| `luat_anh` | `CHART_PHANG` | `CHART_FLAT` |  |
| `luat_anh` | `CHART_SO_MAU` | `CHART_COUNT_COLOR` | ⚠️ mau so |
| `luat_anh` | `DAU_PNG` | `MARK_PNG` | ⚠️ dau |
| `luat_anh` | `DAY_SANG_MAX` | `BRIGHT_BOTTOM_MAX` |  |
| `luat_anh` | `DIEN_TICH_TAI` | `?DIEN_?TICH_DOWNLOAD` |  |
| `luat_anh` | `DUNG_SAI_TI_LE` | `USE_WRONG_RATIO` | ⚠️ dung |
| `luat_anh` | `KHIT` | `?KHIT` |  |
| `luat_anh` | `MAT_CANH_MAX` | `FACE_EDGE_MAX` | ⚠️ canh |
| `luat_anh` | `NGANG_RO` | `LANDSCAPE_?RO` |  |
| `luat_anh` | `NGAY_NHO_ANH` | `DATE_SMALL_IMAGE` |  |
| `luat_anh` | `NGUONG_DO_HOA` | `THRESHOLD_MEASURE_IFY` |  |
| `luat_anh` | `RAC` | `JUNK` |  |
| `luat_anh` | `RONG_MAU` | `EMPTY_COLOR` | ⚠️ mau rong |
| `luat_anh` | `RONG_PHANG` | `EMPTY_FLAT` | ⚠️ rong |
| `luat_anh` | `TU_RAC_DOM` | `FROM_JUNK_DOM` | ⚠️ tu |
| `luat_anh` | `TU_RAC_URL` | `FROM_JUNK_URL` | ⚠️ tu |
| `manifest_build` | `ROOT` | `ROOT` |  |
| `manifest_build` | `STATE` | `STATE` |  |
| `manifest_build` | `TOI_DA_PICK` | `MAX_?PICK` |  |
| `manifest_build` | `VALID_CATEGORIES` | `?VALID_?CATEGORIES` |  |
| `manifest_chung` | `TOI_DA_TU_TOM_TAT` | `MAX_FROM_SUMMARY` | ⚠️ tu |
| `manifest_ghi` | `ROOT` | `ROOT` |  |
| `manifest_ghi` | `STATE` | `STATE` |  |
| `manifest_ghi` | `TIEN_TO` | `PREFIX` |  |
| `miles_chuan_bi` | `DRAFTS` | `DRAFTS` |  |
| `miles_chuan_bi` | `GIONG` | `VOICE` |  |
| `miles_chuan_bi` | `ROOT` | `ROOT` |  |
| `miles_nop` | `DRAFTS` | `DRAFTS` |  |
| `miles_nop` | `ROOT` | `ROOT` |  |
| `moat_publish` | `BAC_CHAT_LUONG` | `?BAC_QUALITY` |  |
| `moat_publish` | `CHAT_LUONG_NEN` | `QUALITY_BACKGROUND` | ⚠️ nen |
| `moat_publish` | `DRAFTS` | `DRAFTS` |  |
| `moat_publish` | `HANG_DOI` | `QUEUE` |  |
| `moat_publish` | `KHOA_MAC_DINH` | `LOCK_DEFAULT` | ⚠️ khoa |
| `moat_publish` | `KHOA_THEO_BRAND` | `LOCK_BY_BRAND` | ⚠️ khoa |
| `moat_publish` | `LICH_LUI` | `SCHEDULE_?LUI` |  |
| `moat_publish` | `MAC_DINH_BRAND` | `DEFAULT_BRAND` |  |
| `moat_publish` | `MAX_ANH` | `MAX_IMAGE` |  |
| `moat_publish` | `MAX_TRACK_DAYS` | `MAX_?TRACK_?DAYS` |  |
| `moat_publish` | `MA_NUT_DANG_LAI` | `CODE_BUTTON_FORM_AGAIN` | ⚠️ ma |
| `moat_publish` | `MIME_BY_SUFFIX` | `?MIME_?BY_?SUFFIX` |  |
| `moat_publish` | `NEN_ANH` | `BACKGROUND_IMAGE` | ⚠️ nen |
| `moat_publish` | `NGUONG_NEN` | `THRESHOLD_BACKGROUND` | ⚠️ nen |
| `moat_publish` | `PLATFORMS` | `?PLATFORMS` |  |
| `moat_publish` | `PLATFORM_LABEL` | `?PLATFORM_LABEL` |  |
| `moat_publish` | `ROOT` | `ROOT` |  |
| `moat_publish` | `SPOOL` | `?SPOOL` |  |
| `moat_publish` | `STATE_DIR` | `STATE_DIR` |  |
| `moat_publish` | `TERMINAL` | `?TERMINAL` |  |
| `moat_publish` | `TIMEOUT` | `TIMEOUT` |  |
| `moat_publish` | `TIMEOUT_DAY` | `TIMEOUT_BOTTOM` | ⚠️ day |
| `moat_publish` | `TRAN_NEN_TANG` | `CEILING_BACKGROUND_LAYER` | ⚠️ nen |
| `moat_publish` | `TRAN_TONG` | `CEILING_TOTAL` |  |
| `model_audition` | `DEM` | `COUNT` |  |
| `model_audition` | `NGUONG_DAU` | `THRESHOLD_MARK` | ⚠️ dau |
| `model_audition` | `ROUTER` | `ROUTER` |  |
| `model_audition` | `SYS` | `?SYS` |  |
| `model_audition` | `TIN` | `STORY` |  |
| `model_audition` | `TOOLS` | `?TOOLS` |  |
| `model_audition` | `UNGVIEN` | `?UNGVIEN` |  |
| `model_watch` | `PROBE` | `?PROBE` |  |
| `model_watch` | `REASONS` | `?REASONS` |  |
| `model_watch` | `ROUTER` | `ROUTER` |  |
| `model_watch` | `TIMEOUT` | `TIMEOUT` |  |
| `nguon_bai` | `BING_RSS` | `BING_RSS` |  |
| `nguon_bai` | `BO_MIEN` | `DROP_DOMAIN` | ⚠️ bo |
| `nguon_bai` | `GNEWS` | `GNEWS` |  |
| `nguon_bai` | `GNEWS_BAI` | `GNEWS_ARTICLE` |  |
| `nguon_bai` | `HDR` | `HDR` |  |
| `nguon_bai` | `RSS_DOAN` | `RSS_GUESS` |  |
| `nguon_bai` | `SO_NGUON` | `COUNT_SOURCE` | ⚠️ so |
| `nguon_bai` | `TU_RONG` | `FROM_EMPTY` | ⚠️ rong tu |
| `nguon_bai` | `TU_RONG_TRUY_VAN` | `FROM_EMPTY_QUERIES` | ⚠️ rong tu |
| `nguon_bai` | `UA` | `UA` |  |
| `nhat_ky` | `DANG_CHAY` | `FORM_RUN` |  |
| `nhat_ky` | `GHI_CHU` | `NOTES` |  |
| `nhat_ky` | `HERMES` | `HERMES` |  |
| `nhat_ky` | `LOAI` | `TYPE` |  |
| `nhat_ky` | `LOI_DOC` | `ERROR_READ` | ⚠️ doc |
| `nhat_ky` | `ROOT` | `ROOT` |  |
| `nhat_ky` | `THUA` | `EXCESS` |  |
| `nhat_ky` | `THU_MUC` | `DIRECTORY` |  |
| `nhat_ky` | `VN` | `VN` |  |
| `nhat_ky_web` | `CSS` | `CSS` |  |
| `nhat_ky_web` | `HOST` | `HOST` |  |
| `nhat_ky_web` | `PORT` | `PORT` |  |
| `nhat_ky_web` | `ROOT` | `ROOT` |  |
| `nop_chung` | `PHUT_ALBUM_VUA_LEN` | `MINUTES_ALBUM_FIT_LEN` |  |
| `nop_chung` | `ROOT` | `ROOT` |  |
| `nop_chung` | `TOI_DA_VONG` | `MAX_ROUND` |  |
| `phien_browser` | `ARGS_MAC_DINH` | `ARGS_DEFAULT` |  |
| `phien_browser` | `MA_CHAN` | `CODE_BLOCK` | ⚠️ ma |
| `phien_browser` | `MOBILE_DPR` | `MOBILE_DPR` |  |
| `phien_browser` | `MOBILE_UA` | `MOBILE_UA` |  |
| `phien_browser` | `MOBILE_VIEWPORT` | `MOBILE_VIEWPORT` |  |
| `publish` | `API` | `API` |  |
| `publish` | `CAPTION_LIMIT` | `CAPTION_LIMIT` |  |
| `publish` | `THE_HOP_LE` | `CARD_VALID` | ⚠️ the |
| `quet_chuan_bi` | `CACHE_GIO` | `CACHE_HOURS` |  |
| `quet_chuan_bi` | `ROOT` | `ROOT` |  |
| `quet_chuan_bi` | `TOPIC` | `TOPIC` |  |
| `quet_chuan_bi` | `TRAN_BAO_CAO` | `CEILING_REPORT` |  |
| `quet_chuan_bi` | `VN` | `VN` |  |
| `quet_chung` | `TEN_VAI` | `NAME_ROLE` |  |
| `quet_chung` | `TU_RONG` | `FROM_EMPTY` | ⚠️ rong tu |
| `quet_chung` | `UA` | `UA` |  |
| `quet_chung` | `VN` | `VN` |  |
| `quet_nop` | `CHAN_GUI` | `BLOCK_SEND` |  |
| `quet_nop` | `NHAN_CANH_BAO` | `LABEL_WARNING` | ⚠️ nhan |
| `quet_nop` | `ROOT` | `ROOT` |  |
| `quet_nop` | `TEN` | `NAME` |  |
| `render_edu` | `ANH_MIME` | `IMAGE_?MIME` |  |
| `render_edu` | `BASE_CSS_TPL` | `BASE_CSS_?TPL` |  |
| `render_edu` | `BAT_BUOC_KIND` | `REQUIRED_KIND` |  |
| `render_edu` | `BUILDERS` | `?BUILDERS` |  |
| `render_edu` | `DIM` | `DIM` |  |
| `render_edu` | `FALLBACK` | `FALLBACK` |  |
| `render_edu` | `FIG_DAY_PHANG` | `FIG_BOTTOM_FLAT` | ⚠️ day |
| `render_edu` | `FIG_DINH` | `FIG_FIXED` |  |
| `render_edu` | `FIG_RONG_TOI_THIEU` | `FIG_EMPTY_MIN` | ⚠️ rong |
| `render_edu` | `FIG_TIEU_DE_DONG` | `FIG_TITLE_LINE` | ⚠️ dong |
| `render_edu` | `FONTS` | `FONTS` |  |
| `render_edu` | `FONTS_DIR` | `FONTS_DIR` |  |
| `render_edu` | `FONT_URL` | `FONT_URL` |  |
| `render_edu` | `HEROES` | `?HEROES` |  |
| `render_edu` | `HERO_GRAPH` | `HERO_?GRAPH` |  |
| `render_edu` | `HERO_GRID` | `HERO_GRID` |  |
| `render_edu` | `HERO_ORBIT` | `HERO_?ORBIT` |  |
| `render_edu` | `HERO_RINGS` | `HERO_?RINGS` |  |
| `render_edu` | `HERO_TPL` | `HERO_?TPL` |  |
| `render_edu` | `HERO_WAVE` | `HERO_?WAVE` |  |
| `render_edu` | `MUTED` | `?MUTED` |  |
| `render_edu` | `NGUONG_HUE_LECH_MAU` | `THRESHOLD_?HUE_OFFSET_COLOR` | ⚠️ mau |
| `render_edu` | `NGUONG_LECH_VIEN` | `THRESHOLD_OFFSET_?VIEN` |  |
| `render_edu` | `NGUONG_SANG_CHU_TOI` | `THRESHOLD_BRIGHT_TEXT_DARK` | ⚠️ chu sang toi |
| `render_edu` | `ROOT` | `ROOT` |  |
| `render_edu` | `SOFT` | `?SOFT` |  |
| `render_edu` | `THEMES` | `?THEMES` |  |
| `render_edu` | `TI_LE_ANH_CO_MAU` | `RATIO_IMAGE_HAS_COLOR` | ⚠️ mau |
| `render_edu` | `TI_LE_MAU_AP_DAO` | `RATIO_COLOR_AP_INVERT` | ⚠️ mau |
| `render_edu` | `TI_LE_PHANG_TOI_THIEU` | `RATIO_FLAT_MIN` |  |
| `render_edu` | `TOI_TOI_DA_MO` | `DARK_MAX_OPEN` | ⚠️ toi |
| `render_edu` | `VEIL_SPAN` | `?VEIL_?SPAN` |  |
| `render_edu` | `WHITE` | `?WHITE` |  |
| `route_thieu_anh` | `DRAFTS` | `DRAFTS` |  |
| `scan_business` | `BAO_LON` | `OUTLET_LARGE` |  |
| `scan_business` | `GNEWS` | `GNEWS` |  |
| `scan_business` | `HANG_CUA_TEN` | `RANK_OF_NAME` |  |
| `scan_business` | `HANG_LOI` | `RANK_ERROR` | ⚠️ hang |
| `scan_business` | `RSS_BAO` | `RSS_OUTLET` |  |
| `scan_business` | `STATE` | `STATE` |  |
| `scan_business` | `TRUY_VAN` | `QUERIES` |  |
| `scan_business` | `TU_RONG` | `FROM_EMPTY` | ⚠️ rong tu |
| `scan_business` | `UA` | `UA` |  |
| `scan_business` | `WATCHLIST` | `WATCHLIST` |  |
| `scan_models` | `AA` | `AA` |  |
| `scan_models` | `AA_MEDIA` | `AA_MEDIA` |  |
| `scan_models` | `ANTHROPIC_CL` | `?ANTHROPIC_?CL` |  |
| `scan_models` | `ARCAGI` | `?ARCAGI` |  |
| `scan_models` | `ARENA` | `ARENA` |  |
| `scan_models` | `ARENA_BOARDS` | `ARENA_BOARDS` |  |
| `scan_models` | `ARENA_WEBDEV` | `ARENA_?WEBDEV` |  |
| `scan_models` | `BENCH_HINTS` | `?BENCH_HINTS` |  |
| `scan_models` | `BIG` | `?BIG` |  |
| `scan_models` | `CATALOG` | `?CATALOG` |  |
| `scan_models` | `ECI` | `?ECI` |  |
| `scan_models` | `GITHUB_REPOS` | `GITHUB_?REPOS` |  |
| `scan_models` | `HANG_MY` | `RANK_?MY` | ⚠️ hang |
| `scan_models` | `HANG_TQ` | `RANK_?TQ` | ⚠️ hang |
| `scan_models` | `HF_API` | `HF_API` |  |
| `scan_models` | `HF_RAC` | `HF_JUNK` |  |
| `scan_models` | `HF_SAN` | `HF_READY` |  |
| `scan_models` | `HLE` | `?HLE` |  |
| `scan_models` | `HLE_PAT` | `?HLE_PAT` |  |
| `scan_models` | `I2V_PAT` | `?I2V_PAT` |  |
| `scan_models` | `KHOA_BANG` | `LOCK_BOARD` | ⚠️ bang khoa |
| `scan_models` | `LIVEBENCH` | `?LIVEBENCH` |  |
| `scan_models` | `NHAN_BANG` | `LABEL_BOARD` | ⚠️ bang nhan |
| `scan_models` | `OC_API` | `?OC_API` |  |
| `scan_models` | `OPENROUTER` | `OPENROUTER` |  |
| `scan_models` | `OPENROUTER_RANK` | `OPENROUTER_RANK` |  |
| `scan_models` | `RSS_HANG` | `RSS_RANK` | ⚠️ hang |
| `scan_models` | `SO_BANG` | `COUNT_BOARD` | ⚠️ bang so |
| `scan_models` | `STATE` | `STATE` |  |
| `scan_models` | `STT_PAT` | `?STT_PAT` |  |
| `scan_models` | `SWEBENCH` | `?SWEBENCH` |  |
| `scan_models` | `SWE_BASH` | `?SWE_?BASH` |  |
| `scan_models` | `SWE_SPLIT` | `?SWE_SPLIT` |  |
| `scan_models` | `TBENCH` | `?TBENCH` |  |
| `scan_models` | `TBENCH_BANG` | `?TBENCH_BOARD` | ⚠️ bang |
| `scan_models` | `TRAN_BANG` | `CEILING_BOARD` | ⚠️ bang |
| `scan_models` | `TRAN_BM` | `CEILING_?BM` |  |
| `scan_models` | `TRAN_GH` | `CEILING_?GH` |  |
| `scan_models` | `TRAN_HF` | `CEILING_HF` |  |
| `scan_models` | `TRAN_MOI` | `CEILING_NEW` | ⚠️ moi |
| `scan_models` | `TTS_PAT` | `?TTS_PAT` |  |
| `scan_models` | `TU_KHOA_TIN` | `KEYWORD_STORY` |  |
| `scan_models` | `UA` | `UA` |  |
| `scan_models` | `VUNG_NHAN` | `REGION_LABEL` | ⚠️ nhan |
| `scan_sources` | `AI_HINTS` | `AI_HINTS` |  |
| `scan_sources` | `ANH_RAC` | `IMAGE_JUNK` |  |
| `scan_sources` | `ARXIV_CATS` | `ARXIV_?CATS` |  |
| `scan_sources` | `HANG_FRONTIER` | `RANK_?FRONTIER` | ⚠️ hang |
| `scan_sources` | `KHONG_CO_ANH` | `NO_HAS_IMAGE` |  |
| `scan_sources` | `MAX_AGE_HOURS` | `MAX_?AGE_?HOURS` |  |
| `scan_sources` | `ROOT` | `ROOT` |  |
| `scan_sources` | `STATE` | `STATE` |  |
| `scan_sources` | `SUBS` | `?SUBS` |  |
| `scan_sources` | `TEN_TO_CHUC` | `NAME_?TO_?CHUC` |  |
| `scan_sources` | `TU_KHOA_AI` | `KEYWORD_AI` |  |
| `scan_sources` | `UA` | `UA` |  |
| `schema` | `CAO_TOI_THIEU_CAT_NGANG` | `HEIGHT_MIN_CROP_LANDSCAPE` |  |
| `schema` | `PHIEN_BAN_MANIFEST` | `VERSION_MANIFEST` |  |
| `soat_cron` | `DAU` | `MARK` | ⚠️ dau |
| `soat_cron` | `MUC` | `ITEM` | ⚠️ muc |
| `soat_cron` | `TICK_CU` | `?TICK_OLD` | ⚠️ cu |
| `soat_cron` | `TRE_GIAY` | `?TRE_SECONDS` |  |
| `social_post` | `HOSTS` | `?HOSTS` |  |
| `social_post` | `ROOT` | `ROOT` |  |
| `social_post` | `SCRIPT` | `?SCRIPT` |  |
| `task_bodies` | `CAROUSEL_BODY` | `?CAROUSEL_BODY` |  |
| `task_bodies` | `EDU_BODY` | `EDU_BODY` |  |
| `task_bodies` | `ILLU_BODY` | `?ILLU_BODY` |  |
| `task_bodies` | `KET_THUC_VAI_ANH` | `END_ROLE_IMAGE` |  |
| `task_bodies` | `WRITER_BODY` | `WRITER_BODY` |  |
| `teaser_assemble` | `CLOSING` | `?CLOSING` |  |
| `teaser_assemble` | `CUM_TUONG_THUAT` | `PHRASE_WALL_?THUAT` |  |
| `teaser_assemble` | `DAI_HONG` | `LONG_BROKEN` |  |
| `teaser_assemble` | `DAI_MONG_MUON` | `LONG_?MONG_?MUON` |  |
| `tele_util` | `GIOI_HAN` | `LIMIT` |  |
| `theo_doi_9router` | `DB` | `DB` |  |
| `theo_doi_9router` | `DRAFTS` | `DRAFTS` |  |
| `theo_doi_9router` | `FALLBACK_THAT` | `FALLBACK_REAL` |  |
| `theo_doi_9router` | `GIAY_LAT` | `SECONDS_FLIP` |  |
| `theo_doi_9router` | `HERMES_HOMES` | `HERMES_HOMES` |  |
| `theo_doi_9router` | `NGUONG_CACHE` | `THRESHOLD_CACHE` |  |
| `theo_doi_9router` | `NHAT_KY` | `JOURNAL` |  |
| `theo_doi_9router` | `PROMPT_TOI_THIEU_CACHE` | `PROMPT_MIN_CACHE` |  |
| `theo_doi_9router` | `RONG_OUT_MAX` | `EMPTY_OUT_MAX` | ⚠️ rong |
| `theo_doi_9router` | `RONG_PROMPT_MIN` | `EMPTY_PROMPT_MIN` | ⚠️ rong |
| `theo_doi_9router` | `ROOT` | `ROOT` |  |
| `theo_doi_9router` | `THU_MUC` | `DIRECTORY` |  |
| `theo_doi_9router` | `VN` | `VN` |  |
| `theo_doi_9router` | `WEB_URL` | `?WEB_URL` |  |
| `tieng_viet` | `AM_MAT_DAU` | `NEGATIVE_FACE_MARK` | ⚠️ dau |
| `tieng_viet` | `CUM_MAT_DAU` | `PHRASE_FACE_MARK` | ⚠️ dau |
| `tieng_viet` | `DAU_CAM` | `MARK_?CAM` | ⚠️ dau |
| `tim_anh_them` | `CANH_NGAN_OPENVERSE` | `SHORT_SIDE_OPENVERSE` |  |
| `tim_anh_them` | `GIAY_PHEP_OK` | `SECONDS_?PHEP_OK` |  |
| `tim_anh_them` | `OPENVERSE` | `OPENVERSE` |  |
| `tim_anh_them` | `ROOT` | `ROOT` |  |
| `tim_anh_them` | `SO_BAO_MOI_LUOT` | `COUNT_OUTLET_NEW_SLOT` | ⚠️ moi so |
| `tim_anh_them` | `SO_COMMONS_MOI_LUOT` | `COUNT_COMMONS_NEW_SLOT` | ⚠️ moi so |
| `tim_anh_them` | `THUMB_COMMONS` | `THUMB_COMMONS` |  |
| `tim_anh_them` | `TOI_DA_ANH_THEM` | `MAX_IMAGE_EXTRA` |  |
| `tim_anh_them` | `TOI_DA_LUOT` | `MAX_SLOT` |  |
| `tu_lieu` | `CHU_TOI_DA` | `TEXT_MAX` | ⚠️ chu |
| `tu_lieu` | `CO_SO` | `HAS_COUNT` | ⚠️ so |
| `tu_lieu` | `ROOT` | `ROOT` |  |
| `tu_lieu` | `SO_BAI_KHAC` | `COUNT_ARTICLE_OTHER` | ⚠️ so |
| `vai` | `MAC_DINH_ANH` | `DEFAULT_IMAGE` |  |
| `vai` | `MAC_DINH_VIET` | `DEFAULT_WRITE` |  |
| `vai` | `MAX_RUNTIME` | `MAX_?RUNTIME` |  |
| `vai` | `MAX_RUNTIME_ANH` | `MAX_?RUNTIME_IMAGE` |  |
| `vai` | `SLUG_CU` | `SLUG_OLD` | ⚠️ cu |
| `vai` | `TEN_HIEN` | `DISPLAY_NAME` |  |
| `vai` | `TEN_SANG_CAP` | `NAME_BRIGHT_CAP` | ⚠️ sang |
| `vai` | `TEN_VAI_ANH` | `NAME_ROLE_IMAGE` |  |
| `vai` | `TEN_VAI_VIET` | `NAME_ROLE_WRITE` |  |
| `vai` | `VAI` | `ROLE` |  |
| `vai` | `VAI_ANH` | `ROLE_IMAGE` |  |
| `vai` | `VAI_CAROUSEL` | `ROLE_?CAROUSEL` |  |
| `vai` | `VAI_EDU` | `ROLE_EDU` |  |
| `vai` | `VIET_THEO_BRAND` | `WRITE_BY_BRAND` |  |
| `vai` | `VIET_THEO_QUET` | `WRITE_BY_SCAN` |  |
| `xep_hang` | `ARGS_CHUP` | `ARGS_CAPTURE` |  |
| `xep_hang` | `CAO_TOI_DA_CSS` | `HEIGHT_MAX_CSS` |  |
| `xep_hang` | `CHU_DE` | `TOPIC` |  |
| `xep_hang` | `DPR` | `DPR` |  |
| `xep_hang` | `GIO_HAN` | `TIME_LIMIT` |  |
| `xep_hang` | `KIEU_CHUP` | `KIND_CAPTURE` |  |
| `xep_hang` | `NGUON` | `SOURCE` |  |
| `xep_hang` | `ROOT` | `ROOT` |  |
| `xep_hang` | `TI_LE_VUA` | `RATIO_FIT` |  |
| `xep_hang` | `TOI_DA_XH` | `MAX_?XH` |  |
| `xep_hang` | `TOP_MAC_DINH` | `TOP_DEFAULT` |  |
| `xep_hang` | `TREN_MODEL` | `ON_MODEL` |  |
| `xep_hang` | `UA` | `UA` |  |
| `xep_hang` | `VANG` | `?VANG` |  |

## E. Token chưa có trong bảng

| token | lần | ví dụ module |
|---|---|---|
| `tbench` | 3 | scan_models |
| `hle` | 3 | scan_models |
| `dien` | 3 | anh_bai, doi_chu_anh, luat_anh |
| `tich` | 3 | anh_bai, doi_chu_anh, luat_anh |
| `chung` | 3 | anh_thuong_hieu, arxiv_hinh, brief_chung |
| `swe` | 3 | bang_model, scan_models |
| `roi` | 3 | card, carousel |
| `veil` | 3 | carousel, render_edu |
| `wm` | 3 | carousel |
| `carousel` | 3 | carousel, duyet_chon_tin, duyet_giao_viec |
| `bac` | 2 | ada_chuan_bi, moat_publish |
| `llm` | 2 | anh_khai_niem |
| `ho` | 2 | approve_service, card, duyet_bai |
| `message` | 2 | approve_service, gui_telegram, nhat_ky_web |
| `publishing` | 2 | approve_service |
| `kb` | 2 | ada_chuan_bi, arxiv_hinh, bang_den |
| `mood` | 2 | bob_nop |
| `tracked` | 2 | card |
| `chip` | 2 | card, carousel |
| `neo` | 2 | card, carousel, teaser_assemble |
| `draw` | 2 | carousel, deck |
| `cyan` | 2 | card, carousel |
| `route` | 2 | anh_chuan_bi, chat_router, render_edu |
| `sung` | 2 | chuan_bi.vong_bu, quet_chuan_bi, tim_anh_them |
| `rut` | 2 | cost_squeeze, duyet_co_so, ghi_log |
| `two` | 2 | deck |
| `statement` | 2 | deck, render_edu |
| `steps` | 2 | deck, render_edu |
| `burst` | 2 | deck |
| `ha` | 2 | chuan_bi.tai_loc, duyet_bai, loai_tin |
| `xa` | 2 | duyet_chon_tin, nhat_ky_web |
| `engine` | 2 | anh_chuan_bi, duyet_chon_tin |
| `create` | 2 | duyet_chon_tin, duyet_giao_viec |
| `gian` | 2 | ada_chuan_bi, khung_anh, quet_chung |
| `dam` | 2 | kite_chuan_bi, nhat_ky_web |
| `muon` | 2 | dong_bo_hermes, loai_tin, teaser_assemble |
| `pick` | 2 | approve_service, manifest_build |
| `intake` | 2 | moat_publish |
| `poll` | 2 | moat_publish |
| `tele` | 2 | moat_publish, tele_util, theo_doi_9router |
| `probe` | 2 | card, carousel, model_watch |
| `feed` | 2 | anh_thuong_hieu, nguon_bai |
| `hue` | 2 | render_edu |
| `catalog` | 2 | scan_models |
| `swebench` | 2 | scan_models |
| `livebench` | 2 | scan_models |
| `arcagi` | 2 | scan_models |
| `epoch` | 2 | scan_models, scan_sources, soat_cron |
| `anthropic` | 2 | scan_models |
| `gon` | 2 | scan_models, theo_doi_9router |
| `age` | 2 | cleanup, scan_sources |
| `hours` | 2 | scan_sources |
| `thuat` | 2 | teaser_assemble |
| `cam` | 2 | brief_chung, duyet_lenh, quet_chung |
| `dac` | 2 | anh_bai, anh_khai_niem, anh_thuong_hieu |
| `skill` | 2 | bob_nop, khung_anh |
| `phep` | 2 | caption_check, duyet_bai, duyet_co_so |
| `assets` | 2 | card, deck |
| `fg` | 2 | card, carousel, deck |
| `mono` | 2 | card, carousel |
| `reg` | 2 | card |
| `ui` | 2 | card, carousel |
| `weight` | 2 | card, carousel, deck |
| `track` | 2 | card, moat_publish |
| `muted` | 2 | card, render_edu |
| `ch` | 2 | approve_service, carousel, chuan_bi.manifest |
| `span` | 2 | carousel, render_edu |
| `xh` | 2 | chuan_bi.manifest, chuan_bi.vong_bu, ethan_chuan_bi |
| `cream` | 2 | deck |
| `white` | 2 | deck, render_edu |
| `to` | 2 | anh_thuong_hieu, bang_den, card |
| `script` | 2 | dong_bo_hermes, social_post |
| `vien` | 2 | anh_bai, anh_thuong_hieu, arxiv_hinh |
| `mime` | 2 | moat_publish, render_edu |
| `tpl` | 2 | render_edu |
| `runtime` | 2 | hermes_adapter, vai |
| `9router` | 1 | ada_chuan_bi, theo_doi_9router |
| `heuristic` | 1 | anh_khai_niem |
| `pageimages` | 1 | anh_thuc_the |
| `tro` | 1 | approve_service, kiem_hermes |
| `tirith` | 1 | approve_service |
| `cuu` | 1 | approve_service |
| `extract` | 1 | article_extract |
| `gop` | 1 | arxiv_hinh, caption_check, theo_doi_9router |
| `chong` | 1 | arxiv_hinh |
| `of` | 1 | bang_den |
| `lap` | 1 | anh_chuan_bi, anh_thuong_hieu, caption_check |
| `wrap` | 1 | card, render_edu |
| `pha` | 1 | card |
| `block` | 1 | carousel |
| `paragraphs` | 1 | article_extract, carousel, teaser_assemble |
| `net` | 1 | card, carousel |
| `watermark` | 1 | carousel |
| `ramp` | 1 | carousel |
| `argv` | 1 | chat_router |
| `ask` | 1 | chat_router |
| `clean` | 1 | chat_router |
| `pass` | 1 | chuan_bi.browser |
| `nhin` | 1 | anh_chuan_bi, chuan_bi.manifest, chuan_bi.nhin |
| `ben` | 1 | chuan_bi.tai_loc |
| `ba` | 1 | chuan_bi.tai_loc |
| `candidates` | 1 | cleanup |
| `trim` | 1 | cleanup |
| `jsonl` | 1 | cleanup |
| `only` | 1 | cleanup |
| `manifests` | 1 | cleanup |
| `suy` | 1 | cost_squeeze |
| `luan` | 1 | cost_squeeze |
| `soul` | 1 | cost_squeeze, dong_bo_hermes |
| `teaser` | 1 | cost_squeeze, teaser_assemble |
| `badge` | 1 | deck |
| `checklist` | 1 | deck |
| `grid3` | 1 | deck |
| `inpaint` | 1 | doi_chu_anh |
| `keyboard` | 1 | duyet_bai |
| `publish` | 1 | duyet_bai, moat_publish, publish |
| `approval` | 1 | duyet_bai |
| `moat` | 1 | duyet_bai, moat_publish |
| `dua` | 1 | duyet_chat |
| `latest` | 1 | duyet_chon_tin |
| `research` | 1 | duyet_chon_tin |
| `sidecar` | 1 | duyet_chon_tin |
| `pair` | 1 | duyet_chon_tin |
| `call` | 1 | duyet_co_so |
| `command` | 1 | duyet_lenh |
| `save` | 1 | emoji_deck |
| `preview` | 1 | gin_chuan_bi |
| `avatar` | 1 | khung_anh |
| `swarm` | 1 | kiem_hermes |
| `openai` | 1 | kiem_moi_truong |
| `gi` | 1 | kite_chuan_bi |
| `tho` | 1 | chuan_bi.nhin, duyet_bai, hermes_adapter |
| `minh` | 1 | luat_anh |
| `container` | 1 | moat_publish |
| `thuan` | 1 | moat_publish |
| `xep` | 1 | anh_chuan_bi, chuan_bi.manifest, chuan_bi.vong_bu |
| `notify` | 1 | moat_publish |
| `use` | 1 | model_watch |
| `luminance` | 1 | nen_chu |
| `chiu` | 1 | nhat_ky |
| `handler` | 1 | nhat_ky_web |
| `persona` | 1 | miles_chuan_bi, miles_nop, nop_chung |
| `hoac` | 1 | phien_browser |
| `check` | 1 | caption_check, publish |
| `manh` | 1 | bat_buoc, chuan_bi.manifest, duyet_chon_tin |
| `photo` | 1 | publish |
| `document` | 1 | publish |
| `scout` | 1 | quet_chuan_bi |
| `market` | 1 | quet_chuan_bi |
| `ghim` | 1 | quet_nop |
| `face` | 1 | render_edu |
| `ff` | 1 | render_edu |
| `data` | 1 | approve_service, article_extract, arxiv_hinh |
| `uri` | 1 | render_edu |
| `esc` | 1 | render_edu |
| `glow` | 1 | render_edu |
| `masthead` | 1 | render_edu |
| `eyebrow` | 1 | render_edu |
| `folio` | 1 | render_edu |
| `mast` | 1 | render_edu |
| `bars` | 1 | render_edu |
| `cta` | 1 | render_edu |
| `truong` | 1 | kiem_moi_truong, render_edu |
| `it` | 1 | ada_chuan_bi, bao_cao_manifest, bat_buoc |
| `tg` | 1 | route_thieu_anh |
| `usd` | 1 | cost_squeeze, scan_models |
| `1m` | 1 | scan_models |
| `usage` | 1 | scan_models |
| `opencompass` | 1 | scan_models |
| `trending` | 1 | scan_models |
| `rsc` | 1 | scan_models |
| `gon2` | 1 | scan_models |
| `trich` | 1 | kite_nop, scan_models, teaser_assemble |
| `benchmark` | 1 | scan_models |
| `ish` | 1 | scan_sources |
| `recency` | 1 | scan_sources |
| `spread` | 1 | scan_sources |
| `hn` | 1 | scan_sources |
| `seen` | 1 | scan_models, scan_sources |
| `sidecarImage` | 1 |  |
| `sidecarWrite` | 1 |  |
| `tuoi` | 1 | quet_chuan_bi, soat_cron |
| `assemble` | 1 | teaser_assemble |
| `ansi` | 1 | tele_util |
| `chia` | 1 | tele_util |
| `hhmm` | 1 | theo_doi_9router |
| `soi` | 1 | theo_doi_9router |
| `pct` | 1 | render_edu, theo_doi_9router |
| `khoanh` | 1 | xep_hang |
| `ct` | 1 | anh_chuan_bi, arxiv_hinh, chuan_bi.nhin |
| `website` | 1 | anh_thuong_hieu |
| `skip` | 1 | article_extract |
| `khe` | 1 | arxiv_hinh, khung_anh |
| `source` | 1 | bob_nop, duyet_bai, duyet_lenh |
| `sao` | 1 | bob_nop, caption_check |
| `bold` | 1 | card, deck |
| `ratios` | 1 | card |
| `lw` | 1 | card, carousel |
| `textbox` | 1 | card |
| `via` | 1 | card, schema, xep_hang |
| `para` | 1 | carousel |
| `avail` | 1 | card, carousel |
| `ease` | 1 | carousel |
| `sec` | 1 | chat_router |
| `byte` | 1 | chuan_bi.tai_loc |
| `th` | 1 | anh_thuong_hieu, chuan_bi.manifest, chuan_bi.vong_bu |
| `lazy` | 1 | chup_trang |
| `blue` | 1 | deck |
| `coral` | 1 | deck |
| `cond` | 1 | deck |
| `sans` | 1 | deck |
| `serif` | 1 | deck |
| `grey` | 1 | deck |
| `ink` | 1 | card, deck |
| `layouts` | 1 | deck |
| `kin` | 1 | doi_chu_anh |
| `agent` | 1 | dong_bo_hermes, scan_models |
| `incoming` | 1 | duyet_co_so |
| `brands` | 1 | duyet_giao_viec |
| `nhip` | 1 | duyet_giao_viec, hermes_adapter, soat_cron |
| `trinh` | 1 | env_load |
| `avatars` | 1 | khung_anh |
| `dots` | 1 | khung_anh |
| `bong` | 1 | khung_anh |
| `maxw` | 1 | khung_anh |
| `khit` | 1 | luat_anh |
| `ro` | 1 | duyet_bai, luat_anh, xep_hang |
| `valid` | 1 | manifest_build |
| `categories` | 1 | manifest_build |
| `lui` | 1 | moat_publish |
| `days` | 1 | cleanup, moat_publish |
| `by` | 1 | chat_router, manifest_build, moat_publish |
| `suffix` | 1 | moat_publish |
| `platforms` | 1 | moat_publish |
| `platform` | 1 | moat_publish |
| `spool` | 1 | moat_publish |
| `terminal` | 1 | moat_publish |
| `sys` | 1 | cost_squeeze, model_audition |
| `tools` | 1 | hermes_adapter, model_audition |
| `ungvien` | 1 | model_audition |
| `reasons` | 1 | model_watch |
| `builders` | 1 | render_edu |
| `heroes` | 1 | render_edu |
| `graph` | 1 | render_edu |
| `orbit` | 1 | render_edu |
| `rings` | 1 | render_edu |
| `wave` | 1 | render_edu |
| `soft` | 1 | render_edu |
| `themes` | 1 | render_edu |
| `cl` | 1 | anh_thuong_hieu, scan_models |
| `webdev` | 1 | scan_models |
| `bench` | 1 | scan_models |
| `big` | 1 | scan_models |
| `eci` | 1 | scan_models |
| `repos` | 1 | scan_models |
| `my` | 1 | scan_models |
| `tq` | 1 | scan_models |
| `i2v` | 1 | scan_models |
| `oc` | 1 | scan_models |
| `stt` | 1 | gin_nop, scan_models, social_post |
| `bash` | 1 | scan_models |
| `bm` | 1 | scan_models |
| `gh` | 1 | arxiv_hinh, kite_nop, scan_models |
| `tts` | 1 | scan_models |
| `cats` | 1 | scan_sources |
| `frontier` | 1 | scan_sources |
| `subs` | 1 | scan_sources |
| `chuc` | 1 | scan_sources |
| `tick` | 1 | soat_cron |
| `tre` | 1 | soat_cron |
| `hosts` | 1 | social_post |
| `illu` | 1 | duyet_chon_tin, task_bodies |
| `closing` | 1 | card, teaser_assemble |
| `mong` | 1 | teaser_assemble |
| `web` | 1 | nhat_ky_web, theo_doi_9router |
| `vang` | 1 | xep_hang |