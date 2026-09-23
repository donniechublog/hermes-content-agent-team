#!/usr/bin/env python3
"""Kho nho DA-THAY dung chung cho MOI vai researcher (Finn/Nova/Vera/Qinn).

LUAT (Ong Chu 23/09/2026, LOW-375): *"chung ta ko dan lai tin da research
duoc"*. Mot muc da DUA VAO BAO CAO cho mot vai thi khong bao gio duoc dua lai
cho chinh vai do.

Truoc LOW-375 moi vai tu viet lay mot ban: Vera va Qinn dung, Finn va Nova
thieu han. Do 23/09 tren may chu: 9/20 dong bao cao Nova ngay 23/09 la model
da nam trong bao cao 22/09; muc "TIN TU HANG" lap 9/10 giua 21/09 va 22/09.

SAU LUAT DUOI DAY, MOI LUAT MOT VET SEO CO THAT. Dong goi o day MOT LAN de
khong vai nao phai tra gia lai:

1. CAT THEO THOI GIAN — khong theo so, khong theo bang chu cai.
   `scan_business` ban cu dung `sorted(khoa)[-2000:]`: cat theo BANG CHU CAI,
   nen tin bat dau a-m bi day ra khoi bo nho va bao lai mai, con tin bat dau z
   khong bao gio duoc quen.

2. DOC TEP CU, CHI THAY TRUONG CUA MINH.
   `scan_business` ban cu ghi de ca tep chi voi hai truong -> xoa mat `note`
   (ghi chu su co 26/08 bay theo cach nay). `scan_models.write_timestamp` con
   ghi mot dict CO DINH bon khoa, nen bat ky truong moi nao cung bi chinh no
   xoa o lan chay ke tiep.

3. DANH DAU LUC BAO, KHONG PHAI LUC QUET.
   Xem `scan_business`: *"Tin bi cat hom nay, mai van con moi thi van len
   duoc"*. Danh dau ca phan bi `--top` cat la bien van an toan thanh may xoa
   tin — vai se khong bao gio nhin thay chung nua.

4. TEP HONG THI DOI TEN `.hong`, CHAY TIEP VOI KHO RONG, NOI TO MOT DONG.
   Im lang tra {} la mat sach kho that: lan ghi ngay sau do ghi de bang muc
   cua hom nay. Xem `required.read` va `scan_models.read_state`.

5. GHI NGUYEN TU, TEN TEP TAM MANG PID (`env_load.write_json`).
   Ten `.json.tmp` co dinh + hai tien trinh cung ghi = `replace` ban cut cua
   nhau. Bon vai cung chay 22:00 UTC, va Qinn chay hai luot mot ngay.

6. `keep_days` >= 2 x CUA SO QUET, va script nao dung kho nay cung phai co co
   `--state` de test khong dung kho production. Su co 26/08: chay `--lan-dau`
   luc test lam ghi de `business_seen.json` that, danh dau nham tin chua bao
   la da thay.

KHOA phai la DINH DANH ON DINH, khong bao gio la tieu de hay ngay thang.
Do 23/09 (LOW-375): cung `convaiinnovations/laya` ma 22/09 bao la "dung dau
trending", 23/09 bao la "tha trong so"; `Altworld/Hemmingway-1` ghi 20/09 roi
lai ghi 16/09. Loc bang chu hay bang ngay deu hong.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402

# Truong giu bo nho trong tep JSON. Dung DUNG ten ma Vera/Qinn da ghi tu truoc
# (`seen_at`) de khong phai migrate mot kho nao dang chay.
SEEN_FIELD = "seen_at"

# Mac dinh du rong cho moi vai: cua so quet lon nhat dang co la 7 ngay (Nova),
# 30 ngay cho gap hon bon lan. Kho ~90 khoa/ngay cua Vera o muc nay la ~2.700
# khoa (~270KB) — khong dang de tiet kiem.
KEEP_DATE_DEFAULT = 30


class SeenStore:
    """Bo nho da-thay cua MOT vai, nam trong MOT tep JSON.

    Hinh dang tep giu nguyen kieu Vera/Qinn dang dung, va cac truong khac cua
    tep KHONG bi dung toi:

        {"updated_at": "<iso>", "seen_at": {"<khoa>": <unix_ts>}, ...}

    Nova gan `seen_at` NGAY CANH `ids`/`rankings`/`aa_reported` trong chinh
    `models_seen.json` — ba truong do khong phai viec cua lop nay.
    """

    def __init__(self, path, keep_days: int = KEEP_DATE_DEFAULT,
                 field: str = SEEN_FIELD, window_days: float = 0):
        self.path = Path(path)
        self.field = field
        # Luat 6: kho phai nho lau hon HAI LAN cua so quet. Ngan hon thi mot
        # muc roi khoi kho trong khi van con trong cua so -> quay lai bao cao.
        if window_days and keep_days < 2 * window_days:
            keep_days = int(2 * window_days)
        self.keep_days = keep_days

    # ---- doc -----------------------------------------------------------
    def _raw(self) -> dict:
        """Ca tep, da boc loi. Luat 4: hong thi doi ten va noi to."""
        if not self.path.exists():
            return {}
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:                               # noqa: BLE001
            hong = self.path.with_suffix(".json.hong")
            try:
                self.path.replace(hong)
            except OSError:
                hong = "(khong doi ten duoc)"
            print(f"[canh bao] {self.path.name} HONG ({type(e).__name__}) — da doi "
                  f"ten thanh {hong}, chay tiep voi kho RONG. Bao cao lan nay se "
                  "coi moi muc la moi; lan sau tro lai binh thuong.", file=sys.stderr)
            return {}
        return d if isinstance(d, dict) else {}

    def read(self) -> dict:
        """{khoa: unix_ts lan cuoi BAO}. Dinh dang cu la list khoa tran —
        doc duoc ca hai, chuyen dan sang dict."""
        d = self._raw().get(self.field, {})
        if isinstance(d, list):                              # dinh dang cu
            now = time.time()
            return {k: now for k in d}
        return d if isinstance(d, dict) else {}

    def seen(self, key) -> bool:
        return bool(key) and key in self.read()

    def unseen(self, items: list, key) -> tuple:
        """(muc CHUA bao gio bao, so muc da bo). `key` la ham lay khoa tu muc.

        Doc kho DUNG MOT LAN cho ca danh sach — goi `seen()` trong vong lap la
        doc lai tep moi vong.
        """
        cu = self.read()
        giu = [it for it in items if key(it) not in cu]
        return giu, len(items) - len(giu)

    # ---- ghi -----------------------------------------------------------
    def mark(self, keys, now: float = 0) -> int:
        """Danh dau `keys` la DA BAO. Tra so khoa con lai trong kho.

        CHI goi voi nhung muc THUC SU da dua vao bao cao (luat 3) — muc bi
        `--top` cat khong duoc danh dau.
        """
        now = now or time.time()
        goc = self._raw()                    # luat 2: giu cac truong khac
        kho = self.read()
        for k in keys:
            if k:
                kho[str(k)] = now
        # Luat 1: cat theo THOI GIAN.
        moc = now - self.keep_days * 86400
        goc[self.field] = {k: v for k, v in kho.items() if v >= moc}
        goc["updated_at"] = datetime.now(timezone.utc).isoformat()
        # Luat 5: nguyen tu, ten tep tam mang pid.
        env_load.write_json(self.path, goc)
        return len(goc[self.field])
