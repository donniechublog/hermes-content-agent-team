#!/usr/bin/env python3
"""Ghi file draft tu caption + metadata da biet truoc — tat dinh, khong LLM.

Truoc day writer phai tu go lai source_url / category / via / duong dan anh
vao JSON, du nhung gia tri nay Finn va vai dung anh da quyet tu truoc. Go tay
la co hoi go sai (lech dau, thieu truong, sai kieu). Script nay nhan caption
tu writer roi tu ghep phan con lai, nen khong the sai.

Metadata duoc nap tu file sidecar do approve_service tao san khi giao task:
  drafts/<draft_id>.meta.json
Neu khong co sidecar, co the truyen tay bang cac tham so dong lenh.
"""
import argparse
import json
import sys
from pathlib import Path

import env_load

DRAFTS = env_load.ROOT / "drafts"

# Draft da duoc Ong Chu duyet/len lich/dang: caption da CHOT, writer khong duoc
# ghi de nua (LOW-296). Truoc day nop lai sau khi Duyet van ghi de caption va
# dat lai status pending, bai dang ra khac ban Ong Chu da duyet tren the.
LOCKED_STATUSES = ("scheduled", "publishing", "published")

# Dau vet the duyet dang song tren Telegram (approve_service push ghi). Mang qua
# lan ghi lai draft de lan push sau biet xoa the cu thay vi them the moi.
PUSH_KEYS = ("tg_card_message_id", "tg_extra_message_ids", "tg_push_fingerprint")


def _read_prev(draft_id):
    p = DRAFTS / f"{draft_id}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def locked_reason(draft_id):
    """Ly do khong cho nop lai (chuoi), hoac None neu nop duoc."""
    st = _read_prev(draft_id).get("status")
    if st in LOCKED_STATUSES:
        return (f"Bài này đã được duyệt/lên lịch/đăng (trạng thái {st}): caption đã chốt, "
                "KHÔNG nộp lại được. Dừng ở đây, kết thúc task. Cần sửa thì báo Ông Chủ "
                "bấm Huỷ lịch rồi giao lại.")
    return None


def main():
    ap = argparse.ArgumentParser(
        description="Ghi draft JSON tu caption + metadata da biet")
    ap.add_argument("draft_id")
    ap.add_argument("--caption-file", required=True,
                    help="File chua caption (HTML Telegram) do writer viet")
    ap.add_argument("--source-url", help="Ghi de source_url tu sidecar")
    ap.add_argument("--category", help="Ghi de category tu sidecar")
    ap.add_argument("--via", help="Ghi de via tu sidecar")
    ap.add_argument("--image", help="Ghi de duong dan anh tu sidecar")
    ap.add_argument("--brand", help="Ghi de brand tu sidecar "
                    "(donniechublog | dcgr). Binh thuong khong can truyen.")
    ap.add_argument("--tu-lieu", help="Tep tu lieu de doi chieu do day du")
    ap.add_argument("--bo-qua-kiem", action="store_true",
                    help="Luu du caption khong dat (chi dung khi Ong Chu yeu cau)")
    a = ap.parse_args()

    meta_path = DRAFTS / f"{a.draft_id}.meta.json"
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    elif not (a.source_url and a.category):
        sys.exit(f"Khong tim thay {meta_path} va cung khong co --source-url/"
                 f"--category truyen tay. Khong du du lieu de ghi draft.")

    khoa = locked_reason(a.draft_id)
    if khoa:
        sys.exit("[LOI] " + khoa)

    caption = Path(a.caption_file).read_text(encoding="utf-8").strip()
    if not caption:
        sys.exit("Caption rong — khong ghi draft.")

    # Cong chan: caption hong thi KHONG luu draft. Bat loi co hoc o day re hon
    # nhieu so voi de no len toi hang duyet roi Ong Chu phai doc ra.
    import caption_check
    tl = ""
    if a.tu_lieu and Path(a.tu_lieu).exists():
        tl = Path(a.tu_lieu).read_text(encoding="utf-8")
    loi, canh, tin = caption_check.check(caption, tl)
    for c in canh:
        print(f"[nhac] {c}", file=sys.stderr)
    if loi and not a.bo_qua_kiem:
        for e in loi:
            print(f"[LOI] {e}", file=sys.stderr)
        sys.exit("Caption khong dat — sua roi chay lai. "
                 "(that su can giu thi them --bo-qua-kiem)")

    image = a.image or meta.get("image") or str(DRAFTS / f"{a.draft_id}.png")
    # Anh phu do vai dung anh tai ve: <draft>_2.png, _3.png... Gom san vao draft de
    # buoc dang gui thanh album. Nhieu anh that van hon mot anh chung chung.
    # Dung env_load.album_secondary (khong tu glob "_[0-9].png") vi mau do bo sot
    # slide thu 10 tro len — bug that lam mat slide 10 khoi album dang kenh.
    phu = env_load.album_secondary(a.draft_id, DRAFTS)
    images = [image] + [str(x) for x in phu] if phu else None
    draft = {
        "caption": caption,
        "image": image,
        **({"images": images} if images else {}),
        "source_url": a.source_url or meta.get("source_url", ""),
        "category": a.category or meta.get("category", "AI"),
        "via": a.via if a.via is not None else meta.get("via", ""),
        # Thuong hieu quyet dinh org ben moat luc bam Duyet. Roi ve
        # donniechublog khi thieu: do la mac dinh cua ca day chuyen.
        "brand": a.brand or meta.get("brand", "donniechublog"),
        "status": "pending",
        # Ban tin van Hiro (LOW-405): source_url chi la link tin #1 (cac cho can MOT link),
        # danh sach day du di kem de buoc dang/nguoi doc sau biet day la bo nhieu tin.
        **({"digest": True, "digest_links": meta.get("digest_links") or []} if meta.get("digest") else {}),
    }

    # Draft con pending: giu dau vet the dang song de push sau xoa the cu (LOW-296).
    # Trang thai khac (rejected/cancelled/...): the cu da doi thanh "da bo/huy",
    # khong xoa.
    prev = _read_prev(a.draft_id)
    if prev.get("status") == "pending":
        draft.update({k: prev[k] for k in PUSH_KEYS if k in prev})

    missing = [k for k in ("source_url", "category") if not draft[k]]
    if missing:
        sys.exit(f"Thieu truong bat buoc: {', '.join(missing)}")

    if not Path(image).exists():
        print(f"[canh bao] chua thay anh {image} — vai dung anh da chay xong chua?",
              file=sys.stderr)

    out = DRAFTS / f"{a.draft_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    env_load.write_json(out, draft)
    print(f"da ghi {out} | {len(caption)} ky tu caption")


if __name__ == "__main__":
    main()
