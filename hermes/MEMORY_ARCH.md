# Kiến trúc Memory — v0

Bản ghi quyết định cho hệ memory của đội (dcgr.tech + donniechublog). Bản CHẠY THẬT ở `~/.hermes-<brand>/` (mỗi brand một home từ 09/2026); thư mục `hermes/` trong repo là bản chép để có lịch sử (xem `dong_bo_hermes.py`).

## Ba lớp

1. **Built-in (per-profile, giữ NHỎ)** — `~/.hermes-<brand>/profiles/<vai>/memories/MEMORY.md` + `USER.md`, và profile mặc định `~/.hermes-<brand>/memories/`. Chỉ chứa thứ luôn-phải-biết. Giới hạn: MEMORY 2200 / USER 1375 ký tự.
2. **Retrieval = holographic (BỘ NÃO CHUNG)** — 1 file SQLite `memory_store.db` (đường dẫn tuyệt đối, đặt trong `db_path`), dùng chung cho **mọi persona + cả 2 dự án**. 0đ, không daemon, không API key. Recall = FTS5 keyword + HRR compositional (cần numpy).
3. **Obsidian** — hoãn (thêm sau khi recall thành nút thắt).

Kiến trúc Hermes **ép đúng 1 external provider**. Vì sao chọn holographic thay vì Hindsight/mem0: workload v0 (10–20 bài/ngày) ưu tiên nhẹ/ổn định/ít kinh phí; holographic không có chi phí trích xuất LLM, không dịch vụ ngoài. Đổi sang Hindsight khi mass adoption.

## Bộ não chung cho 2 dự án — QUY ƯỚC TAG

dcgr.tech và donniechublog **dùng chung 1 kho fact** vì researcher dùng chung. Trục chia là **project**, không phải handle.

Khi ghi qua `fact_store(action='add')`:
- Research / hạ tầng dùng chung → tag `shared`
- Fact brand / biên tập riêng dự án → tag `dcgr` hoặc `dnb`
- **Fact brand PHẢI nêu tên dự án ngay trong nội dung.**

Vì sao phải nêu tên trong nội dung: đã kiểm code holographic — `prefetch()` auto-recall gọi `search(query, limit=5)` **không scope**; `category` khóa cứng 4 giá trị (`user_pref/project/tool/general`); `search()` **không lọc theo tags** (chỉ cộng điểm). ⇒ 1 DB **không chặn cứng** lẫn brand ở auto-recall. Nêu tên dự án trong nội dung là cách duy nhất tránh lẫn giọng ở v0. Hard-separation thật để dành cho Hindsight (`bank_id` theo project).

Quy ước này được nhắc mỗi turn qua dòng "QUY ƯỚC TAG dự án" trong `MEMORY.md` của từng persona (marker để idempotent).

## Cấu hình để tái lập

Provider là **per-profile** (config global KHÔNG kế thừa sang profile). Sau `hermes update` hoặc trên máy mới, chạy lại:

```bash
cd ~/hermes-agent
DB=/home/donniechu/.hermes-blog/memory_store.db      # MỘT DB chung cho cả hai home
for H in ~/.hermes-blog ~/.hermes-dcgr; do
  # profile mặc định của home
  HERMES_HOME=$H venv/bin/python -m hermes_cli.main config set memory.provider holographic
  HERMES_HOME=$H venv/bin/python -m hermes_cli.main config set plugins.hermes-memory-store.db_path "$DB"
  # từng persona — lấy slug thật trong home, không liệt kê tay (slug cũ heller/dre/ethan/miles đã bỏ)
  for v in $(ls $H/profiles); do
    HERMES_HOME=$H/profiles/$v venv/bin/python -m hermes_cli.main config set memory.provider holographic
    HERMES_HOME=$H/profiles/$v venv/bin/python -m hermes_cli.main config set plugins.hermes-memory-store.db_path "$DB"
  done
done
```

`db_path` phải là **đường dẫn tuyệt đối** — nếu để `$HERMES_HOME/...` thì mỗi profile sẽ ra 1 DB riêng (không còn chung não).

Khôi phục nội dung MEMORY.md/USER.md: `dong_bo_hermes.py --ra-hermes` (repo → ~/.hermes).

## Giới hạn đã biết

- **numpy** cần cho HRR compositional (related/probe/reason). Runtime venv `~/hermes-agent/venv` đã có sẵn; `.venv` thì không. Fact ghi lúc thiếu numpy sẽ có `hrr_vector` NULL — cần backfill (`_compute_hrr_vector` + `_rebuild_bank`).
- **FTS5** hiểu dấu `-` là toán tử NOT, nên query `content-team` = `content NOT team`. Dùng term không dấu gạch.
- ~~**bob** không nằm trong danh sách đồng bộ~~ — sai từ lâu, sửa 06/09/2026: `cap_tep()` quét toàn bộ `profiles/{blog,dcgr,shared}/*.SOUL.md` nên bob luôn được đồng bộ như mọi vai. Từ 06/09/2026 SOUL của bob nằm ở `shared/`, còn MEMORY vẫn riêng từng brand (`profiles/<brand>/bob.MEMORY.md`).
- **SQLite 3.50.4** dính bug WAL-reset; holographic tự né bằng journal_mode=DELETE. `hermes update` nâng runtime SQLite.

## Đồng bộ & version

`dong_bo_hermes.py` đã mở rộng để đồng bộ thêm `MEMORY.md` (13 vai + mặc định) và `USER.md` mặc định. **USER.md riêng từng vai KHÔNG** đồng bộ (có thể chứa dữ liệu cá nhân). `memory_store.db` KHÔNG vào git (dữ liệu chạy, tự sinh lại). Lệnh: `--vao-repo` (trước commit) / `--ra-hermes` (sau update).
