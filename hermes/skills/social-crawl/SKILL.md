---
name: social-crawl
description: >
  Đọc NỘI DUNG một post X/Twitter hoặc Instagram cụ thể — chữ trong bài, tác giả,
  số liệu tương tác, thread và reply — qua endpoint crawl nội bộ. Dùng khi Ông Chủ
  dán một link x.com/twitter.com/instagram.com vào hội thoại và muốn biết bài đó
  nói gì, thay vì đoán từ tiêu đề link.
when_to_use: >
  Ông Chủ đưa MỘT link post cụ thể trong hội thoại và cần nội dung của nó. KHÔNG
  dùng để đi tìm bài mới (đó là việc của tuyến quét theo lịch), KHÔNG dùng cho
  YouTube/TikTok/Facebook, và KHÔNG dùng trong ba bước của nhiệm vụ quét cron.
category: web
keywords: [x, twitter, instagram, crawl, doc bai, noi dung post]
argument-hint: "<link-post-x-hoac-instagram>"
metadata:
  author: content-team
  version: "1.0.0"
---

# social-crawl — đọc nội dung một post X/Instagram

Trang x.com và instagram.com chặn khách chưa đăng nhập, nên `curl` hay tải trang
thẳng chỉ nhận được tường đăng nhập. Endpoint nội bộ `crawl-queue` đọc hộ bằng
một trình duyệt đã đăng nhập thật, không cần API key, không OAuth.

## Chạy

```bash
/home/donniechu/content-team/venv/bin/python /home/donniechu/content-team/hermes/skills/social-crawl/scripts/social_fetch.py "<url>"
```

Chạy ĐÚNG một dòng, đường dẫn tuyệt đối, link trong ngoặc kép. Dạng lệnh này nằm
trong `command_allowlist` nên không phải chờ duyệt; gói nó trong `cd … &&` hay
`$(…)` là lệch allowlist và sẽ bị từ chối.

In ra JSON: với X có `text` (nguyên văn bài), `author`, `timestamp`, `metrics`
(reply/retweet/like/view), `thread`, `replies`; với Instagram có `media[]` kèm
link CDN. Thêm `--tries N` nếu muốn kiên nhẫn hơn mặc định 6 lần.

## Những chỗ đã trả giá, đừng "sửa" lại

- **Endpoint chạy bất đồng bộ và có warm-up.** Lần gọi đầu cho một link chưa
  crawl bao giờ có thể trả lỗi GIẢ ("url must be an https x.com…", "Instagram
  media JSON not found") dù link hoàn toàn đúng. Script tự thử lại — đừng thấy
  một lần hỏng mà kết luận link sai.
- **Mỗi lần gọi là một lượt crawl SỐNG, mất 10–40 giây.** Bình thường, không
  phải treo. Đừng bấm lại chồng lên.
- **Post ảnh trên X thường trả `media[]` RỖNG.** Đó là giới hạn đã biết của
  crawler, không phải link hỏng. Cần chính tấm ảnh thì đó là việc của Bob
  (`url-mascot-frame`), không phải skill này.
- **Không bao giờ dùng `localPath`/`mediaPath` trong kết quả** — đường dẫn đó
  nằm trong container của dịch vụ crawl, máy này không với tới. Muốn file thật
  thì tải lại từ `media[].url`.
- **Link CDN có tham số hết hạn (`oe=`)** — đừng cất lại dùng sau, phải crawl
  lại để lấy link mới.

## Ranh giới

Skill này chỉ ĐỌC HỘ một link Ông Chủ đưa. Nó không thay tuyến quét tin theo
lịch: trong ba bước của nhiệm vụ cron (`quet_chuan_bi.py` → viết JSON →
`quet_nop.py`) vẫn giữ nguyên luật cũ — không tự tải trang, không web_search,
không chạy gì ngoài ba lệnh đó.

Script ở đây là bản của đội, nằm trong git. Bob có một bản riêng ở
`~/.claude/skills/social-crawl/` mà `get_source.py` gọi để lấy ẢNH — nếu endpoint
đổi thì phải sửa cả hai bản, đừng sửa một bên rồi tưởng xong.
