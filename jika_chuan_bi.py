#!/usr/bin/env python3
"""jika_chuan_bi.py — BRIEF cho Jika (vai viet cua donniechublog).

MOT DONG, khong phai mot ban sao: Jika va Miles dung CHUNG engine chuan bi
(`miles_chuan_bi.py`). Luat caption, cach gom tu lieu, cach doc ban giao cua vai
anh la giong het nhau — chi NGUOI DOC khac, va thu do da nam trong `GIONG` cua
brief, chon theo brand cua bai chu khong theo ten vai.

Tep nay ton tai vi hai le:
  1. quy uoc cua ban dang ky (`vai.py`): them mot vai = mot dong o do + MOT CAP
     <persona>_chuan_bi/_nop + mot SOUL. Task cua Jika phai goi lenh mang ten
     Jika, khong the bao Jika "chay miles_chuan_bi.py" — doc ra nhu giao nham.
  2. brief tu chon ten tep va lenh nop theo persona cua bai, nen chay tep nay
     hay tep kia deu ra dung ket qua; khac biet chi la chu Ong Chu doc thay.

Dung:
    venv/bin/python jika_chuan_bi.py <draft_id>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from miles_chuan_bi import main                              # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
