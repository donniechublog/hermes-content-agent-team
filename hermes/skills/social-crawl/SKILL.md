---
name: social-crawl
description: >
  Đọc NỘI DUNG một post X/Twitter, Instagram hoặc Facebook cụ thể — chữ trong bài,
  tác giả, số liệu tương tác, ảnh — qua endpoint crawl nội bộ. Dùng khi Ông Chủ dán
  một link x.com/twitter.com/instagram.com/facebook.com vào hội thoại và muốn biết
  bài đó nói gì, thay vì đoán từ tiêu đề link.
when_to_use: >
  Ông Chủ đưa MỘT link post cụ thể trong hội thoại và cần nội dung của nó. KHÔNG
  dùng để đi tìm bài mới (đó là việc của tuyến quét theo lịch), KHÔNG dùng cho
  YouTube/TikTok, và KHÔNG dùng trong ba bước của nhiệm vụ quét cron.
category: web
keywords: [x, twitter, instagram, facebook, crawl, doc bai, noi dung post]
argument-hint: "<link-post-x-instagram-hoac-facebook>"
metadata:
  author: content-team
  version: "1.1.0"
---

# social-crawl — đọc nội dung một post X/Instagram/Facebook

Trang x.com, instagram.com và facebook.com chặn khách chưa đăng nhập, nên `curl`
hay tải trang thẳng chỉ nhận được tường đăng nhập. Endpoint nội bộ `crawl-queue`
đọc hộ bằng một trình duyệt đã đăng nhập thật, không cần API key, không OAuth.

## Chạy

```bash
/home/dc-group/content-team/venv/bin/python /home/dc-group/content-team/hermes/skills/social-crawl/scripts/social_fetch.py "<url>"
```

Chạy ĐÚNG một dòng, đường dẫn tuyệt đối, link trong ngoặc kép. Dạng lệnh này nằm
trong `command_allowlist` nên không phải chờ duyệt; gói nó trong `cd … &&` hay
`$(…)` là lệch allowlist và sẽ bị từ chối.

In ra JSON: với X có `text` (nguyên văn bài), `author`, `timestamp`, `metrics`
(reply/retweet/like/view), `thread`, `replies`; với Instagram có `media[]` kèm
link CDN; với Facebook có `text` (TOÀN VĂN post), `author`, `postId`, `media[]`
và `metrics` (reactions/comments/shares). Thêm `--tries N` nếu muốn kiên nhẫn hơn
mặc định 6 lần.

## Lấy chính tấm ảnh về máy

`--download <thư mục>` tải luôn `media[]` xuống, đặt tên `01.jpg`, `02.jpg`… đúng
thứ tự slide trong carousel (video ra `NN.mp4` kèm `NN-thumb.jpg`):

```bash
/home/dc-group/content-team/venv/bin/python /home/dc-group/content-team/hermes/skills/social-crawl/scripts/social_fetch.py "<url>" --download "<thư mục>"
```

`?img_index=N` trong link Instagram là **slide thứ N** của carousel, ứng với tệp
`NN.jpg`. Gin không phải chạy lệnh này tay: `gin_prepare.py "<link>"` gọi nó
sẵn rồi chọn đúng slide.

## Những chỗ đã trả giá, đừng "sửa" lại

- **Endpoint chạy bất đồng bộ và có warm-up.** Lần gọi đầu cho một link chưa
  crawl bao giờ có thể trả lỗi GIẢ ("url must be an https x.com…", "Instagram
  media JSON not found") dù link hoàn toàn đúng. Script tự thử lại — đừng thấy
  một lần hỏng mà kết luận link sai.
- **Mỗi lần gọi là một lượt crawl SỐNG, mất 10–40 giây.** Bình thường, không
  phải treo. Đừng bấm lại chồng lên.
- **Post ảnh trên X thường trả `media[]` RỖNG.** Đó là giới hạn đã biết của
  crawler, không phải link hỏng — và `--download` khi đó cũng không có gì để
  tải. Instagram thì trả đủ. Cần ảnh của một post X mà `media[]` rỗng thì đó là
  việc của Bob (`url-mascot-frame`).
  (Trước 07/09/2026 mục này ghi mọi việc lấy ảnh đều là của Bob, viết từ hồi
  script chưa có `--download`. Gin đọc đúng câu đó rồi kết luận mình không lấy
  được ảnh từ link, và tắc — 07/09 msg 810.)
- **Không bao giờ dùng `localPath`/`mediaPath` trong kết quả** — đường dẫn đó
  nằm trong container của dịch vụ crawl, máy này không với tới. Muốn file thật
  thì tải lại từ `media[].url`.
- **Link CDN có tham số hết hạn (`oe=`)** — đừng cất lại dùng sau, phải crawl
  lại để lấy link mới.
- **Facebook chỉ khớp permalink dạng SỐ** `facebook.com/<trang>/posts/<id số>`.
  Đo ngày 08/09/2026: link `/share/<mã>` bị trả 400, dạng có slug tiếng Việt
  (`/posts/có-những-…-<id>/`) trả 500 "không khoanh được post", còn
  `permalink.php?story_fbid=` thì "thấy 0 story_message". Script tự chuẩn hoá cả
  ba về dạng số (`normalize_url`) — đừng gỡ bước đó cho "gọn".
- **Trang share của Facebook chỉ mở cho UA của chính nó.** Bước đọc thẻ
  `canonical` dùng UA `facebookexternalhit`; UA Chrome hiện đại bị trả 400 kèm
  thân trang 1,5 KB, còn UA đó trả 340 KB. Đổi UA là hỏng bước chuẩn hoá.

## Ranh giới

Skill này chỉ ĐỌC HỘ một link Ông Chủ đưa. Nó không thay tuyến quét tin theo
lịch: trong ba bước của nhiệm vụ cron (`scan_prepare.py` → viết JSON →
`scan_submit.py`) vẫn giữ nguyên luật cũ — không tự tải trang, không web_search,
không chạy gì ngoài ba lệnh đó.

Script ở đây là bản của đội, nằm trong git. Bob có một bản riêng ở
`~/.claude/skills/social-crawl/` mà `get_source.py` gọi để lấy ẢNH — nếu endpoint
đổi thì phải sửa cả hai bản, đừng sửa một bên rồi tưởng xong.
