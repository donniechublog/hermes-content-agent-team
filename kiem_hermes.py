"""SHIM tạm (LOW-50): tên cũ của `check_hermes.py`. Mọi thứ nằm ở `check_hermes.py`.

Giữ để task kanban đang `ready`, cron và SOUL trên máy chủ gọi tên cũ vẫn chạy
trong lúc đổi. `sys.modules[__name__] = <module mới>` nên `import kiem_hermes` và
`kiem_hermes.ten` đều trỏ đúng đối tượng thật (kể cả tên `_riêng`). Gỡ sau 1 tuần
(ticket con của LOW-50)."""
import sys as _sys

import check_hermes as _new

_sys.modules[__name__] = _new

if __name__ == "__main__":
    _sys.exit(_new.main() if hasattr(_new, "main") else 0)
