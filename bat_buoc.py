#!/usr/bin/env python3
"""Danh sach BAT BUOC cho cac vai di tim tin (Finn/scout, Nova/nova, Vera/market).

Luat Ong Chu 04/09/2026: nguon/su kien ma script quet thay la PHAI dua vao
bao cao, vai khong duoc tu quyet "khong dang". Hom truoc sot thi hom sau bo
sung — muc nam trong danh sach cho toi khi thuc su co trong manifest.

Co che:
  - Script quet goi `them(vai, khoa, ten, loai, ghi_chu, link)` cho tung muc
    dat tieu chi tat dinh (top diem, watchlist, vao bang xep hang...). Trung
    khoa thi giu muc cu (ngay phat hien cu).
  - Script ghi manifest goi `kiem(vai, items)`: tra ve cac muc CHUA co trong
    danh sach vai nop. Tu 05/09/2026 script KHONG con tu choi ghi ma TU THEM
    muc thieu vao manifest kem ghi chu "vai bo sot" (het vong tu choi roi bat
    vai sua). Sau khi ghi thanh cong goi `xoa(vai, items)` de bo muc da dua.
  - Khop bang link (chuan hoa) hoac bang ten: xem `khop()`.

Tep: state/<brand>/bat_buoc_<vai>.json (runtime, gitignore).
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402


def tep(vai: str) -> Path:
    return env_load.state_dir() / f"bat_buoc_{vai}.json"


def doc(vai: str) -> dict:
    p = tep(vai)
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:                                        # noqa: BLE001
        return {}


def _ghi(vai: str, bb: dict) -> None:
    p = tep(vai)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(bb, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def them(vai: str, khoa: str, ten: str, loai: str, ghi_chu: str = "",
         link: str = "") -> bool:
    """Them mot muc; tra True neu la muc MOI."""
    bb = doc(vai)
    if khoa in bb:
        return False
    bb[khoa] = {"ten": ten, "loai": loai, "ghi_chu": ghi_chu, "link": link or "",
                "ngay": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    _ghi(vai, bb)
    return True


def them_nhieu(vai: str, muc: list) -> int:
    """muc = [(khoa, ten, loai, ghi_chu, link)]. Tra so muc moi."""
    bb = doc(vai)
    moi = 0
    hom_nay = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for m in muc:
        khoa, ten, loai, ghi_chu, link = m[:5]
        tu_khoa = list(m[5]) if len(m) > 5 and m[5] else []
        if khoa in bb:
            continue
        bb[khoa] = {"ten": ten, "loai": loai, "ghi_chu": ghi_chu,
                    "link": link or "", "ngay": hom_nay, "tu_khoa": tu_khoa}
        moi += 1
    if moi:
        _ghi(vai, bb)
    return moi


def chuan_link(u: str) -> str:
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    u = re.sub(r"[?#].*$", "", u)
    return u.rstrip("/")


def _chuan(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(t or "").lower())


def khop(muc: dict, item: dict) -> bool:
    if muc.get("link") and item.get("link"):
        if chuan_link(muc["link"]) == chuan_link(item["link"]):
            return True
    van_ban = _chuan((item.get("title") or "") + " " + (item.get("summary_vi") or ""))
    # `tu_khoa` (neu co): chi can DU cac tu khoa nay — dung cho tin "mot hang
    # mot ngay" cua Vera (Nvidia mua Hugging Face: 3 bao, Vera chon 1 bai).
    if muc.get("tu_khoa"):
        # Chi khop trong TIEU DE: tom tat bai khac nhac "OpenAI" khong tinh la
        # da dua tin OpenAI.
        tieu_de = _chuan(item.get("title") or "")
        return all(_chuan(t) in tieu_de for t in muc["tu_khoa"])
    # Ten khop nguyen khoi truoc: chac chan nhat, khong phu thuoc manh vun.
    ten_chuan = _chuan(muc.get("ten", ""))
    if ten_chuan and ten_chuan in van_ban:
        return True
    # Roi moi den tung manh. Nguong 2 ky tu (truoc 06/09/2026) khop gan nhu moi
    # tieu de: "v3", "ai", "4o" nam san trong van ban da bo ky hieu, nen mot muc
    # BAT BUOC bi coi la "da dua" trong khi bai noi chuyen khac. Doi thanh:
    # manh >= 3 ky tu, va phai co it nhat mot manh >= 4 ky tu lam neo.
    manh = [m for m in re.findall(r"[a-z0-9]+", str(muc.get("ten", "")).lower())
            if len(m) >= 3]
    if not manh or not any(len(m) >= 4 for m in manh):
        return False
    return all(m in van_ban for m in manh)


# Link cua bang xep hang theo `loai` — de brief in san URL cho muc BAT BUOC
# khong co link (Nova 05/09 mo 17 tool call grep repo tim link cho 15 muc).
LINK_BANG = {
    "text": "https://arena.ai/leaderboard/text",
    "webdev": "https://arena.ai/leaderboard/code/webdev",
    "vision": "https://arena.ai/leaderboard/vision",
    "search": "https://arena.ai/leaderboard/search",
    "image": "https://arena.ai/leaderboard/text-to-image",
    "image_edit": "https://arena.ai/leaderboard/image-edit",
    "video": "https://arena.ai/leaderboard/text-to-video",
    "coding": "https://artificialanalysis.ai/leaderboards/models",
    "tri_tue": "https://artificialanalysis.ai/leaderboards/models",
    "agentic": "https://artificialanalysis.ai/leaderboards/models",
    "ra_mat": "https://artificialanalysis.ai/leaderboards/models",
    "swebench": "https://www.swebench.com/",
    "swe_bash": "https://www.swebench.com/",
    "swe_da_ngon_ngu": "https://www.swebench.com/",
    "livebench": "https://livebench.ai/",
    "openrouter": "https://openrouter.ai/rankings",
    "tbench": "https://www.tbench.ai/leaderboard",
    "arcagi": "https://arcprize.org/leaderboard",
    "hle": "https://scale.com/leaderboard/humanitys_last_exam",
    "eci": "https://epoch.ai/data/ai-benchmarking-dashboard",
    "opencompass": "https://rank.opencompass.org.cn/home",
    "tts": "https://artificialanalysis.ai/text-to-speech",
    "stt": "https://artificialanalysis.ai/speech-to-text",
    "i2v": "https://artificialanalysis.ai/video/leaderboard/image-to-video",
}


def link_goi_y(muc: dict) -> str:
    """Link co san cua muc, khong co thi suy tu loai: model tren router ->
    trang model openrouter.ai/<id>; con lai -> trang bang xep hang."""
    if muc.get("link"):
        return muc["link"]
    loai, ten = muc.get("loai", ""), str(muc.get("ten", ""))
    if loai in ("router", "openrouter") and "/" in ten:
        return f"https://openrouter.ai/{ten.split(':')[0]}"
    return LINK_BANG.get(loai, "")


def kiem(vai: str, items: list) -> list:
    """Cac muc bat buoc CHUA co trong `items` (list dict co title/summary_vi/link)."""
    return [v for v in doc(vai).values() if not any(khop(v, it) for it in items)]


def xoa(vai: str, items: list) -> int:
    """Bo cac muc da co trong `items`. Tra so muc da bo."""
    bb = doc(vai)
    con = {k: v for k, v in bb.items() if not any(khop(v, it) for it in items)}
    _ghi(vai, con)
    return len(bb) - len(con)


def in_danh_sach(vai: str, tieu_de: str = "BAT BUOC DUA VAO BAO CAO") -> None:
    bb = doc(vai)
    if not bb:
        return
    print(f"\n=== {tieu_de} ({len(bb)}) — {vai} KHONG duoc bo; thieu thi script "
          "ghi manifest TU THEM va ghi ro 'vai bo sot' tren bao cao ===")
    for v in bb.values():
        print(f"  {v['ngay']}  [{v['loai']:<10s}] {str(v['ten'])[:60]:<61s} {v.get('ghi_chu', '')[:70]}")
        if v.get("link"):
            print(f"        {v['link'][:110]}")


