# Nhật ký sự cố & bài học

Tách khỏi `README.md` ngày 06/09/2026. README chỉ mô tả **hiện trạng**; mọi
chẩn đoán, số đo một lần, và bài học rút ra thì nằm ở đây — nguyên văn, không
cắt gọt, vì phần lớn giá trị của chúng nằm ở con số cụ thể và cách đo.

Đọc README trước để biết hệ thống ĐANG chạy thế nào; đọc tệp này khi cần biết
**vì sao** nó thành ra như vậy, hoặc khi một sự cố cũ có vẻ đang lặp lại.

Nguồn sự thật của cấu hình luôn là chính máy chủ, không phải hai tệp này:

```bash
grep -h "^  model:" ~/.hermes-*/profiles/*/config.yaml | sort | uniq -c
```

---

## Vera gửi ba báo cáo trong một task, reply vào bản thứ hai thì im lặng (12/09/2026)

Ticket theo dõi: LOW-25. Ông Chủ báo: *"Vera ticket. gửi 2
lần báo cáo, reply chuyển task cho Dre cũng ko phản hồi"*. Thực tế là **ba** lần
gửi, và lần im lặng là hệ quả trực tiếp của chúng.

Một task `t_901479ea` ("Quet tin kinh doanh 2026-09-12"), phiên
`20260911_220030_fade87`, Vera chạy `quet_nop.py --vai vera` ba lần — mỗi lần
là một báo cáo mới vào topic:

| Lần | Vera viết sai gì | stderr | Vẫn gửi? |
|---|---|---|---|
| 1 | `k` ghi `"#15"` thay vì `"15"` | 20 dòng `[bo qua] ... ngoai danh sach 1..80` | có — bản 4 mục |
| 2 | title ASCII, không dấu | 19 dòng `[canh bao] ... title tieng Viet mat dau` | có — bản 27 mục (msg 2004) |
| 3 | sạch | — | có — bản 27 mục (msg 2005) |

Cả ba lần `rc=0`. `--luu-mid` ghi mid của bản **cuối**, nên
`state/dcgr/bao_cao_mid.vera.json` = 2005. Ông Chủ đọc bản 2004 (bản không dấu,
đứng trước trong topic) và reply vào đó:

```
09-12 00:24:30 [vao] msg=2007 thread=83 vai=vera text=1, 7 - Dre
09-12 00:24:30 [route] msg=2007 ung-vien-chon vai=vera reply_that=2004 la_reply_bao_cao=False
09-12 00:24:30 [route] msg=2007 giong lenh chon nhung khong phai reply bao cao vai=vera -> coi la hoi thoai
09-12 00:24:30 [route] msg=2007 chat -> nhuong gateway (CT_CHAT_QUA_GATEWAY=1)
```

Rồi **không gì cả**: `~/.hermes-dcgr/logs/agent.log` không có một dòng nào lúc
00:24. Gateway dcgr đặt `require_mention: true` và đã bỏ `free_response_topics`
(08/09/2026), nên tin không nhắc tên bot thì không ai trả lời. Hai lớp cộng lại
ra đúng thứ tệ nhất: **im lặng** — nhìn y hệt lúc bot chết.

Lỗi phụ cùng chuỗi: `manifest_ghi.py` lấy ngày bằng `datetime.now(timezone.utc)`
trong khi cả đội sống theo giờ VN. Cron chạy 05:01 VN = 22:01 UTC hôm trước, nên
báo cáo đề "Vera — 2026-09-11" cho bản quét ngày 12, tên tệp đụng tên hôm trước
và rơi xuống nhánh `duong_ra_moi` → `vera_candidates_2026-09-11_t2201.json`. Mà
`duong_ra_moi` chỉ tới PHÚT: ba lần chạy trong cùng phút ra cùng một tên, bản
sau đè bản trước — đúng cái mà docstring của chính nó hứa là không làm.

Bốn chỗ sửa, theo đúng thứ tự chuỗi hỏng:

1. `quet_nop.loi_chan_gui` — `[bo qua]` (mất tin) và title mất dấu **chặn gửi**,
   rc=1, vai sửa rồi chạy lại. Một lần quét, một báo cáo. `[tu them]` và
   summary dài vẫn gửi: script đã tự xử lý xong, chặn là kẹt task.
2. `publish.py --luu-mid` ghi `message_ids` của **mọi mảnh** — báo cáo dài bị
   Telegram cắt đôi thì mục số 1 nằm ở mảnh đầu, và Ông Chủ reply vào đó.
3. `_la_reply_bao_cao` nhận bất kỳ mid nào trong cùng một lần gửi. Reply vào
   báo cáo CŨ vẫn bị từ chối như cũ (số thứ tự của bản cũ khác).
4. `_bao_khong_phai_reply` — cổng từ chối thì **nói**, không im. Và
   `manifest_da_gui` ghim đường dẫn manifest vào tệp mid ngay sau khi gửi: từ
   khi cổng 1 chặn gửi mà vẫn ghi manifest, "bản mới nhất theo mtime" không còn
   bằng "bản Ông Chủ đang nhìn" nữa.

Chạy thử lại bằng chính `ds.json` thật của hôm đó (`--thu`, không gửi Telegram):
bản `k` sai → rc=1 không gửi; bản mất dấu → rc=1 không gửi; bản sạch → gửi, và
tiêu đề báo cáo ra đúng `Vera — 2026-09-12`.

**Bổ sung cùng ngày (LOW-28) — cổng NHẬN cũng phải nói.** Ông Chủ: *"phải có
phản hồi 'đang gửi cho Dre' ngay sau khi nhận được reply"*. Đo trên
`approve.log` 11/09: lệnh vào 04:22:43, `[chon] xong sau 157s` lúc 04:25:20 —
**157 giây** topic không có gì. Có `_bao_nhan_viec`, nhưng nó bắn vào topic CỦA
VAI NHẬN (Dre), không phải topic quét Ông Chủ đang nhìn; nên ở bên này im lặng
y hệt lúc lệnh bị nuốt. Nay `_bao_da_nhan` gửi ngay vào đúng topic đó, TRƯỚC
khoá và trước `create_pair` (mỗi tin tới 180 giây), kèm tiêu đề từng số để đọc
một dòng là biết số vừa gõ có trỏ đúng tin định giao không.

**Bài học:** một cổng chỉ *in cảnh báo* rồi vẫn cho đi tiếp thì không phải cổng —
nó chỉ dời việc hỏng xuống chỗ khác. Ở đây nó dời sang topic của Ông Chủ, dưới
dạng ba bản gần giống nhau mà chỉ một bản bấm được. Và cổng nào từ chối cũng
phải trả lời: trên dcgr, "rơi về hội thoại" nghĩa là rơi vào im lặng.

---

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

## Máy tìm ảnh hãng dựng xong nhưng treo sau chữ "nếu thiếu ảnh" (10/09/2026)

Ông Chủ, kèm hai link task: *"Dre vẫn ko chịu đi tìm các hình liên quan như logo,
brand, founder, trụ sở... của chủ đề được nhắc tới"* — **đúng câu đã nói hôm
09/09**, sau khi bản sửa 09/09 đã chạy được một ngày.

Bản 09/09 không sai chỗ nào nó làm: UA Wikimedia, hỏi nhiều hãng, Wikidata
`P18`/`P154`/`P112`, câu hỏi vision riêng cho từng loại tư liệu — đo lại vẫn ra
ảnh thật. Sai ở chỗ **nối nó vào dây chuyền**: `anh_chuan_bi.chuan_bi()` gọi
`_vong_thuong_hieu` bên trong một `if len(dung_duoc) < muc_tieu_tim or not
_co_bia(...)`. Tức nó là **vòng bù khi thiếu ảnh**, không phải một vòng đi tìm.

Đo bằng cách thay mọi pha nặng bằng stub rồi đếm vòng nào thật sự chạy (tin
`Samsung opens new chip plant in Texas`, ngưỡng Dre = 5):

```
2 ảnh của chính bài dùng được -> ['thuong_hieu', 'khai_niem']
4 ảnh                          -> ['thuong_hieu', 'khai_niem']
5 ảnh                          -> KHÔNG VÒNG NÀO
9 ảnh                          -> KHÔNG VÒNG NÀO
```

Bài viết về một hãng lớn mà báo gốc có sẵn 5 ảnh thì **không một request nào**
tới Commons/Wikidata — không logo, không chân dung founder, không trụ sở. Mà vai
thì bị brief cấm tự tải thêm ("chỉ dùng MÃ ẢNH, không tải/crop/mở gì thêm") và
từ kiến trúc 3 lớp cũng không còn công cụ tìm ảnh. Nên nhìn từ phía Ông Chủ nó
hiện ra đúng như *"Dre không chịu đi tìm"*, còn thật ra Dre không có gì để chọn.

**Bài học**: một tính năng "đi tìm thêm tư liệu" mà đặt sau điều kiện *thiếu* thì
nó chỉ là lưới an toàn, không phải tính năng. Hai thứ đó khác nhau ở chỗ ai được
hưởng: lưới cứu bài nghèo ảnh, tính năng làm giàu **mọi** bài. Câu của Ông Chủ cả
hai lần đều là loại thứ hai; lần đầu đọc thành loại thứ nhất vì câu 09/09 mở đầu
bằng *"ko thấy ảnh liên quan thì..."*.

Sửa: gọi thẳng, không `if`. Giá phải trả có trần sẵn — tối đa +4 ảnh một bộ,
tổng không quá `TOI_DA_ANH + 4`, và tin không nhắc hãng nào trong watchlist thì
`hang_trong_tin` trả rỗng nên vòng thoát ngay, không tốn request. Riêng nhánh
**mở browser đi chụp bảng xếp hạng** vẫn giữ điều kiện thiếu ảnh — đó mới là
phần đắt (một Chromium + `xep_hang.tim_va_chup`). Vòng **ảnh khái niệm** (cờ,
rack) cũng giữ nguyên điều kiện cũ: nó là ảnh chung chung, không phải ảnh của
chủ đề được nhắc tới.

**Vế thứ hai — "task này thì ko chịu dùng hình của Founder".** Brief của Dre thật
ra gắn nhãn đủ (`👤 CHÂN DUNG NHÀ SÁNG LẬP — <tên>, ... phải khai "nhan_vat"`),
nên với Dre nguyên nhân vẫn quy về lỗi trên: không có ảnh để mà dùng. Nhưng cùng
bộ ảnh đó, `ethan_chuan_bi.nhan_ethan` **dựng lại `ghi_chu` từ đầu** nên vứt mất
ghi chú `anh_thuong_hieu.nhan_thuong_hieu` đã cài, và thay bằng một câu *"trụ
sở/campus/biển hiệu"* dán chung cho **mọi** loại tư liệu. Một tấm chân dung tới
tay Ethan vì thế không có cái **tên** để khai `nhan_vat` — mà `kiem_nhan_vat`
chặn ảnh có mặt người không khai tên, nên Ethan buộc phải bỏ ảnh founder. Câu
nhãn tách thành `anh_thuong_hieu.nhan_theo_loai(th)`, một bản cho cả hai brief.

**Cổng chặn**: `tests/test_vong_thuong_hieu_luon_chay.py`. Ba test hành vi chạy
thật `chuan_bi()` với stub, cộng một cổng ở mức **mã nguồn** — đọc AST của
`chuan_bi()` và bắt lỗi nếu lời gọi `_vong_thuong_hieu` lại nằm trong một `if`.
Cổng AST cần thiết vì test hành vi dùng stub: ai đó treo lại điều kiện bằng một
biến khác thì con số có thể tình cờ thuận và test vẫn xanh. Đối chứng ngược trên
bản `git HEAD`: hai test đó hỏng đúng như mong đợi, hai test giữ hành vi cũ xanh
cả hai bên.

---

## Ethan bị bắt làm carousel: engine áp ngưỡng của Dre cho mọi vai (10/09/2026)

Ông Chủ hỏi: *"việc của Ethan là làm single image, sao hôm nay Ethan lại báo
không thể tạo slide?"*. Giả thuyết đầu tiên — giao nhầm task — **sai**. Phân
công vẫn đúng: `duyet_chon_tin` tạo task tiêu đề `"Anh: …"` cho `designer` và
`"Carousel: …"` cho `carousel`, kanban của cả hai brand không có task nào lệch.

Bằng chứng thật nằm ở `state/blog/approve.log`:

```
09-10 00:42:02 [nut] draft=muse-spark-1-3-max-meta-m-i-v-o-8-designer-donniechubl:
  ⚠️ Chỉ 2 ảnh thật mà carousel cần tối thiểu 5 slide — bấm tiếp cũng không
  dựng được. Chuyển Kite vẽ vector, hoặc bỏ tin.
09-10 00:42:17 [nut] draft=nex-agi-nex-n2-5-pro-th-tr-ng-s-hu-designer-donniechubl:  (y hệt)
```

Đuôi draft là `-designer-…` — bài của **Ethan**, mà hệ thống nói bằng tiếng của
carousel. Ông Chủ đọc đúng như nó hiện ra: Ethan đang loay hoay với slide.

**Nguyên nhân:** `anh_chuan_bi.chuan_bi()` chạy CHUNG cho cả ba vai dùng ảnh
nhưng tính ngưỡng bằng `carousel.FLAGSHIP_MIN if flagship else
carousel.MIN_SLIDE` — luôn 5, hoặc 8 với tin flagship — bất kể vai nào sẽ dùng
bộ ảnh. `card.py` của Ethan chỉ cần **một** tấm. Nên mọi bài giao Ethan có dưới
5 ảnh khả dụng (rất thường gặp với tin không phải benchmark) đều bị kẹt ở bước
"thiếu ảnh", rồi `route_thieu_anh` gửi lên topic của Ethan câu hỏi carousel kèm
nút "Gửi Kite vẽ vector". `chuan_bi/manifest.py` ghi tiếp
`toi_thieu_co_ban = carousel.MIN_SLIDE` nên nút "hạ sàn" cũng lấy sàn 5.

Lỗi sống được lâu vì với Dre **hai con số trùng nhau**: mỗi slide một ảnh riêng,
nên "số ảnh tối thiểu" và "số slide tối thiểu" là một — `dre_nop` đọc
`m["toi_thieu"]` theo nghĩa slide, engine ghi nó theo nghĩa ảnh, không ai thấy
sự khác. Chỉ Ethan mới làm hai nghĩa đó tách ra.

**Sửa:** ngưỡng thành thuộc tính của vai trong bản đăng ký (`vai.py`:
`anh_toi_thieu`, `anh_toi_thieu_flagship`; Ethan 1, Dre 5/8, Kite 1 vì vẽ
vector), engine hỏi `vai.so_anh_toi_thieu(vai_anh, flagship)`. Vai lấy từ
`tom["vai_anh"]` — `_tom_tat_tu_img_json` đã đọc sẵn khoá đó từ sidecar
`.img.json` từ lâu, chỉ là chưa ai dùng tới.

**Cái bẫy khi sửa:** hạ thẳng ngưỡng xuống 1 cho Ethan thì hỏng theo chiều
ngược lại. Một con số đang gánh **hai việc**: nó vừa là ngưỡng CHẶN, vừa là mốc
để vòng tìm ảnh biết khi nào dừng. Ethan chỉ cần 1 tấm để *dựng*, nhưng cần
nhiều tấm để *chọn* — `card.py` chặn chart và ảnh ngang >1.6 đi một mình, vision
còn loại thêm ảnh không liên quan. Cho engine dừng tìm ở tấm đầu tiên là đúng
kiểu block đã thấy ở `t_618244d2` sáng nay ("chuẩn bị chỉ có 1 ảnh A1, A1 là
chart, hết đường"). Nên tách hẳn: `toi_thieu` (chặn, theo vai) và
`muc_tieu_tim` (dừng tìm, giữ nguyên số cũ 5/8 cho **mọi** vai). Phần tìm ảnh
chạy y hệt trước, chỉ phần chặn là đổi. Kèm ba thứ nhỏ:

- `create_pair` ghi sidecar **trước** khi chạy engine nền. Trước đó ngược lại,
  tức engine đọc một tệp chưa ai ghi — trước giờ chỉ mất tóm tắt (im lặng), từ
  nay mất cả ngưỡng.
- Nút "hạ sàn" gọi sản phẩm đúng tên: "slide" cho Dre/Kite, "ảnh" cho Ethan.
- `test_nguong_anh_theo_vai.py`: 10 test, trong đó **hai cổng đọc mã nguồn** —
  dòng thật sự hỏng nằm trong hàm mở Chromium + gọi vision, không unit test
  được. Một cổng giữ "ngưỡng chặn phải hỏi bản đăng ký vai", cổng kia giữ "vòng
  tìm ảnh không được đo bằng ngưỡng chặn". Đã thử làm hỏng lại từng chiều để
  chắc cả hai cổng thật sự đỏ, không phải test rỗng.

**Bài học:** một hằng số mượn từ module của vai khác thì sớm muộn cũng áp sai
cho vai không liên quan. Thứ thuộc về vai phải nằm trong bản đăng ký vai — đúng
lý do `vai.py` ra đời (audit A4/F1), chỉ là lần đó mới gom bảng tên, chưa gom
luật. Và khi một biến đang gánh hai nghĩa mà chỉ một nghĩa sai, tách hai nghĩa
ra trước, đừng sửa con số.

---

## Thiếu bảng "Image Edit Arena" và tên mã biến thể (09/09/2026)

Ông Chủ gửi hai ảnh chụp Arena — "Image Edit Arena" và "Text-to-Image Arena",
cả hai đều xếp GPT-Image-2.5 hạng #1 (Sunburst) và #2 (Flare) — kèm một câu:
*"làm thông tin về model mà không đưa được 2 chart này vào là quá kém"*. Đúng,
và có hai lỗ hổng cộng dồn trong `xep_hang.py`, cả hai đều hỏng câm lặng:

1. **"Image Edit Arena" chưa từng có trong registry `NGUON`.** Chỉ có
   `arena-t2i` (Text-to-Image) — bảng chỉnh sửa ảnh là một board KHÁC, tách
   riêng trên arena.ai (`/leaderboard/image-edit`), và trước giờ registry chưa
   liệt kê. Xác nhận bằng WebFetch trước khi thêm (nguyên tắc đã ghi ngay
   trong `xep_hang.py`: "không thêm nguồn chưa chụp được"): trang thật, 55
   model, dữ liệu khớp hệt ảnh Ông Chủ gửi (sunburst 1520±9, flare 1491±9, gpt
   image 2 medium 1461±3...).
2. **`_DUOI` không có "Sunburst"/"Flare".** Hai cái tên đó là mã của **hai biến
   thể cùng họ, cùng đứng trên cùng một bảng** — thiếu chúng thì `tach_model`
   dừng ở "GPT Image 2.5", khớp NHẬP NHẰNG cả hai hàng. Engine khoanh hàng nào
   tìm thấy trước, bất kể tin đang nói về Sunburst hay Flare — sai ảnh cho
   đúng một nửa số tin về cặp model này.

**Sửa:** thêm `arena-image-edit` vào `NGUON` (ngay sau `arena-t2i`) và một
mục `CHU_DE` mới ưu tiên nó khi tiêu đề nói "chỉnh sửa ảnh" / "image edit";
mục `\bimage\b` chung giờ xét **cả hai** bảng — một model tạo ảnh mạnh
thường lên cả hai board cùng lúc, đúng như dữ liệu thật lần này. Thêm
`Sunburst|Flare` vào `_DUOI`. Test hồi quy ở `tests/test_xep_hang.py` khớp lại
đúng số liệu Ông Chủ gửi (không đoán URL — mọi test dùng dữ liệu đã xác nhận
qua WebFetch).

**Cập nhật cùng ngày — lấy được cả hai chart.** Đưa ra lo ngại "kiến trúc chỉ
mang được một bảng mỗi tin, đổi sang nhiều ảnh là thay đổi lớn hơn, cần chốt
trước" — Ông Chủ bác thẳng cả tiền đề: *"đã làm social media thì làm gì có
chuyện bị giới hạn ở nguồn tư liệu"*, và chỉ ra hai bảng đó *"một bảng là top
model tạo sinh, một bảng là top model chỉnh sửa, đâu có trùng lặp"* — tức
không có lý do tự giới hạn khi hai nguồn không hề overlap.

Sửa: `xep_hang.tim_va_chup_nhieu()` (hàm mới, **không sửa** `tim_va_chup()` cũ —
`_xep_hang_boi_canh` trong `anh_chuan_bi.py` và CLI `main()` vẫn gọi bản cũ,
đợi đúng MỘT dict) đọc cờ `doc_lap: True` gắn ngay tại khai báo NGUON của
`arena-t2i`/`arena-image-edit`: nguồn "độc lập" (đo năng lực riêng) không bao
giờ bị một thành công khác chặn lại; nguồn "thường" (4 biến thể đo cùng một
năng lực code — arena-code/swebench/aider/livecodebench) vẫn dừng ở thành công
đầu tiên như cũ, lấy thêm chỉ lặp lại bằng chứng. Luật chọn nằm trọn trong một
hàm thuần `_bo_qua_nguon(n, da_chup_thuong)`, tách riêng để test không cần
Playwright (không cài được trong môi trường này để mock trình duyệt thật).

`anh_chuan_bi.py` đổi `xh` (dict|None) → `xhs` (list, có thể rỗng) xuyên suốt
`_chup_xep_hang` → `_gom_va_tai_anh` → `dung_manifest`; mỗi bảng chụp được
mang mã riêng (`XH`, `XH2`...) qua `_anh_muc_xep_hang()` (hàm thuần, tách để
test không phải chạy `_gom_va_tai_anh` — hàm đó gọi mạng thật nên test trực
tiếp treo/timeout). `dung_manifest` nhận cả `None` (quy ước cũ, hai test có
sẵn của tính năng ảnh thương hiệu truyền `None` ở vị trí này) lẫn `[]` — không
đổi hành vi cho mọi tin chỉ có một bảng. `m["xep_hang"]` (bảng ĐẦU TIÊN, dùng
bởi cổng chặn `can_anh_xep_hang`) và mọi gate hiện có không đổi hợp đồng; thêm
`m["so_xep_hang"]` để `dong_brief_xep_hang` nói rõ cho vai biết có mã `XH2` khi
có, tránh bỏ phí tấm thứ hai vì brief không nhắc tới nó.

Không đổi những gì các file khác (đang sửa `anh_thuong_hieu.py`/
`anh_khai_niem.py` cùng lúc) không nhắc tới: mỗi ảnh xếp hạng vẫn mang
`"xep_hang": xh` của riêng nó nên mọi cổng đọc PER-IMAGE (`dre_nop.py`,
`ethan_nop.py`, `ethan_chuan_bi.py`) coi XH2 y hệt XH, không cần sửa gì.

---

## Nút "hạ sàn" hết đường thì gỡ luôn bàn phím (09/09/2026)

Ông Chủ bấm "🖼 Dre làm với 4 ảnh" (imgtiep) trên một tin chỉ có 4/8 ảnh thật.
Engine trả lời đúng: *"Chỉ 4 ảnh thật mà carousel cần tối thiểu 5 slide — bấm
tiếp cũng không dựng được. Chuyển Kite vẽ vector, hoặc bỏ tin."* — nhưng **gỡ
luôn bàn phím ngay sau đó**. Hai đường vừa nêu không còn nút nào bấm được nữa;
Ông Chủ phải tự gõ lệnh.

Nguyên nhân: `_chot_nut()` (đuôi chung của mọi nút duyệt ảnh trong
`duyet_bai.py`) gỡ bàn phím **vô điều kiện**, không phân biệt "tương tác đã kết
thúc" (đã tạo task, đã ghi quyết định) với "vẫn còn đường phải chọn tiếp".
`_nut_ha_san()` — xử lý imgtiep — có ba nhánh: hạ sàn thành công (kết thúc),
sàn đã ở mức tối thiểu (kết thúc), và **hết đường vì số ảnh thật còn dưới cả
sàn cứng** `carousel.MIN_SLIDE` — nhánh cuối này KHÔNG kết thúc, nó đang hỏi
tiếp, nhưng trả về y hệt hai nhánh kia (chỉ một chuỗi `note`) nên `_chot_nut`
không có cách nào biết mà giữ bàn phím lại.

**Sửa:** `_nut_ha_san()` giờ trả `(note, keyboard)`; nhánh hết đường build lại
bàn phím "🎨 Gửi Kite vẽ vector" + "❌ Bỏ hẳn tin" (bỏ nút Kite nếu brand chưa
có Kite — cùng nguyên tắc "không hứa suông" đã áp cho nhánh `khong_kite` của
`anh_chuan_bi._route_thieu_anh`). `_chot_nut()` nhận thêm tham số `keyboard`
tuỳ chọn: có thì gắn lại đúng bàn phím đó, không thì gỡ trắng như cũ — mọi nút
khác (imgok/imgno/imgkite/imgredo) không đổi hành vi.

---

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

## Nova: 12 bảng → 23 bảng (06/09/2026)

Trích nguyên văn từ mục `scan_models.py` của README cũ.

**06/09/2026 — 12 bảng → 23 bảng.** Khảo sát 16 nguồn ứng viên, mỗi kết luận
"lấy được" bị một lần fetch độc lập phản biện. Ba nhóm thay đổi:

1. *Sửa chỗ tràn trước đã.* Ở trạng thái production (arena sống + có mốc cũ)
   báo cáo ra **13.635 ký tự** trong khi brief cắt ở 12.000 — `LIVEBENCH` và
   `OPENROUTER USAGE` bị nuốt **câm lặng**, Nova không biết hai bảng đó tồn
   tại. Ba mục `MODEL MOI`, trích benchmark, `ENGINE SUY LUAN` trước đó không
   có cận trên. Nay có `TRAN_*`, trần brief lên 22.000, và `_cat()` nói rõ khi
   đã cắt. Thêm nguồn trước khi vá chỗ này là làm phủ sóng **tệ đi**.
2. *Số đã tải về mà chưa dùng.* `agenticIndex` nằm sẵn trong payload AA từ lâu
   nhưng chưa bao giờ được dựng bảng → `so_hang()` mù với "leo hạng agentic"
   (cùng loại sự cố qwen3.8-max WebDev 02/09). SWE-bench trả 5 split trong
   **một** request, ta chỉ dùng `Verified`. Cả hai không tốn thêm request nào.
3. *Chiều thật sự mới* — `tbench` (agent gõ lệnh trong container), `arcagi`
   (bài chưa từng thấy), `hle` (trần kiến thức), `eci` (Epoch, có khoảng tin
   cậy), `opencompass` (đề đóng, phần lớn lab TQ), `tts`/`stt`/`i2v` (mảng
   không phải văn bản — trước đây mù hẳn), `hf_trending` (bắt model thả trọng
   số trước router 1–3 ngày).

**Bảng bị loại và lý do** — không phải vì lấy không được, cả 5 đều lấy được:
BFCL đóng băng từ 13/04/2026, LiveCodeBench từ 01/08/2025, Aider Polyglot từ
03/10/2025, BigCodeBench từ 16/04/2025, Papers With Code đã đóng cửa. Thêm
bảng chết vào script quét = mỗi lần chạy tốn một request để nhận `diff = 0`
vĩnh viễn. Vellum bị loại vì tự nó ghi là trang **tổng hợp** lại số của người
khác; GAIA vì nó xếp hạng **hệ thống agent** chứ không phải model (cột model
là chuỗi viết tay, không join được). SWE-bench `Lite`/`Full`/`Multimodal` đều
quá hạn nên chỉ lấy `Verified` + `Multilingual`.

Nợ kỹ thuật đã biết: `TBENCH` là edge function moi từ bundle JS của tbench.ai,
không phải API công bố — đổi project ref là chết im, cần theo dõi. `ids` trong
`models_seen.json` chỉ tăng, chưa có cơ chế cắt tỉa (~40 byte/model/ngày).

`fetch_opencompass` chập chờn (máy chủ ở TQ, hỏng kiểu `ConnectTimeout` /
`SSL: UNEXPECTED_EOF` chứ không phải bị chặn) nên có retry 2 lần; đo 06/09 từ
server thì một lượt hỏng cả 2 lần, lượt sau sạch. **Đường lui nếu nó tệ đi**:
CDN tĩnh `https://cdn.opencompass.org.cn/assets/llm-rank/<fileName>.json`
nhanh và ổn hơn hẳn (1,7s so với 6,5s), schema là `OverallTable`/`Knowledge`/
`Reason`/`Math`/`CodeTable`. Chưa dùng vì `<fileName>` xoay theo quý và chỉ
API kia mới cho biết tên — muốn chuyển thì phải nhớ tên tệp vào state và chỉ
gọi API khi CDN trả 404. Chưa làm: đổi một nguồn đang chạy được lấy thêm một
chỗ để hỏng thì không lời.

---

## Model từng vai

**Chuỗi đang chạy** (nguồn sự thật: `~/.hermes-<brand>/profiles/*/config.yaml`
— mỗi container một home riêng từ khi tách brand, không còn `~/.hermes` gộp
chung). Đo lại 04/09/2026, theo brand:

| Vai | donniechublog | dcgr.tech | Suy luận |
|---|---|---|---|
| Ada (analyst) | `ds/deepseek-reasoner` | `ds/deepseek-reasoner` | **bật** — vai duy nhất, việc đối chiếu điểm chấm cần suy luận thật |
| Bob | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | **medium** |
| Ethan (designer) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Dre (carousel) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Kite (carousel-edu) | `ds/deepseek-v4-flash` | — (chưa deploy *lúc đo 04/09*; dcgr deploy 05/09) | tắt |
| Gin / Itachi | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Nova / Vera (market) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Finn (scout) | `ds/deepseek-v4-flash` | — (dcgr chỉ có Vera) | tắt |
| Jean (teaser) | `ds/deepseek-v4-flash` | — (blog only) | tắt |
| Miles (writer) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |

Dự phòng của mọi vai (trừ Ada): `v4flash@api.b.ai → ds/deepseek-chat` (xem
mục Provider). Gin chạy việc thật **trên server** (torch+cpu cài từ 28/08/2026,
xem skill `inplace-translate`) — không còn phụ thuộc máy local. Kite ĐÃ DEPLOY
(2026-09-01), generator `render_edu.py` chạy live trên server.

**Đã thử glm-5.3 rồi hạ lại 04/09/2026:** Finn/Jean/Miles bên donniechublog và
Ethan bên dcgr.tech từng chạy chính bằng `xk/z-ai/glm-5.3`, kết quả một đợt A/B
chỉnh trực tiếp trên server ngày 01/09/2026 — không đi qua git nên không có
commit nào ghi lại lý do chọn. Audit 04/09 đo bằng `usage_audit.py`: glm-5.3 tốn
**$0,416 / 20 request** (~$0,0208/req) so với v4-flash **$0,0997 / 204 request**
(~$0,0005/req trong cùng cửa sổ) — đắt hơn khoảng **40 lần mỗi request** mà
không có bảng audition nào chứng minh bù lại được bằng chất lượng, nên cả bốn
vai đã hạ về `ds/deepseek-v4-flash` cùng ngày. Bản config trước khi hạ được giữ
ở `profiles/<vai>/config.yaml.bak-truoc-doi-v4flash-0904` trong từng home,
phòng khi cần so lại hoặc thử lại có kiểm soát hơn.

Đo bằng `cost_squeeze.py`, chạy lặp trên việc thật, chấm bằng code:

| Vai | Model | Trượt | USD/1000 lần |
|---|---|---|---|
| teaser | **deepseek-chat** | **0/5** | **0,77** |
| teaser | mimo-v2.5-pro | 1/5 (lan man 2417 từ) | 0,83 |
| teaser | v4-flash | 1/5 (rỗng) | 1,11 |
| teaser | v4-pro | 2/5 (rỗng, mất dấu) | 3,83 |
| writer | deepseek-chat | 0/6 | 0,06 |
| writer | v4-pro | 0/6 | 0,14 |

Gemini đã gỡ khỏi mọi chuỗi: trên số liệu usage thật nó tốn 1,72 USD/1M input
còn v4-flash chỉ 0,04 — **đắt gấp 44 lần**, vì cột cached của gemini trống rỗng,
không cache nổi một token. Kimi K3 đắt gấp 14 lần v4-pro và mọi tuyến Kimi đều
báo `thinkingCanDisable: false` — không tắt suy luận được.


---

## Hai nguyên tắc bắt buộc khi dùng nhiều model

**1. Bắt buộc phải có giám sát model.** Hermes fallback im lặng hoàn toàn — đặt
model chính thành model chết, agent vẫn trả lời bình thường, không một dòng báo.
Cần cả hai lớp: `model_watch.py` (model còn sống không) và `theo_doi_9router.py`
(model nào **thật sự** được gọi).

**2. Ghim mỗi hội thoại vào một model. Chuyển tầng thì chuyển ở ranh giới task.**
`try_activate_fallback` đổi model ngay giữa lượt, `restore_primary_runtime` lật
về model chính ở lượt sau — một hội thoại có thể chạy qua 2–3 model mà không ai
biết. Cache là per-model, mỗi lần lật là mất sạch prefix đã cache và cả ngữ cảnh
bị tính lại giá gốc. Cột `cache%` trong nhật ký ngày của `theo_doi_9router.py` chính là thước đo
nguyên tắc này: tụt cache nghĩa là đang lật model.

**Đã bắt được một nguyên nhân lật cụ thể (cron 05/09/2026, cả Finn/Nova/Vera):**
bước phụ `title_generation` (Hermes tự đặt tên phiên) gửi `response_format` mà
DeepSeek v4-flash trả `400 This response_format type is unavailable now`; 9router
coi đó là lỗi provider và đưa `deepseek/deepseek-v4-flash` vào cooldown ~30s
(`reset after 28s`); hai lần retry của vòng chính (cách 2–3s) rơi trọn trong
cooldown → `Fallback activated: v4-flash → deepseek-chat`, dính tới hết phiên
(1 call v4-flash rồi 11–24 call deepseek-chat). Dòng log nằm ở
`profiles/<vai>/logs/agent.log`, **không** có trong `logs/gateway.log`. Đếm
19/08–04/09: lỗi này 5–48 lần/ngày, fallback 4–33 lần/ngày. Chặn bằng
`auxiliary.title_generation.enabled: false` trong `config.yaml` từng profile:
script `tat_title_generation.py` (đã chạy xong và xoá khỏi repo 05/09, xem git log; quay lại
bằng tệp `.bak-truoc-tat-title-0905` trong từng profile); tiêu đề phiên vô dụng với task kanban/cron.

**Từ 05/09/2026 model chính là combo `DS-v4Flash` của 9router** (đổi bằng script
`doi_model_combo.py`, đã chạy xong và xoá khỏi repo cùng `bo_fallback_chat.py`; quay lại bằng
`.bak-truoc-doi-combo-0905` / `.bak-truoc-bo-fallback-chat-0905`; analyst giữ `ds/deepseek-reasoner`).
9router chỉ xoay giữa các connection *cùng* provider; ba route v4-flash (deepseek trực
tiếp `ds/`, xKiro `dsx/deepseek/deepseek-v4-flash`, aellm `dsa/deepseek-v4-flash`) chỉ
nối được với nhau qua Combo, gọi bằng đúng tên combo làm model (không có prefix
`combo/`). Trước đó cả ba node đều đặt prefix `ds` nên hai node ngoài bị che, 7 ngày
0 request. Đo route thật bằng `usageHistory.provider` của 9router; Hermes chỉ thấy
model `DS-v4Flash`. Combo còn chứa mục chết (`ds/ds/…`, `tokenrouter/…` không có
credential, `oc/…-free` unavailable) và chưa có `dsa/`: dọn trên dashboard.

**dcgr chạy chat theo bot mode chuẩn của Hermes từ 05/09/2026 (thí điểm, blog giữ
chat_router để so ~1 tuần).** Gateway dcgr: `multiplex_profiles: true`, 8 `profile_routes`
theo thread_id, bot riêng @hermesdcgr_bot; approve dcgr vẫn dùng @hermesmodebot cho chọn
số/Duyệt/Làm lại, chỉ nhường phần chat qua cờ `CT_CHAT_QUA_GATEWAY=1` đặt trong drop-in
`~/.config/systemd/user/hermes-approve@dcgr.service.d/override.conf` (unit template dùng
chung, blog không có cờ). Mỗi profile cần `profiles/<vai>/.env` với `OPENAI_API_KEY` +
`TELEGRAM_ALLOWED_USERS` (multiplex fail-closed, không fallback `.env` gốc) nhưng
**KHÔNG** được chứa `TELEGRAM_BOT_TOKEN`/`TELEGRAM_HOME_CHANNEL`: `backfill_profile_envs`
của Hermes chép cả token → gateway từ chối 8 profile vì "same credential" (đã gặp 05/09,
phải xoá dòng token khỏi 8 tệp). Đo bằng journal `hermes-gateway@dcgr` + `logs/gateway.log`
(INFO không vào journal) so với approve.log blog: độ trễ, mất mạch, 429/timeout. Nhận xét
đầu: reply qua gateway ngắn và không biết tình trạng task kanban như approve.
Bản chụp config + drop-in + mẫu .env để tái tạo: `hermes/gateway/dcgr/` (xem DOC.md ở đó).


---

## Provider

Mọi vai trừ Ada chạy chính bằng `ds/deepseek-v4-flash` trên connection DeepSeek
gốc, dự phòng là `v4flash` của
provider mới (connection `openai-compatible-chat-ba685909…`, baseUrl `api.b.ai`)
rồi `ds/deepseek-chat`. Ada giữ `ds/deepseek-reasoner` vì provider mới không có.

**Provider mới từng là tuyến chính, đã hạ xuống dự phòng ngày 25/08** khi nó trả
429 hết quota suốt nhiều giờ. Dây chuyền không gãy vì dự phòng gánh được, nhưng
chạy dài ngày ở tuyến dự phòng là mất sạch cache per-model mà không ai đo được
(xem điểm mù bên dưới), nên đảo hẳn thứ tự thay vì để nguyên.

Provider mới **chỉ phục vụ `deepseek-v4-flash`** và bản vision — `deepseek-v4-pro`
trả 403, `deepseek-chat` và `deepseek-reasoner` trả 404.

**Điểm mù cần nhớ: 9router KHÔNG ghi log connection này.** Đo thật: gọi thẳng 5
lượt, số bản ghi trong `usageHistory` đứng yên. Nghĩa là `usage_audit.py` và bảng
usage của 9router không thấy chi phí chạy qua đây. Muốn đo phải dùng
`hermes --usage-file`.

Nhưng `--usage-file` cũng có bẫy: nó ghi model được **cấu hình**, không phải model
**thực chạy**. Đã bắt được một lần Miles lặng lẽ tụt xuống `ds/deepseek-v4-pro`
mà tệp usage vẫn khai là đang chạy provider mới — chỉ lộ ra khi đối chiếu với log
9router.

**Điểm mù thứ hai: cả hai brand dùng CHUNG một instance 9router cục bộ**
(`http://127.0.0.1:20128/v1` trong cả hai `config.yaml`), và trong log
`usageHistory` cả hai brand hiện ra đúng **một** `apiKey` duy nhất. `usage_audit.py`
có sẵn cờ `--api-key` để tách theo client, nhưng vô dụng ở trạng thái hiện tại vì
chỉ có một khoá — nên báo cáo usage-audit của blog và dcgr luôn ra **cùng một
con số tổng**, không tách được brand nào tốn bao nhiêu.

**Đã tách 05/09/2026:** 9router có hai khoá `hermes blog` và `hermes dcgr` (bảng
`apiKeys`); khoá vào Hermes qua `OPENAI_API_KEY` trong `~/.hermes-<brand>/.env`
(config.yaml chỉ ghi `${OPENAI_API_KEY}`). **Nhưng** dcgr chạy multiplex nên 8
`profiles/<vai>/.env` cũng có `OPENAI_API_KEY`, và Hermes nạp `.env` của profile với
`override=True` (`hermes_cli/env_loader.py`) → khoá trong profile **đè** khoá gốc. Lúc
05/09 12:55 chỉ `.env` gốc mang khoá `hermes dcgr`, 8 profile vẫn mang khoá `hermes blog`
→ 9router ghi 181/182 request dcgr vào khoá blog, tách mà như chưa tách. Đổi khoá cho
dcgr = sửa `.env` gốc **và** cả 8 `profiles/*/.env` (blog không có profile .env nên chỉ
một dòng), rồi restart gateway brand đó. Từ đó `theo_doi_9router.py` tự tách req/$ theo
brand ở mục "theo khoá API" (đọc tên khoá từ bảng `apiKeys`, không cần sửa code).

**Điểm mù thứ ba: 9router KHÔNG ghi IP máy gọi.** `usageHistory` không có cột IP,
`meta` luôn `{}`; `custom-server.js` có tính `x-9r-real-ip` nhưng chỉ dùng cho
rate-limit. Service đang bind `0.0.0.0` (LAN 192.168.1.61 + netbird) nên ai trong
mạng cũng gọi được bằng khoá chung. Watcher socket `--canh` (đọc bảng TCP mỗi 2s,
ghi IP theo kết nối) đo 05/09 sáng rồi **bỏ 05/09 chiều**: nó chỉ thấy kết nối,
không thấy request (httpx keep-alive chở nhiều request một kết nối), và cách đúng
là bind 9router về `127.0.0.1` hoặc địa chỉ netbird rồi cấp khoá riêng cho từng
máy (mục "theo khoá API" tự tách). Nhật ký ngày `9router_<ngày>.md` cột "đổi model
liên tiếp" chỉ tin cặp v4-flash→deepseek-chat là fallback thật,

Token burn đo được cho một luồng trọn vẹn (Finn quét → vai ảnh dựng → vai viết,
17 lượt gọi): **~398.000 token chạm model**, cache 36%, 227 giây, ước $0,038.


---

## Bài học một tuần config 9router không chuẩn (29/08–05/09/2026)

1. **Hai chuỗi dự phòng chồng nhau, không ai nhìn cả hai.** Combo của 9router và
   `fallback_providers` của Hermes là hai cơ chế độc lập. Tắt deepseek-chat trên 9router
   xong vẫn thấy nó trong log vì 19 config Hermes còn giữ nó làm dự phòng. Quy tắc: đổi
   model là phải sửa CẢ HAI chỗ, kiểm bằng `grep deepseek-chat ~/.hermes-*/**/config.yaml`.
2. **Một route chết trong combo kéo cả chuỗi lật.** xKiro trả 404 "model does not exist"
   từ 06:34 05/09 mà vẫn nằm trong combo → combo lỗi định kỳ → Hermes fallback. Trước khi
   thêm route vào combo phải gọi thử; snapshot connection lỗi trong nhật ký ngày để bắt.
3. **Bước phụ làm lật model chính.** `title_generation` gửi `response_format`, v4-flash trả
   400, 9router cooldown 30s, 2 retry của Hermes rơi đúng cooldown → cả phiên chạy
   deepseek-chat. Mọi bước phụ (title, summary, vision) phải cùng model hoặc tắt hẳn.
4. **9router chỉ xoay connection cùng provider.** Ba route v4-flash khác provider chỉ nối
   được qua Combo; gọi bằng đúng tên combo, không có tiền tố `combo/`. Prefix trùng
   (`ds`) từng che mất hai node ngoài.
5. **Tên model lệch ba kiểu.** Hermes ghi `ds/deepseek-v4-flash`, `DS-v4Flash`,
   `DeepSeek-V4-Flash`; 9router ghi `deepseek-v4-flash`, `deepseek/deepseek-v4-flash`.
   Mọi script đối chiếu phải chuẩn hoá (bỏ tiền tố nhà cung cấp, không phân biệt hoa
   thường, resolve combo qua bảng `combos`), không so chuỗi thô.
6. **Nhìn số gộp thì không thấy gì.** usage_audit in một bảng N giờ rồi quên; glm-5.3 đắt
   40x/request ăn 70% tiền suốt nhiều ngày mà README vẫn nói v4-flash. Phải có nhật ký
   theo ngày, $ theo vai, $/bài, và đọc config thật trên server chứ không tin README.
7. **Hạ tầng dùng chung thì không tách được ai tốn gì.** Một 9router, một apiKey cho hai
   brand, bind 0.0.0.0 không ghi IP. Muốn tách brand cần khoá riêng; muốn biết máy nào
   gọi phải tự bắt ở socket. Đừng để mặc định của công cụ quyết định độ quan sát.

8. **Cache là của từng nhà cung cấp, không phải của model.** Cùng v4-flash, qua DeepSeek
   trực tiếp cache 93–96%, qua aellm (bán lại) 49% → đắt ~7x mỗi token prompt. Combo phải
   xếp DeepSeek trực tiếp TRƯỚC, reseller chỉ để dự phòng; và đừng để hết credit (402 hôm
   05/09 đẩy cả ngày sang aellm).
9. **System prompt đổi mỗi task vì một dòng.** Hermes in `Current working directory:` vào
   giữa prompt; workspace `scratch` tạo thư mục mới mỗi task nên 37% cuối prompt (skills,
   memory) không bao giờ trúng cache giữa hai task. Đo 05/09: hai task carousel cách 5 phút
   chỉ khác đúng dòng đó. Sửa: `approve_service.kanban_create` tạo task với
   `--workspace dir:~/.hermes-<brand>/kanban/workspaces/co-dinh`. Còn lại trong prompt chỉ
   đổi theo ngày (`Conversation started`) và theo model (`Model:`) — thêm lý do ghim model.
   Sửa SOUL cũng làm cache về 0 cho vai đó, gom sửa thành đợt. Chạy thử từ `~/hermes-agent`
   thì bị nhét cả AGENTS.md của Hermes (prompt 115k ký tự) — chỉ thử từ `~/content-team`.

Trạng thái sau khi sửa (05/09): combo = [ds trực tiếp, dsx xKiro, dsa aellm], 19 profile dự
phòng `ds/deepseek-v4-flash`, title_generation tắt, nhật ký ngày + web + tin 6h đã chạy.
Chỉ tiêu: fallback = 0 từ 06/09; sai thì trang chi tiết chỉ ra route nào.


---

## Suy luận (reasoning) — số đo


Lý do: model deepseek đốt hết ngân sách token vào suy luận rồi trả về **rỗng**.
Đo thật trên v4-pro: 3/24 lần (2/8 ở `max_tokens=800`, 1/8 ở 1200, 0/8 ở 2000).
Tái hiện y hệt trên v4-flash. Lỗi phụ thuộc ngân sách nên im lặng và ngắt quãng —
loại tệ nhất. Tắt suy luận: 0/24 lần rỗng, nhanh gấp 3, rẻ hơn, chữ vẫn đủ dấu.

Đã thử model rẻ hơn cho Jean (`ds/deepseek-chat`, `ds/deepseek-v4-flash`): chữ
vẫn tốt nhưng **lệch giọng** — viết kiểu tường thuật "bài viết nói rằng..." thay
vì giọng mời đọc. Chênh lệch giá chỉ 0,0026 USD/teaser nên không đáng đổi.

Kimi K3 đậu audition nhưng **đắt gấp 14 lần** v4-pro và mọi tuyến Kimi đều báo
`thinkingCanDisable: false` — không tắt suy luận được. Không dùng.

---

## Thiết kế thẻ kiểu `dai` (bỏ khỏi mã 05/09/2026)

Giữ lại làm **tham chiếu thiết kế**, không phải mô tả hiện trạng: không vai nào
dùng kiểu này nữa và `card.py` không còn nhánh nào cho nó. Trước đây nằm trong
`STYLE_TEXT_SPEC.md` và làm tệp đó tự mâu thuẫn với chính mã.

## Hệ chữ — kiểu `dai` (đã bỏ khỏi mã 05/09/2026, giữ lại làm tham chiếu thiết kế)
| Vai trò | Font | Cỡ | Kiểu |
|---|---|---|---|
| Tiêu đề | JetBrains Mono ExtraBold | 38–104px (tự nở theo chỗ trống) | IN HOA toàn bộ, đơn cách |
| Subtitle | Noto Serif | 20–50px | chữ thường, có dấu, serif |
| Chip nhãn | JetBrains Mono Bold | 26px | IN HOA |
| Via | Inter weight 500 | 29px | chữ thường |
| Tên kênh | Inter weight 500 | 27px | chữ thường |

## Bố cục kiểu `dai` — đã bỏ khỏi mã 05/09/2026, tham chiếu thiết kế (1200px ngang)
1. Vùng ảnh nguồn trên cùng — ảnh thật, không chèn chữ đè lên (trừ mascot nếu còn góc trống).
2. Khung kỹ thuật: 4 góc vát — 2 góc trên cyan, 2 góc dưới trắng; 2 đường dọc đôi; đường chia ngắt quãng ngay ranh giới ảnh/text.
3. Chip category trái: nền đặc cyan, chữ đen, đè lên ranh giới ảnh/textbox, có 2 tam giác gấp xuống phải (kiểu ruy-băng).
4. Chip category phải: nền trong suốt, viền cyan, chữ trắng, gấp lên.
5. Tiêu đề: căn trái, tối đa 2 dòng, trắng FG.
6. Subtitle: căn trái, tối đa 3 dòng, màu xám nhạt (donniechublog) hoặc trắng 95% (dcgr).
7. Chân thẻ: `via: <nguồn>` trái, màu cyan mờ; hàng icon social + @handle phải, icon mờ hơn chữ.

## Bố cục kiểu `dai` — đã bỏ khỏi mã 05/09/2026, tham chiếu thiết kế (1200px ngang)
1. Vùng ảnh nguồn trên cùng — ảnh thật, không chèn chữ đè lên (trừ mascot nếu còn góc trống).
2. Khung kỹ thuật: 4 góc vát — 2 góc trên cyan, 2 góc dưới trắng; 2 đường dọc đôi; đường chia ngắt quãng ngay ranh giới ảnh/text.
3. Chip category trái: nền đặc cyan, chữ đen, đè lên ranh giới ảnh/textbox, có 2 tam giác gấp xuống phải (kiểu ruy-băng).
4. Chip category phải: nền trong suốt, viền cyan, chữ trắng, gấp lên.
5. Tiêu đề: căn trái, tối đa 2 dòng, trắng FG.
6. Subtitle: căn trái, tối đa 3 dòng, màu xám nhạt (donniechublog) hoặc trắng 95% (dcgr).
7. Chân thẻ: `via: <nguồn>` trái, màu cyan mờ; hàng icon social + @handle phải, icon mờ hơn chữ.

---

## Thẻ "#3 bảng văn bản" đi kèm ảnh khoanh #26, và 50 phút Ethan "không phản hồi" (12/09/2026)

Ticket theo dõi: LOW-22, LOW-23, LOW-26 (con: LOW-24, LOW-25, LOW-27, LOW-28).

Ông Chủ gửi thẻ Ethan (task `t_d3ae2109`): hook *"claude-opus-4-7-high leo lên #3
bảng văn bản Arena, chốt 1501.8 điểm Elo"*, ảnh nền khoanh vàng hàng **#26**, 1555.
Hỏi: *"lý do gì tiêu đề là #3 mà hình minh hoạ lại chụp #26"*. Rồi ảnh Telegram:
*"⚠️ Ethan không phản hồi hơn 20 phút"* trên task trước đó (`t_24b214a6`).

**Thẻ arena (LOW-22).** Cả hai số đều đúng — của hai bảng khác nhau. Đo từ payload
arena.ai cùng ngày: bảng text #3 / 1501.79 (`round(,1)` = 1501.8 của
`scan_models._arena_board`), bảng code #26 / 1555.2 / spread 23–29 — khớp ảnh
từng con số. Chạy lại `tim_va_chup_nhieu` với đúng đầu vào tái hiện **y hệt tấm
ảnh**: `arena-code: khớp … hàng #26`. Nguyên nhân: `CHU_DE` có mục code mà không
có mục text, một chữ "code" trong 1500 ký tự đầu bài gốc đủ đẩy arena-code
(999+500+200) lên trên arena-text (1000+500); `_bo_qua_nguon` rồi bỏ luôn bảng
text. Cảnh báo "ĐÂY LÀ BẢNG KHÁC" trong `cau_xep_hang` không nổ vì `duoc_nhac`
so theo **tên miền** — bảy bảng arena chung một miền, có link arena.ai là cả bảy
đều "được nhắc". Không cổng nào so `#3` trong hook với `xep_hang["hang"]=26`;
brief có in "#26 / WebDev / Code Arena" nhưng chỉ là chữ, và `can_anh_xep_hang`
thì *ép* dùng ảnh đó. Sửa: mục `CHU_DE` cho text; `bang_re` theo từng bảng arena,
`duoc_nhac` đòi khớp bảng trong tiêu đề/link/via (không đọc thân bài). Đo lại:
`arena-text: khớp … hàng #3`. Cổng cứng so hạng hook↔ảnh để LOW-24.

**"Không phản hồi" (LOW-23).** Đọc kanban.db trên máy chủ (`ssh
donniechu-01.netbird.mated`, python `mode=ro` — sqlite3 CLI của macOS không mở
được URI, `-readonly` hỏng vì WAL): hai run 25.1 phút đều `timed_out` (1502s >
1500s), rồi `gave_up` → blocked; `task_events` có **heartbeat mỗi ~60s suốt cả
hai run**. Câu cảnh báo tính từ `tasks.started_at` — mốc lần ĐẦU, hermes không
bao giờ reset (`COALESCE(started_at, ?)`, chính bộ quét timeout của hermes ghi
"runtime is per attempt, not lifetime-of-task"); `_COT_VIEC` không SELECT
`last_heartbeat_at`/`worker_pid`. Hai lần bị giết im lặng vì vòng tiến độ bỏ qua
`ready`. Sửa: đo theo run đang mở (`moc_lan_chay`), đọc nhịp thở/pid (`nhip_tho`,
`pid_song`), ba câu khác nhau cho chết / im lặng / đang làm, và một dòng ⏱ mỗi
run `timed_out`. Test cũ không bắt được vì cả bốn test đặt `bat_dau_luc` như mốc
của lần chạy hiện tại — mã hoá đúng cái hiểu sai.

**Nguyên nhân thật của 50 phút (LOW-26).** Log run: `ethan_chuan_bi.py` được gọi
~16 lần, 3 lần `exit 139` (SIGSEGV), 1 lần `exit 124` vì đợi khoá `dang_chay.pid`
tròn 300s = trần bash tool của vai. Ethan tự `ps -p` thấy pid chết, tự `rm -f`,
tự viết `faulthandler` — vai chẩn đoán đúng, chỉ không có quyền dừng. Đẩy vào:
router vision 503 cả 8 ảnh (2/119 draft). Sửa: tách `_doi_khoa` (khoá mồ côi
dọn ngay + nói ra; `CHO_KHOA_GIAY=60`), `faulthandler.enable()` ở engine. Truy
chỗ segfault để LOW-27; cổng "engine chết N lần thì vai dừng" để LOW-28. Thẻ
arena `t_d3ae2109` chờ 50 phút sau task chết rồi xong trong 52 giây.

Bài học: (1) một câu cảnh báo phải nói đúng cái nó đo — "không phản hồi" trong
khi DB có nhịp thở mỗi phút là nói sai, không phải đo thô; (2) giả thuyết đọc từ
code (`_cho_luot`) bị số liệu máy chủ bác — ghi vào ticket cả cái bị bác; (3) hai
hẹn giờ bằng nhau (300s/300s) thì cái ngoài luôn thắng, đường xử lý phía sau
không bao giờ được chạm tới.

**Bổ sung cùng ngày (LOW-24/25/27/28).** Truy segfault bằng `faulthandler` trên máy
chủ: chết tại `luat_anh.dem_mat → det.detect()`; chạy từng ảnh trong tiến trình
riêng thì 7/8 ok, **A2.png 9440×5310 chết `-11` kể cả một mình** — YuNet không
chịu ảnh 50 MP, vision 503 chỉ trùng thời điểm. Vá: thu về `MAT_CANH_MAX=1600`
trước khi dò; chạy lại đúng draft: `exit 139` → `exit 0` + `xong.json`. Kèm:
cổng `kiem_hang_tren_the` (hạng trên thẻ = hạng trong ảnh, Ethan + Dre),
`max_runtime` 40m cho vai ảnh (đo p95 dre/kite ≈ 23 phút), `_cho_luot` có trần
240s + báo 30s, và engine tự dừng + báo Telegram khi chết bất thường 2 lần liên
tiếp (`so_lan_chet.json`). Deploy: push `origin` (= máy chủ, `updateInstead`),
restart `hermes-approve@blog/@dcgr`.

---

## Thẻ DeepSeek-V4.1-Flash ra ảnh con vịt-robot: "báo khác" khớp nhầm bằng tên site (12/09/2026)

Ticket theo dõi: LOW-33 (con: LOW-34).

Ông Chủ: *"tin về Deepseek mà ko vào trang chủ Deepseek lấy hình… lại dùng cái
hình ở hành tinh nào? rule tìm ảnh của bạn là gì vậy?"* Bìa Ethan chọn là `A13`,
`tu: chup_nguon`, nhãn *"ảnh hero của chính bài gốc"* — nhưng URL là
`therundown.ai/articles/hugging-face-robot-duck-is-already-a-hit`, bài về con
vịt-robot ở booth Hugging Face.

Ba lớp, mỗi lớp tự nó vô hại: (1) `nguon_bai._tieu_de_trang` bóc hậu tố site
bằng `[|\-–—]`, HF dùng `·` nên `tieu_de_en` = *"deepseek-ai/DeepSeek-V4.1-Flash
· Hugging Face"* — đúng 4 từ, vừa lọt cổng "<4 từ" sinh ra từ vụ "Tech in Asia"
06/09; (2) `bao_khac_bing` coi "cùng tin" = chung ≥2 từ đặc trưng, "hugging"+
"face" tự đủ → Bing trả bài vịt-robot thành "báo khác"; (3) `_vong_chup_nguon`
lấy tấm ĐẦU TIÊN chụp được trong `[link]+trang`, HF không chụp được lead nên rơi
xuống bài vịt-robot, rồi gán `lien_quan = True` không hỏi vision, không so tít.
Sửa: `bo_hau_to_site` (thêm `·`, `»`), `_TU_NEN` loại tên nền tảng khỏi từ đặc
trưng, một hàm `cung_tin` dùng cho cả Bing lẫn vòng chụp; `chup_lead_mobile` trả
`tit_trang` để đối chiếu. Bài gốc (`link`) vẫn được tin.

Bài học: bốn nguồn ảnh tôi kể cho Ông Chủ đều đúng — nhưng cả bốn ngầm tin
danh sách `trang` là sạch. "Đây là trang của CHÍNH tin, hỏi liên quan làm gì"
là một giả định, không phải một sự thật; giả định phải có cổng.
