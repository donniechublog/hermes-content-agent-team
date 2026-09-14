# Quy tắc worktree & push (tránh phiên/máy đè việc của nhau)

Bối cảnh: repo này được sửa từ nhiều máy (Mac này + 2 máy khác, mỗi máy một clone riêng), và nhiều phiên Claude Code có thể chạy song song trên cùng một máy. Không có isolation nào là mặc định — phải chủ động áp các quy tắc dưới đây.

## 1. Một tác vụ = một worktree

- Nếu có khả năng một phiên khác đang chạy trong thư mục gốc (`content-team/`), KHÔNG sửa/commit trực tiếp ở đó. Dùng `EnterWorktree` để lấy một worktree cô lập (`.claude/worktrees/<tên>`, nhánh riêng) trước khi động vào file.
- Dấu hiệu nghi có phiên khác đang chạy trong thư mục gốc: `git status` có nhiều file lạ đang sửa dở, hoặc `git reflog` của nhánh hiện tại có commit mới trong vài phút gần nhất mà bạn không phải người tạo. Khi nghi ngờ — dừng, kiểm tra trước (`git reflog`, `ps aux | grep -i claude`), đừng `checkout`/reset/ghi đè để "khôi phục".
- Xong việc: review diff, commit, rồi `ExitWorktree` — `remove` nếu đã merge/xong hẳn, `keep` nếu tạm dừng. Không bỏ worktree lửng lơ trên một nhánh cũ — đó cũng là một dạng "phiên khác" gây lẫn về sau.

## 2. Remotes & thứ tự push

- `origin` = `donniechu@donniechu-01.netbird.mated:/home/donniechu/content-team` — server có `receive.denyCurrentBranch=updateInstead`. **Push vào `origin` là deploy production ngay lập tức**, không phải một push bình thường.
- `github` = `donniechublog/hermes-content-agent-team` — remote an toàn, không side-effect, dùng làm nơi chốt/đồng bộ giữa 3 máy.
- Nhánh task (bất kể tạo từ máy nào) chỉ push lên `github`. Không push nhánh task lên `origin`.
- Chỉ `git push origin main` sau khi `main` đã chốt xong trên `github`. Coi đây là bước "bấm nút deploy" — làm riêng, có chủ đích, một nơi/một lúc — không phải việc mỗi phiên tự làm ngay khi xong task của mình.

## 3. `main` chỉ tiến ở một chỗ

- Merge vào `main` là một bước tuần tự, làm ở một chỗ (qua PR trên GitHub, hoặc một máy/phiên được chỉ định gác merge) — không phải máy nào xong việc trước thì tự merge/push `main` trước.

## 4. Không bao giờ force-push nhánh chung

- Luôn `git fetch` trước khi push. Bị từ chối "non-fast-forward" nghĩa là có người/máy khác đã push trước bạn — `git pull --rebase` rồi push lại. Không bao giờ `--force` qua một nhánh chung (đặc biệt `main`).
- Nếu cần dọn dẹp trong lúc làm việc, không dùng `git stash` / `git stash pop` trần — stash stack dùng chung giữa các worktree của repo, phiên khác có thể push/pop đè lên. Nếu bắt buộc phải stash, đặt tag riêng (`git stash push -u -m "<tag>"`) và `apply` theo SHA, không `pop`.

## 5. Đặt tên: mọi tên MỚI chỉ dùng English (LOW-129, Ông Chủ 14/09/2026)

- Áp cho mọi thứ tạo mới: biến, tham số, hàm, lớp, hằng, module/tệp, thư mục, khoá cấu hình mới, **tên nhánh và worktree**. Không đặt tên Việt không dấu nữa (`tim_anh_moi` ✗ → `find_new_image` ✓; `fix/cat-ngang-vision` ✗ → `fix/vision-horizontal-crop` ✓).
- Khái niệm đã có tên: tra `docs/tu_dien_ten/` để dùng đúng từ đã chốt, không tự dịch thành từ khác.
- Sửa tệp cũ: phần thêm mới vẫn English; KHÔNG tiện tay đổi tên cũ xung quanh. Đổi tên hàng loạt phải có ticket riêng và kiểm phiên khác trước (dùng `docs/tu_dien_ten/rename.py`).
- KHÔNG áp cho nội dung: chuỗi hiển thị, prompt/SOUL, nhật ký, commit message, tài liệu tiếng Việt giữ nguyên; khoá JSON/đường dẫn state đang chạy trên máy chủ không đổi.
- Cổng CI `tests/test_ten_english.py` (LOW-53) chặn tên top-level Việt quay lại; nó không xét biến cục bộ hay tên nhánh — phần đó dựa vào quy ước này. Đỏ vì từ English/tên riêng bị nhận nhầm → thêm vào `docs/tu_dien_ten/them.json` (PASS), không tắt cổng.
