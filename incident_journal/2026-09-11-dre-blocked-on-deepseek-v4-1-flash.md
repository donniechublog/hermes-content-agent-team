## Dre bị chặn tin DeepSeek-V4.1-Flash: truy vấn mất tên model, không có đường tới trang công bố (11/09/2026)

Ticket theo dõi: LOW-21. Lần thứ **ba** cùng câu của Ông Chủ ("Dre vẫn không
chịu tìm ảnh liên quan"), lần này kèm luật chốt: *"phải tìm tất cả ảnh liên quan
chứ không phải chỉ tìm ảnh trong nguồn topic, đặc biệt là thông tin liên quan
tới benchmark của model"*. Tin `deepseek-v4.1-flash-max vào bảng LiveBench ở #6`,
nguồn Finn chỉ có `livebench.ai/`. Brief: 5/8 ảnh — XH + 2 chart LiveBench, thẻ
logo, 2 rack data center — Dre block.

Đo lại từng bước (`chuan_bi.log` trên máy chủ + chạy lại hàm ở local):

```
og:title livebench.ai            = 'LiveBench'  -> bỏ (< 4 từ)
_ten_rieng_khong_dau(tiêu đề)    = 'v4.1 LiveBench #6 81.4 2.4'   <- mất 'deepseek'
bao_khac_bing(...)               = 0 báo
bao_khac_bing('deepseek v4.1 flash') = 6 báo, Google News 100 item
xep_hang.tach_model(tiêu đề)     = 'deepseek-v4.1-flash-max'      <- engine ĐÃ có tên
browser_pass(deepseek.com/en/news/deepseek-v4-1-flash/) = 4 chart 5148×2640, 1671×1712, 3801×1950, 2450×1350
Google News 100 item: 0 từ deepseek.com; 14 báo: 1 link sang trang công bố
```

Ba lỗi, ba chỗ:

1. `nguon_bai._ten_rieng_khong_dau` xoá `-` trước khi tách từ → `deepseek-v4.1-flash-max`
   vỡ, `deepseek` (thường, không số) bị bỏ. Sửa: giữ gạch nối trong token;
   `_truy_van_bing` thử bản bỏ gạch trước (Bing coi `deepseek-v4.1-flash-max` là
   token lạ: 1 bài; `deepseek v4.1 flash max`: 6 bài).
2. `manifest.dong_brief_xep_hang` và `nop_chung.can_anh_xep_hang` so
   `kieu == "chup"` — giá trị `xep_hang.py` **chưa bao giờ** phát ra (chỉ `bang`,
   `bang-ghep`, `danh-sach`, `danh-sach-ghep`, `svg`, `the`). Hệ quả: mọi tin xếp
   hạng bị brief gọi là "THẺ DỰ PHÒNG", cổng ép bìa XH chưa từng chạy từ 06/09.
   Bốn tệp test stub `"chup"` nên xanh giả. Sửa: `xep_hang.KIEU_CHUP` +
   `la_chup()`, hai chỗ đọc hỏi hàm; test AST đối chiếu tập `kieu` phát ra với
   tập người đọc hiểu.
3. Không có đường tới trang công bố chính chủ. Thêm `anh_thuong_hieu.trang_cong_bo`
   (Wikidata P856 → `/news/` hoặc RSS → khớp slug model) nối ở
   `vong_bu._them_trang_cong_bo` trước browser; browser mở trang `công bố` trước,
   trần 4 ảnh. Đo 4/4 hãng ra đúng bài: DeepSeek, Anthropic, OpenAI (qua RSS vì
   HTML chặn bot), Google DeepMind. Luật ghi ở LUAT_ANH §1.2b + SKILL Dre/Kite.

Bài học: một lỗi "vai không đi tìm" lần thứ ba thì không chỉ vá — phải có cổng
ở mức mã nguồn (`tests/test_tim_tat_ca_anh_lien_quan.py`, 13 test fail trên code
cũ). Và khi Ông Chủ nói "chỉ cần vào trang announce", đừng gạt sang "để sau":
đó là quy ước chưa ai ghi, việc là ghi nó ra rồi làm.

---

