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

**Bổ sung cùng ngày (LOW-34/35).** Cùng draft: (34) trang công bố deepseek.com
không bao giờ được hỏi — `tach_model("deepseek-ai/DeepSeek-V4.1-Flash · …")`
ra `['deepseek']` vì tiền tố repo, `_khoa_model` rỗng, `trang_cong_bo` trả
None **im lặng**; `_them_trang_cong_bo` lại "en trước, có là lấy" nên tiêu đề
Việt đúng không được xét. Sửa: `tach_model` bỏ `org/`, lấy tên dài nhất từ cả
hai tiêu đề, `trang_cong_bo` in lý do khi không có khoá. (35) Commons theo tên
hãng chỉ đòi *mỗi từ có mặt*: "Hugging Face" khớp "Rathlin **hugging** the
cliff **face**" và "Octopus' Hugging Face"; sửa `_co_cum` (liền nhau, đúng thứ
tự), `_ten_rieng_dau`/`tieu_de_nhin` đi qua `bo_hau_to_site` nên hậu tố site
không còn thành hãng trong tin.

---

