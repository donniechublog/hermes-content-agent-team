# Từ điển tên — Việt không dấu → English — **v0** (CHƯA đụng mã)

Bước 0 của việc chuyển quy ước đặt tên tệp/hàm/hằng số từ tiếng Việt không dấu
sang English (xem `feedback_dat_ten_english_cho_sau.md` trong memory của agent:
quy ước cũ không do Ông Chủ đặt — phiên đầu 20/08/2026 tự chọn — bị coi là nhập
nhằng, nhưng đổi ngay là refactor giữa lúc nhiều nhánh đang hoạt động).

**Trạng thái v0 (13/09/2026): mọi tên trong 103 module đều có tên English đích,
0 token chưa map, 0 va chạm. Chưa rename một tên nào trong mã. Chờ Ông Chủ duyệt.**

## Tiêu chí chốt (Ông Chủ 12/09/2026)

> *"ngữ nghĩa là gì không quan trọng, thích gán nó là gì cũng được, không bị
> lẫn lộn hàm là được"*

Tức bảng chỉ cần đảm bảo **không hai hàm/lớp top-level nào trong cùng module
trùng tên sau khi dịch** (Python ghi đè định nghĩa trùng tên trong cùng module —
đó mới là "lỗi gọi" thật). `gen.py` tự kiểm ở **mục F** và thoát mã 1 nếu còn
va chạm. Nghĩa đúng từng chữ **không** là điều kiện.

## Tệp trong thư mục này

| Tệp | Vai trò |
|---|---|
| `TU_DIEN_TEN_v0.md` | Bảng đề xuất đầy đủ (A/A2 từ gốc → B module → C hàm/lớp → D hằng số → E chưa map → F va chạm) — **cái Ông Chủ đọc/duyệt** |
| `cum.json` | 392 CỤM Việt → English, khớp trước khi xét từ đơn |
| `don.json` | 369 TỪ ĐƠN Việt → English |
| `moho.json` | 40 token mơ hồ (một chữ không dấu, nhiều nghĩa) + giá trị mặc định đã chọn |
| `them.json` | Chỉ còn `PASS` — 954 token đã là English/tên riêng/benchmark, giữ nguyên |
| `overrides.json` | 65 ca đè tuyệt đối theo `"module.tên_gốc": "tên_mới"` — thắng mọi bảng trên |
| `gen.py` | Sinh lại `TU_DIEN_TEN_v0.md` từ 5 tệp JSON + repo; tự kiểm va chạm |
| `SOAT_NGU_NGHIA_5_module.md` | Lượt soát tay 86 hàm theo hành vi thật (tham khảo; 60 tên đã đưa vào `overrides.json`) |

## Thứ tự ưu tiên khi dịch một tên (`gen.py`)

1. `overrides.json` khớp `module.tên_gốc` → dùng ngay, bỏ qua mọi bước dưới.
2. Tách tên theo `_`; tại mỗi vị trí thử CỤM 4→3→2 token trong `cum.json`.
3. Không khớp cụm → từ đơn: **PASS** (giữ nguyên) → `don.json` → `?token` (chưa map).
4. Module: `cum.json` tra theo tên tệp; `__init__` giữ nguyên; `chuan_bi/` → `prepare/`.

## Những gì v0 chốt so với bản nháp

**Gộp từ điển về một chỗ.** Bản nháp có `them.json["DON"]` bổ sung `don.json` bằng
`setdefault` — 10 khoá Việt có **hai giá trị khác nhau** ở hai tệp và bản trong
`them` chết lặng lẽ. v0 gộp hết vào `cum`/`don`, `them.json` chỉ còn `PASS`.
Mười ca đó chọn tường minh theo cách dùng thật trong mã:

| Khoá | Chọn | Bỏ | Vì sao (đo trong mã) |
|---|---|---|---|
| `bao` | `report` | outlet | `bao_tien_do`, `_bao_chet_lap`, `da_bao` = báo cáo; "báo khác" đi qua cụm `bao_khac` |
| `dich` | `translate` | target | `kiem_quote_dich` = đã dịch |
| `doi` | `change` | team | `doi_chu_anh` = đổi; "đợi" đi qua cụm `doi_khoa` = wait_lock — ⚠️ mơ hồ |
| `duoi` | `below` | under/bottom | `roi_duoi` = rơi xuống dưới |
| `gia` | `fake` | price | đa số là stub test (`_gia`, `anh_hang_gia`); "giá" đi qua cụm `gia_vao/gia_ra/gia_usd/gia_moi_bai` |
| `kho` | `format` | size | `kho_the`, `kho_khoa` = khổ; "size" đã thuộc `kich_thuoc` |
| `luot` | `turn` | slot | `luot_tai`, `luot_dung`; "slot" đã thuộc cụm `cho_luot` |
| `noi` | `say` | place | `noi_ra` |
| `tren` | `on` | top | `kiem_so_tren_anh` = trên ảnh |
| `truy_van` | `query` | queries | thống nhất số ít với các hàm trả một truy vấn |

**Sửa PASS trùng tiếng Việt.** 21 token vừa nằm trong `PASS` (giữ nguyên) vừa là
tiếng Việt. Vì PASS được tra **trước** `don.json`, chúng bị coi là English.
Quyết định theo cách dùng thật:

| Token | Quyết | Vì sao |
|---|---|---|
| `in` | dịch → `print` | `in_log`, `in_bang`, `in_ket_qua` = in ra; English "in" chỉ có trong cụm `in_progress`/`in_use`/`in_executor` → thêm cụm giữ nguyên |
| `nhat` | dịch → `most` | `it_dung_nhat`, `moi_nhat`; "nhật" đã thuộc cụm `nhat_ky` |
| `gia` | dịch → `fake` | như trên |
| `ap` | dịch → `apply` | `de_ap` |
| `vi` | **giữ PASS** | `summary_vi` là **mã ngôn ngữ**, đổi là hỏng; "vì/vị" đi qua cụm `vi_sao`, `vi_tri`, `vi_du`, `don_vi` |
| `cap` | **giữ PASS** | `cap_fb`, `p_cap`, `max_cap_h` là English cap (trần); "cặp" qua cụm `cap_ghep`, "cập" qua `cap_nhat` |
| `gap` | **giữ PASS** | chỉ xuất hiện trong tên test |
| 14 token còn lại (`brand`, `draft`, `slug`, `task`, `text`, `title`, `url`…) | giữ PASS, xoá khỏi `don` | là English thật, `don` chỉ map identity |

**Map nốt 276 token thiếu.** ~200 là English/tên riêng/benchmark (`tbench`, `hle`,
`yandex`, `masthead`…) → PASS; ~70 là tiếng Việt → `don`/`cum`, đặt theo ngữ
cảnh thật (grep identifier trong mã): `chung`→common, `nhin`→seen (module
`chuan_bi.nhin` vẫn → `vision` qua bảng module), `lap`→repeat, `hoac`→or,
`bang_chung`→evidence, `to_chuc`→organization, `doc_lap`→independent, `ho_so`→profile…

**Đưa 60 tên soát tay vào `overrides.json`.** Lượt soát 5 module quan trọng nhất
tìm ra tên đúng hành vi hơn dịch máy (`dung_manifest`→`build_manifest` chứ không
phải `use_manifest`, `dan_xuat`→`compute_derived`, `khoa_tin`→`story_key`,
`_so_da_dung`→`_used_images_log`, `ghep_hai_hang`→`pair_two_vendor_images`).
Không bắt buộc theo tiêu chí, nhưng đã có sẵn và không tạo va chạm nên dùng.

## Cách duyệt / sửa

1. Đọc `TU_DIEN_TEN_v0.md`: mục **F** phải trống; mục **B** (103 module) và các
   dòng ⚠️ trong **C/D** (449 dòng chứa token mơ hồ — máy đã chọn mặc định theo
   `moho.json`, sai chỗ nào thì sửa bằng `overrides.json`).
2. Sửa `cum.json` / `don.json` / `moho.json` / `them.json` / `overrides.json`.
3. Chạy lại:
   ```bash
   cd docs/tu_dien_ten && python3 gen.py . [/đường/dẫn/checkout-đầy-đủ]
   ```
   Thoát mã 0 = không va chạm. Mã 1 = còn va chạm, xem mục F.

## Ghi chú: bản v0 quét từ checkout `feat/org-id-multitenant` (103 module)

`main` lúc dựng chỉ có 62/103 tệp `.py` — nhiều nhánh feature chưa gộp. Tham số
thứ hai của `gen.py` cho phép trỏ sang checkout đầy đủ. Sau khi `main` gộp đủ,
chạy `python3 gen.py .` không tham số là được.

## Luật khi rename thật (đã thống nhất)

- Rename 1-1 theo cấu trúc cụm — không gộp hai tên thành một, không tách một thành hai.
- **Khoá JSON/manifest trên đĩa KHÔNG đổi** (`xong.json`, 337+ sidecar, body task trong
  `kanban.db` đang đọc theo tên hiện tại — đổi là migrate dữ liệu, rủi ro cao, giá trị thấp).
- Tên vai (`ethan`, `dre`, `kite`, `miles`…) giữ — là slug profile hermes thật trên máy chủ.
- Chú thích/tài liệu/thông báo Telegram vẫn tiếng Việt có dấu — chỉ định danh trong mã đổi.
- Đổi tên bằng công cụ AST (định nghĩa + mọi nơi gọi trong một bước), chạy đủ bộ test
  sau mỗi module — không `sed` theo chuỗi.
- Chờ các nhánh feature đang chạy song song gộp xong — xem `CLAUDE.md`.
