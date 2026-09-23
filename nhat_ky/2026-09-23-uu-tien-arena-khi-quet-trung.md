# Ưu tiên arena.ai khi cùng model quét được ở cả AA — 23/09/2026

Ticket theo dõi: LOW-383 (cha: LOW-381).

Sau khi đo nguồn ảnh xếp hạng ở LOW-381 (arena chụp được 37/45 lần, `aa-models` 0/45),
Ông Chủ chốt: *"giữ nó làm nguồn bổ sung cho Nova quét, nếu quét được ở cả AA thì tin quét
từ Arena.ai được ưu tiên"*.

Cái bẫy không nằm ở luật ưu tiên mà ở **phép so tên**. Hai trang đặt tên khác hệ:

| | arena.ai | artificialanalysis |
|---|---|---|
| Claude Opus 5.5 | `claude-opus-5-5-max` | `Claude Opus 5.5` |
| GPT-6 Astra | `gpt-6-astra-max` | `GPT-6 Astra` |
| Qwen3.8 | `qwen3.8-max-0902` | `Qwen3.8` |

Đo trên máy chủ (top-20 mỗi bảng, 7 bảng arena × 3 bảng AA): khớp thô thấy **1/20** tên
trùng, qua `model_name.key` thấy **16/20**. Luật ưu tiên mà dùng khớp thô thì im lặng bỏ sót
15/16 ca — Nova vẫn ra tin đôi, mà bản dư ra là bản đi đường AA (đường không có ảnh).

Làm:

- `model_name.key()` — khoá so tên giữa hai nhà cung cấp, cùng phép chuẩn hoá với `norm`
  trong `ranking._JS_NORM` (bỏ dấu tách, GIỮ chữ số: `claudeopus5` ≠ `claudeopus55`).
- `model_boards.ARENA_KEYS` / `AA_KEYS` — dẫn xuất từ `BOARD`, không chép tay (bài học 07/09:
  thêm bảng mà quên một danh sách thì mất tin, không báo gì).
- `scan_models.prefer_arena()` — hàm thuần: bỏ mục bảng AA khi arena đã có cùng model. Bản
  phát hành AA chỉ nhường khi arena thấy model đó **lần đầu** ("leo 3 bậc" bên arena là tin
  khác, không thay được tin "model mới xuất hiện"). Mục đã nhường vẫn được đánh dấu "đã báo".

Đo end-to-end trên máy chủ, state riêng trong `/tmp/low383`: bỏ `claude-fable-5.1` khỏi mốc
cũ rồi quét lại → `[uu tien arena] bo 1 muc cua artificialanalysis vi arena.ai da co cung
model: intelligence|Claude Fable 5.1`, mục bắt buộc còn lại là bản arena. Chạy trên dữ liệu
thật của một lượt quét: 160 mục → 144, đúng 16 mục AA nhường chỗ, 4 tên chỉ có ở AA
(`Claude Opus 5.5`, `GPT-5.6 Terra`, `GPT-6 Sol`, `Step 5 Preview`) giữ nguyên — đó là lý do
KHÔNG bỏ AA khỏi bộ quét.

Còn đó, chưa đụng: một model vào top nhiều bảng **arena** vẫn sinh nhiều mục bắt buộc
(`webdev|claude-fable-5.1-max` + `text|claude-fable-5.1-max`). Đó là thiết kế cũ (mỗi bảng đo
một năng lực khác), không phải thứ LOW-383 đặt ra — cần Ông Chủ chốt có gộp không.
