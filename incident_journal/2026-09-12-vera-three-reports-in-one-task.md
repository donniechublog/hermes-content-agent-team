## Vera gửi ba báo cáo trong một task, reply vào bản thứ hai thì im lặng (12/09/2026)

Ticket theo dõi: LOW-25. Ông Chủ báo: *"Vera ticket. gửi 2
lần báo cáo, reply chuyển task cho Dre cũng ko phản hồi"*. Thực tế là **ba** lần
gửi, và lần im lặng là hệ quả trực tiếp của chúng.

Một task `t_901479ea` ("Quet tin kinh doanh 2026-09-12"), phiên
`20260911_220030_fade87`, Vera chạy `quet_nop.py --vai vera` ba lần — mỗi lần
là một báo cáo mới vào topic:

| Lần | Vera viết sai gì | stderr | Vẫn gửi? |
|---|---|---|---|
| 1 | `k` ghi `"#15"` thay vì `"15"` | 20 dòng `[bo qua] ... ngoai danh sach 1..80` | có — bản 4 mục |
| 2 | title ASCII, không dấu | 19 dòng `[canh bao] ... title tieng Viet mat dau` | có — bản 27 mục (msg 2004) |
| 3 | sạch | — | có — bản 27 mục (msg 2005) |

Cả ba lần `rc=0`. `--luu-mid` ghi mid của bản **cuối**, nên
`state/dcgr/bao_cao_mid.vera.json` = 2005. Ông Chủ đọc bản 2004 (bản không dấu,
đứng trước trong topic) và reply vào đó:

```
09-12 00:24:30 [vao] msg=2007 thread=83 vai=vera text=1, 7 - Dre
09-12 00:24:30 [route] msg=2007 ung-vien-chon vai=vera reply_that=2004 la_reply_bao_cao=False
09-12 00:24:30 [route] msg=2007 giong lenh chon nhung khong phai reply bao cao vai=vera -> coi la hoi thoai
09-12 00:24:30 [route] msg=2007 chat -> nhuong gateway (CT_CHAT_QUA_GATEWAY=1)
```

Rồi **không gì cả**: `~/.hermes-dcgr/logs/agent.log` không có một dòng nào lúc
00:24. Gateway dcgr đặt `require_mention: true` và đã bỏ `free_response_topics`
(08/09/2026), nên tin không nhắc tên bot thì không ai trả lời. Hai lớp cộng lại
ra đúng thứ tệ nhất: **im lặng** — nhìn y hệt lúc bot chết.

Lỗi phụ cùng chuỗi: `manifest_ghi.py` lấy ngày bằng `datetime.now(timezone.utc)`
trong khi cả đội sống theo giờ VN. Cron chạy 05:01 VN = 22:01 UTC hôm trước, nên
báo cáo đề "Vera — 2026-09-11" cho bản quét ngày 12, tên tệp đụng tên hôm trước
và rơi xuống nhánh `duong_ra_moi` → `vera_candidates_2026-09-11_t2201.json`. Mà
`duong_ra_moi` chỉ tới PHÚT: ba lần chạy trong cùng phút ra cùng một tên, bản
sau đè bản trước — đúng cái mà docstring của chính nó hứa là không làm.

Bốn chỗ sửa, theo đúng thứ tự chuỗi hỏng:

1. `quet_nop.loi_chan_gui` — `[bo qua]` (mất tin) và title mất dấu **chặn gửi**,
   rc=1, vai sửa rồi chạy lại. Một lần quét, một báo cáo. `[tu them]` và
   summary dài vẫn gửi: script đã tự xử lý xong, chặn là kẹt task.
2. `publish.py --luu-mid` ghi `message_ids` của **mọi mảnh** — báo cáo dài bị
   Telegram cắt đôi thì mục số 1 nằm ở mảnh đầu, và Ông Chủ reply vào đó.
3. `_la_reply_bao_cao` nhận bất kỳ mid nào trong cùng một lần gửi. Reply vào
   báo cáo CŨ vẫn bị từ chối như cũ (số thứ tự của bản cũ khác).
4. `_bao_khong_phai_reply` — cổng từ chối thì **nói**, không im. Và
   `manifest_da_gui` ghim đường dẫn manifest vào tệp mid ngay sau khi gửi: từ
   khi cổng 1 chặn gửi mà vẫn ghi manifest, "bản mới nhất theo mtime" không còn
   bằng "bản Ông Chủ đang nhìn" nữa.

Chạy thử lại bằng chính `ds.json` thật của hôm đó (`--thu`, không gửi Telegram):
bản `k` sai → rc=1 không gửi; bản mất dấu → rc=1 không gửi; bản sạch → gửi, và
tiêu đề báo cáo ra đúng `Vera — 2026-09-12`.

**Bổ sung cùng ngày (LOW-28) — cổng NHẬN cũng phải nói.** Ông Chủ: *"phải có
phản hồi 'đang gửi cho Dre' ngay sau khi nhận được reply"*. Đo trên
`approve.log` 11/09: lệnh vào 04:22:43, `[chon] xong sau 157s` lúc 04:25:20 —
**157 giây** topic không có gì. Có `_bao_nhan_viec`, nhưng nó bắn vào topic CỦA
VAI NHẬN (Dre), không phải topic quét Ông Chủ đang nhìn; nên ở bên này im lặng
y hệt lúc lệnh bị nuốt. Nay `_bao_da_nhan` gửi ngay vào đúng topic đó, TRƯỚC
khoá và trước `create_pair` (mỗi tin tới 180 giây), kèm tiêu đề từng số để đọc
một dòng là biết số vừa gõ có trỏ đúng tin định giao không.

**Mở rộng cùng ngày — luật chung cho MỌI vai, không riêng chọn số.** Ông Chủ:
*"thật ra tất cả các role đều cần trả lời reply 'đã gửi [task] cho [name]' và
'đã nhận [task] từ [name]', còn khi nào bắt tay vào làm thì sẽ thông báo 'đã
bắt đầu ...'"* — tức ba mốc riêng biệt cho MỌI lần giao việc, không chỉ đường
chọn số vừa vá. Soát lại bốn điểm `kanban_create` thật trong repo (chọn số,
làm lại, chuyển Kite, duyệt ảnh→viết) thì ba mốc đó **đã có sẵn** ở gần hết:

- **"đã bắt đầu"** đã có từ trước, dùng CHUNG cho mọi task bất kể tạo kiểu gì:
  `bao_tien_do_kanban` gửi dòng `▶️ <vai> bắt đầu: <tiêu đề>` vào đúng topic của
  vai đó ngay khi dispatcher chuyển trạng thái sang `running` — không cần sửa.
- **"đã gửi"** + **"đã nhận"** đã đủ ở ba trong bốn điểm: chọn số (mới vá,
  `_bao_da_nhan` + `_bao_nhan_viec`), làm lại (gửi ngay trong chính topic người
  nhận vì không đổi topic nên một dòng là đủ), chuyển Kite (`"🎨 Đã giao
  Kite..."` + `_bao_nhan_viec` sang topic Kite).
- **Lỗ còn lại: duyệt ảnh → tạo task viết cho Miles/Jika** (`duyet_bai._nut_duyet`,
  nút `imgok`). Đây là đường **chạy nhiều nhất** trong cả bốn — mọi tấm ảnh
  được duyệt đều qua đây, không như chọn số chỉ vài lần một ngày. Trước sửa:
  `note = f"✅ Đã duyệt ảnh — {ten} bắt đầu viết caption (task {wid})"` — gộp
  "gửi" với "bắt đầu" làm một (task còn chưa chạy đã nói "bắt đầu"), và
  KHÔNG gọi `_bao_nhan_viec` — topic của Miles/Jika im lặng cho tới khi
  dispatcher chạy thật (50–60s + hàng đợi), y hệt lỗ hổng LOW-28 nhưng ở một
  đường tần suất cao hơn nhiều.

Sửa: `_nut_duyet` nhận thêm `chat_id` (trước đó không có đường truyền vào để
gọi `_bao_nhan_viec`), đổi câu trả lời ngay thành `"✅ Đã duyệt ảnh — đã gửi
cho {ten} viết caption (task {wid})"` (bỏ chữ "bắt đầu"), và đọc `vai_anh` từ
sidecar `.img.json` để gọi `_bao_nhan_viec(token, chat_id, vai_viet, vai_anh,
title, wid)` — nói rõ "chuyển từ Dre/Ethan" trong topic của người viết, đúng
cơ chế `_bao_nhan_viec` đã có sẵn cho đường chuyển Kite.

**Bài học:** một cổng chỉ *in cảnh báo* rồi vẫn cho đi tiếp thì không phải cổng —
nó chỉ dời việc hỏng xuống chỗ khác. Ở đây nó dời sang topic của Ông Chủ, dưới
dạng ba bản gần giống nhau mà chỉ một bản bấm được. Và cổng nào từ chối cũng
phải trả lời: trên dcgr, "rơi về hội thoại" nghĩa là rơi vào im lặng.

---

