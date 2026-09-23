# Chụp bảng của chính trang nguồn trước khi in thẻ chữ — 23/09/2026

Ticket theo dõi: LOW-385 (cha: LOW-381).

Câu hỏi gốc của Ông Chủ sáng 23/09: *"sao chúng ta ko chụp luôn trang này mà lại dùng text
nhỉ?"*. LOW-381 chữa được ca cụ thể (khớp tên model), nhưng giữa "không khoanh được hàng
nào" và `ranking.fallback_card` vẫn không có nấc nào — trong khi `capture_chart.py` nằm sẵn
trong repo.

Đo trên máy chủ trước khi sửa: **23 bài** đã rơi về thẻ chữ, trong đó **4 bài** có `link gốc`
là chính một trang bảng — artificialanalysis ×3 (`/leaderboards/models`, `/text-to-speech`,
`/speech-to-text`), arena.ai ×1 (`/leaderboard/code/webdev`). **Ba trong bốn bảng đó không có
mục riêng trong registry `SOURCE`**, nên vòng đi nguồn không bao giờ chạm tới chúng dù bài lấy
tin từ đúng trang ấy.

Làm: `ranking.source_page_is_board` (hàm thuần, chỉ mở nấc này khi tên miền đã nằm trong
registry — không chụp đại chart của bài bất kỳ, LOW-179) + `ranking.capture_source_board`
dùng phiên browser đang mở.

## Năm lần dựng hình thật mới ra được tấm dùng được

Mục 6 của CLAUDE.md nói "test chỉ chứng minh điều mình đã nghĩ tới, còn hình thật mới lộ điều
mình chưa nghĩ tới". Lần này đúng năm lần:

1. **2796×29920** (tỉ lệ 1:10,7). Chụp trọn phần tử thì được cả bảng 300 hàng. Bề ngang là nội
   dung nên không được chạm; chiều cao thì cắt được.
2. **`max-height` đặt lên `<table>` bị bỏ qua** — CSS không áp `max-height` cho `display:table`.
   Đặt xong đo lại vẫn đúng 29920px.
3. **`element.screenshot()` hỏng hai kiểu khác nhau**: nó ĐỢI phần tử đứng yên nên hết giờ trên
   trang có hiệu ứng chạy số (`/text-to-speech`), và ném *"Element is not attached to the DOM"*
   khi trang React vẽ lại giữa chừng (arena.ai). `page.screenshot(clip=…)` chỉ là bốn con số —
   không đợi gì, không đụng vào DOM.
4. **Chụp phải KHUNG XƯƠNG lúc đang tải**: arena.ai ra một tấm toàn ô xám, không một con số
   nào — mà cổng "ảnh rỗng" không bắt được vì nó có hình khối. Đúng loại lỗi bò Broadcom
   04/09. Thêm cổng đếm hàng CÓ CHỮ (≥5, cùng ngưỡng với `capture_board`) và đợi tới 12s.
5. **`query_selector("table")` lấy bảng ĐẦU TIÊN của trang, không phải bảng vừa đo** —
   `capture_chart.MEASURE_JS` chỉ trả về TÊN KIỂU. Đo một đằng chụp một nẻo. Giờ JS tự đánh
   dấu phần tử nó chọn (`data-xh-board`).

Chốt cuối: cắt theo **18 hàng đầu**, không theo chiều cao phần tử (nửa dưới là chart đang
quay) cũng không theo hàng cuối (bản đã tải xong của arena có 131 hàng, cao 6934px). 18 chứ
không phải 15 vì 15 hàng ra tỉ lệ 1,68–1,70 — quá ngưỡng 1,6 của `card.kiem_anh_thap` nên
Ethan không dùng một mình được; 18 hàng về ~1,40.

## Kết quả đo cuối

| Trang | Ra ảnh | Cỡ | Tỉ lệ |
|---|---|---|---|
| artificialanalysis/leaderboards/models | ✅ | 2796×1968 | 1,42 |
| arena.ai/leaderboard/code/webdev | ✅ | 2668×1906 | 1,40 |
| artificialanalysis/speech-to-text | ✅ | 2796×1620 | 1,73 |
| artificialanalysis/text-to-speech | ❌ từ chối | — | — |

`/text-to-speech`: phần tử đo được là `figure` **0 ký tự** — cổng nội dung từ chối, bài rơi về
thẻ chữ đúng như trước, không có hồi quy.

**Còn đó, chưa chữa:** bản CHƯA bung của bảng arena chỉ có 10 hàng + nút "View all", nên tấm
ảnh có khoảng 30% cuối là khung chart trống. Bảng thật nằm ở trên, ảnh vẫn dùng được, nhưng
chưa đẹp. Ghi ra đây để lần sau không phải đo lại từ đầu.

Bài học: đừng dùng `element.screenshot()` cho trang ứng dụng — `page.screenshot(clip=…)` vừa
nhanh vừa không phụ thuộc DOM còn sống hay không. Và một phép đo trả về "tên kiểu phần tử"
thì bên nhận phải đánh dấu lại đúng phần tử, nếu không hai bên nói về hai thứ khác nhau.
