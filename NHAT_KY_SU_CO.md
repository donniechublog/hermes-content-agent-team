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

## Nội dung nằm ở `nhat_ky/`, mỗi sự cố một tệp

Tách tiếp ngày 12/09/2026. Trước đó cả nhật ký là **một tệp**, mà mỗi ticket
xong đều phải thêm một mục vào đó — nên hai việc chạy song song là hai nhánh
cùng sửa cùng một chỗ, lần merge nào cũng đụng. Đo trên 200 commit gần nhất:
`NHAT_KY_SU_CO.md` dính 15 commit, `README.md` dính 40 — cao gấp đôi mọi tệp mã.

Bây giờ:

```
nhat_ky/YYYY-MM-DD-ten-ngan.md   mỗi sự cố một tệp, viết xong không sửa lại
nhat_ky/tham_chieu.md            mục không phải sự cố (model, provider, kiểu `dai`)
```

**Ghi một sự cố mới = tạo một tệp mới.** Không ai sửa tệp của người khác, nên
với git đây luôn là "thêm tệp", không bao giờ là "hai nhánh sửa cùng một dòng"
— hết đụng nhau, dù bao nhiêu phiên chạy song song.

Không có tệp mục lục, và đừng tạo: một mục lục chung cũng là một tệp ai cũng
phải sửa, tức là dựng lại đúng chỗ nghẽn vừa gỡ. Tên tệp có ngày ở đầu nên
`ls nhat_ky/` đã là mục lục xếp theo thời gian.

Đọc gộp toàn bộ theo thứ tự thời gian:

```bash
cat nhat_ky/*.md
```

Tìm một sự cố cũ:

```bash
grep -rl "tu khoa" nhat_ky/
```
