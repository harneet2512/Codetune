"""Restricted Python execution tool."""

from __future__ import annotations

import contextlib
import io
import traceback


def run(code: str) -> str:
    stdout = io.StringIO()
    globals_dict = {"__builtins__": {"print": print, "range": range, "sum": sum, "len": len}}
    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, globals_dict, {})
    except Exception:
        return traceback.format_exc(limit=1).strip()
    return stdout.getvalue().strip()
