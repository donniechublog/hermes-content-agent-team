#!/usr/bin/env python3
"""quet_nop.py — NOP cho ba vai di tim tin: ghi manifest danh so (kiem muc bat
buoc), viet bao cao, gui len topic. Vai chi viet picks.json (Finn) hoac ds.json
(Nova/Vera) theo khung cua quet_chuan_bi.py.

    --khong-co   khong co tin dat nguong: gui MOT dong "hom nay khong co gi" kem
                 so tin da quet (Ong Chu phan biet duoc voi "co gi do hong")
    --thu        chay het nhung KHONG gui Telegram, KHONG ghi manifest that,
                 KHONG xoa muc bat buoc

Dung:
    venv/bin/python quet_nop.py --vai scout|nova|market [--khong-co] [--thu]
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import quet_chung                                            # noqa: E402
import env_load                                              # noqa: E402
import quet_chuan_bi as qb                                   # noqa: E402

TEN = quet_chung.TEN_VAI       # mot ban duy nhat, xem quet_chung


# Nhan cua cac dong dang chu y trong stderr cua manifest_build / manifest_ghi.
# "[bo qua]" la loai NANG NHAT — mat tron mot tin — va truoc 06/09/2026 no KHONG
# nam trong bo loc: bo loc chi nhat [canh bao] / [tu them] / dong bat dau "- ",
# nen ca ba nhanh [bo qua] cua manifest_ghi (k ngoai danh sach, thieu title hoac
# link, link khong phai URL) khong bao gio duoc in. Chay thu voi Vera: mot muc
# go nham k=9 lam tin "OpenAI IPO dinh gia 900 ty USD" bien mat sach, KHONG mot
# dong canh bao nao, rc=0, va vai ket thuc task bao "da gui bao cao".
NHAN_CANH_BAO = ("[canh bao]", "[tu them]", "[bo qua]", "[LOI]")


def loc_canh_bao(stderr: str) -> list:
    """Cac dong stderr dang cho vai va Ong Chu doc (rc=0 KHONG co nghia la sach:
    script van ghi manifest khi da cat diem ngoai dai, doi category la, bo tin
    trung, cat theo tran, hay BO HAN mot tin)."""
    return [d.strip() for d in (stderr or "").splitlines()
            if d.strip() and (any(n in d for n in NHAN_CANH_BAO)
                              or d.strip().startswith("- "))]


def _chay(args: list, timeout=300):
    return subprocess.run([sys.executable] + args, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def _in_loi(r):
    for d in ((r.stderr or "") + "\n" + (r.stdout or "")).strip().splitlines():
        if d.strip():
            print(f"[LOI] {d.strip()}")


def gui(vai: str, tep: Path, thu: bool) -> bool:
    if thu:
        print(f"[thu] khong gui. Noi dung {tep}:\n" + tep.read_text(encoding="utf-8")[:1500])
        return True
    # --luu-mid: approve_service doi chieu REPLY cua Ong Chu dung vao MID nay
    # truoc khi coi la lenh chon so — xem ghi chu o _la_reply_bao_cao.
    mid_tep = env_load.state_dir() / f"bao_cao_mid.{vai}.json"
    r = subprocess.run([str(ROOT / "venv/bin/python"), str(ROOT / "publish.py"), "--to-env", "TELEGRAM_GROUP_ID",
                        "--thread-name", qb.TOPIC[vai], "--file", str(tep),
                        "--luu-mid", str(mid_tep)],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        _in_loi(r)
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop cho vai di tim tin")
    ap.add_argument("--vai", required=True, choices=list(qb.TOPIC))
    ap.add_argument("--khong-co", action="store_true")
    ap.add_argument("--thu", action="store_true")
    a = ap.parse_args()
    wd = qb.workdir(a.vai)
    state = env_load.state_dir()
    ngay = datetime.now(qb.VN).strftime("%Y-%m-%d")

    if a.khong_co:
        so = "?"
        if a.vai == "scout":
            d = json.loads((wd / "candidates.json").read_text(encoding="utf-8")) if (wd / "candidates.json").exists() else {}
            so = len(d.get("candidates", []))
        elif a.vai == "market":
            d = json.loads((wd / "quet.json").read_text(encoding="utf-8")) if (wd / "quet.json").exists() else {}
            so = d.get("tong_quet", "?")
        tep = wd / "khong_co.txt"
        tep.write_text(f"{TEN[a.vai]}: hôm nay không có tin nào đạt ngưỡng (đã quét {so} tin). "
                       "Không có gì để chọn.", encoding="utf-8")
        ok = gui(a.vai, tep, a.thu)
        print("Ket qua task: Không có tin đạt ngưỡng, đã báo Ông Chủ." if ok else "[LOI] gui bao cao hong")
        return 0 if ok else 1

    bao_cao = wd / "baocao.txt"
    if a.vai == "scout":
        picks = wd / "picks.json"
        if not picks.exists():
            sys.exit(f"Chua co {picks} — viet theo khung trong {wd / 'brief.md'} roi chay lai "
                     "(hoac --khong-co neu khong tin nao dat nguong).")
        out = (wd / "thu_manifest.json") if a.thu else (state / f"finn_candidates_{ngay}.json")
        args = [str(ROOT / "manifest_build.py"), "--candidates", str(wd / "candidates.json"),
                "--picks", str(picks), "--out", str(out), "--bao-cao", str(bao_cao)]
        if a.thu:
            args.append("--khong-xoa-bat-buoc")
    else:
        ds = wd / "ds.json"
        if not ds.exists():
            sys.exit(f"Chua co {ds} — viet theo khung trong {wd / 'brief.md'} roi chay lai "
                     "(hoac --khong-co neu khong co gi dang len kenh).")
        args = [str(ROOT / "manifest_ghi.py"), "--vai", a.vai, "--in", str(ds), "--bao-cao", str(bao_cao)]
        if a.vai == "market":
            args += ["--nguon", str(wd / "quet.json")]      # de Vera chon bang so thu tu k
        if a.thu:
            args += ["--khong-xoa-bat-buoc", "--out", str(wd / "thu_manifest.json")]
    r = _chay(args)
    if r.returncode != 0:
        _in_loi(r)
        tep = "picks.json" if a.vai == "scout" else "ds.json"
        print(f"\nSua {wd / tep} theo cac dong [LOI] (thieu muc bat buoc thi THEM vao, link phai y het "
              f"danh sach) roi chay lai: venv/bin/python quet_nop.py --vai {a.vai}")
        return 1
    print((r.stdout or "").strip()[-800:])
    # rc=0 KHONG co nghia la sach: manifest_build/manifest_ghi van ghi manifest
    # khi da cat diem ngoai dai, doi category la, bo tin trung hay cat theo tran
    # 8 tin. Truoc 06/09/2026 nhung dong do chi nam o stderr va bi nuot o day —
    # vai tuong moi thu binh thuong, Ong Chu khong bao gio biet.
    canh = loc_canh_bao(r.stderr)
    if canh:
        print("\n[SCRIPT DA SUA/CANH BAO] — bao cao gui di van tinh, nhung biet de lan sau nop dung:")
        for d in canh[:20]:
            print("  " + d)
    if not bao_cao.exists():
        sys.exit("[LOI] manifest xong nhung khong thay bao cao")
    ok = gui(a.vai, bao_cao, a.thu)
    if not ok:
        return 1
    # Bao cao la HTML Telegram, dong tin bat dau bang "<b>1." — bo the truoc khi
    # dem, khong thi in "nop 0 tin" va vai di doc ma nguon (Nova/Vera 05/09).
    n = sum(1 for d in bao_cao.read_text(encoding="utf-8").splitlines()
            if re.sub(r"<[^>]+>", "", d).strip()[:2].rstrip(".").isdigit())
    print(f"[xong] manifest + bao cao ({n} muc) da gui topic {qb.TOPIC[a.vai]}" + (" (thu)" if a.thu else ""))
    print(f"Ket qua task (dung dong nay de ket thuc task): {TEN[a.vai]} nộp {n} tin đánh số, đã gửi báo cáo, "
          "Ông Chủ trả lời số để chọn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
