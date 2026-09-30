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

