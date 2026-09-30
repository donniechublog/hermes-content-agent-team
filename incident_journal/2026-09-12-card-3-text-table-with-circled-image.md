## Thẻ "#3 bảng văn bản" đi kèm ảnh khoanh #26, và 50 phút Ethan "không phản hồi" (12/09/2026)

Ticket theo dõi: LOW-22, LOW-23, LOW-26 (con: LOW-24, LOW-25, LOW-27, LOW-28).

Ông Chủ gửi thẻ Ethan (task `t_d3ae2109`): hook *"claude-opus-4-7-high leo lên #3
bảng văn bản Arena, chốt 1501.8 điểm Elo"*, ảnh nền khoanh vàng hàng **#26**, 1555.
Hỏi: *"lý do gì tiêu đề là #3 mà hình minh hoạ lại chụp #26"*. Rồi ảnh Telegram:
*"⚠️ Ethan không phản hồi hơn 20 phút"* trên task trước đó (`t_24b214a6`).

**Thẻ arena (LOW-22).** Cả hai số đều đúng — của hai bảng khác nhau. Đo từ payload
arena.ai cùng ngày: bảng text #3 / 1501.79 (`round(,1)` = 1501.8 của
`scan_models._arena_board`), bảng code #26 / 1555.2 / spread 23–29 — khớp ảnh
từng con số. Chạy lại `tim_va_chup_nhieu` với đúng đầu vào tái hiện **y hệt tấm
ảnh**: `arena-code: khớp … hàng #26`. Nguyên nhân: `CHU_DE` có mục code mà không
có mục text, một chữ "code" trong 1500 ký tự đầu bài gốc đủ đẩy arena-code
(999+500+200) lên trên arena-text (1000+500); `_bo_qua_nguon` rồi bỏ luôn bảng
text. Cảnh báo "ĐÂY LÀ BẢNG KHÁC" trong `cau_xep_hang` không nổ vì `duoc_nhac`
so theo **tên miền** — bảy bảng arena chung một miền, có link arena.ai là cả bảy
đều "được nhắc". Không cổng nào so `#3` trong hook với `xep_hang["hang"]=26`;
brief có in "#26 / WebDev / Code Arena" nhưng chỉ là chữ, và `can_anh_xep_hang`
thì *ép* dùng ảnh đó. Sửa: mục `CHU_DE` cho text; `bang_re` theo từng bảng arena,
`duoc_nhac` đòi khớp bảng trong tiêu đề/link/via (không đọc thân bài). Đo lại:
`arena-text: khớp … hàng #3`. Cổng cứng so hạng hook↔ảnh để LOW-24.

**"Không phản hồi" (LOW-23).** Đọc kanban.db trên máy chủ (`ssh
donniechu-01.netbird.mated`, python `mode=ro` — sqlite3 CLI của macOS không mở
được URI, `-readonly` hỏng vì WAL): hai run 25.1 phút đều `timed_out` (1502s >
1500s), rồi `gave_up` → blocked; `task_events` có **heartbeat mỗi ~60s suốt cả
hai run**. Câu cảnh báo tính từ `tasks.started_at` — mốc lần ĐẦU, hermes không
bao giờ reset (`COALESCE(started_at, ?)`, chính bộ quét timeout của hermes ghi
"runtime is per attempt, not lifetime-of-task"); `_COT_VIEC` không SELECT
`last_heartbeat_at`/`worker_pid`. Hai lần bị giết im lặng vì vòng tiến độ bỏ qua
`ready`. Sửa: đo theo run đang mở (`moc_lan_chay`), đọc nhịp thở/pid (`nhip_tho`,
`pid_song`), ba câu khác nhau cho chết / im lặng / đang làm, và một dòng ⏱ mỗi
run `timed_out`. Test cũ không bắt được vì cả bốn test đặt `bat_dau_luc` như mốc
của lần chạy hiện tại — mã hoá đúng cái hiểu sai.

**Nguyên nhân thật của 50 phút (LOW-26).** Log run: `ethan_chuan_bi.py` được gọi
~16 lần, 3 lần `exit 139` (SIGSEGV), 1 lần `exit 124` vì đợi khoá `dang_chay.pid`
tròn 300s = trần bash tool của vai. Ethan tự `ps -p` thấy pid chết, tự `rm -f`,
tự viết `faulthandler` — vai chẩn đoán đúng, chỉ không có quyền dừng. Đẩy vào:
router vision 503 cả 8 ảnh (2/119 draft). Sửa: tách `_doi_khoa` (khoá mồ côi
dọn ngay + nói ra; `CHO_KHOA_GIAY=60`), `faulthandler.enable()` ở engine. Truy
chỗ segfault để LOW-27; cổng "engine chết N lần thì vai dừng" để LOW-28. Thẻ
arena `t_d3ae2109` chờ 50 phút sau task chết rồi xong trong 52 giây.

Bài học: (1) một câu cảnh báo phải nói đúng cái nó đo — "không phản hồi" trong
khi DB có nhịp thở mỗi phút là nói sai, không phải đo thô; (2) giả thuyết đọc từ
code (`_cho_luot`) bị số liệu máy chủ bác — ghi vào ticket cả cái bị bác; (3) hai
hẹn giờ bằng nhau (300s/300s) thì cái ngoài luôn thắng, đường xử lý phía sau
không bao giờ được chạm tới.

**Bổ sung cùng ngày (LOW-24/25/27/28).** Truy segfault bằng `faulthandler` trên máy
chủ: chết tại `luat_anh.dem_mat → det.detect()`; chạy từng ảnh trong tiến trình
riêng thì 7/8 ok, **A2.png 9440×5310 chết `-11` kể cả một mình** — YuNet không
chịu ảnh 50 MP, vision 503 chỉ trùng thời điểm. Vá: thu về `MAT_CANH_MAX=1600`
trước khi dò; chạy lại đúng draft: `exit 139` → `exit 0` + `xong.json`. Kèm:
cổng `kiem_hang_tren_the` (hạng trên thẻ = hạng trong ảnh, Ethan + Dre),
`max_runtime` 40m cho vai ảnh (đo p95 dre/kite ≈ 23 phút), `_cho_luot` có trần
240s + báo 30s, và engine tự dừng + báo Telegram khi chết bất thường 2 lần liên
tiếp (`so_lan_chet.json`). Deploy: push `origin` (= máy chủ, `updateInstead`),
restart `hermes-approve@blog/@dcgr`.

---

