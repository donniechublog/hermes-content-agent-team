# Khuôn ticket — vòng lặp cấp tác vụ 7 bước

Mọi ticket LOW-* (Bug, Feature, Improvement) viết theo khuôn này, bằng tiếng
Việt. Nhịp mục tiêu 5→30 phút một vòng; việc lớn hơn 30 phút thì tách ticket
con **trước** khi làm, không làm dở rồi tách.

Linear của team LowProfile chưa có template (kiểm tra 10/09/2026), nên khuôn
nằm ở đây và trong memory của agent. Khi nào Linear có template thì dán nguyên
phần dưới vào, tệp này vẫn là nguồn sự thật.

Bước cuối (Backlog) nuôi lại bước đầu (Đặc tả) của vòng kế tiếp: đóng ticket
mà không có ticket "để sau" nào thì phải nói rõ là không còn gì.

---

## 1. Đặc tả

Một đoạn: ai báo, báo gì, nguyên văn nếu có (link Telegram `t.me/c/...` đính
làm chứng cứ, agent không mở được). Với Feature/Improvement: muốn hệ thống làm
gì khác đi so với hôm nay.

## 2. Bối cảnh

Những gì đã đọc và đã đo **trước khi sửa**, để kết luận tái hiện được bằng lệnh:

- Tệp đã đọc: `tệp:dòng` của chỗ nghi là nguyên nhân.
- Lệnh đã chạy và số đo (bảng). Không đoán từ đọc code.
- Vì sao test hiện có không bắt được.

## 3. Định nghĩa hoàn thành

Checklist, tick được:

- [ ] Test mới `tests/test_<tên>.py` **fail trên code cũ**, pass trên code mới.
- [ ] `bash tests/chay.sh` xanh, `pyflakes` sạch trên tệp đã sửa.
- [ ] Bảng trước/sau bằng số đo cùng lệnh ở bước 2.
- [ ] **Chạy thử trên MÁY CHỦ** (mục 6) — số đo từ máy dev không tính,
      trừ khi bản vá thuộc nhóm được miễn và đã ghi rõ lý do.
- [ ] Điều kiện riêng của ticket này: …

## 4. Phân loại

- **Xong trong ticket này:** …
- **Để sau (thành ticket con ở bước 7):** …
- **Không làm, vì:** …

## 5. Kiểm tra

Tên test mới, lệnh chạy, kết quả nguyên văn (fail cũ / pass mới).

## 6. Chạy thử — **TRÊN MÁY CHỦ**, không phải máy dev

> **Luật cứng (Ông Chủ chốt 12/09/2026).** Máy dev xanh **không phải** là chạy
> thử. Chỉ số đo lấy từ máy chủ mới được tick mục này.

Chạy thật một lượt, không gửi Telegram: `python <vai>_submit.py --khong-gui --out
/tmp/x` hoặc task kanban mẫu. Ghi **lệnh và kết quả nguyên văn**.

```bash
ssh donniechu@donniechu-01.netbird.mated 'cd ~/content-team && <lệnh>'
```

**Vì sao là luật, không phải lời khuyên.** Bản vá `0b395ad` (nấc chụp trang
nguồn) xanh **58/58** trên máy dev và chụp được cả theverge lẫn techcrunch.
Deploy xong, cùng URL theverge hỏng **3/3** trên máy chủ: `page.goto` với
`wait_until="networkidle"` không bao giờ đạt trên trang có quảng cáo +
websocket, ném `TimeoutError` sau trọn 45s, tới lúc đó `h1`/ảnh hero chưa
hydrate. Lỗi này **không thể lộ ở máy dev** (mạng nhanh hơn, egress khác) —
và nó đã đi thẳng ra production vì mục 6 lúc đó chỉ ghi "dự kiến".

**Bắt buộc chạy trên máy chủ** khi bản vá chạm bất kỳ thứ nào sau đây:

| Chạm gì | Vì sao dev không đủ |
|---|---|
| Mạng (HTTP, API, Commons, RSS) | egress khác, độ trễ khác, site trả nội dung khác cho IP datacenter |
| Browser / Playwright / Chromium | phiên bản, font, `networkidle`, tốc độ hydrate |
| Đường dẫn, `state/`, khoá tệp, quyền | layout thư mục và user khác hẳn |
| Service, cron, systemd | dev không chạy chúng |
| Model / router / key theo brand | profile và hạn mức nằm ở máy chủ |

**Được miễn:** hàm thuần không I/O, sửa tài liệu, đổi chuỗi hiển thị. Ghi rõ
"miễn vì <lý do>" thay vì để trống.

**Chưa chạy được trên máy chủ thì KHÔNG tick** — viết thẳng "CHƯA chạy thử
trên máy chủ" vào mục 6 và để ticket ở trạng thái chưa xong. Không có mục
"dự kiến": một dòng "dự kiến chạy `X`" là mục 6 **trống**, không phải mục 6
đã làm.

Còn phải ghi **nhìn ở đâu sau khi deploy**: topic Telegram nào, cột nào trong
nhật ký ngày, dòng log nào, cron nào.

## 7. Backlog

Danh sách ticket con đã tạo từ mục "để sau" (LOW-x — một dòng tên). Ticket này
sinh ra một **tệp mới** `nhat_ky/YYYY-MM-DD-ten-ngan.md` (không sửa tệp nhật ký
của ticket khác — xem `INCIDENT_LOG.md`), trong đó phải ghi "ticket theo dõi: LOW-x".

---

## Luật comment trong ticket

1. Comment **chẩn đoán** (bước 2) đi trước bản vá.
2. Comment **kết quả vá** (bước 3, 5, 6) sau khi sửa.
3. Comment **đóng ticket** (bước 4, 7): phân loại và ticket con.

---

# Vòng ngoài — từ tín hiệu tới ticket, và từ sự cố quay lại ticket

Vòng 1 ở trên là cấp tác vụ. Vòng này bao ngoài nó: một tín hiệu (Ông Chủ báo
trên Telegram, số đo trong nhật ký, khách phàn nàn) đi qua 7 bước, bước 3 đẻ
ra ticket theo khuôn Vòng 1, bước 7 quay lại bước 1. Mỗi bước có **một câu hỏi
phải trả lời** và **một lỗi hay mắc**; khi mở hoặc đóng ticket, soát lại cột
"Lỗi thường gặp" trước.

| Bước | Câu hỏi | Lỗi thường gặp | Ở content-team |
|---|---|---|---|
| 1. Phân loại tín hiệu | Phản hồi khách hàng hay chiến lược? | Mọi thứ đều bị coi là khẩn cấp như nhau | Tin Telegram của Ông Chủ = phản hồi; slide/định hướng = chiến lược. Gắn priority trong Linear thay vì mặc định 0 |
| 2. Chuyển thành roadmap | Cần khám phá thêm hay đủ rõ để làm? | Bỏ qua xác thực, xây sai thứ | Chưa rõ thì ticket dừng ở mục 2 (Bối cảnh) với lệnh đo, không viết mục 3. Xem nhật ký 10/09 Dre: sửa đúng chỗ nhưng nối sai |
| 3. Thực thi | Đủ nhỏ để giao Vòng 1 chưa? | Việc quá to, bị kẹt thay vì chia nhỏ | Quá 30 phút thì tách ticket con **trước** khi làm (LOW-16 → LOW-17/18/19) |
| 4. Vận hành & theo dõi | Theo dõi tín hiệu gì khi lên production? | Không định nghĩa giám sát cho tới khi có sự cố | Mục 6 (Chạy thử) chạy **trên máy chủ** (luật cứng 12/09/2026) và phải ghi **cái nhìn ở đâu sau khi deploy**: topic Telegram nào, cột nào trong nhật ký ngày, cron nào |
| 5. Phát hiện vấn đề | Gì báo hiệu trước khi khách phàn nàn? | Vấn đề chỉ lộ ra qua khiếu nại | Cổng chặn ở `*_submit.py`, `kanban_block`, nhật ký 9router. Ticket sửa lỗi phải trả lời: cổng nào lẽ ra phải chặn |
| 6. Phòng ngừa vấn đề | Guardrail nào ngăn được việc tái diễn? | Cùng loại lỗi lặp lại nhiều lần | Test mới fail-trên-code-cũ (mục 3, 5). Lỗi lặp lần hai thì mở ticket cho guardrail, không chỉ vá |
| 7. Sửa vấn đề (quay lại 1) | Cần cập nhật đặc tả/backlog không? | Sửa xong nhưng không cập nhật gốc gây lỗi | Mục 7 (Backlog) + README/IMAGE_RULES sửa cùng commit; nhật ký sự cố ghi "ticket theo dõi" (LOW-19) |
