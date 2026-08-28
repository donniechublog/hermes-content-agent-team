---
name: inplace-translate
description: "Remake carousel GIỮ NGUYÊN bố cục ảnh gốc, chỉ đổi chữ Anh sang Việt tại đúng vị trí/màu cũ — khác deck.py (thiết kế lại từ đầu). Gin dùng doi_chu_anh.py --xuat-vung để đo vị trí+màu từng vùng chữ khi xoá; Itachi viết bản dịch rồi dùng ve_chu_thay_the.py vẽ đè vào đúng đó, font gần giống nhất tự chọn hoặc chỉ định tay. Giới hạn: hợp nhãn/tiêu đề/badge ngắn, KHÔNG hợp đoạn văn nhiều dòng vì OCR trả box theo từng dòng."
version: 1.0.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [inplace-translate, doi-chu-anh, ve-chu-thay-the, gin, itachi, remake, ocr]
---

# inplace-translate — dịch tại chỗ, giữ nguyên bố cục ảnh gốc

Đường thứ hai để remake carousel, bên cạnh `deck.py` (thiết kế lại toàn bộ
theo `LAYOUTS`). Đường này **không** thiết kế lại gì — chỉ lấy đúng ảnh gốc,
xoá chữ Anh, và vẽ chữ Việt vào **đúng vị trí, đúng cỡ khung, màu gần giống**
chữ cũ. Dùng khi bố cục ảnh gốc đã tốt, không cần đổi, chỉ cần đổi ngôn ngữ —
nhanh hơn viết spec `deck.py` cho những trường hợp đơn giản (nhãn, badge,
tiêu đề ngắn), và **không cần đoán toạ độ tay** như cách cũ (`"y"/"x"/"max_w"`
ghi đè trong layout `statement`).

**Ai làm gì:** Gin đo đạc (chạy trên máy nặng riêng), Itachi viết bản dịch +
vẽ (chạy trên server, việc nhẹ, không đụng torch/OCR).

## KHÔNG dùng tool `clarify` trong luồng Telegram — luôn kết luận bằng text

Kênh Telegram của Gin/Itachi chạy **one-shot** (`chat_router.py` gọi `hermes
CLI -z "<text>"` một lần, không giữ kết nối chờ trả lời). Gọi tool `clarify`
ở đây KHÔNG có người thật để trả lời — hermes tự chọn "Recommended" trong chế
độ oneshot, nhưng nếu bạn không nhận ra và tự đọc tiếp, bạn sẽ **lặp lại việc
kiểm tra đã kiểm tra rồi** (đã xảy ra thật: kiểm tra `cv2`/`easyocr` ba lần
liền, không tiến thêm được gì) cho tới khi hết 600 giây timeout của
`chat_router.ask` — phiên chết ngang, **Telegram không nhận được gì cả**,
không lỗi, không tin nhắn, im lặng hoàn toàn. Đây là lỗi thật đã xảy ra, không
phải giả định.

Cần hỏi lại Ông Chủ điều gì đó → viết thẳng câu hỏi vào **câu trả lời cuối
cùng** (text bình thường bạn gửi về Telegram), rồi DỪNG LƯỢT — không gọi thêm
tool nào sau đó. Ông Chủ đọc, trả lời bằng một tin nhắn mới trong topic, bạn
xử lý tiếp ở lượt sau. Đây là hội thoại bất đồng bộ bình thường, không phải
một cuộc gọi chờ trả lời ngay.

## Server hermes ĐÃ có cv2/easyocr/torch (từ 28/08/2026)

Mục này trước đây nói ngược lại — đã hết đúng. `~/content-team/venv` nay có
đủ `torch`+`torchvision` (bản `+cpu`), `easyocr`, `opencv-python-headless`,
`simple-lama-inpainting`, nên Bước 1 chạy được NGAY trên server, không phải
chờ máy riêng của Gin. Gặp ảnh chưa có `vung.json`/`nen_sach.png` thì tự chạy
`doi_chu_anh.py`, đừng báo lại rồi dừng.

1. **Kiểm đĩa trước khi chạy**: server 16G hay ở ~94%. `df -h /` còn dưới
   ~500MB thì dọn trước (`journalctl --vacuum-size=100M`, `rm -rf /tmp/pip-*`,
   `pip cache purge`). Lần đầu chạy còn tải model LaMa 196MB về `~/.cache/torch`.
2. **Đừng tự viết mask/threshold PIL thay thế** trừ khi nền THẬT SỰ phẳng
   tuyệt đối một màu (case hiếm — xem cảnh báo ở docstring `ve_chu_thay_the.py`).
   Ảnh có bố cục phức tạp (ảnh chụp, nhân vật, gradient, banner chồng lớp...)
   mà tự chế mask là hỏng âm thầm, không ai cảnh báo.
3. **Dịch sẵn phần chữ** (đọc bằng `vision_analyze`, viết bản tiếng Việt cho
   từng vùng) để không mất thời gian khi Gin xong việc — nhưng ẢNH thì chưa
   dựng được.
4. **Kết luận bằng MỘT câu trả lời cuối**, liệt kê rõ: đã dịch chữ gì, đang
   chờ Gin chạy `doi_chu_anh.py --xuat-vung` trên máy riêng, và ảnh sẽ ra khi
   nào có `nen_sach.png`/`vung.json`. Không lặp lại tool nào sau đó.

## Bước 1 (Gin, máy riêng) — xoá chữ + xuất vị trí

```bash
venv/bin/python doi_chu_anh.py \
  --anh nguon.jpg --out nen_sach.png \
  --xuat-vung vung.json \
  --giu "0,0,260,110"
```

(`--anh-url <url>` thay `--anh` nếu cần tải ảnh gốc từ link trước — dùng
`urllib` chuẩn, không cần cài thêm gì.)

`vung.json` là một mảng, mỗi phần tử một vùng chữ đã xoá:
```json
[{"x": 84, "y": 200, "w": 900, "h": 90,
  "color_rgb": [255, 255, 255], "ocr_text": "HELLO WORLD", "conf": 0.9}, ...]
```
`color_rgb` là **màu chữ thật đo được** từ ảnh gốc (trung vị pixel chữ trước
khi xoá) — không phải đoán. Mảng sắp theo **trên→dưới, trái→phải**, thứ tự
đọc tự nhiên. Xem `--xem-mask` như cũ để tự kiểm trước khi giao.

Giao cả `nen_sach.png` và `vung.json` cho Itachi.

## Bước 2 (Itachi) — viết bản dịch

Viết `thay_the.json`: **mảng cùng độ dài `vung.json`, cùng thứ tự** (phần tử
thứ *i* là bản dịch của vùng thứ *i*). Dùng `null` để bỏ qua một vùng (giữ nền
sạch, không vẽ gì — vùng đó hoá ra là logo/nhiễu OCR không cần dịch):

```json
[
  {"text": "Xin chào thế giới"},
  null,
  {"text": "Đoạn thân bài", "font": "regular", "align": "center", "color_rgb": [230, 230, 230]}
]
```

Trường tuỳ chọn mỗi phần tử:
- `font`: `bold`/`regular`/`serif`/`condensed`/`mono` — xem "Chọn font" bên
  dưới. Bỏ trống thì công cụ tự đoán theo chiều cao vùng.
- `align`: `left` (mặc định — bám đúng mép trái của box OCR gốc) hoặc
  `center`.
- `color_rgb`: ghi đè màu đo được từ `vung.json` nếu bạn thấy màu tự động
  không hợp (ví dụ chữ gốc có gradient, trung vị ra màu lệch).

## Bước 3 (Itachi) — vẽ

```bash
venv/bin/python ve_chu_thay_the.py \
  --anh nen_sach.png --vung vung.json --spec thay_the.json --out ket_qua.png
```

Cổng chặn giống `deck.py`/`card.py`: thiếu dấu tiếng Việt ở bất kỳ vùng nào
là **dừng hẳn**, in rõ vùng nào sai. Chỉ dùng `--bo-qua-dau` khi chữ thật sự
là tiếng Anh.

`ket_qua.png` là ảnh hoàn chỉnh — không cần đi qua `deck.py` nữa (đường này
thay thế `deck.py` cho case cụ thể này, không phải bổ sung).

## Chọn font — "gần giống nhất" là đủ

Không có nhận diện font thật từ ảnh (bài toán CV riêng, không đáng đầu tư cho
mức cần "gần giống"). Bộ font sẵn có, chọn bằng mắt khi nhìn ảnh gốc:

| `font` | File | Hợp khi ảnh gốc dùng |
|---|---|---|
| `bold` | BeVietnamPro-Bold | tiêu đề đậm, sans-serif hiện đại (mặc định cho vùng cao) |
| `regular` | BeVietnamPro-Regular | thân bài, chú thích (mặc định cho vùng thấp) |
| `serif` | NotoSerifDisplay | tiêu đề kiểu báo/tạp chí, chân chữ |
| `condensed` | Oswald | nhãn hẹp, badge, chữ viết hoa dồn ép |
| `mono` | JetBrainsMono-Bold | text kiểu code/kỹ thuật |

Mặc định khi bỏ trống `font`: vùng cao ≥ 4.5% chiều cao ảnh → `bold`, thấp
hơn → `regular`. Đây là **suy đoán thô**, chỉ đúng khi một vùng OCR là một
DÒNG đơn (trường hợp phổ biến — xem giới hạn bên dưới); nhìn ảnh gốc thấy sai
kiểu (vd tiêu đề serif, nhãn condensed) thì ghi `font` tay, đừng để mặc định.

## Giới hạn: hợp nhãn/tiêu đề, KHÔNG hợp đoạn văn dài

EasyOCR trả **một box cho mỗi dòng chữ**, không gộp một đoạn nhiều dòng thành
một box. Với nhãn/badge/tiêu đề một dòng, `vung.json` khớp gọn 1-vùng-1-ý,
dùng thẳng được. Với một đoạn thân bài 3-4 dòng trong ảnh gốc, `vung.json` sẽ
có 3-4 vùng NHỎ liên tiếp — mà câu tiếng Việt dịch ra hiếm khi ngắt dòng đúng
y hệt bản Anh, nên nhồi bản dịch vào từng box nhỏ riêng lẻ dễ vỡ chữ hoặc cắt
ý sai chỗ.

Gặp đoạn văn nhiều dòng: hoặc gộp thủ công các vùng liên tiếp thuộc cùng một
đoạn thành một vùng lớn hơn trước khi viết `thay_the.json` (sửa tay `x/y/w/h`
trong `vung.json`, lấy min/max của các vùng con), hoặc bỏ qua các vùng đó
(`null`) và dùng `deck.py` dựng lại toàn bộ slide đó theo layout `statement`/
`list_steps` như cách cũ — công cụ này không cố tự động gộp đoạn, đừng ép nó
làm việc ngoài phạm vi.

## Khi nào dùng đường này, khi nào dùng `deck.py`

| | inplace-translate | `deck.py` |
|---|---|---|
| Bố cục ảnh gốc | giữ nguyên | thiết kế lại theo `LAYOUTS` |
| Hợp với | nhãn/tiêu đề/badge ngắn, ảnh gốc đã đẹp | đoạn văn dài, cần bố cục mới, ảnh gốc xấu/không rõ chữ |
| Vị trí chữ Việt | tự động (đo từ OCR) | tay (`"y"/"x"/"max_w"` ghi đè trong `statement`) |
| Ảnh nền | ảnh thật đã dọn (`doi_chu_anh.py`) | ảnh thật đã dọn HOẶC nền AI (`ai-background`) HOẶC nền màu phẳng |

Hai đường không loại trừ nhau trong cùng một bộ carousel — slide nào chữ đơn
giản, giữ nguyên bố cục đẹp thì dùng `inplace-translate`; slide nào cần viết
lại/đoạn dài thì dùng `deck.py` như cũ.
