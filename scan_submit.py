#!/usr/bin/env python3
"""scan_submit.py — NOP cho ba vai di tim tin: ghi manifest danh so (kiem muc bat
buoc), viet bao cao, gui len topic. Vai chi viet picks.json (Finn) hoac list.json
(Nova/Vera) theo khung cua scan_prepare.py.

    --khong-co   khong co tin dat nguong: gui MOT dong "hom nay khong co gi" kem
                 so tin da quet (Ong Chu phan biet duoc voi "co gi do hong")
    --thu        chay het nhung KHONG gui Telegram, KHONG ghi manifest that,
                 KHONG xoa muc bat buoc

Dung:
    venv/bin/python scan_submit.py --vai finn|nova|vera|qinn [--khong-co] [--thu]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import scan_common                                            # noqa: E402
import env_load                                              # noqa: E402
import scan_prepare as qb                                   # noqa: E402
import role                                                   # noqa: E402
import state_paths                                           # noqa: E402

NAME = scan_common.NAME_ROLE       # mot ban duy nhat, xem scan_common

# LOW-283 (19/09/2026): vai quet -> (brand nhan phan du, so tin toi da mot bao
# cao). Ong Chu: Vera quet ra hon 15 headline thi san bot qua blog, chia theo
# thu tu Vera nop (manifest_write.split_overflow). Chi bat khi brand dich DA CO
# topic cho vai nay (overflow_target) — chua tao topic thi giu hanh vi cu.
OVERFLOW = {"vera": ("blog", 15)}


def overflow_target(vai: str):
    """(brand dich, tran) neu vai nay duoc chuyen phan du VA brand dich co topic
    cua vai; nguoc lai None. Khong bao gio tro ve chinh container dang chay."""
    cfg = OVERFLOW.get(vai)
    if not cfg:
        return None
    brand, cap = cfg
    if brand == os.environ.get("CT_BRAND", "").strip():
        return None
    if qb.TOPIC[vai] not in env_load.topics(brand):
        return None
    return brand, cap


def overflow_manifest_path(stdout: str):
    """Manifest phan du, doc tu dong `overflow -> <duong dan>` cua manifest_write."""
    for d in (stdout or "").splitlines():
        if d.startswith("overflow -> "):
            p = Path(d[len("overflow -> "):].strip())
            return p if p.exists() else None
    return None


# Nhan cua cac dong dang chu y trong stderr cua manifest_build / manifest_write.
# "[bo qua]" la loai NANG NHAT — mat tron mot tin — va truoc 06/09/2026 no KHONG
# nam trong bo loc: bo loc chi nhat [canh bao] / [tu them] / dong bat dau "- ",
# nen ca ba nhanh [bo qua] cua manifest_write (k ngoai danh sach, thieu title hoac
# link, link khong phai URL) khong bao gio duoc in. Chay thu voi Vera: mot muc
# go nham k=9 lam tin "OpenAI IPO dinh gia 900 ty USD" bien mat sach, KHONG mot
# dong canh bao nao, rc=0, va vai ket thuc task bao "da gui bao cao".
LABEL_WARNING = ("[canh bao]", "[tu them]", "[bo qua]", "[LOI]")

# Nhung dong trong so do CHAN HAN viec gui: ban bao cao nay khong duoc len topic.
# Hai loai, va ca hai xay ra THAT trong MOT task cua Vera sang 12/09/2026:
#   [bo qua]        mat tron mot tin. Vai ghi k="#15" thay vi "15" -> 20/27 muc
#                   roi het, ban gui di chi con 4 muc BAT BUOC.
#   title mat dau   headline ASCII ("dat muc tieu 2 ty USD doanh thu nam") — ma
#                   headline la thu DUY NHAT Ong Chu doc tren topic.
# Truoc day hai loai nay chi duoc IN ra roi van gui, rc=0. Vai doc canh bao, sua
# list.json, chay lai — va moi lan chay lai la MOT bao cao nua vao topic. Sang hom
# do Ong Chu nhan BA ban gan giong nhau; reply vao ban thu hai thi khong co gi
# xay ra, vi `--luu-mid` chi giu mid cua ban CUOI (xem _is_reply_report).
# Chan o day thi chi ban sach moi len topic: mot lan quet, mot bao cao.
BLOCK_SEND = ("[bo qua]", "title tieng Viet mat dau")


def error_block_send(canh: list) -> list:
    """Cac dong trong `canh` khien bao cao KHONG duoc gui.

    Nhung canh bao con lai VAN gui: `[tu them]` (script da tu sua), summary_vi
    dai (script co y giu nguyen), muc BAT BUOC khong co link (vai khong sua
    duoc — chan la ket task ma Ong Chu khong nhan duoc gi ca)."""
    return [d for d in canh if any(n in d for n in BLOCK_SEND)]


def path_manifest(stdout: str):
    """Manifest vua ghi, doc tu stdout cua manifest_write / manifest_build.

    Hai script in khac nhau (`<duong dan>` va `da ghi N muc -> <duong dan>`) nen
    khong bam theo so dong: lay token cuoi cua tung dong, nhan cai nao la tep
    .json co that. None = khong nhan ra (nguoi goi bo qua viec ghim)."""
    for d in (stdout or "").splitlines():
        tok = d.strip().split()[-1] if d.strip() else ""
        if tok.endswith(".json") and Path(tok).exists():
            return Path(tok)
    return None


def pin_manifest(mid_tep: Path, manifest: Path) -> None:
    """Ghim duong dan manifest vao tep mid, NGAY SAU khi gui thanh cong.

    Vi sao can ghim: approve_pick truoc day tu doan bang `latest_manifest`
    (ban moi nhat theo mtime). Dieu do chi dung khi moi lan ghi manifest deu
    ket thuc bang mot lan GUI — tu khi co cong BLOCK_SEND thi khong con: lan chay
    bi chan van ghi manifest moi, roi Ong Chu tra loi so tren bao cao CU (mid cu
    van khop) va so do tro vao mot ban CHUA AI NHIN THAY. Ghim thi so thu tu
    luon doc tren dung ban da gui.

    Best-effort: ghim hong khong duoc lam hong viec da gui xong (approve_pick
    lui ve latest_manifest nhu cu)."""
    try:
        d = json.loads(mid_tep.read_text(encoding="utf-8"))
        d["manifest"] = str(manifest)
        mid_tep.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError) as e:
        print(f"[canh bao] khong ghim duoc manifest vao {mid_tep}: {e}")


REPORT_HISTORY_KEEP = 200          # so bao cao cu con reply duoc (moi vai ~3 bao cao/ngay)


def record_report_history(mid_tep: Path, history: Path) -> None:
    """Noi {message_ids, manifest, ts} cua bao cao VUA GUI vao lich su (LOW-362).

    Ong Chu 22/09/2026: "duoc phep reply 1 so nhieu lan vao researcher" — ke ca bao cao
    CU. Tep mid (`report_message_id.<vai>.json`) bi ghi de moi lan gui nen chi nho bao
    cao moi nhat; lich su nay cho approve_pick tra mid cua bao cao cu ve DUNG manifest
    cua no. Best-effort nhu pin_manifest."""
    try:
        d = json.loads(mid_tep.read_text(encoding="utf-8"))
        if not d.get("manifest") or not d.get("message_ids"):
            return
        dong = history.read_text(encoding="utf-8").splitlines() if history.exists() else []
        dong.append(json.dumps({"message_ids": d["message_ids"], "manifest": d["manifest"],
                                "ts": d.get("ts")}, ensure_ascii=False))
        history.write_text("\n".join(dong[-REPORT_HISTORY_KEEP:]) + "\n", encoding="utf-8")
    except (OSError, ValueError) as e:
        print(f"[canh bao] khong ghi duoc lich su bao cao {history}: {e}")


def filter_warning(stderr: str) -> list:
    """Cac dong stderr dang cho vai va Ong Chu doc (rc=0 KHONG co nghia la sach:
    script van ghi manifest khi da cat diem ngoai dai, doi category la, bo tin
    trung, cat theo tran, hay BO HAN mot tin)."""
    return [d.strip() for d in (stderr or "").splitlines()
            if d.strip() and (any(n in d for n in LABEL_WARNING)
                              or d.strip().startswith("- "))]


def nothing_found_block(candidates: list) -> list:
    """Cac dong khien "hom nay khong co tin nao dat nguong" KHONG duoc gui (LOW-317).

    Diem CO HOC (`score_partial` = moi + lan, script tu cham) la SAN TREN cua
    diem tong: vai chi cong them technical (0-30) va relevance (0-20), khong bao
    gio tru. Nen mot tin da >= `SCORE_PASS` diem co hoc thi CHAC CHAN dat nguong
    du vai cham the nao — noi "khong co tin nao dat nguong" luc do la sai, kiem
    duoc bang may, khong can phan doan.

    Su co 20/09/2026: Finn chay `--khong-co` khi chua viet picks.json; topic blog
    nhan "hom nay khong co tin nao dat nguong (da quet 35 tin)" trong khi 3 tin
    da 50 diem co hoc. Blog mat tron mot ngay tin."""
    cao = sorted((c for c in candidates if (c.get("score_partial") or 0) >= scan_common.SCORE_PASS),
                 key=lambda c: -(c.get("score_partial") or 0))
    if not cao:
        return []
    dong = [f"[LOI] KHONG gui 'hom nay khong co gi': {len(cao)} tin da >= "
            f"{scan_common.SCORE_PASS} diem CO HOC truoc khi cong technical + relevance, "
            "tuc chac chan dat nguong."]
    for c in cao[:3]:
        dong.append(f"  {c.get('score_partial')}d | {str(c.get('title', ''))[:70]}")
    if len(cao) > 3:
        dong.append(f"  ... va {len(cao) - 3} tin nua")
    return dong


def _run(args: list, timeout=300):
    return subprocess.run([sys.executable] + args, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def _in_error(r):
    for d in ((r.stderr or "") + "\n" + (r.stdout or "")).strip().splitlines():
        if d.strip():
            print(f"[LOI] {d.strip()}")


def send(vai: str, tep: Path, thu: bool, manifest: Path = None, brand: str = None) -> bool:
    """`brand` (LOW-283): gui vao group/topic cua brand KHAC container dang chay —
    publish.py chay voi env sach cua brand do (env_load.env_for_brand), mid ghi
    vao state cua brand do de approve ben kia doi chieu reply."""
    if thu:
        print(f"[thu] khong gui{f' (sang {brand})' if brand else ''}. Noi dung {tep}:\n"
              + tep.read_text(encoding="utf-8")[:1500])
        return True
    # --luu-mid: approve_service doi chieu REPLY cua Ong Chu dung vao MID nay
    # truoc khi coi la lenh chon so — xem ghi chu o _is_reply_report.
    mid_tep = env_load.state_dir(brand) / state_paths.REPORT_MESSAGE_ID_FILE.format(vai)
    r = subprocess.run([str(ROOT / "venv/bin/python"), str(ROOT / "publish.py"), "--to-env", "TELEGRAM_GROUP_ID",
                        "--thread-name", qb.TOPIC[vai], "--file", str(tep),
                        "--luu-mid", str(mid_tep)],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120,
                       env=env_load.env_for_brand(brand) if brand else None)
    if r.returncode != 0:
        _in_error(r)
        return False
    if manifest:
        pin_manifest(mid_tep, manifest)
        record_report_history(mid_tep, env_load.state_dir(brand) / state_paths.REPORT_HISTORY_FILE.format(vai))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop cho vai di tim tin")
    ap.add_argument("--vai", required=True, type=role.canonical_slug, choices=list(qb.TOPIC))
    ap.add_argument("--khong-co", action="store_true")
    ap.add_argument("--thu", action="store_true")
    a = ap.parse_args()
    wd = qb.workdir(a.vai)
    state = env_load.state_dir()
    ngay = datetime.now(qb.VN).strftime("%Y-%m-%d")

    if a.khong_co:
        scanned = "?"
        if a.vai == "finn":
            d = json.loads((wd / "candidates.json").read_text(encoding="utf-8")) if (wd / "candidates.json").exists() else {}
            scanned = len(d.get("candidates", []))
            chan = nothing_found_block(d.get("candidates") or [])
            if chan:
                for dong in chan:
                    print(dong)
                print(f"\nCham diem roi viet {wd / 'picks.json'} theo khung trong {wd / 'brief.md'}, "
                      f"roi chay lai: venv/bin/python scan_submit.py --vai {a.vai}")
                return 1
        elif a.vai in ("vera", "qinn"):
            d = json.loads((wd / state_paths.SCAN_RESULT_FILE).read_text(encoding="utf-8")) if (wd / state_paths.SCAN_RESULT_FILE).exists() else {}
            scanned = d.get("scanned_total", "?")
        tep = wd / state_paths.SCAN_NONE_FOUND_FILE
        tep.write_text(f"{NAME[a.vai]}: hôm nay không có tin nào đạt ngưỡng (đã quét {scanned} tin). "
                       "Không có gì để chọn.", encoding="utf-8")
        ok = send(a.vai, tep, a.thu)
        print("Ket qua task: Không có tin đạt ngưỡng, đã báo Ông Chủ." if ok else "[LOI] gui bao cao hong")
        return 0 if ok else 1

    bao_cao = wd / state_paths.SCAN_REPORT_FILE
    if a.vai == "finn":
        picks = wd / "picks.json"
        if not picks.exists():
            sys.exit(f"Chua co {picks} — viet theo khung trong {wd / 'brief.md'} roi chay lai "
                     "(hoac --khong-co neu khong tin nao dat nguong).")
        out = (wd / state_paths.SCAN_TRIAL_MANIFEST_FILE) if a.thu else (state / f"finn_candidates_{ngay}.json")
        args = [str(ROOT / "manifest_build.py"), "--candidates", str(wd / "candidates.json"),
                "--picks", str(picks), "--out", str(out), "--bao-cao", str(bao_cao)]
        if a.thu:
            args += ["--khong-xoa-bat-buoc", "--ghi-de"]   # ban thu ghi de duoc
    else:
        ds = wd / state_paths.SCAN_LIST_FILE
        if not ds.exists():
            sys.exit(f"Chua co {ds} — viet theo khung trong {wd / 'brief.md'} roi chay lai "
                     "(hoac --khong-co neu khong co gi dang len kenh).")
        args = [str(ROOT / "manifest_write.py"), "--vai", a.vai, "--in", str(ds), "--bao-cao", str(bao_cao)]
        if a.vai in ("vera", "qinn"):
            # de vai chon bang so thu tu k; script tu lay link tu scan.json
            args += ["--nguon", str(wd / state_paths.SCAN_RESULT_FILE)]
        if a.thu:
            args += ["--khong-xoa-bat-buoc", "--out", str(wd / state_paths.SCAN_TRIAL_MANIFEST_FILE)]
        dich = overflow_target(a.vai)
        if dich:
            args += ["--overflow-brand", dich[0], "--overflow-after", str(dich[1]),
                     "--overflow-report", str(wd / state_paths.SCAN_OVERFLOW_REPORT_FILE)]
            if a.thu:
                args += ["--overflow-out", str(wd / state_paths.SCAN_TRIAL_OVERFLOW_MANIFEST_FILE)]
    r = _run(args)
    if r.returncode != 0:
        _in_error(r)
        tep = "picks.json" if a.vai == "finn" else state_paths.SCAN_LIST_FILE
        print(f"\nSua {wd / tep} theo cac dong [LOI] (thieu muc bat buoc thi THEM vao, link phai y het "
              f"danh sach) roi chay lai: venv/bin/python scan_submit.py --vai {a.vai}")
        return 1
    print((r.stdout or "").strip()[-800:])
    # rc=0 KHONG co nghia la sach: manifest_build/manifest_write van ghi manifest
    # khi da cat diem ngoai dai, doi category la, bo tin trung hay cat theo tran
    # 8 tin. Truoc 06/09/2026 nhung dong do chi nam o stderr va bi nuot o day —
    # vai tuong moi thu binh thuong, Ong Chu khong bao gio biet.
    canh = filter_warning(r.stderr)
    chan = error_block_send(canh)
    if canh:
        print("\n[CANH BAO] — ban gui di bi chan, xem ly do o cuoi:" if chan else
              "\n[SCRIPT DA SUA/CANH BAO] — bao cao gui di van tinh, nhung biet de lan sau nop dung:")
        for d in canh[:20]:
            print("  " + d)
    if chan:
        tep = "picks.json" if a.vai == "finn" else state_paths.SCAN_LIST_FILE
        print(f"\n[LOI] KHONG GUI bao cao: {len(chan)} loi lam hong chinh ban Ong Chu doc "
              "(mat tin, hoac tieu de tieng Viet mat dau).")
        print(f"Sua {wd / tep} theo cac dong tren roi chay lai DUNG lenh: "
              f"venv/bin/python scan_submit.py --vai {a.vai}")
        print("Moi lan chay lai deu gui THEM mot bao cao vao topic neu khong chan o day — "
              "Ong Chu chi duoc nhan MOT ban cho moi lan quet, va chi reply vao ban do moi ra bai.")
        return 1
    if not bao_cao.exists():
        sys.exit("[LOI] manifest xong nhung khong thay bao cao")
    ok = send(a.vai, bao_cao, a.thu, path_manifest(r.stdout))
    if not ok:
        return 1
    n = _count_items(bao_cao)
    print(f"[xong] manifest + bao cao ({n} muc) da gui topic {qb.TOPIC[a.vai]}" + (" (thu)" if a.thu else ""))
    them = _send_overflow(a.vai, wd, a.thu, overflow_manifest_path(r.stdout))
    hiro = "" if a.thu else _auto_hiro(a.vai, path_manifest(r.stdout))
    print(f"Ket qua task (dung dong nay de ket thuc task): {NAME[a.vai]} nộp {n} tin đánh số, đã gửi báo cáo, "
          "Ông Chủ trả lời số để chọn." + them + hiro)
    return 0


def _auto_hiro(vai: str, manifest) -> str:
    """LOW-406: `/hiro on` -> Hiro tu dung ban tin tu bao cao VUA gui (tren 10 tin lay 10 tin
    dau). Chi bao cao CHINH cua container nay; phan du sang brand khac (OVERFLOW) thi Ong Chu
    reply `Hiro` ben do. KHONG BAO GIO nem: bao cao da len topic roi (xem _send_overflow)."""
    try:
        import hiro_pick                                     # tre: keo approve_*, chi khi can
        return hiro_pick.auto_from_report(vai, manifest)
    except Exception as e:                                   # noqa: BLE001
        print(f"[CANH BAO] Hiro tu dong loi: {type(e).__name__}: {e}")
        return f" ⚠️ Hiro tự động lỗi ({type(e).__name__}), chưa dựng bản tin."


def _count_items(bao_cao: Path) -> int:
    # Bao cao la HTML Telegram, dong tin bat dau bang "<b>1." — bo the truoc khi
    # dem, khong thi in "nop 0 tin" va vai di doc ma nguon (Nova/Vera 05/09).
    return sum(1 for d in bao_cao.read_text(encoding="utf-8").splitlines()
               if re.sub(r"<[^>]+>", "", d).strip()[:2].rstrip(".").isdigit())


def _send_overflow(vai: str, wd: Path, thu: bool, manifest) -> str:
    """Gui bao cao phan du sang brand dich SAU khi bao cao chinh da len. Tra ve
    doan them vao dong "Ket qua task" ("" neu khong co phan du).

    Hong o day KHONG tra ma loi: bao cao chinh da gui roi, ma vai thay rc!=0 thi
    chay lai — tuc gui THEM mot ban bao cao chinh (dung su co 12/09, xem
    BLOCK_SEND). Thay vao do noi to trong dong ket qua cho Ong Chu doc."""
    if manifest is None:
        return ""
    dich = OVERFLOW[vai][0]
    tep = wd / state_paths.SCAN_OVERFLOW_REPORT_FILE
    m = _count_items(tep) if tep.exists() else 0
    if tep.exists() and send(vai, tep, thu, manifest, brand=dich):
        print(f"[xong] phan du ({m} muc) da gui topic {qb.TOPIC[vai]} ben {dich}" + (" (thu)" if thu else ""))
        return f" {m} tin dư đã chuyển sang topic {NAME[vai]} bên {dich}."
    print(f"[LOI] KHONG gui duoc phan du ({m} muc) sang {dich} — manifest van nam o {manifest}")
    return (f" ⚠️ Gửi {m} tin dư sang {dich} HỎNG — các tin này chưa tới topic {NAME[vai]} bên {dich} "
            "(đừng chạy lại lệnh nộp: báo cáo chính đã gửi).")


if __name__ == "__main__":
    sys.exit(main())
