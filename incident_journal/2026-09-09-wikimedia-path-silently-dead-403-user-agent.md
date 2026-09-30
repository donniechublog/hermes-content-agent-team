## Cả đường Wikimedia chết câm lặng — 403 vì User-Agent (09/09/2026)

Ông Chủ, kèm ảnh chụp topic Dre sáng 09/09: *"Dre vẫn chưa tự tìm thêm hình liên
quan khi làm các nội dung có Big Brand"*. Năm tin liên tiếp trong một tiếng —
Qualcomm × Amazon, xưởng Samsung, kiện tập thể Anthropic, DeepSeek gọi vốn,
Philippines rót 34 tỷ — đều dừng ở cùng một nút: *"chỉ 2/5 ảnh thật dùng được
(nguồn: commons.wikimedia.org). Chọn đường: Kite vẽ vector / Dre làm với N ảnh"*.

Câu đó tự tố cáo nó: brief ghi **nguồn là commons.wikimedia.org** mà lại bảo chỉ
có 2 ảnh. Đo ra **ba lỗi chồng lên nhau**, cả ba đều hỏng câm lặng:

1. **403 ở mọi cửa Wikimedia.** Robot policy đòi UA có tên công cụ + đường liên
   hệ trong ngoặc. `anh_chuan_bi.UA` (`Mozilla/5.0 (compatible; donniechu-dre/1.0)`)
   và `anh_khai_niem.UA` đều là UA kiểu trình duyệt → **403 ở cả API tìm kiếm lẫn
   bước tải byte** từ `upload.wikimedia.org`. Ba chỗ gọi Commons đều
   `except Exception → []`, nên toàn bộ ảnh Commons — ảnh hãng *và* ảnh khái niệm
   — trả về rỗng, không một dòng nào lên tới brief. Đổi sang
   `env_load.UA_WIKI` = `donniechu-content-team/1.0 (https://dcgr.tech)` thì 200
   ngay. Bỏ ngoặc liên hệ đi là 403 lại — đo cả bốn biến thể.

2. **Chỉ hỏi MỘT hãng, hỏi bằng tên trần.** `_ten_rieng_dau` lấy cụm tên riêng
   **đầu** tiêu đề: tin "Qualcomm ... with Amazon" không bao giờ hỏi tới Amazon;
   tin nào cũng chỉ hỏi đúng chữ "Qualcomm", thứ Commons trả về lẫn ảnh hội thảo.
   → `anh_thuong_hieu.py` (LUAT_ANH §1.2d): mọi hãng watchlist tin nhắc tới, hỏi
   thẳng `"<Hãng> headquarters/building/campus"`. Đo lại trên chính tin Qualcomm:
   4 ảnh thật — trụ sở La Jolla, Qualcomm Atheros San Jose, Amazon Tower 3,
   Amazon HQ from Lake Union Park.

3. **`icon` nằm trong `sil-icon`.** `TEN_LOAI` của `anh_khai_niem` viết `icon`,
   `graph`, `chart` **trần**, khớp chuỗi con. Nên **mọi** ảnh `silicon wafer` bị
   loại — mà đó là từ khoá khái niệm của **toàn bộ tin bán dẫn**; `photograph`
   dính `graph`; `Charterhouse` dính `chart`. Bọc `` là 20/20 tệp wafer qua
   cổng. Lỗi này có từ 07/09 nhưng bị lỗi (1) che: không request nào tới được
   bộ lọc để mà lộ ra.

Cộng thêm bảng nước thiếu **Philippines** (đủ 5 nước SEA còn lại) nên tin
Philippines không ra nổi một từ khoá. Sau khi sửa, cả năm tin đều ra ảnh thật:
Qualcomm/Amazon → 4 ảnh trụ sở; Anthropic → toà án; Samsung → wafer;
Philippines → cờ.

**Vòng hai, cùng ngày.** Ông Chủ đọc kết quả trên và chỉ đúng chỗ còn hụt:
*"ko thấy ảnh liên quan thì lấy ảnh logo, ảnh founder, ảnh chụp trên các bảng
xếp hạng của model... có thiếu tư liệu đâu?"* — đúng, và **tìm theo TÊN TỆP thì
không bao giờ với tới ba thứ đó**. Anthropic/DeepSeek ra 0 ảnh không phải vì
Commons nghèo mà vì ta hỏi sai câu. Wikidata giữ sẵn hồ sơ có cấu trúc:

- `P154` logo chính thức, `P18` ảnh công ty, `P112`/`P169` người sáng lập/CEO
  → `P18` của chính họ. Anthropic: logo + chân dung Dario Amodei. DeepSeek: logo.
  Qualcomm: trụ sở + Cristiano Amon + Irwin M. Jacobs.
- `P18` còn với tới thứ tìm-tên-tệp không với được: trụ sở OpenAI trên Commons
  tên là *"Pioneer Building, San Francisco"*, không một chữ "openai" nào.

Ba cái bẫy khi nối ba nguồn đó vào dây chuyền, cả ba chỉ lộ ra khi chạy thật:

1. **Wikidata trả cả người tiền nhiệm.** Hỏi CEO OpenAI ra *Sam Altman* **và**
   *Mira Murati* (CEO tạm quyền cuối 2023) — phân biệt bằng *qualifier* `P582`
   "end time", không phải bằng thứ tự. Không lọc thì brief ghi "CEO OpenAI: Mira
   Murati", sai sự thật, mà vai không có đường nào kiểm.
2. **Thẻ logo tự chặn chính nó.** `URL_RAC` (bộ từ vựng rác) có chữ `logo` để
   chặn logo báo/quảng cáo lọt vào từ `<img>` của trang — nên tệp `the_logo.png`
   ta cố tình dựng bị nó vứt ngay ở cổng tải. Thêm cờ `cho_do_hoa` để ứng viên
   **có chủ ý** là đồ hoạ đi qua được cả cổng này lẫn cổng `_do_hoa`.
3. **Đừng chặn chân dung theo số mặt đếm được.** `luat_anh.dem_mat` trả `None`
   khi thiếu cv2 và `phan_loai` đổi thành `0`; lấy `mat == 0` làm "không phải
   chân dung" thì trên máy thiếu cv2 **mọi** chân dung bị bỏ câm lặng — đúng
   loại lỗi của mục 1 ở trên, lặp lại ngay trong bản sửa của chính nó. Để con
   mắt phán, bằng **câu hỏi riêng cho từng loại tư liệu**: câu chung hỏi "có
   phải ảnh của tin không" thì chân dung và thẻ logo chắc chắn trượt.

**Vòng ba: hàng chuyển sang Kite.** Ông Chủ: *"sau khi tìm được hình tốt mà vẫn
ko đủ để làm và pass qua cho Kite thì Kite cũng phải dùng những hình đó trong
body"*. Cổng cũ của `kite_nop` chỉ đòi **ít nhất một** tấm — nên Kite hợp lệ khi
đặt đúng một tấm lên bìa rồi vẽ vector cả thân, đúng cái bị chê. Giờ tin có
`chuyen_tu` thì đòi **đủ mã** và đòi **có hình ngoài bìa**. Hai chỗ phải nhớ:
tín hiệu "chuyển vì thiếu ảnh" nằm ở `img.json` chứ không ở `xong.json` (nút của
Ông Chủ bấm SAU khi engine ghi xong), và phải có trần 6 tấm — bộ chỉ được 6..10
slide, ép 9 tấm là hai cổng đá nhau và vai không có đường nào nộp được.

Bảng xếp hạng thì mượn thẳng `xep_hang.py`, nhưng chỉ nhận ảnh **chụp thật**:
hết đường thì `tim_va_chup` tự dựng *thẻ dự phòng* `"<model> #<hạng>"` — với một
tin KHÔNG PHẢI tin xếp hạng, thẻ đó là bịa ra một thứ hạng không ai nói.

**Bài học đúng loại cũ:** `except Exception → []` ở một nhánh *bù* thì không bao
giờ kêu. Nhánh chính (ảnh trong bài) vẫn chạy nên số ảnh không về 0, chỉ mỏng đi
— và "mỏng" trông y hệt "tin này ít ảnh thật". Ba tuần không ai nghi Commons hỏng
vì brief vẫn **ghi tên commons.wikimedia.org** trong dòng nguồn.

Một cái bẫy nữa, chỉ lộ ra khi chạy thật: câu `"Amazon building"` trả về hai tấm
*International Day of Solidarity With Alabama Amazon Workers* — ảnh mít tinh công
đoàn, đúng chữ "Amazon", sai hẳn loại ảnh cho tin ký hợp đồng chip. `TEN_LOAI` có
`protest` nhưng tên tệp không có chữ đó. → thêm `NHIEU_CHUNG` (solidarity, rally,
strike, picket…), tránh `march` (trùng tháng Ba) và `union` trần (trùng Union
Square).

---

