---
name: carousel-sli
description: "Dựng carousel tech-editorial (magazine, vibe TechCrunch/The Verge) bằng ART VECTOR GỐC tự vẽ — không ảnh thật, không nền AI. Hệ thiết kế: nền tối #0A0B0E, duotone cyan #2FD4E1 x tím #8E86F0, font Archivo (display) + Newsreader italic (standfirst) + JetBrains Mono (nhãn/số), bộ khung magazine (masthead chạy đầu, eyebrow chuyên mục, hairline, folio số trang, byline) và một hero art vector trên bìa. Chia slide theo nhịp feature, tối thiểu 5 tối đa 10, chữ Việt có dấu, tương phản cứng. Ranh giới ngoại lệ với luật không-tự-vẽ: chỉ art trừu tượng/sơ đồ khái niệm, cấm ảnh/screenshot/logo hãng/số liệu/quote giả. Dùng cho vai Kite (role carousel.sli)."
version: 0.1.0
author: content-team
license: internal
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [carousel-sli, carousel, editorial, magazine, kite, vector, techcrunch, verge]
---

# carousel-sli — carousel tạp chí công nghệ, art vector gốc

Kiểu carousel thứ ba của đội, bên cạnh `carousel` bảng-tin (Heller/Dre) và
`carousel.rep` editorial-deck remake (Itachi). **Kite** dựng nó.

Điểm tách bạch với các kiểu kia: **không có ảnh nào từ bên ngoài**. Bìa và các
slide được dựng bằng **art vector tự vẽ** (SVG/đồ hoạ code) + typography, trên
nền tối sạch. Đây là **ngoại lệ có chủ đích** với luật cứng "không bao giờ tự vẽ
minh hoạ" của cả đội — vì thế nó phải là một vai riêng, không trộn vào `carousel`.

## Ranh giới của ngoại lệ (đọc trước tiên)

Luật "không tự vẽ" tồn tại để **không bịa hiện thực**. Kite được nới đúng phần
*không đụng tới hiện thực*:

| ĐƯỢC vẽ (art trừu tượng, trang trí ý tưởng) | CẤM (giả làm bằng chứng thật) |
|---|---|
| Mô-típ hình học, quỹ đạo/orbit, node, glow | Ảnh giả trông như ảnh thật |
| Sơ đồ khái niệm: vòng lặp, các bước, luồng | Screenshot / UI sản phẩm giả |
| Đồ hoạ chữ, khối màu, hairline, badge | **Logo/nhận diện hãng thật** (Google, OpenAI…) |
| Biểu đồ *chỉ khi* số liệu có thật, ghi nguồn | Biểu đồ với số liệu bịa |
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

1. **Masthead chạy đầu trang:** wordmark `donniechublog` (Archivo 800) — hairline
   giãn — nhãn chuyên mục phải (mono, vd `AI TOOLING`).
2. **Eyebrow chuyên mục:** thanh nhấn cyan ngắn + nhãn mono cyan (vd `BỐI CẢNH`,
   `CÁCH VẬN HÀNH`, `CƠ CHẾ`, `ÁP DỤNG`).
3. **Tiêu đề lớn** (Archivo 900, tracking âm) + **standfirst in nghiêng**
   (Newsreader italic) kiểu đứng đầu bài báo.
4. **Folio dưới chân:** hairline + dòng mono (vd chủ đề trái, `NN / 05` phải,
   số trang hiện tại tô cyan).
5. **Byline** trên bìa: `donniechublog · Phân tích · N phút đọc`.
6. **Hero art vector** trên bìa (bắt buộc), motif nhỏ + glow trên các slide trong.

## Hero art — vẽ khái niệm, không vẽ hiện thực

Bìa cần một mảng art vector kể đúng khái niệm của bài. Ví dụ bộ /boost: một **lõi
phát sáng** ở giữa (khái niệm lệnh), các **node bay trên quỹ đạo** (subagent),
đường nối (phân việc), glow radial (chiều sâu), scatter dots. Tất cả là SVG dựng
bằng code — trừu tượng, gốc, không đụng logo/ảnh ai.

Các slide trong: một motif nhỏ ở góc (cung quỹ đạo + node) hoặc chỉ một glow
radial mờ — giữ nhẹ để không phạm chính luật "nền sạch, không rối".

## Chia slide (nhịp feature)

Tối thiểu **5**, tối đa **10**. Khung tham chiếu (không cứng):

1. **Bìa — hook** + hero art + byline.
2. **Bối cảnh / vấn đề** — vì sao chủ đề đáng quan tâm.
3. **Cách vận hành** — cơ chế chính (hợp với sơ đồ các bước).
4. **Cơ chế / hệ quả** — tầng sâu hơn (hợp với sơ đồ vòng lặp/luồng).
5. **Áp dụng + CTA** — khi nào dùng, nguồn để đọc thêm, follow.

Mỗi slide **một ý mới**. Bìa giật, slide cuối để lại câu hỏi/mốc + CTA. Chữ Việt
có dấu; câu ngắn, chủ động; không em-dash.

## Toolchain — `render_sli.py` (hướng B: HTML→PNG)

Đã chốt **hướng B**: renderer `render_sli.py` ở gốc repo dựng từng slide bằng
HTML/CSS/SVG rồi chụp bằng **Chromium headless (Playwright)**. Chạy **trên
server** như cả đội.

```bash
venv/bin/python render_sli.py --spec spec.json --out drafts/<id>.png
```

Ra `drafts/<id>.png` (bìa) + `<id>_2.png`… đúng glob `{id}_[0-9].png` của
`draft_write.py`. Cờ: `--brand` (donniechublog|dcgr), `--bo-qua-dau` (chỉ khi copy
là tiếng Anh), `--scale` (mặc định 2 → 2160×2700 cho nét), `--spec -` đọc stdin.

**Spec JSON:** xem docstring đầu `render_sli.py` và `reference/boost.spec.json`
(spec đầy đủ của bộ /boost). 5 `kind` slide: `cover`, `statement`, `steps`,
`loop`, `cta`. Cổng chặn tái dùng `card.tim_mat_dau` (tiếng Việt có dấu) + luật
4..10 slide + slide 1 phải là `cover`.

**Cài trên server (một lần):**
```bash
venv/bin/pip install playwright
venv/bin/playwright install chromium
```

**Font:** `render_sli.py` nhúng font base64 từ `assets/fonts` (Chromium headless
trên server tối giản không có font hệ thống → phải nhúng, tránh tofu tiếng Việt).
Hiện dùng bộ Vietnamese-safe có sẵn: **Be Vietnam Pro** (display+body), **Noto
Serif** (standfirst in nghiêng), **JetBrains Mono** (nhãn/số). Bản canvas
`reference/` dùng **Archivo + Newsreader** — để khớp 100%, thả 2 TTF đó vào
`assets/fonts` rồi sửa bảng `FONTS` trong `render_sli.py`.

**Trạng thái:** code đã viết + tự test ở local (import/format/cổng chặn/dựng HTML
đều pass). **CHƯA chạy thử live trên server** (chưa cài Chromium ở đó) — lần đầu
chạy trên server để ra PNG thật rồi soi mắt trước khi vào production.

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
4. ≥5 slide, mỗi slide một ý mới?
5. Có mảng art nào bị đọc thành "ảnh/logo/số liệu thật" không? Có thì sửa —
   đó là lằn ranh của ngoại lệ.
