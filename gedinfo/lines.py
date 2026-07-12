"""Shared lexical layer for the raw GEDCOM line format.

This module owns the low-level splitting of GEDCOM text lines into their
``(level, tag, value, xref)`` components, line-ending detection, and the
file-reading prologue (UTF-8 with BOM tolerance, undecodable bytes replaced,
universal-newline suppression). It is shared by the parser (``parser.py``)
and by the raw-line commands that deliberately bypass the lossy model layer
(``anonymize``, ``strip``). Centralizing it keeps their line handling from
drifting apart.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple


def split_line(line: str) -> Tuple[int, str, str, Optional[str]]:
    """Return ``(level, tag, value, xref)`` for a single GEDCOM line.

    Malformed lines whose first token is not an integer return the inert
    sentinel ``(-1, "", "", None)``. The ``xref`` value is only non-``None``
    for level-0 records that use the ``0 @XREF@ TAG`` syntax.
    """
    parts = line.split(" ", 2)
    try:
        level = int(parts[0])
    except (ValueError, IndexError):
        return -1, "", "", None
    tag = ""
    value = ""
    xref: Optional[str] = None
    if level == 0 and len(parts) >= 3 and parts[1].startswith("@"):
        xref = parts[1]
        rest = parts[2]
        sub = rest.split(" ", 1)
        tag = sub[0]
        value = sub[1] if len(sub) > 1 else ""
    elif len(parts) >= 2:
        tag = parts[1]
        if len(parts) == 3:
            value = parts[2]
    return level, tag, value, xref


def detect_line_ending(raw_text_lines: list[str]) -> str:
    """Return the line-ending style of ``raw_text_lines``.

    Inspects the lines as read with ``newline=""`` (so terminators are
    preserved) and returns the first of ``"\\r\\n"``, ``"\\r"``, or ``"\\n"``
    seen, falling back to ``"\\n"`` when no terminator is present.
    """
    for raw in raw_text_lines:
        if raw.endswith("\r\n"):
            return "\r\n"
        if raw.endswith("\r"):
            return "\r"
        if raw.endswith("\n"):
            return "\n"
    return "\n"


def read_raw_lines(path: str | Path) -> Tuple[list[str], str]:
    """Read ``path`` and return ``(lines, line_ending)``.

    Opens with ``encoding="utf-8-sig"`` (stripping any BOM),
    ``errors="replace"`` (undecodable bytes become U+FFFD), and
    ``newline=""`` (no universal-newline translation, so the original
    terminators survive for detection). Returns the lines stripped of their
    ``\\r\\n`` terminators alongside the detected line ending.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        raw_text_lines = fh.readlines()
    line_ending = detect_line_ending(raw_text_lines)
    return [line.rstrip("\r\n") for line in raw_text_lines], line_ending
