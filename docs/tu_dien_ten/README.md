# Từ điển tên — Việt không dấu → English (bản nháp, CHƯA đụng mã)

Bước 0 của việc chuyển quy ước đặt tên tệp/hàm/hằng số từ tiếng Việt không dấu
sang English (xem `feedback_dat_ten_english_cho_sau.md` trong memory của agent:
quy ước cũ không do Ông Chủ đặt — phiên đầu 20/08/2026 tự chọn — bị coi là nhập
nhằng, nhưng đổi ngay là refactor giữa lúc nhiều nhánh đang hoạt động).

**Trạng thái: nháp, chờ Ông Chủ duyệt. Chưa rename một tên nào trong mã.**

## Tệp trong thư mục này

| Tệp | Vai trò |
|---|---|
| `TU_DIEN_TEN_nhap.md` | Bảng đề xuất đầy đủ — đây là cái Ông Chủ đọc/duyệt |
| `cum.json` | Từ gốc dạng CỤM (Việt → English), khớp trước khi xét từ đơn |
| `don.json` | Từ gốc dạng TỪ ĐƠN |
| `moho.json` | Token mơ hồ (một chữ không dấu, nhiều nghĩa) kèm giải nghĩa — cần chọn tay |
| `them.json` | Bổ sung `don.json` + danh sách `PASS` (token đã là English, giữ nguyên) |
| `gen.py` | Sinh lại `TU_DIEN_TEN_nhap.md` từ 4 tệp JSON trên + repo hiện tại |

## Cách duyệt / sửa

1. Đọc `TU_DIEN_TEN_nhap.md`, mục **E** trước (token chưa map) và các dòng có
   cờ ⚠️ trong mục B/C/D (token mơ hồ — máy không tự chọn nghĩa được).
2. Sửa `cum.json` / `don.json` / `moho.json` / `them.json` cho đúng ý.
3. Chạy lại:
   ```bash
   cd docs/tu_dien_ten && python3 gen.py .
   ```
   Bảng B/C/D/E cập nhật theo, không cần dựng lại từ đầu.

## Ghi chú quan trọng: bản nháp hiện tại dựng từ **103 module** trên
`feat/org-id-multitenant`, không phải từ `main`

Lúc dựng bản nháp này, repo đang phân mảnh trên nhiều nhánh feature
(`feat/tim-anh-web`, `fix/anh-bao-thuc-the`, `sua/low35-thuc-the`…) chưa gộp về
`main` — `main` lúc đó chỉ có 62 tệp `.py`, thiếu 41 module đang nằm rải trên
các nhánh đó. `gen.py` giờ tự quét repo tại chỗ chạy nó (không phụ thuộc máy/
thư mục tạm nào), nên **chạy lại đúng lúc `main` đã gộp xong tất cả nhánh
feature** thì bảng mới đầy đủ và không bị hụt module như lần "main mới merge
PR #5" ở đây.

## Luật đặt ra khi rename thật (đã thống nhất, ghi lại để không quên)

- Rename 1-1 theo cấu trúc cụm — không gộp hai tên thành một, không tách một
  tên thành hai.
- **Khoá JSON/manifest trên đĩa KHÔNG đổi** (coi như wire format/API — 337+
  sidecar cũ, `xong.json`, `kanban.db` task body đều đang đọc theo tên hiện
  tại; đổi là phải migrate dữ liệu, rủi ro cao, giá trị thấp).
- Tên vai (`ethan`, `dre`, `kite`, `miles`…) giữ nguyên — đây là slug profile
  hermes thật trên máy chủ, không phải tên biến trong mã.
- Chú thích/tài liệu/thông báo Telegram vẫn tiếng Việt có dấu — chỉ tên định
  danh trong mã (module, hàm, biến, hằng số) đổi.
- Việc rename thật phải đợi các nhánh feature đang chạy song song gộp xong —
  xem `CLAUDE.md` mục "Remotes & thứ tự push".
