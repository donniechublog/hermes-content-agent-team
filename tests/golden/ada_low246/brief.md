# ADA — SỐ LIỆU 2 NGÀY QUA (đến 15/09 08:00 VN), brand blog

## Tin quét & chọn: 7 tin, chọn 4
Theo bậc điểm (tổng/chọn): ≥90: 2/2, 80–89: 2/0, 70–79: 2/2, không điểm: 1/0
Theo nguồn (tổng/chọn): The Verge: 2/1, Google News: 1/1, VnExpress: 1/1, ?: 1/0, TechCrunch: 1/0, Reuters: 1/1
Theo category (tổng/chọn): model: 2/1, chip: 2/1, funding: 1/1, ?: 1/0, device: 1/1
Điểm ≥85 mà KHÔNG chọn: [88] Nvidia công bố chip Rubin Ultra cho trung tâm (finn, 2026-09-14); [86] Anthropic mở rộng cửa sổ ngữ cảnh lên 2 triệu (nova, t2201.json)
Điểm <75 mà ĐƯỢC chọn: [70] Meta thử nghiệm kính AR mới (nova, t2201.json); [72] Startup AI Việt gọi vốn 12 triệu USD vòng Ser (finn, 2026-09-14)

## Draft: {'pending': 1, 'published': 1, 'rejected': 1}
  - pending   [-] d2-rubin-dcgr
  - published [81] d1-gpt6-blog
  - rejected  [-] d3-meta-ar

## Kanban theo vai: miles: {'done': 2}; dre: {'blocked': 1}; ada: {'failed': 1}; finn: {'done': 1}
Giây trung bình/task: miles: 450, finn: 60
  - dre blocked: Ảnh cho bài chip Rubin | thiếu ảnh thật
  - ada failed: Phân tích tuần | timeout xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  - finn done: Quét tin sáng | cảnh báo nhẹ

## Token theo vai (phiên / tool call / input token / api call)
⚠️ KHÔNG đọc được state.db của: qinn — số dưới đây THIẾU các vai đó, không phải họ không làm gì
  - miles: 3 / 41 / 1,234,567 / 52 | nặng nhất: Viết bài GPT-6 (20 tool, 600,000 in); Viết bài TSMC (11 tool, 300,000 in)
  - dre: 2 / 12 / 45,678 / 14 | nặng nhất: Ảnh cho bài chip Rubin (12 tool, 45,678 in)
Chi phí 9router (chung cả 2 brand, tổng $0.226, 8 model tốn nhất): deepseek-v4-flash: 6 req, 195,900 prompt, $0.1741, glm-5.3: 3 req, 12,500 prompt, $0.05, deepseek-chat: 1 req, 5,000 prompt, $0.002

## 9router theo ngày (req / $ / cache% / fallback v4-flash→deepseek-chat / lỗi | model tốn nhất)
  - 09-14: 2 / $0.0031 / 51.3% / 0 / 0 | deepseek-v4-flash @ deepseek-v4-flash
  - 09-15: 8 / $0.223 / 72.1% / 1 / 2 | deepseek-v4-flash @ DS main (ds)
Đổi model liên tiếp gộp (gồm cả vai chạy song song, chỉ v4-flash→deepseek-chat là fallback thật): deepseek-v4-flash → deepseek-chat 1 lần; deepseek-chat → deepseek-v4-flash 1 lần; deepseek-v4-flash → glm-5.3 1 lần
Lỗi gộp: glm-5.3: error 429 1; glm-5.3: error 502 1
$ theo vai (ước lượng phân bổ token, gộp N ngày) — vai: $ / api call / task done / $/task:
  - blog/miles: $0.1523 / 42 / 2 / $0.0761
  - dcgr/jika: $0.0123 / 7 / 0 / -
  - blog/ada: $0.0001 / 1 / 0 / -
$/bài published theo brand: blog: $0.1524 / 2 bài = $0.0762, dcgr: $0.0123 / 0 bài = chưa có bài
Phiên rỗng (ok nhưng ≤5 token out dù prompt ≥1k): deepseek-v4-flash 2, deepseek-chat 1, glm-5.3 1
Connection lỗi trong ngày: 09-15 Xiaoke <x> & co [429] Too Many Requests: quota hết hạn mức ngày; 09-15 tắt rồi [ECONNREFUSED] connect ECONNREFUSED 127.0.0.1:443 — dài xxxxxxxxxxxxxxxxxxx
Theo khoá API: khoa la …efgh $0.0031, blog $0.171, dcgr $0.002, khoa la …7777 $0.05

## Viết nhận xét vào: <WD>/spec.json — CHỈ từ số liệu trên, mỗi ý kèm bằng chứng (bài nào, điểm bao nhiêu, kết quả gì)
{
 "nhan_xet": [
  "<3–5 điều rút ra, mỗi điều một câu có số>"
 ],
 "de_xuat_rubric": [
  {
   "thay_doi": "<sửa trọng số/tiêu chí gì>",
   "bang_chung": "<bài, điểm, kết quả>"
  }
 ],
 "token": "<1–2 câu: vai nào đốt nhiều nhất, vì sao, cắt ở đâu>",
 "router": "<1–2 câu: ngày nào đốt nhất, vai nào đắt nhất và $/bài, có fallback/phiên rỗng/connection lỗi/IP lạ không>",
 "ket_luan": "<một câu>"
}
Không có gì đáng chỉnh thì ghi de_xuat_rubric: [] và nói thẳng. Không suy diễn ngoài số liệu.

## Rồi chạy đúng MỘT lệnh:
cd <ROOT> && venv/bin/python ada_submit.py
Script dựng báo cáo (số liệu do code, nhận xét của bạn), lưu nhật ký, gửi topic analyst. KHÔNG truy vấn sqlite tay, KHÔNG ls drafts, KHÔNG đọc từng manifest.