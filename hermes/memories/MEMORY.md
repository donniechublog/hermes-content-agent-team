Chọn model: ghim mỗi hội thoại vào đúng một model; giám sát là bắt buộc, không tự đổi model giữa chừng.
§
Chi phí model tính bằng số đo thật (cache quyết định giá thực), không dựa giá niêm yết.
§
Khung giờ chạy tác vụ nặng/cron: 6h sáng giờ VN; né khung 8-11h và 13-17h.
§
Kiến trúc memory (v0): built-in MEMORY.md/USER.md giữ NHỎ — chỉ điều luôn-phải-biết. Chi tiết dự án (routing content-team, spec thẻ ảnh, quyết định content, cái gì đã hiệu quả) → ghi vào fact_store của provider retrieval để recall khi cần, KHÔNG nhồi vào built-in. Provider hiện tại = holographic (local SQLite, 0đ, không daemon); đổi sang Hindsight khi scale mass adoption.
§
Bộ não CHUNG cho 2 dự án dcgr.tech + donniechublog (researcher dùng chung). QUY ƯỚC TAG khi ghi fact_store: research/hạ tầng dùng chung → tag `shared`; fact brand/biên tập riêng dự án → tag `dcgr` hoặc `dnb`. Lưu ý: holographic auto-recall KHÔNG lọc cứng theo tag (chỉ cộng điểm), nên viết fact brand phải nêu rõ tên dự án trong nội dung để không lẫn giọng giữa 2 brand.
