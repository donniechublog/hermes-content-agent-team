# Quy tắc worktree & push (tránh phiên/máy đè việc của nhau)

Bối cảnh: repo này được sửa từ nhiều máy (Mac này + 2 máy khác, mỗi máy một clone riêng), và nhiều phiên Claude Code có thể chạy song song trên cùng một máy. Không có isolation nào là mặc định — phải chủ động áp các quy tắc dưới đây.

## 1. Một tác vụ = một worktree

- Nếu có khả năng một phiên khác đang chạy trong thư mục gốc (`content-team/`), KHÔNG sửa/commit trực tiếp ở đó. Dùng `EnterWorktree` để lấy một worktree cô lập (`.claude/worktrees/<tên>`, nhánh riêng) trước khi động vào file.
- Dấu hiệu nghi có phiên khác đang chạy trong thư mục gốc: `git status` có nhiều file lạ đang sửa dở, hoặc `git reflog` của nhánh hiện tại có commit mới trong vài phút gần nhất mà bạn không phải người tạo. Khi nghi ngờ — dừng, kiểm tra trước (`git reflog`, `ps aux | grep -i claude`), đừng `checkout`/reset/ghi đè để "khôi phục".
- Xong việc: review diff, commit, rồi `ExitWorktree` — `remove` nếu đã merge/xong hẳn, `keep` nếu tạm dừng. Không bỏ worktree lửng lơ trên một nhánh cũ — đó cũng là một dạng "phiên khác" gây lẫn về sau.

## 2. Remotes & thứ tự push

- **Tên remote KHÁC NHAU giữa các clone** — nhận remote bằng URL, không bằng tên. Chạy `git remote -v` trước mọi lần push. Ví dụ clone Windows (`D:\Hermes\content-team`): `origin` = GitHub, `deploy` = dc-group; clone khác có thể ngược lại (`origin` = dc-group, `github` = GitHub).
- **Remote deploy** = URL trỏ tới dc-group (`dc-group:/home/dc-group/content-team` hoặc `dc-group@dc-group-system-product-name.netbird.mated:/home/dc-group/content-team`) — production ĐÃ CHUYỂN MÁY 20/09/2026, `donniechu-01` không còn là đích deploy (21/09/2026 phát hiện một lần deploy lạc vào máy cũ). Server có `receive.denyCurrentBranch=updateInstead`. **Push vào remote này là deploy production ngay lập tức**, không phải một push bình thường.
- Trên máy production, cách kéo code đang dùng thực tế là `git pull origin main` chạy TAY (`origin` ở đây là remote của chính máy production; reflog toàn `merge origin/main: Fast-forward`) — nên kiểm `hostname` trước khi kéo, phải ra `dc-group-System-Product-Name`.
- **Remote GitHub** = `donniechublog/hermes-content-agent-team` — remote an toàn, không side-effect, dùng làm nơi chốt/đồng bộ giữa 3 máy.
- Nhánh task (bất kể tạo từ máy nào) chỉ push lên remote GitHub. Không push nhánh task lên remote deploy.
- Chỉ push `main` lên remote deploy sau khi `main` đã chốt xong trên GitHub. Coi đây là bước "bấm nút deploy" — làm riêng, có chủ đích, một nơi/một lúc — không phải việc mỗi phiên tự làm ngay khi xong task của mình.

## 3. `main` chỉ tiến ở một chỗ

- Merge vào `main` là một bước tuần tự, làm ở một chỗ (qua PR trên GitHub, hoặc một máy/phiên được chỉ định gác merge) — không phải máy nào xong việc trước thì tự merge/push `main` trước.

## 4. Không bao giờ force-push nhánh chung

- Luôn `git fetch` trước khi push. Bị từ chối "non-fast-forward" nghĩa là có người/máy khác đã push trước bạn — `git pull --rebase` rồi push lại. Không bao giờ `--force` qua một nhánh chung (đặc biệt `main`).
- Nếu cần dọn dẹp trong lúc làm việc, không dùng `git stash` / `git stash pop` trần — stash stack dùng chung giữa các worktree của repo, phiên khác có thể push/pop đè lên. Nếu bắt buộc phải stash, đặt tag riêng (`git stash push -u -m "<tag>"`) và `apply` theo SHA, không `pop`.

## 5. Đặt tên: mọi tên MỚI chỉ dùng English (LOW-129, Ông Chủ 14/09/2026)

- Áp cho mọi thứ tạo mới: biến, tham số, hàm, lớp, hằng, module/tệp, thư mục, khoá cấu hình mới, **tên nhánh và worktree**. Không đặt tên Việt không dấu nữa (`tim_anh_moi` ✗ → `find_new_image` ✓; `fix/cat-ngang-vision` ✗ → `fix/vision-horizontal-crop` ✓).
- Khái niệm đã có tên: tra `docs/tu_dien_ten/` để dùng đúng từ đã chốt, không tự dịch thành từ khác.
- Sửa tệp cũ: phần thêm mới vẫn English; KHÔNG tiện tay đổi tên cũ xung quanh. Đổi tên hàng loạt phải có ticket riêng và kiểm phiên khác trước (dùng `docs/tu_dien_ten/rename.py`).
- KHÔNG áp cho nội dung: chuỗi hiển thị, prompt/SOUL, nhật ký, commit message, tài liệu tiếng Việt giữ nguyên.
- Khoá JSON manifest/ảnh/`img.json` đã English từ LOW-227 (bảng `docs/tu_dien_ten/manifest_keys_v2.json`, `schema.py`); đường dẫn state `state/<brand>/prepare/<draft>/…` đã English từ LOW-228 — tên tệp/thư mục CHỈ lấy từ `state_paths.py`, không viết chuỗi `"original"`, `"manifest.json"`… rải trong code (`tests/test_state_paths.py` chặn tên cũ). Giá trị liệt kê trong manifest đã là mã English từ LOW-230 (bảng `docs/tu_dien_ten/manifest_values_v3.json`); chữ hiển thị tiếng Việt in qua `manifest_values.py` — thêm giá trị mới thì thêm cả nhãn. Khoá JSON bên trong MỌI kho khác (tệp nguồn, ứng viên scan, nhật ký 9router, bot duyệt, writer/designer, spec vai LLM…) đã English từ LOW-232..248 (mỗi kho một bảng `docs/tu_dien_ten/<kho>_keys_v2.json`); khoá do vai LLM tự viết (spec.json) đổi CÙNG prompt (brief/SOUL/SKILL/IMAGE_RULES/lỗi submit), code còn đọc khoá spec cũ qua `role_spec.py` và `_legacy_spec` (Ada/Gin/Itachi/deck) tới LOW-252; dấu metadata PNG cũ đọc vĩnh viễn qua `image_provenance.LEGACY_*`. Tệp/thư mục cấp state (`article_source_<id>.json`, `used_images.jsonl`, `scan/`, `journal/`…) đã English từ LOW-231 (bảng `docs/tu_dien_ten/state_files_v2.json`), cũng CHỈ lấy từ `state_paths.py`.
- Cổng CI `tests/test_name_english.py` (LOW-53) chặn tên top-level Việt quay lại; nó không xét biến cục bộ hay tên nhánh — phần đó dựa vào quy ước này. Đỏ vì từ English/tên riêng bị nhận nhầm → thêm vào `docs/tu_dien_ten/them.json` (PASS), không tắt cổng.
- Cổng CI `tests/test_json_keys_english.py` (LOW-229) chặn KHOÁ dict/JSON (`x["k"]`, `{"k": …}`, `.get("k")`, `dict(k=…)`) và ĐOẠN ĐƯỜNG DẪN (`… / "x"`, `Path/open/glob(...)`) tiếng Việt MỚI, so với mốc `docs/tu_dien_ten/vietnamese_keys_baseline.json` (còn ~40 chỗ có chủ đích: bảng đọc tên cũ, giá trị đã quyết giữ); trường của `schema.Manifest/Image/SidecarImage` phải English tuyệt đối. Nhận nhầm → PASS trong `them.json`; cố ý thêm (định dạng ngoài không đổi được) → `venv/bin/python tests/test_json_keys_english.py --write-baseline` và nói rõ lý do trong PR. Shim tên cũ LOW-50 đã gỡ hết (LOW-229) — không còn import tên Việt nào chạy được.

## 6. Đổi cách ra HÌNH thì phải dựng hình thật cho Ông Chủ xem trước khi deploy (LOW-286)

Áp cho mọi thay đổi ảnh hưởng tới hình xuất ra: nền chữ, bố cục, crop, cỡ chữ, ghép ảnh (`carousel.py`, `card.py`, `render_edu.py`, `crop_ratio.py`…).

- **Đọc lại luật hình đang có trước khi sửa** (`IMAGE_RULES_<vai>.md`, nhất là mục 6–7). Sửa một lời phàn nàn KHÔNG được phá một luật cũ. Bài học 19/09/2026: LOW-272 chữa "chữ nhoè" bằng nền đặc 30–47% khung, phá luật "chữ ~20% khung, nền chữ chỉ là overlay". Ông Chủ bác cùng ngày (LOW-286).
- **Dựng lại ít nhất 3 slide/thẻ THẬT** từ `state/<brand>/prepare/*/` trên máy chủ, bằng code nhánh, ra `/tmp` (không đụng production). Làm ảnh trước/sau và gửi Ông Chủ xem **trước khi merge/deploy**. Test chỉ chứng minh điều mình đã nghĩ tới, còn hình thật mới lộ điều mình chưa nghĩ tới.
- Luật hình mới được chốt thì khoá bằng **test + cổng đo trên pixel thật**, không chỉ ghi vào tài liệu. Mẫu: `carousel._gate_text_background`, `tests/test_low286_text_overlay.py`.

