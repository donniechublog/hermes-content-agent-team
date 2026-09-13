#!/usr/bin/env python3
"""jika_submit.py — NOP caption cua Jika. Cung engine voi `miles_submit.py`.

Xem ghi chu o `jika_prepare.py`: mot cap script mang ten vai la quy uoc cua ban
dang ky, khong phai mot ban sao logic. `miles_submit.py` doc sidecar writer.json de
biet AI viet bai nay, nen `author` ghi len bang den va ten tep brief deu ra
"jika" khi bai la cua Jika — chay tep nao cung the.

Dung:
    venv/bin/python jika_submit.py <draft_id>
    venv/bin/python jika_submit.py <draft_id> --khong-push       # thu: khong day hang duyet
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from miles_submit import main                                   # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
