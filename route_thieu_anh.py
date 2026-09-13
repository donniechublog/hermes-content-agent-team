"""SHIM tạm (LOW-50): tên cũ của `route_missing_images.py`. Mọi thứ nằm ở `route_missing_images.py`.

Giữ để task kanban đang `ready`, cron và SOUL trên máy chủ gọi tên cũ vẫn chạy
trong lúc đổi. `sys.modules[__name__] = <module mới>` nên `import route_thieu_anh` và
`route_thieu_anh.ten` đều trỏ đúng đối tượng thật (kể cả tên `_riêng`). Gỡ sau 1 tuần
(ticket con của LOW-50)."""
import sys as _sys

import route_missing_images as _new

_sys.modules[__name__] = _new

if __name__ == "__main__":
    _sys.exit(_new.main() if hasattr(_new, "main") else 0)
