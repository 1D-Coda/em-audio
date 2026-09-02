"""Filesystem helpers that behave the same on Windows as on POSIX.

An independent validator's run died in the footprint calibration with

    PermissionError: [WinError 5] Acceso denegado:
    'C:\\em-audio\\corpus\\calibration\\trim_10_90'

on a plain ``shutil.rmtree``. On Windows a directory cannot be removed while a
handle to anything inside it is open, and a virus scanner or the search indexer
opens files moments after they are written. The read-only attribute stops
removal too, where POSIX only needs write permission on the parent.

Nine call sites had the same defect; his run happened to hit one of them.
"""
from __future__ import annotations

import os
import shutil
import stat
import sys
import time
from pathlib import Path

WINDOWS = sys.platform.startswith("win")


def _clear_readonly(func, path, _exc):
    """onexc handler: drop the read-only bit and try the operation again."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def rmtree(path, attempts: int = 5) -> None:
    """Remove a tree, tolerating Windows' transient locks and read-only bits.

    Retries because the usual holder is a scanner that lets go within a second.
    Raises with the path and the likely cause if it never does.
    """
    p = Path(path)
    if not p.exists():
        return
    last = None
    for i in range(attempts):
        try:
            if sys.version_info >= (3, 12):
                shutil.rmtree(p, onexc=_clear_readonly)
            else:
                shutil.rmtree(p, onerror=lambda f, q, e: _clear_readonly(f, q, e))
            return
        except (PermissionError, OSError) as exc:
            last = exc
            if not WINDOWS or i == attempts - 1:
                break
            time.sleep(0.4 * (i + 1))
    raise RuntimeError(
        f"could not remove {p}\n"
        f"  {type(last).__name__}: {last}\n"
        + ("  On Windows a directory cannot be removed while any file inside it\n"
           "  is open. A virus scanner or the search indexer is the usual cause,\n"
           "  and it normally lets go within seconds. Retried "
           f"{attempts} times.\n"
           "  Exclude this folder from real-time scanning, or close anything\n"
           "  browsing it, and run again.\n" if WINDOWS else "")
    ) from None
