# Từ điển tên — Việt không dấu → English — **v0** (CHƯA đụng mã)

Bước 0 của việc chuyển quy ước đặt tên tệp/hàm/hằng số từ tiếng Việt không dấu
sang English (xem `feedback_dat_ten_english_cho_sau.md` trong memory của agent:
quy ước cũ không do Ông Chủ đặt — phiên đầu 20/08/2026 tự chọn — bị coi là nhập
nhằng, nhưng đổi ngay là refactor giữa lúc nhiều nhánh đang hoạt động).

**Trạng thái (13/09/2026): từ điển v0 đã duyệt (LOW-49). Refactor thật LOW-50 ĐÃ CHẠY
HẾT trên nhánh `rename/viet-to-english`: 5 lô + đổi gói `chuan_bi/ → prepare/`,
mọi module/hàm/hằng top-level đã mang tên English; tên tệp cũ là shim (gỡ sau 1 tuần).
pyflakes 0, `tests/run.sh` 84/84 sau mỗi lô.**

## Tiêu chí chốt (Ông Chủ 12/09/2026)

> *"ngữ nghĩa là gì không quan trọng, thích gán nó là gì cũng được, không bị
> lẫn lộn hàm là được"*

Tức bảng chỉ cần đảm bảo **không hai hàm/lớp top-level nào trong cùng module
trùng tên sau khi dịch** (Python ghi đè định nghĩa trùng tên trong cùng module —
đó mới là "lỗi gọi" thật). `gen.py` tự kiểm ở **mục F** và thoát mã 1 nếu còn
va chạm. Nghĩa đúng từng chữ **không** là điều kiện.

## Soát tên đóng nhiều vai (LOW-333) — `name_role_scan.py`

Cổng CI chỉ soi tên **top-level**; tham số và biến cục bộ nằm ngoài tầm (có chủ ý,
từ LOW-53). Script này soi đúng phần còn lại, theo câu hỏi khác: *đọc một tên, có
biết nó đang là hàm hay biến hay trường không?*

```
venv/bin/python docs/tu_dien_ten/name_role_scan.py            # nhóm lẫn hàm <-> biến
venv/bin/python docs/tu_dien_ten/name_role_scan.py --all      # mọi tên đóng >=2 vai
venv/bin/python docs/tu_dien_ten/name_role_scan.py --name so  # một tên, kèm danh sách tệp
```

Đo 20/09/2026: **27 tên vừa là hàm vừa là biến/trường — 381 chỗ, 91 tệp** mã sản
xuất. Nặng nhất: `browser_session.dong()` là **đóng**, còn `dong = [...]` ở 21 tệp
khác là **dòng**. Đừng đổi hàng loạt bằng máy — nhóm này bị từ điển đánh dấu nhập
nhằng, phải đọc từng chỗ (bài học `roi/rồi/rối/rời`).

## Thực thi (LOW-50) — `rename.py`

```bash
venv/bin/python docs/tu_dien_ten/rename.py . vai --dry-run     # xem kế hoạch một module
venv/bin/python docs/tu_dien_ten/rename.py . vai luat_anh      # đổi theo lô, test sau mỗi module
venv/bin/python docs/tu_dien_ten/rename.py . xep_hang --no-module   # chỉ hàm/hằng, giữ tên tệp
venv/bin/python docs/tu_dien_ten/rename.py . --package chuan_bi     # đổi thư mục gói — làm cuối
```

Mỗi module: rope đổi hàm/lớp top-level → hằng số → tên tệp (định nghĩa + mọi nơi
gọi, `docs=False` nên **không đụng chuỗi** → khoá JSON/đường dẫn state giữ nguyên)
→ vá chuỗi có quy tắc hẹp (`<cũ>.py` → `<mới>.py` trong .py/.md/.json/.sh trừ lịch
sử; trong `tests/` chỉ `def cũ(`, `cũ(`, `modcũ.cũ`, tên trần trong ngoặc kép **nếu
không phải khoá dict**; `__all__`) → shim `<cũ>.py` (`sys.modules[__name__] = <mới>`,
chạy được cả dạng script) → `pyflakes` + `tests/run.sh`. Đỏ là dừng.

Pilot `vai.py → role.py` (13/09/2026): 13 hàm/lớp + 14 hằng + module qua 36 tệp,
xanh sau 3 vòng vá công cụ — ba ca thật đã thành quy tắc: biến cục bộ trùng tên
module mới (`role = sorted(...)` trong test_vai) → **mục F2**; `"$VAI"` biến shell
bị đổi thành `"$ROLE"` → lookbehind `$`; test viết regex `vai\.so_anh_toi_thieu\(`
→ chấp nhận `\.`/`\(`.

Lô 1 (8 module lõi, 126 tệp) và lô 2 (26 module ảnh/nguồn, gồm 5 module con
`chuan_bi/`) — mỗi lô vài vòng vá công cụ trước khi xanh 84/84. Quy tắc mới đã
vào `rename.py`, mỗi cái là một ca đo được:

- **rope bỏ sót `import cũ` nằm trong hàm** (`import anh_chuan_bi as cb` ở 3 hàm
  test_cong_chan) — chạy được nhờ shim, nhưng `patch.object(cb, …)` không nhận
  ra module → `_va_import_cu`: đổi bằng token, chỉ trên dòng import hoặc `cũ.x`
  khi tệp có import ràng buộc tên trần đó (không đụng kwarg `vai="ethan"`, không
  đụng `with … as chung` — chú thích trên dòng import bị bỏ trước khi xét).
- **Module RE-EXPORT** (`image_prepare` re-export `_luu_crop` của
  `chuan_bi.tai_loc`, `vong_bu` re-export `tai_va_loc`): rope không đổi
  `cb._luu_crop` trong test → `_va_re_export` (token qua alias của module
  re-export) + `patch.object(vong_bu, "…")` nhận module re-export làm đối tượng.
- **Hằng MỘT TỪ không đổi trần trong chuỗi** — `CAO`/`NGUON`/`RONG` là chữ Việt
  thường gặp (`"BAO CAO BI CAT"`, `"NGUON KHONG LAY DUOC"`, JS `Y0+CAO`); lô 2
  đổi bừa làm test_bang_nova/test_render_edu đỏ. Hằng có `_` chỉ đổi trần trong
  test soi nguồn; còn lại phải có `mod.` phía trước.
- **f-string tách token ở Python 3.12** (`FSTRING_MIDDLE`) — `f"… tim_anh_them.py
  {id}"` trong dre_chuan_bi bị bỏ sót; chỉ đổi khi lát cắt trên dòng khớp đúng
  chuỗi token (vị trí sai khi có `{{`, cpython#104825).
- `__import__("loai_tin")` rope không nhìn thấy → đổi tay thành import tĩnh
  TRƯỚC khi chạy lô (28d2d24); `grep __import__(` trước mỗi lô.
- Chuỗi soi nguồn không ngoặc: `src.index("def _vong_thuc_the")`, `= _vong_thuc_the"`
  → mẫu `def cũ\b` và tên nhiều từ trần (có `_`) trong test soi nguồn/thân task.
- Bẫy git: rope tự `git mv` (đã stage) → `git commit` chỉ định tệp docs vẫn kéo
  theo 26 rename đang stage. Trước khi commit công cụ giữa lô: `git reset` hoặc
  `git commit -- <đường dẫn>` tường minh.

Lô 3 (28 module lớp vai), lô 4 (27 module duyệt/điều phối), lô 5 (10 module giữ
tên tệp) và bước `--package chuan_bi → prepare` — thêm các quy tắc, mỗi cái một ca đo:

- **rope 1.14 / Python 3.12 không đổi tên trong ô `{…}` của f-string**, và khi
  dòng có chữ Việt trước ô đó rope còn **ghi lệch offset** (`THOI_PHONG[:6]` →
  `TIME_ROOM[TIME_ROOM:6]`). `_va_fstring` (token) chạy TRƯỚC rope để rope không
  còn thấy tên cũ ở đó. Soát cả cây sau mỗi lô bằng `soi_trung_ten.py` (dòng `+`
  có tên mới nhiều hơn số tên cũ ở dòng `-`): 0 nghi ngờ ở lô 1–5.
- **Tên tệp trùng tên thư mục** (`nhat_ky.py` / `nhat_ky/`): rope phân giải
  `import nhat_ky as nk` sang thư mục → bỏ sót `nk.<tên>`; sau mỗi rope rename quét
  token `alias.tên_cũ` cho chính module (luới an toàn, không chỉ module re-export).
- **Chú thích kiểu dạng chuỗi** `-> "_HangFIFO"` rope không đổi (docs=False) và
  `-> "X":` từng bị đếm nhầm là khoá dict. Chỉ đổi sau `->`, `x: "…"`, trong
  `list[...]`/`Optional[...]`; **KHÔNG** đổi `a["dung"]` (subscript = khoá dict —
  lần đầu đổi nhầm ở 85 tệp).
- **Tên hàm trùng khoá dict** (`trang_thai`, `dung`): không thay trần trong chuỗi
  test dù có `_`. **Hằng một từ** (`SO`, `CAO`) không thay trần kể cả trong ngoặc kép.
- `getattr/setattr/hasattr(mod, "tên")` trong **mã chính** cũng phải đổi
  (env_load `getattr(card, "THUONG_HIEU")` → masthead in slug).
- Test chạy mã Python trong chuỗi (`subprocess -c "import bat_buoc; …"`) → mẫu
  `import cũ` / `from cũ import` trong chuỗi test.
- Module ngoài rope (`render_edu`, `scan_models`): đổi cả `alias.tên` khi
  `import scan_models as s`, không chỉ `scan_models.tên`.
- Chuỗi ghép tên module lúc chạy (`f"{persona}_nop.py"`, `"<vai>_chuan_bi.py"`)
  công cụ không thấy — grep tay sau lô (9 dòng ở lô 3). systemd `.service`/`.timer`
  và `%h/…/x.py` (có `/` trước tên) đã vào bộ vá.
- `--package`: `chuan_bi/x.py` trong tài liệu và `ROOT / "chuan_bi" / "x.py"` trong
  test đổi theo; `STATE_DIR / "chuan_bi"` và `"chuan_bi"` trần **không bao giờ đổi**
  (thư mục state trên đĩa). Shim `chuan_bi/__init__.py` → `prepare`.

## Cổng CI sau refactor (LOW-53) — `tests/test_name_english.py`

Chạy trong `tests/run.sh` (CI `ci` / job `check`): `bang_doi_ten()` trên cây hiện tại phải
**rỗng**. Còn tên top-level nào từ điển vẫn dịch ra tên khác thì đỏ và in
`module.tên → tên_đề_xuất`. Hai cách sửa, theo đúng thứ tự:

1. Tên đó là tiếng Việt → đổi sang tên đề xuất (hoặc tên English khác, miễn
   không trùng trong module).
2. Tên đó là English/tên riêng/benchmark bị nhận nhầm (vd `gap`, `cap`) → thêm
   token vào `them.json` mục `PASS`, chạy lại `python3 gen.py .` để chắc không
   sinh va chạm mới.

Test thứ hai trong tệp tự trồng `def tim_anh_moi()` vào thư mục tạm để chứng
minh cổng còn sống (từ điển nạp được, quét được). Phạm vi = phạm vi LOW-50:
tên top-level; tham số/biến cục bộ không xét.

`tudien.py` là thư viện chung của `gen.py` và `rename.py` — bảng in ra và cái sẽ
đổi luôn là một bộ. Tên module mới hết shadow được kiểm ở **F2** (tên biến/tham
số/def/alias trùng tên tệp mới trong tệp có import module đó).

## Tệp trong thư mục này

| Tệp | Vai trò |
|---|---|
| `TU_DIEN_TEN_v0.md` | Bảng đề xuất đầy đủ (A/A2 từ gốc → B module → C hàm/lớp → D hằng số → E chưa map → F va chạm) — **cái Ông Chủ đọc/duyệt** |
| `cum.json` | 392 CỤM Việt → English, khớp trước khi xét từ đơn |
| `don.json` | 369 TỪ ĐƠN Việt → English |
| `moho.json` | 40 token mơ hồ (một chữ không dấu, nhiều nghĩa) + giá trị mặc định đã chọn |
| `them.json` | Chỉ còn `PASS` — 954 token đã là English/tên riêng/benchmark, giữ nguyên |
| `overrides.json` | 65 ca đè tuyệt đối theo `"module.tên_gốc": "tên_mới"` — thắng mọi bảng trên |
| `tudien.py` | Thư viện chung: nạp JSON, `dich`/`dich_ten`/`dich_module`, `quet` repo, kiểm F (trùng tên) + F2 (shadow) |
| `gen.py` | Sinh lại `TU_DIEN_TEN_v0.md` từ `tudien.py`; exit 1 khi còn F/F2 |
| `rename.py` | Thực thi (LOW-50): rope + vá chuỗi + shim + pyflakes/tests theo lô |
| `SOAT_NGU_NGHIA_5_module.md` | Lượt soát tay 86 hàm theo hành vi thật (tham khảo; 60 tên đã đưa vào `overrides.json`) |

## Tài liệu `.md` ở gốc repo (LOW-142, 14/09/2026)

Từ điển và `rename.py` chỉ xét tên **mã** (module/hàm/hằng), nên LOW-50 đổi
`luat_anh.py` → `image_rules.py` mà sót tài liệu cùng tên. Đổi tay, ghi ở đây để
lần sau tra:

| Tên cũ | Tên mới | Ghi chú |
|---|---|---|
| `KIEN_TRUC.md` | `ARCHITECTURE.md` | |
| `LUAT_ANH.md` | `IMAGE_RULES.md` | khớp module `image_rules.py`; tham chiếu mục `LUAT_ANH §1.2d` → `IMAGE_RULES §1.2d`, giữ số mục |
| `KHUON_TICKET.md` | `TICKET_TEMPLATE.md` | LOW-148, 14/09/2026 |
| `NHAT_KY_SU_CO.md` | `INCIDENT_LOG.md` | LOW-149, 14/09/2026. Chỉ đổi TÊN TỆP + đường dẫn tham chiếu; không đổi tên trong `incident_journal/*.md` (thuần lịch sử) và không đụng câu đo commit cũ bên trong chính tệp nếu câu đó nhắc TÊN CŨ như một số đo lịch sử |

Không đổi NỘI DUNG trong `incident_journal/` (lịch sử) và trong chính thư mục này.
`skill_lesson_filter.SOURCE_OF_TRUTH` khớp **cả hai** tên vì bài học cũ vẫn ghi
`LUAT_ANH`.

## Script/cấu hình không phải `.md` (LOW-151/152, 14/09/2026)

Cùng lý do trên — không phải mã, `rename.py`/`test_name_english.py` không xét.

| Tên cũ | Tên mới | Ghi chú |
|---|---|---|
| `hermes/scripts/cap_nhat_hermes.sh` | `hermes/scripts/update_hermes.sh` | chỉ tự nhắc chính nó |
| `mau_bai_goc.json` | `original_post_template.json` | dữ liệu mẫu cho `cost_squeeze.py`, có tracked trong git |
| `hermes/scripts/quet_daily_scan.sh` | `hermes/scripts/daily_scan.sh` | 4 wrapper (`finn_daily_scan.sh`, `nova_daily_scan.sh`, `vera_daily_scan.sh`, `qinn_scan.sh`) gọi qua đường dẫn tương đối, **giữ nguyên tên wrapper** (README: để khỏi sửa job cron trên máy chủ); `sync_hermes.SCRIPT` phải sửa theo, deploy xong nhớ `--ra-hermes` |
| `hermes/profiles/cau_hinh_that.yaml` | `hermes/profiles/live_config_snapshot.yaml` | tệp do máy sinh (`sync_hermes.py --chup-cau-hinh`, tên cờ chưa đổi — ngoài phạm vi) |
| `tests/chay.sh` | `tests/run.sh` | LOW-152. **Rủi ro cao nhất trong đợt**: CI thật (`.github/workflows/ci.yml`) và chính `rename.py:693` gọi thẳng tên này — sửa CI TRƯỚC KHI push, không sau |
| `cai_dat.sh` | `setup.sh` | LOW-153. `cai_dat` → `setup` đã có sẵn trong `cum.json`. Một SKILL (`url-mascot-frame`) nhắc tên này — vai đọc lúc chạy |
| `hermes/scripts/nhat_ky_daily.sh` | `hermes/scripts/journal_daily.sh` | LOW-151, đợt 2. Tên nằm trong trường `"script"` của job cron `daily-log` (id `1d476e2f3a8f`, cùng id ở cả hai home) — **deploy phải kèm** `hermes cron edit <id> --script journal_daily.sh` cho CẢ HAI home, và chép tệp mới sang home trước (sync không tự tạo tệp mới) |
| `hermes/systemd/nhat-ky-web.service` | `hermes/systemd/journal-web.service` | LOW-151, đợt 2. Unit đang chạy thật — deploy phải kèm: cp unit mới → `daemon-reload` → `disable --now nhat-ky-web` → `enable --now journal-web` → kiểm cổng 9130 → xoá unit cũ |

Thư mục `nhat_ky/` ở gốc repo → **`incident_journal/`** (LOW-367, Ông Chủ 22/09/2026 đảo quyết định "không đổi" của đợt này), kèm tên 18 tệp bên trong → English; `tham_chieu.md` → `reference.md`. Không lấy `journal/` theo `cum.json` vì trùng tên `journal.py` (bẫy ở mục rope phía trên). Nội dung tệp giữ nguyên. Cổng: `tests/test_docs.py::test_incident_journal_names_english`.
Đường dẫn `state/9router/nhat_ky` đã thành `state/9router/journal` ở LOW-231.

Biến môi trường `NHAT_KY_URL`/`NHAT_KY_HOST`/`NHAT_KY_PORT` (`monitor_9router.py`,
`journal_web.py`, unit `journal-web.service`) đổi thành
`JOURNAL_WEB_URL`/`JOURNAL_WEB_HOST`/`JOURNAL_WEB_PORT` ở LOW-239 (bảng
`journal_keys_v2.json`, mục `env`). Tên cũ **không còn được đọc** — máy nào đặt tay
biến cũ ngoài unit trong repo (shell, `.env`, unit đã sửa tại chỗ) phải đổi theo khi
deploy; unit mới phải chép lại + `daemon-reload` + restart `journal-web`.

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
