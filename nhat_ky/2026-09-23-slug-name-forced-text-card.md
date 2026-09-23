# Tên model dạng slug làm tin xếp hạng ra thẻ chữ — 23/09/2026

Ticket theo dõi: LOW-381 (con: LOW-383).

Ông Chủ, nguyên văn, khi thấy hero của Ethan bên dcgr: *"sao chúng ta ko chụp luôn trang
này mà lại dùng text nhỉ?"* — *"hình ảnh chart sẽ luôn được ưu tiên hơn text thuần chứ"*.

Ảnh bị hỏi là `ranking.fallback_card`: chữ trần trên nền đen, ghi
`ARTIFICIALANALYSIS.AI · INTELLIGENCE INDEX` / `claude-opus-5-5-max`, trong khi hook nói
**LiveBench**. Bài `claude-opus-5-5-max-effort-va-xhigh-effo-ethan-dcgr`, link gốc chính là
trang bảng xếp hạng của artificialanalysis.

Hệ thống **không** chọn text. Nó đã đi chụp và trượt ở mọi nguồn:

```
[arena_x] … không tweet nào nhắc đúng ['claude-opus-5-5-max']
[xep_hang] aa-models: bỏ — … không có bảng ≥5 hàng chứa tên model
[xep_hang] livebench: bỏ — … không có bảng ≥5 hàng chứa tên model
[xep_hang] không nguồn nào chụp được → thẻ dự phòng claude-opus-5-5-max #?
```

Ba lớp chồng lên nhau:

1. **Tiêu đề mang tên dạng slug.** Tin lấy từ trang bảng, mà arena.ai viết tên model dạng
   `claude-opus-5-max`; AA thì in `Claude Opus 5.5 (max with fallback)`. Tiêu đề bài này
   viết `claude-opus-5-5-max-effort`.
2. **`extract_model` rút gọn theo TỪ cách nhau bằng dấu cách.** Slug là MỘT từ nên vòng rút
   gọn không chạy: danh sách ứng viên có đúng một cái. Hàng thật có chuỗi `claude opus 5.5`
   rồi dấu `(` chen vào trước `max`, nên `matchesModel` không khớp.
3. **Thẻ dự phòng tự khai sai bảng.** Nó lấy `nguon_ds[0]` — nguồn xếp đầu theo điểm, ở đây
   là AA (lọt vào vì LINK bài trỏ tới đó), chứ không phải bảng tiêu đề gọi tên (LiveBench).

Sửa (LOW-381):

- `model_name.py` mới — quy slug về tên hiển thị (gạch nối → dấu cách, `5-5` → `5.5`, bỏ hậu
  tố mức nỗ lực và đuôi ngày `-0902`). Tệp thuần, không import gì của dự án; `scan_models`
  dùng chung ở LOW-383. Gạch nối trong tên CÓ chữ hoa (`Kimi-K3`, `MiMo-V2.6-Pro`) được giữ
  nguyên — đó là một phần của tên, không phải dấu tách của slug.
- `ranking.extract_model` thêm bản hiển thị trước khi rút gọn theo từ:
  `['claude-opus-5-5-max', 'Claude Opus 5.5', 'Claude Opus']`.
- Thẻ dự phòng ghi bảng được gọi tên ở TIÊU ĐỀ (khoá mới `in_title`) và in tên model dạng
  hiển thị.

Đo trên máy chủ cùng tiêu đề đó, code nhánh trong `/tmp/low381`:

| | Trước | Sau |
|---|---|---|
| Đường @arena (LOW-337) | không tweet nào khớp | khớp `claude opus 5.5`, ra ảnh chính chủ |
| Đường bảng (tắt arena) | không nguồn nào chụp được | `aa-models` khớp, bảng 2828x1846 khoanh đúng hàng |

`tests/test_ranking_slug_model.py` đỏ 4/6 trên code cũ, xanh 6/6 trên code mới; toàn bộ
`tests/run.sh` xanh 193/193 trên máy chủ.

Bài học: thẻ dự phòng là một cái **hỏng im lặng** — ảnh vẫn ra, bài vẫn đăng, không cổng nào
nổ. Một đường chụp chết có thể chạy cả tuần mà chỉ Ông Chủ nhìn ảnh mới thấy. Đo lại toàn bộ
log còn trong `state`: arena 37/45 lần chụp được, aa-models **0/45** — con số 0 đó lẽ ra phải
là một tín hiệu từ lâu, nhưng không ai đếm.
