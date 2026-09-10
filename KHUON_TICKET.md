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
- [ ] Điều kiện riêng của ticket này: …

## 4. Phân loại

- **Xong trong ticket này:** …
- **Để sau (thành ticket con ở bước 7):** …
- **Không làm, vì:** …

## 5. Kiểm tra

Tên test mới, lệnh chạy, kết quả nguyên văn (fail cũ / pass mới).

## 6. Chạy thử

Chạy thật một lượt, không gửi Telegram: `python <vai>_nop.py --khong-gui --out
/tmp/x` hoặc task kanban mẫu. Ghi lệnh và kết quả. Việc cần ghi lên server thì
agent chuẩn bị script, Ông Chủ chạy, kết quả dán lại đây.

## 7. Backlog

Danh sách ticket con đã tạo từ mục "để sau" (LOW-x — một dòng tên). Mục mới
trong `NHAT_KY_SU_CO.md` sinh ra từ ticket này phải ghi "ticket theo dõi: LOW-x".

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
| 4. Vận hành & theo dõi | Theo dõi tín hiệu gì khi lên production? | Không định nghĩa giám sát cho tới khi có sự cố | Mục 6 (Chạy thử) phải ghi **cái nhìn ở đâu sau khi deploy**: topic Telegram nào, cột nào trong nhật ký ngày, cron nào |
| 5. Phát hiện vấn đề | Gì báo hiệu trước khi khách phàn nàn? | Vấn đề chỉ lộ ra qua khiếu nại | Cổng chặn ở `*_nop.py`, `kanban_block`, nhật ký 9router. Ticket sửa lỗi phải trả lời: cổng nào lẽ ra phải chặn |
| 6. Phòng ngừa vấn đề | Guardrail nào ngăn được việc tái diễn? | Cùng loại lỗi lặp lại nhiều lần | Test mới fail-trên-code-cũ (mục 3, 5). Lỗi lặp lần hai thì mở ticket cho guardrail, không chỉ vá |
| 7. Sửa vấn đề (quay lại 1) | Cần cập nhật đặc tả/backlog không? | Sửa xong nhưng không cập nhật gốc gây lỗi | Mục 7 (Backlog) + README/LUAT_ANH sửa cùng commit; nhật ký sự cố ghi "ticket theo dõi" (LOW-19) |
