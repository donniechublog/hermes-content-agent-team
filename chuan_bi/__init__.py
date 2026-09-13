"""SHIM tạm (LOW-50): gói cũ của `prepare/`."""
import sys as _sys
import prepare as _new
_sys.modules[__name__] = _new
