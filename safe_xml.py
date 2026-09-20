#!/usr/bin/env python3
"""Parse XML from the outside world (Google News / Bing News RSS, newsroom feeds, Atom)
without the entity-expansion hole of `xml.etree` (LOW-303).

`xml.etree.ElementTree.fromstring` expands nested entity declarations ("billion laughs"),
so one hostile or broken feed can hang or exhaust a research process. `defusedxml` refuses
entity declarations and external references outright. It returns the same plain
`xml.etree.ElementTree.Element`, so a call site changes one word and nothing else.

A refused document raises `defusedxml.common.DefusedXmlException` (a `ValueError`; its class
name, e.g. `EntitiesForbidden`, is what the call sites log). A malformed one raises
`xml.etree.ElementTree.ParseError`. Every call site already sits inside `except Exception`, so
a refused feed is skipped exactly like a dead one.

defusedxml may be missing: the server venv is shared with hermes and gets it after a deploy
decision. Then fall back to `xml.etree` with ONE warning line per process, the way
`article_extract._parser()` treats lxml. Never die because an optional safety net is absent.
"""
import importlib
import sys
import xml.etree.ElementTree as ET

_WARNED = False


def _backend():
    """`defusedxml.ElementTree`, or None when it is not installed."""
    try:
        # import_module, not `import defusedxml`: still a real import (a broken install is
        # caught too) but leaves no unused name for pyflakes, which CI runs.
        return importlib.import_module("defusedxml.ElementTree")
    except ImportError:
        return None


def fromstring(data):
    """Drop-in for `xml.etree.ElementTree.fromstring` (str or bytes)."""
    global _WARNED
    backend = _backend()
    if backend is not None:
        return backend.fromstring(data)
    if not _WARNED:
        _WARNED = True
        print("[safe_xml] THIEU defusedxml -> parse XML bang xml.etree: mot feed doc hai co the lam "
              "treo hoac ngon het RAM tien trinh (thuc the long nhau). Cai defusedxml de dung "
              "(xem requirements.txt).", file=sys.stderr)
    return ET.fromstring(data)
