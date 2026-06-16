"""GEDCOM file parsing utilities.

The parser is intentionally lightweight and only extracts the fields
required by the domain model.  It tolerates both LF and CRLF line endings
and ignores unrecognised tags.  Errors during parsing are wrapped in a
`GedcomParseError` to provide user-friendly messages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from .config import TagConfig, load_tag_config
from .models import Family, GedcomData, Individual


# truthy set for _LIVING parsing
_LIVING_TRUTHY: frozenset[str] = frozenset(
    {
        "y",
        "yes",
        "true",
        "1",
    }
)


class GedcomParseError(Exception):
    """Raised when a GEDCOM file cannot be parsed.

    The message should be suitable for display to end users; internal
    tracebacks are suppressed unless the CLI runs with ``--debug``.
    """


def parse(path: str | Path, tag_config: TagConfig | None = None) -> GedcomData:
    """Parse the GEDCOM file at ``path`` and return a ``GedcomData``.

    ``tag_config`` supplies the custom (non-standard) GEDCOM tag names. When
    ``None``, it is resolved from the settings files relative to ``path``.

    Raises
    ------
    GedcomParseError
        If the file cannot be opened or does not appear to be a valid
        GEDCOM file (e.g. missing ``0 HEAD`` record).
    """
    if tag_config is None:
        tag_config = load_tag_config(path)
    p = Path(path)
    if not p.exists():
        raise GedcomParseError(f"File not found: {path}")

    try:
        # Use 'utf-8-sig' to silently handle files that start with a
        # UTF-8 BOM (U+FEFF). Opening with 'utf-8' leaves the BOM in
        # the first line which breaks the "0 HEAD" check.
        with p.open(encoding="utf-8-sig", errors="replace") as f:
            raw_lines = [line.rstrip("\r\n") for line in f]
    except Exception as exc:  # pragma: no cover - defensive
        raise GedcomParseError(str(exc))

    # skip blank lines for the head check
    meaningful = [ln for ln in raw_lines if ln.strip()]
    if not meaningful or not meaningful[0].startswith("0 HEAD"):
        raise GedcomParseError("Not a valid GEDCOM file: missing 0 HEAD record")

    data = GedcomData(tag_config=tag_config)
    idx = 0
    total = len(raw_lines)

    while idx < total:
        line = raw_lines[idx]
        level, tag, value, xref = _parse_line(line)
        if level == 0 and tag in ("INDI", "FAM") and xref:
            if tag == "INDI":
                indi = Individual(id=xref)
                ctx: dict = {"event": None}
                idx += 1
                while idx < total:
                    lvl, t, v, _ = _parse_line(raw_lines[idx])
                    if lvl == 0:
                        break
                    _populate_individual(indi, t, v, lvl, ctx, tag_config)
                    idx += 1
                data.individuals[indi.id] = indi
                continue
            elif tag == "FAM":
                fam = Family(id=xref)
                ctx = {"event": None}
                idx += 1
                while idx < total:
                    lvl, t, v, _ = _parse_line(raw_lines[idx])
                    if lvl == 0:
                        break
                    _populate_family(fam, t, v, lvl, ctx)
                    idx += 1
                data.families[fam.id] = fam
                continue
        idx += 1

    return data


# helpers


def _parse_line(line: str) -> Tuple[int, str, str, Optional[str]]:
    """Return ``(level, tag, value, xref)`` for a given GEDCOM line.

    The ``xref`` value is only non-``None`` for level-0 records that use
    the ``0 @XREF@ TAG`` syntax.
    """
    parts = line.split(" ", 2)
    try:
        level = int(parts[0])
    except ValueError:  # malformed
        level = -1
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


def _populate_individual(
    indi: Individual,
    tag: str,
    value: str,
    level: int = 1,
    ctx: dict | None = None,
    cfg: TagConfig | None = None,
) -> None:
    if ctx is None:
        ctx = {}
    if cfg is None:
        cfg = TagConfig()
    tag = tag.upper()
    if level == 1:
        ctx["event"] = tag if tag in ("BIRT", "DEAT") else None
    if tag == "DATE":
        event = ctx.get("event")
        if event == "BIRT" and indi.birth_date is None:
            indi.birth_date = value.strip()
        elif event == "DEAT" and indi.death_date is None:
            indi.death_date = value.strip()
        return
    if tag == "NAME":
        fn, ln = _split_name(value)
        indi.first_name = fn
        indi.last_name = ln
    elif tag == "SEX":
        v = value.strip().upper()
        if v == "M":
            indi.sex = "M"
        elif v == "F":
            indi.sex = "F"
        else:
            indi.sex = "U"
    elif tag == "FAMC":
        if value:
            indi.family_ids_as_child.append(value.strip())
    elif tag == "FAMS":
        if value:
            indi.family_ids_as_spouse.append(value.strip())
    elif cfg.living and tag == cfg.living:
        raw = value.strip()
        if raw == "":
            indi.living = None
        elif raw.lower() in _LIVING_TRUTHY:
            indi.living = True
        else:
            indi.living = False
    elif tag == "GIVN":
        if value.strip():
            indi.givn.append(value.strip())
    elif cfg.secondary_name and tag == cfg.secondary_name:
        if value.strip():
            indi.secondary_names.append(value.strip())
    elif cfg.alternate_name and tag == cfg.alternate_name:
        if value.strip():
            indi.alternate_names.append(value.strip())
    elif tag == "NOTE" and level == 1:
        if value.strip():
            indi.notes.append(value.strip())
    # ignore other tags


def _populate_family(
    fam: Family, tag: str, value: str, level: int = 1, ctx: dict | None = None
) -> None:
    if ctx is None:
        ctx = {}
    tag = tag.upper()
    if level == 1:
        ctx["event"] = tag if tag == "MARR" else None
    if tag == "DATE" and ctx.get("event") == "MARR" and fam.marriage_date is None:
        fam.marriage_date = value.strip()
        return
    if tag == "HUSB":
        fam.husband_id = value.strip() or None
    elif tag == "WIFE":
        fam.wife_id = value.strip() or None
    elif tag == "CHIL":
        if value:
            fam.child_ids.append(value.strip())
    elif tag == "NOTE" and level == 1:
        if value.strip():
            fam.notes.append(value.strip())
    # ignore others


def _split_name(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """Split a GEDCOM NAME value into first and last parts.

    The surname is the text between forward slashes.  Text before the
    first slash is treated as the given name.  If no slashes are present,
    the last token is assumed to be the surname.
    """
    text = raw.strip()
    if not text:
        return None, None
    if "/" in text:
        parts = text.split("/")
        first = parts[0].strip() or None
        last = parts[1].strip() or None
        return first, last
    tokens = text.split()
    if len(tokens) == 1:
        return tokens[0], None
    return " ".join(tokens[:-1]), tokens[-1]
