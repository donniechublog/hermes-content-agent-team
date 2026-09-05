#!/usr/bin/env python3
"""Bảng đen kanban cho MỘT bài — lớp "kanban swarm" của content-team (05/09/2026).

Vì sao: Ông Chủ muốn các vai phối hợp trên một bài và NHÌN THẤY được, nhưng
không muốn mỗi vai một bot Telegram (giới hạn Telegram: bot không nhận lại tin
của chính nó, nên Dre nhắn Miles qua cùng một bot thì Miles điếc). Hermes có
sẵn `hermes_cli.kanban_swarm`: thẻ gốc làm bảng đen, bàn giao là comment có
cấu trúc, quan hệ cha-con là `task_links` — dashboard/notifier đọc được ngay.

Không dùng `create_swarm()` nguyên khối vì nó tạo verifier + synthesizer ngay
từ đầu và chạy thẳng worker → verifier → synthesizer, KHÔNG có chỗ cho cổng
"Ông Chủ duyệt ảnh" giữa Dre và Miles. Ở đây dùng đúng các viên gạch của nó
(thẻ gốc blocked→done, `post_blackboard_update`, `latest_blackboard`) và dựng
đồ thị dần theo tiến trình thật của bài:

    thẻ gốc "Bài: …"  (done ngay, assignee `ban_bien_tap` — không ai nhận việc)
      └─ task Dre (parent=gốc)          ← approve_service tạo khi Ông Chủ chọn số
           └─ task Miles (parent=Dre,gốc) ← tạo khi Ông Chủ bấm "Duyệt ảnh"

Mỗi vai kết thúc bằng `kanban_complete(summary, metadata)` — hermes tự đưa
summary/metadata đó vào context của task con ("Parent task results"), nên
Miles thấy Dre mà không ai phải "nhắn" ai. Bảng đen trên thẻ
gốc là bản ghi gộp toàn bộ chuỗi (đọc bằng `kanban_show(task_id=<gốc>)`).

Dùng (chạy bằng python của hermes-agent, HERMES_HOME của container):
    root    <draft_id> --title T [--goal G] [--author A]   -> in id thẻ gốc
    ghi     <draft_id> <key> <json | @tệp> [--author A]    -> ghi một mục bảng đen
    doc     <draft_id>                                     -> in bảng đen gộp (JSON)
    root-of <draft_id>                                     -> in id thẻ gốc (rỗng nếu chưa)

Mọi lệnh đều BEST-EFFORT với người gọi: lỗi thì in [bang-den] ... ra stderr,
exit 0 (trừ `root` — cần id thật). Bảng đen hỏng không được làm hỏng bài.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DRAFTS = ROOT / "drafts"
HERMES_DIR = Path.home() / "hermes-agent"
ROOT_ASSIGNEE = "ban_bien_tap"          # không phải profile: dispatcher không bao giờ nhận
TIEN_TO_BAI = "Bài: "


def _meta_path(draft_id: str) -> Path:
    return DRAFTS / f"{draft_id}.meta.json"


def _meta(draft_id: str) -> dict:
    p = _meta_path(draft_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return {}


def _ghi_meta(draft_id: str, meta: dict) -> None:
    DRAFTS.mkdir(parents=True, exist_ok=True)
    _meta_path(draft_id).write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                    encoding="utf-8")


def _chuan_home(draft_id: str) -> None:
    """HERMES_HOME quyết định kanban.db nào. Dispatcher đặt sẵn; chạy tay thì
    suy từ brand trong meta (dcgr -> ~/.hermes-dcgr). Đặt TRƯỚC khi import
    hermes_cli để mọi đường dẫn bên trong tính đúng."""
    if os.environ.get("HERMES_HOME"):
        return
    brand = (_meta(draft_id).get("brand") or "").strip()
    if brand and brand != "donniechublog":
        os.environ["HERMES_HOME"] = str(Path.home() / f".hermes-{brand}")
    elif brand == "donniechublog":
        os.environ["HERMES_HOME"] = str(Path.home() / ".hermes-blog")


def _kb():
    sys.path.insert(0, str(HERMES_DIR))
    from hermes_cli import kanban_db as kb                   # noqa: WPS433
    from hermes_cli import kanban_swarm as ks                # noqa: WPS433
    return kb, ks


def root_of(draft_id: str) -> str:
    return str(_meta(draft_id).get("root_task") or "")


def tao_root(draft_id: str, title: str, goal: str, author: str) -> tuple:
    """(root_id, moi_tao). Idempotent theo draft_id — gọi lại trả id cũ."""
    meta = _meta(draft_id)
    if meta.get("root_task"):
        return meta["root_task"], False
    kb, ks = _kb()
    tieu_de = (TIEN_TO_BAI + title)[:120]
    than = ("Thẻ gốc / bảng đen của bài. Xong ngay để các vai bắt đầu; giữ lại làm "
            "chỗ ghi bàn giao giữa Dre → Miles → Ada và làm neo cho dashboard.\n\n"
            f"Mục tiêu:\n{goal or title}")
    with kb.connect_closing() as conn:
        with kb.write_txn(conn):
            # workspace co dinh nhu approve_service.kanban_create: the goc khong
            # ai chay nen khong ton cache, nhung de dong bo va khong de scratch
            # de lai thu muc t_xxx rong moi bai.
            ws = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "kanban" / "workspaces" / "co-dinh"
            ws.mkdir(parents=True, exist_ok=True)
            rid = kb.create_task(
                conn, title=tieu_de, body=than, assignee=ROOT_ASSIGNEE,
                created_by=author, initial_status="blocked",
                workspace_kind="dir", workspace_path=str(ws),
                idempotency_key=f"bang_den:{draft_id}")
            t = kb.get_task(conn, rid)
            if t is not None and t.status == "blocked":
                if not ks._activate_root_inline(                 # noqa: SLF001
                        conn, rid,
                        summary="Thẻ gốc (bảng đen) của bài — không phải việc của ai.",
                        metadata={"kind": "bang_den_v1", "draft_id": draft_id}):
                    raise RuntimeError("không chuyển được thẻ gốc sang done")
        kb.recompute_ready(conn)
        ks.post_blackboard_update(conn, rid, author=author, key="bai",
                                  value={"draft_id": draft_id, "title": title})
    meta["root_task"] = rid
    _ghi_meta(draft_id, meta)
    return rid, True


def ghi(draft_id: str, key: str, value, author: str) -> bool:
    rid = root_of(draft_id)
    if not rid:
        print(f"[bang-den] {draft_id}: chưa có thẻ gốc, bỏ qua mục '{key}'", file=sys.stderr)
        return False
    kb, ks = _kb()
    with kb.connect_closing() as conn:
        ks.post_blackboard_update(conn, rid, author=author, key=key, value=value)
    return True


def ghi_nen(draft_id: str, key: str, value, author: str = "script", hermes_home=None) -> tuple:
    """Ghi mot muc len bang den bang PYTHON CUA HERMES trong tien trinh con — de
    script chay trong venv content-team (khong co hermes_cli) goi duoc.
    Best-effort: tra ve (ok, thong_bao), khong nem. `hermes_home` None = thua ke
    moi truong (dispatcher/systemd da dat, hoac _chuan_home suy tu brand);
    dat gia tri thi ep HERMES_HOME cho tien trinh con.
    Truoc 05/09/2026 doan nay chep bon ban o dre_nop/kite_nop/miles_nop/approve_service."""
    import subprocess
    sys.path.insert(0, str(ROOT))
    import env_load
    env = dict(os.environ, HERMES_HOME=str(hermes_home)) if hermes_home else None
    try:
        r = subprocess.run([str(env_load.HERMES_PY), str(Path(__file__).resolve()), "ghi", draft_id, key,
                            json.dumps(value, ensure_ascii=False), "--author", author],
                           cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=60)
    except Exception as e:                                   # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"
    if r.returncode != 0 or "[bang-den] lỗi" in (r.stderr or ""):
        return False, (r.stderr or r.stdout).strip()[-200:]
    return True, ""


def doc(draft_id: str) -> dict:
    rid = root_of(draft_id)
    if not rid:
        return {}
    kb, ks = _kb()
    with kb.connect_closing() as conn:
        return ks.latest_blackboard(conn, rid)


def _gia_tri(raw: str):
    if raw.startswith("@"):
        raw = Path(raw[1:]).read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw                       # chuỗi thường cũng là một giá trị hợp lệ


def main() -> int:
    ap = argparse.ArgumentParser(description="Bảng đen kanban của một bài")
    sub = ap.add_subparsers(dest="lenh", required=True)
    p = sub.add_parser("root");     p.add_argument("draft_id")
    p.add_argument("--title", required=True); p.add_argument("--goal", default="")
    p.add_argument("--author", default=os.environ.get("HERMES_PROFILE") or "approve_service")
    p = sub.add_parser("ghi");      p.add_argument("draft_id"); p.add_argument("key")
    p.add_argument("value", help="JSON, chuỗi thường, hoặc @tệp")
    p.add_argument("--author", default=os.environ.get("HERMES_PROFILE") or "script")
    p = sub.add_parser("doc");      p.add_argument("draft_id")
    p = sub.add_parser("root-of");  p.add_argument("draft_id")
    a = ap.parse_args()

    _chuan_home(a.draft_id)
    if a.lenh == "root-of":
        print(root_of(a.draft_id))
        return 0
    if a.lenh == "doc":
        print(json.dumps(doc(a.draft_id), ensure_ascii=False, indent=2))
        return 0
    if a.lenh == "root":
        rid, moi = tao_root(a.draft_id, a.title, a.goal, a.author)
        print(f"[bang-den] thẻ gốc {'mới' if moi else 'đã có'}: {rid}", file=sys.stderr)
        print(rid)                       # dòng cuối stdout = id, để script khác đọc
        return 0
    try:                                 # ghi: best-effort
        ok = ghi(a.draft_id, a.key, _gia_tri(a.value), a.author)
        print(f"[bang-den] {'đã ghi' if ok else 'bỏ qua'} '{a.key}' cho {a.draft_id}",
              file=sys.stderr)
    except Exception as e:                                   # noqa: BLE001
        print(f"[bang-den] lỗi ghi '{a.key}': {type(e).__name__}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
