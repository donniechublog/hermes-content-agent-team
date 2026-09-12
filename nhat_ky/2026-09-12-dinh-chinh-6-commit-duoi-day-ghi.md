## Đính chính: 6 commit dưới đây ghi SAI mã Linear (12/09/2026)

Sáu commit `ed63bd0..e6e6564` (và cả `5c13476`, `f3b7751`, `8d19b15`, `f749102`
trước đó) ghi "LOW-24/25/27/28/33/34/35" trong message — **những mã đó KHÔNG
phải mã Linear của việc đã làm**. Tôi (phiên Claude làm việc offline hôm đó)
lấy số bằng cách grep mã LOW cao nhất từng nhắc trong repo (ra LOW-21) rồi tự
đếm tiếp, chưa từng hỏi thật Linear — trong khi một phiên khác đang mở ticket
thật trên cùng dải số, cùng ngày, khiến trùng. Một phiên Claude khác
(`hermes-content-team-58`) phát hiện và báo qua tin nhắn liên-phiên.

Đối chiếu Linear thật (team `LowProfile`), lúc phát hiện:

| Commit (nhánh `feat/org-id-multitenant`) | Việc THẬT ĐÃ LÀM (khớp nội dung diff) | Mã LOW ghi trong message | Ticket thật mang mã đó |
|---|---|---|---|
| `5c13476` | Cổng so hạng trên thẻ với hạng trong ảnh XH (Ethan/Dre) | LOW-24 | Backlog — "Vai tự ghi bài học vào SKILL.md" |
| `f3b7751` | `max_runtime` theo vai + trần chờ engine song song | LOW-25 | In Review, đã deploy `81b0824` — "Vera gửi ba báo cáo" |
| `8d19b15` | Thu nhỏ ảnh trước khi dò mặt — hết SIGSEGV YuNet | LOW-27 | Backlog — "Chat thường trong topic quét không ai trả lời" |
| `f749102` | Engine chết bất thường 2 lần liên tiếp thì tự dừng + báo | LOW-28 | In Review, đã deploy `81b0824` — "Lệnh chọn số báo đang gửi" |
| `ed63bd0` | "Báo khác" phải cùng tin trước khi làm ảnh chính bài | LOW-33 | Backlog — "Cổng chặn ảnh quá cao cho Kite" |
| `e6e6564` | Hỏi trang công bố chính chủ; Commons khớp cụm liền nhau | LOW-34, LOW-35 | **Cả hai còn Backlog, chờ Ông Chủ chốt A/B** — tiêu chí "ảnh đẹp" và đường lùi bìa Kite khi 0 ảnh đạt |

**Quan trọng nhất:** LOW-34 và LOW-35 thật là hai câu hỏi thiết kế **CHƯA AI
QUYẾT** (tiêu chí "đẹp" cho ảnh khái niệm; có mở lại hero vector khi 0 ảnh đạt
không) — không liên quan gì tới trang công bố/Commons tôi sửa trong `e6e6564`.
Đọc commit đó **không được hiểu là** hai quyết định kia đã chốt.

**Không rewrite lịch sử git**: nhánh đang có phiên khác hoạt động sống, commit
của họ (`955f33b`, `0b395ad`, `113ef0f`, `8b532b2`, `124fb03`, `baff9d7`,
`f420a5c`, `39c0366`...) xen kẽ với commit của tôi và đã đẩy lên cả máy chủ
production lẫn GitHub — force-push để sửa message sẽ đụng lịch sử của họ. Giữ
nguyên 6 commit, chỉ đính chính bằng mục này. Nội dung/mã sửa của cả sáu commit
đều đã đo thật và deploy — chỉ CÁI NHÃN sai, không phải việc làm sai.

Bài học: `ToolSearch` nạp Linear MCP có sẵn từ đầu phiên, không dùng vì tưởng
grep repo là đủ. "Chốt số thật khi mở Linear" phải làm ngay lúc viết ticket,
không phải một câu hẹn để sau.
