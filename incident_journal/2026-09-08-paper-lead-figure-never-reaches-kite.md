## Hình đầu paper không bao giờ tới được Kite (08/09/2026)

Ông Chủ, về một bộ dựng từ paper arxiv: *"ngay đầu paper có image mà Kite không
dùng để làm hero"*, kèm link `arxiv.org/html/2510.04618v3` (ACE, ICLR 2026).
Đúng, và không phải Kite bỏ qua — **kho ảnh của bài chưa bao giờ có tấm đó**. Ba
đường đều hụt, mỗi đường vì một lý do khác nhau, và cả ba đều hỏng **câm lặng**:

1. Link trong kho tin là `arxiv.org/abs/<id>` (`scan_sources.fetch_arxiv` lấy
   `entry/id` của API). Trang abs chỉ có tóm tắt — browser mở ra về tay không,
   không lỗi, không cảnh báo.
2. Bản HTML thì **có** hình, nhưng LaTeXML xuất figure ra
   `<object type="image/svg+xml">`; `JS_IMG` của `browser_pass` quét
   `document.images` nên không thấy `<object>` bao giờ. Cổng chụp `figure` đòi
   ≥ 600×300, mà Figure 1 của ACE là **521×160pt** — rộng mà thấp, trượt luôn
   cổng còn lại.
3. `arxiv_bia.py` chỉ chạy ở nhánh `if not cands` và chỉ chụp **trang bìa**
   (tên công trình + tác giả). Không phải biểu đồ kết quả.

Nên `anh_chuan_bi.py` báo "0 ảnh thật" → tự chuyển Kite vẽ vector, và Kite vẽ
đúng theo brief. Lỗi nằm ở kho ảnh, không ở vai.

**Sửa:** `arxiv_hinh.py` bóc thẳng hình từ PDF (định vị khối chữ `Figure N:`,
lấy vùng đồ hoạ ngay trên nó), chạy cho **mọi** tin arxiv/PDF chứ không phải chỉ
khi hết ứng viên; Figure 1 vào brief của Kite kèm chỉ dẫn đặt lên `image` của
slide `cover`. Đo trên 4 paper khác kiểu bố cục (ACE, Attention, DeepSeek-R1,
BERT): 2–4 hình mỗi bài, 2200–3000px bề ngang.

Bốn luật hình học trong `vung_hinh()` đều sinh ra từ một paper thật làm hỏng bản
trước đó — chi tiết trong `tests/test_arxiv_hinh.py`, mỗi test ghi tên paper:

- ACE vẽ cột biểu đồ bằng đường **kéo dài rồi cắt bằng clip**, nên hộp của nét
  vẽ cao tới y=964 trên trang 792. Cắt theo hộp đó thì ảnh nuốt cả đoạn văn dưới
  chú thích. → cắt theo **dải** giữa thân bài và chú thích, không theo hộp nét vẽ.
- ACE hình 4 nằm ngay đầu trang: dải chạm đường kẻ mờ dưới chạy đầu trang
  (y=39.15) và kéo theo nửa dòng *"Published as a conference paper at ICLR 2026"*.
  → chặn bằng chính khối chữ chạy đầu, không bằng lề cố định (DeepSeek-R1 không
  có chạy đầu, hình bắt đầu ngay từ ~6% trang — lề cứng sẽ cắt cụt tên biểu đồ).
- DeepSeek-R1 viết `Figure 1 | ...` (gạch đứng, không phải hai chấm), và MuPDF
  cắt chú thích **từng dòng một** thay vì cả đoạn như ACE. Gộp dòng phải đo khe
  theo chiều cao **một dòng**: lấy nửa chiều cao cả khối thì chú thích 5 dòng của
  BERT nuốt đoạn thân bài cách 30pt, rồi chuỗi tiếp xuống hết trang.
- BERT hình 1 có những hàng ô token trải rộng bằng cột, trông y hệt một dòng thân
  bài, nên mốc chặn bị chốt **giữa hình** → ảnh còn một vệt 5.4:1 và bị loại. →
  thử lần lượt các mốc, hình còn chạm trần dải thì nối dải lên tiếp.

**Không lấy bảng.** Chú thích bảng khi ở trên khi ở dưới tuỳ nơi đăng (BERT đặt
dưới), và từng dòng của bảng không phân biệt được với dòng thân bài — không có
mốc nào chắc để chặn. Bảng 1 của BERT cắt ra thành nguyên một trang chữ hai cột.
Cắt sai một cái bảng là dán lên slide một bảng **khác** với bảng trong bài, nên
thà không có.

---

