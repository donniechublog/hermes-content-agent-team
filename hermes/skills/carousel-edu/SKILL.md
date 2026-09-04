---
name: carousel-edu
description: "Carousel EDU — diễn đạt lại kiến thức & nghiên cứu (paper arXiv, kinh nghiệm dev) cho chuyên nghiệp, tường minh; phong cách tech × magazine bằng ART VECTOR GỐC tự vẽ — không đi tìm ảnh minh hoạ, không nền AI, nhưng biểu đồ/bảng/trang báo cáo CÓ SẴN thì chèn bản thật trải hết bề ngang slide (kind figure). Hệ thiết kế: nền tối #0A0B0E, duotone cyan #2FD4E1 x tím #8E86F0, font Archivo (display) + Newsreader italic (standfirst) + JetBrains Mono (nhãn/số), bộ khung magazine (masthead chạy đầu, eyebrow chuyên mục, hairline, folio số trang, byline) và một hero art vector trên bìa. Chia slide theo nhịp feature, tối thiểu 6 tối đa 10, chữ Việt có dấu, tương phản cứng. Ranh giới ngoại lệ với luật không-tự-vẽ: art trừu tượng/sơ đồ khái niệm + hình thật của biểu đồ/bảng/báo cáo có ghi via; cấm ảnh AI/screenshot dựng lại/logo hãng/số liệu/quote giả. Dùng cho vai Kite (role carousel.edu)."
version: 0.1.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [carousel-edu, carousel, editorial, magazine, kite, vector, techcrunch, verge]
---

# carousel-edu — carousel kiến thức & nghiên cứu (tech × magazine)

Kiểu carousel thứ ba của đội, bên cạnh `carousel` bảng-tin (Dre) và
`carousel.rep` editorial-deck remake (Itachi). **Kite** dựng nó.

**Mục đích:** diễn đạt lại nội dung **kiến thức & nghiên cứu** — paper arXiv,
kinh nghiệm dev lâu năm — cho **chuyên nghiệp và tường minh**. Phần lớn research
là "paper trắng" (text nặng, không ảnh minh hoạ tử tế); chụp ảnh hay tìm ảnh đều
không hợp → Kite trình bày lại bằng **art vector + typography**. Paper thường dài
nên **tối thiểu 6 slide** (cổng chặn `render_edu.py` dừng nếu ít hơn).

Điểm tách bạch với các kiểu kia: **không đi tìm ảnh minh hoạ**. Bìa và các slide
được dựng bằng **art vector tự vẽ** (SVG/đồ hoạ code) + typography, trên nền tối
sạch. Đây là **ngoại lệ có chủ đích** với luật cứng "không bao giờ tự vẽ minh
hoạ" của cả đội — vì thế nó phải là một vai riêng, không trộn vào `carousel`.

Nhưng Kite **không phải chỉ biết chữ**. Tin nào **đã có sẵn** một biểu đồ, một
bảng số hay một trang báo cáo thì chèn **bản thật** vào bằng slide `figure` —
xem "Hình thật" bên dưới. Vẽ lại một biểu đồ có sẵn vừa mất công vừa dễ sai số.

## Ranh giới của ngoại lệ (đọc trước tiên)

Luật "không tự vẽ" tồn tại để **không bịa hiện thực**. Kite được nới đúng phần
*không đụng tới hiện thực*:

| ĐƯỢC vẽ (art trừu tượng, trang trí ý tưởng) | CẤM (giả làm bằng chứng thật) |
|---|---|
| Mô-típ hình học, quỹ đạo/orbit, node, glow | Ảnh giả trông như ảnh thật |
| Sơ đồ khái niệm: vòng lặp, các bước, luồng | Screenshot / UI sản phẩm giả |
| Đồ hoạ chữ, khối màu, hairline, badge | **Logo/nhận diện hãng thật** (Google, OpenAI…) |
| Biểu đồ *chỉ khi* số liệu có thật, ghi nguồn | Biểu đồ với số liệu bịa |
| **Chèn bản thật** của biểu đồ/bảng/báo cáo (`figure`, có caption "via") | Ảnh minh hoạ AI sinh ra |
| Ảnh chụp hiện trường có thật, ghi "via" | Ảnh + chữ tách thành hai mảng rời |
| | Quote bịa gán cho người/hãng |

Gọi tên sản phẩm bằng **chữ** ("Google Antigravity") thì được; **tái tạo logo**
của họ thì không. Nghi ngờ một mảng art có bị đọc thành "bằng chứng thật" không —
thì nó thuộc cột CẤM.

## Hệ thiết kế (design tokens)

- **Khổ:** 1080×1350 (4:5), portrait.
- **Nền:** `#0A0B0E` (đen hơi lạnh, không đen tuyệt đối). Nền luôn **sạch** — Kite
  tự dựng nền nên không bao giờ có cớ để nền rối/chi chít chữ.
- **Chữ:** trắng `#F4F6F9`; phụ (dịu) `#838A96`; hairline/viền `#262A33`; panel
  `#14161B`.
- **Duotone accent** (cùng chroma/lightness, khác hue): cyan `#2FD4E1` (chính) ×
  tím `#8E86F0` (phụ). Cyan là nhận diện; tím chỉ dùng trong art + vài micro-accent.
- **Font** (1–3 vai trò rõ ràng):
  - **Archivo** — display headline (700–900, tracking âm) + body (400–500).
  - **Newsreader** *italic* — standfirst / pull-quote (chất báo).
  - **JetBrains Mono** — masthead, eyebrow chuyên mục, folio, số, nhãn code.
  - Fallback khi export: Archivo→sans hệ thống, Newsreader→Georgia/serif,
    JetBrains Mono→monospace. (Google Fonts chưa nhúng được vào PNG/PDF export —
    chọn fallback gần metric, đừng để vỡ layout.)
- **Tương phản = luật cứng.** Chữ sáng trên nền tối. Không chữ trắng trên nền
  sáng; không đặt chữ lên vùng art rối.

## Bộ khung magazine (thứ tạo "vibe" — thiếu là hỏng)

Mỗi slide có bộ furniture nhất quán:

1. **Masthead chạy đầu trang:** wordmark `donniechublog` **chìm** (weight 500,
   cỡ nhỏ, xám `#838A96`) — kiểu wordmark wikipedia, KHÔNG nổi trắng đậm. Hairline
   giãn — nhãn chuyên mục phải (mono, vd `AI TOOLING`).
2. **Eyebrow chuyên mục:** thanh nhấn cyan ngắn + nhãn mono cyan (vd `BỐI CẢNH`,
   `CÁCH VẬN HÀNH`, `CƠ CHẾ`, `ÁP DỤNG`).
3. **Tiêu đề lớn** (Archivo 900, tracking âm) + **standfirst in nghiêng**
   (Newsreader italic) kiểu đứng đầu bài báo.
4. **Folio dưới chân:** hairline + dòng mono (vd chủ đề trái, `NN / 05` phải,
   số trang hiện tại tô cyan).
5. **Byline** trên bìa: `donniechublog · Phân tích · N phút đọc`.
6. **Hero art vector** trên bìa (bắt buộc), motif nhỏ + glow trên các slide trong.

### Ba luật bổ sung (Ông Chủ yêu cầu, đã vào render_edu.py — KHÔNG được phá)

1. **Masthead wordmark chìm như wikipedia** — `.mast-name` = DISPLAY weight 500,
   cỡ 26px, màu `DIM` (`#7B828E`), KHÔNG phải 700/WHITE/30px. Wordmark đừng giành
   mắt người đọc.
2. **Slide `cta` có `follow` → masthead BARE** (chỉ hairline, bỏ wordmark + nhãn
   chuyên mục). Vì folio slide cuối đã có "Theo dõi @donniechublog" — nhắc kênh 2
   lần cùng slide là lỗi.
3. **Dẫn nguồn ghi "via", không ghi "nguồn"** — render_edu.py cổng chặn dừng spec
   nào có chữ "nguồn" trong trường chữ (kể cả cụm như "mã nguồn mở" — đổi thành
   "mã mở").

## Tone & hero — MỖI BỘ MỘT TONE, không lặp bộ trước

Ông Chủ chê (04/09/2026): Kite làm đi làm lại một tone cyan × tím + hero quỹ
đạo. Renderer giờ có **5 theme** và **5 hero**, spec ghi `"theme"` / `"hero"`:

| theme | tone | hợp với |
|---|---|---|
| `orbit` | cyan × tím | agent, hệ thống, mặc định cũ |
| `ember` | cam hổ phách × đỏ san hô | hiệu năng, tốc độ, cảnh báo |
| `moss` | xanh lá × vàng chanh | dữ liệu mở, tăng trưởng, sinh học |
| `ink` | xanh navy × vàng | benchmark, học thuật, paper nghiêm |
| `rose` | hồng × tím oải hương | sinh ảnh, sáng tạo, multimodal |

| hero | hình | hợp với |
|---|---|---|
| `orbit` | lõi sáng + node quỹ đạo | subagent, phân việc |
| `grid` | lưới toạ độ + ô sáng | benchmark, bảng số, đo lường |
| `wave` | dải sóng + điểm nối | xu hướng, tín hiệu, theo thời gian |
| `rings` | vòng đồng tâm + kim | mục tiêu, độ chính xác, tầng lớp |
| `graph` | mạng node-cạnh | quan hệ, so sánh nhiều bên |

Luật: **chọn theo nội dung tin**, và **không trùng cả theme lẫn hero với bộ
ngay trước** (renderer in `CANH BAO` nếu trùng — thấy là đổi). **"Làm lại" thì
BẮT BUỘC đổi theme hoặc hero** — Ông Chủ bấm làm lại để thấy bộ khác, không phải
bộ cũ render lại. Bỏ trống hai khoá này thì renderer tự xoay khác lần trước
(ghi nhớ ở `state/edu_theme_da_dung.jsonl`); vẫn nên tự chọn cho hợp tin. Cờ
`--theme`/`--hero` ghi đè spec.

## Hero art — vẽ khái niệm, không vẽ hiện thực

Bìa cần một mảng art vector kể đúng khái niệm của bài. Ví dụ bộ /boost: một **lõi
phát sáng** ở giữa (khái niệm lệnh), các **node bay trên quỹ đạo** (subagent),
đường nối (phân việc), glow radial (chiều sâu), scatter dots. Tất cả là SVG dựng
bằng code — trừu tượng, gốc, không đụng logo/ảnh ai.

Các slide trong: một motif nhỏ ở góc (cung quỹ đạo + node) hoặc chỉ một glow
radial mờ — giữ nhẹ để không phạm chính luật "nền sạch, không rối".

## Hình thật — biểu đồ, bảng số, trang báo cáo (`kind: figure`)

Khi nguồn **đã có** hình đáng đưa lên, đừng vẽ lại: chèn bản thật.

```json
{"kind": "figure", "eyebrow": "SỐ LIỆU",
 "title": "Điểm số trên SWE-bench Verified", "accent": "SWE-bench Verified",
 "image": "drafts/chart_swebench.png",
 "caption": "Biểu đồ trong bản công bố · via Google DeepMind",
 "standfirst": "Chữ minh hoạ cho phần chiều cao còn thừa dưới hình.",
 "cards": [{"num": "01", "text": "Ý phụ, nếu còn chỗ."}]}
```

Luật bố cục. Hai luật, luật thứ hai đứng trên:

**1. Bề ngang trước, chiều cao xét sau** (cùng luật với `chup_chart.py`): ảnh
**trải hết 1080px**, chạm hai mép slide, **không bao giờ cắt hai bên**. Bề ngang
của một biểu đồ là *nội dung*: mất cột cuối, mất trục, mất đúng cái điểm đang
nói tới — cắt đi là **nói sai**, không phải thiếu một tí. Cao quá thì cắt, và
**giữ mép trên** (tiêu đề, trục, hàng đầu nằm ở trên); renderer in ra mất bao
nhiêu px để Kite biết mà tự cắt lại cho đúng.

**2. Một mặt phẳng liền — chữ chìm vào ảnh, không bao giờ là hai mảng.** Đây là
đúng luật của Dre (`carousel.py`), Kite dùng chung ngôn ngữ đó:

- **Nền quanh ảnh bao giờ cũng liền với ảnh**, không bao giờ là một hộp tối đặt
  cạnh ảnh. Hai cách, renderer tự chọn theo ảnh:
  - Ảnh có **nền phẳng** (biểu đồ, bảng số, trang tài liệu — thường nền trắng):
    trải thẳng **màu nền của chính nó** ra cả thẻ. Cùng một màu thì không thể có
    mép. *(Làm mờ bản cover kiểu Dre ở đây lại ra một mảng xám lệch tông với
    chính tấm ảnh sắc ở trên — vẫn đọc ra hai vùng.)*
  - **Ảnh chụp**: bản cover của chính nó, làm mờ mạnh — đúng cách của Dre.
- **Chữ đè lên ảnh** qua màn tối liền mạch bắt đầu từ ~42% chiều cao, đậm dần
  theo đường cong, kèm một lớp mờ của chính tấm ảnh hiện lên **cùng nhịp**. Chỉ
  làm tối thôi thì chữ trong ảnh vẫn lờ mờ dưới chữ mình; lớp mờ mới xoá hết.
- Masthead: chừa 150px đầu thẻ, ảnh không tràn lên. Nền sáng thì masthead tự
  đổi sang mực tối — **không** phủ thêm một màn tối ở đỉnh, màn đó chính là một
  dải band vắt ngang, đúng cái đang tránh.
- Ảnh **nền phẳng** dừng ở 63% chiều cao, không tràn xuống vùng chữ: dưới màn
  tối nó vẫn đọc được mờ mờ, chữ mình đè lên chữ của người ta thành một đám rối.
  Ảnh chụp thì phủ xuống thoải mái — ảnh chụp không có chữ để đụng.

Cổng chặn: `image` phải trỏ tới tệp có thật, rộng **>= 800px** (hẹp hơn mà kéo
lên 1080 là bể nát — chụp lại bằng `chup_chart.py`, DPR 2), và **bắt buộc**
`caption` ghi "via <ai>" vì hình là của người ta.

## Chia slide (nhịp feature)

Tối thiểu **6**, tối đa **10**. Khung tham chiếu (không cứng):

1. **Bìa — hook** + hero art + byline.
2. **Bối cảnh / vấn đề** — vì sao chủ đề đáng quan tâm.
3. **Cách vận hành** — cơ chế chính (hợp với sơ đồ các bước).
4. **Số liệu** — nếu nguồn có biểu đồ/bảng thật thì `figure`, không thì bỏ.
5. **Cơ chế / hệ quả** — tầng sâu hơn (hợp với sơ đồ vòng lặp/luồng).
6. **Áp dụng + CTA** — khi nào dùng, nguồn để đọc thêm, follow.

Mỗi slide **một ý mới**. Bìa giật, slide cuối để lại câu hỏi/mốc + CTA. Chữ Việt
có dấu; câu ngắn, chủ động; không em-dash.

## Toolchain — `render_edu.py` (hướng B: HTML→PNG)

Đã chốt **hướng B**: renderer `render_edu.py` ở gốc repo dựng từng slide bằng
HTML/CSS/SVG rồi chụp bằng **Chromium headless (Playwright)**. Chạy **trên
server** như cả đội.

```bash
venv/bin/python render_edu.py --spec spec.json --out drafts/<id>.png
```

Ra `drafts/<id>.png` (bìa) + `<id>_2.png`… đúng glob `{id}_[0-9].png` của
`draft_write.py`. Cờ: `--brand` (donniechublog|dcgr), `--bo-qua-dau` (chỉ khi copy
là tiếng Anh), `--scale` (mặc định 2 → 2160×2700 cho nét), `--spec -` đọc stdin,
`--theme`/`--hero` (xem mục Tone & hero).

**Spec JSON:** xem docstring đầu `render_edu.py` và `reference/boost.spec.json`
(spec đầy đủ của bộ /boost). 6 `kind` slide: `cover`, `statement`, `steps`,
`loop`, `figure`, `cta`. Cổng chặn tái dùng `card.tim_mat_dau` (tiếng Việt có
dấu) + luật 6..10 slide + slide 1 phải là `cover` + luật ảnh của `figure`.

**Cài trên server (một lần):**
```bash
venv/bin/pip install playwright
venv/bin/playwright install chromium
```

**Font:** `render_edu.py` nhúng font base64 từ `assets/fonts` (Chromium headless
trên server tối giản không có font hệ thống → phải nhúng, tránh tofu tiếng Việt).
Hiện dùng bộ Vietnamese-safe có sẵn: **Be Vietnam Pro** (display+body), **Noto
Serif** (standfirst in nghiêng), **JetBrains Mono** (nhãn/số). Bản canvas
`reference/` dùng **Archivo + Newsreader** — để khớp 100%, thả 2 TTF đó vào
`assets/fonts` rồi sửa bảng `FONTS` trong `render_edu.py`.

**Trạng thái:** Đã chạy LIVE trên server — Playwright+Chromium cài xong, render boost.spec.json ra 6 slide chuẩn (đã soi mắt). Production-ready.

## Bản dựng tham chiếu

`reference/` giữ bộ **/boost 5 slide** (`Main`, `Problem`, `HowItWorks`,
`RegressionLoop`, `Takeaway` — định dạng artboard `.dc.html`) là *nguồn sự thật*
của hệ thiết kế: màu, font, khung magazine, hero art vector đều lấy số đo từ đây.
Generator (hướng A hay B) phải tái tạo đúng bộ này. Bản canvas gốc dựng trong
Claude Design (Ông Chủ giữ link).

## Nhìn lại trước khi giao

1. Bìa có art vector + hook giật không? (Chỉ chữ trên nền đen = hỏng.)
2. Đủ bộ khung magazine mọi slide (masthead, eyebrow, folio)?
3. Mọi chữ tương phản đủ? Không chữ trắng trên vùng sáng?
4. ≥6 slide, mỗi slide một ý mới?
5. Có mảng art nào bị đọc thành "ảnh/logo/số liệu thật" không? Có thì sửa —
   đó là lằn ranh của ngoại lệ.
