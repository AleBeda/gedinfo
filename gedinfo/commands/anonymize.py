"""`gedinfo anonymize` subcommand implementation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple

from faker import Faker

Faker.seed(0)
_fake = Faker()

_KEEP_TAGS: frozenset[str] = frozenset({
    "SEX", "DATE", "HUSB", "WIFE", "CHIL", "FAMC", "FAMS", "_LIVING",
    "BIRT", "DEAT", "MARR", "DIV", "BAPM", "CHR", "CREM", "BURI",
    "EMIG", "IMMI", "NATU", "ADOP", "CONF", "GRAD", "RETI", "WILL",
    "CENS", "RESI",
})
_ANON_TAGS: frozenset[str] = frozenset({
    "NAME", "GIVN", "SURN", "PLAC", "ADDR", "CITY", "STAE", "CTRY", "POST",
    "NOTE", "CONT", "CONC",
})
_MINIMAL_HEAD: list[str] = ["0 HEAD", "1 GEDC", "2 VERS 5.5.1", "1 CHAR UTF-8"]


def _split_line(line: str) -> Tuple[int, str, str, Optional[str]]:
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


def _split_gedcom_name(raw: str) -> Tuple[Optional[str], Optional[str]]:
    text = raw.strip()
    if "/" in text:
        parts = text.split("/")
        first = parts[0].strip() or None
        last = parts[1].strip() or None
        return first, last
    tokens = text.split()
    if len(tokens) <= 1:
        return text or None, None
    return " ".join(tokens[:-1]), tokens[-1]


def _gen_fake_first(n: int, sex: str) -> str:
    method = (_fake.first_name_male if sex == "M"
              else _fake.first_name_female if sex == "F"
              else _fake.first_name)
    return " ".join(method() for _ in range(n))


def _gen_fake_last(n: int) -> str:
    return " ".join(_fake.last_name() for _ in range(n))


def _gen_fake_place(original: str) -> str:
    parts = [c.strip() for c in original.split(",")]
    return ", ".join(_fake.city() for _ in parts)


def _build_name_entry(
    name_value: str,
    sex: str,
    name_map: dict[str, str],
    last_name_map: dict[str, str],
) -> None:
    first, last = _split_gedcom_name(name_value)
    n_first = len(first.split()) if first else 1
    n_last = len(last.split()) if last else 1
    if last is not None:
        if last not in last_name_map:
            last_name_map[last] = _gen_fake_last(n_last)
        fake_last = last_name_map[last]
    else:
        fake_last = _gen_fake_last(1)
    fake_first = _gen_fake_first(n_first, sex)
    name_map[name_value] = f"{fake_first} /{fake_last}/"


def _collect_mappings(raw_lines: list[str]) -> dict:
    last_name_map: dict[str, str] = {}
    name_map: dict[str, str] = {}
    place_map: dict[str, str] = {}
    addr_map: dict[str, str] = {}
    city_map: dict[str, str] = {}
    stae_map: dict[str, str] = {}
    ctry_map: dict[str, str] = {}
    post_map: dict[str, str] = {}

    cur_sex = "U"
    cur_name: Optional[str] = None
    in_indi = False

    def flush() -> None:
        nonlocal cur_sex, cur_name, in_indi
        if in_indi and cur_name is not None and cur_name not in name_map:
            _build_name_entry(cur_name, cur_sex, name_map, last_name_map)
        cur_sex = "U"
        cur_name = None

    for line in raw_lines:
        level, tag, value, xref = _split_line(line)
        tag_up = tag.upper()
        if level == 0:
            flush()
            in_indi = tag_up == "INDI"
            continue
        v = value.strip()
        if not v:
            continue
        # Collect location values from all records
        if tag_up == "PLAC" and v not in place_map:
            place_map[v] = _gen_fake_place(v)
        elif tag_up == "ADDR" and v not in addr_map:
            addr_map[v] = _fake.street_address()
        elif tag_up == "CITY" and v not in city_map:
            city_map[v] = _fake.city()
        elif tag_up == "STAE" and v not in stae_map:
            stae_map[v] = _fake.state_abbr()
        elif tag_up == "CTRY" and v not in ctry_map:
            ctry_map[v] = _fake.country()
        elif tag_up == "POST" and v not in post_map:
            post_map[v] = _fake.postcode()
        # Collect individual identity fields
        if in_indi:
            if tag_up == "SEX":
                s = v.upper()
                if s in ("M", "F"):
                    cur_sex = s
            elif tag_up == "NAME" and cur_name is None:
                cur_name = v

    flush()

    return {
        "name_map": name_map,
        "place_map": place_map,
        "addr_map": addr_map,
        "city_map": city_map,
        "stae_map": stae_map,
        "ctry_map": ctry_map,
        "post_map": post_map,
    }


def _default_action(tag_up: str) -> str:
    if tag_up in _KEEP_TAGS:
        return "keep"
    if tag_up in _ANON_TAGS:
        return "anon"
    return "strip"


def _resolve_action(tag_up: str, action_map: dict[str, str]) -> str:
    return action_map.get(tag_up) or _default_action(tag_up)


def _anonymize_value(tag_up: str, value: str, mappings: dict) -> str:
    if tag_up == "NAME":
        v = value.strip()
        return mappings["name_map"].get(v, v)
    if tag_up == "GIVN":
        v = value.strip()
        return _gen_fake_first(max(1, len(v.split())), "U")
    if tag_up == "SURN":
        v = value.strip()
        return _gen_fake_last(max(1, len(v.split())))
    if tag_up == "PLAC":
        v = value.strip()
        return mappings["place_map"].get(v) or _gen_fake_place(v)
    if tag_up == "ADDR":
        v = value.strip()
        return mappings["addr_map"].get(v, _fake.street_address())
    if tag_up == "CITY":
        v = value.strip()
        return mappings["city_map"].get(v, _fake.city())
    if tag_up == "STAE":
        v = value.strip()
        return mappings["stae_map"].get(v, _fake.state_abbr())
    if tag_up == "CTRY":
        v = value.strip()
        return mappings["ctry_map"].get(v, _fake.country())
    if tag_up == "POST":
        v = value.strip()
        return mappings["post_map"].get(v, _fake.postcode())
    if tag_up in ("NOTE", "CONT", "CONC"):
        n = max(1, len(value.split()))
        return _fake.sentence(nb_words=n).rstrip(".")
    return value


def _fake_value(tag_up: str, value: str, mappings: dict) -> str:
    if tag_up == "DATE":
        d = _fake.date_of_birth()
        return f"{d.day} {d.strftime('%b').upper()} {d.year}"
    if tag_up in ("NAME", "GIVN", "SURN", "PLAC", "ADDR", "CITY", "STAE", "CTRY", "POST"):
        return _anonymize_value(tag_up, value, mappings)
    n = max(1, len(value.split()))
    return _fake.sentence(nb_words=n).rstrip(".")


def _transform(
    raw_lines: list[str],
    mappings: dict,
    action_map: dict[str, str],
) -> list[str]:
    out: list[str] = []
    in_head = False
    head_emitted = False
    ctx_anon = False  # True when most recent level-1 tag resolves to anon/fake

    for line in raw_lines:
        if not line.strip():
            continue
        level, tag, value, xref = _split_line(line)
        tag_up = tag.upper()

        # HEAD handling
        if level == 0 and tag_up == "HEAD":
            in_head = True
            continue
        if in_head:
            if level == 0:
                in_head = False
                if not head_emitted:
                    out.extend(_MINIMAL_HEAD)
                    head_emitted = True
                # fall through to process this level-0 line
            else:
                continue

        # Emit HEAD before first non-HEAD level-0 line if there was no HEAD block
        if not head_emitted and level == 0:
            out.extend(_MINIMAL_HEAD)
            head_emitted = True

        # Level-0 structural lines always emitted as-is
        if level == 0:
            out.append(f"0 {xref} {tag_up}" if xref else f"0 {tag_up}")
            ctx_anon = False
            continue

        # Track level-1 context for CONT/CONC decisions
        if level == 1:
            ctx_anon = _resolve_action(tag_up, action_map) in ("anon", "fake")

        # CONT/CONC follow their parent context
        if tag_up in ("CONT", "CONC"):
            if not ctx_anon:
                continue
            fake_v = _anonymize_value(tag_up, value, mappings)
            out.append(f"{level} {tag_up} {fake_v}")
            continue

        action = _resolve_action(tag_up, action_map)
        if action == "strip":
            continue
        if action == "keep":
            out.append(line)
        elif action == "anon":
            if not value.strip():
                out.append(line)
            else:
                out.append(f"{level} {tag_up} {_anonymize_value(tag_up, value, mappings)}")
        elif action == "fake":
            if not value.strip():
                out.append(line)
            else:
                out.append(f"{level} {tag_up} {_fake_value(tag_up, value, mappings)}")

    return out


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``anonymize`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "anonymize",
        help="Output an anonymized version of a GEDCOM file",
        description="Output an anonymized version of a GEDCOM file",
    )
    sub.add_argument(
        "-o", "--output",
        help="Write output to FILE instead of stdout",
        metavar="FILE",
    )
    sub.add_argument(
        "--keep", action="append", default=[], metavar="FIELD",
        help="Keep FIELD unchanged (repeatable)",
    )
    sub.add_argument(
        "--remove", action="append", default=[], metavar="FIELD",
        help="Strip FIELD from output (repeatable)",
    )
    sub.add_argument(
        "--fake", action="append", default=[], metavar="FIELD",
        help="Anonymize FIELD with realistic fake data (repeatable)",
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args) -> None:
    """Handler invoked when ``gedinfo anonymize`` is run."""
    keep_set   = {f.upper() for f in (args.keep   or [])}
    remove_set = {f.upper() for f in (args.remove or [])}
    fake_set   = {f.upper() for f in (args.fake   or [])}

    conflicts = (keep_set & remove_set) | (keep_set & fake_set) | (remove_set & fake_set)
    if conflicts:
        raise ValueError(
            f"Conflicting options for field(s): {', '.join(sorted(conflicts))}"
        )

    action_map: dict[str, str] = {}
    for f in keep_set:
        action_map[f] = "keep"
    for f in remove_set:
        action_map[f] = "strip"
    for f in fake_set:
        action_map[f] = "fake"

    p = Path(args.gedcom_file)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {args.gedcom_file}")

    with p.open(encoding="utf-8-sig", errors="replace") as fh:
        raw_lines = [line.rstrip("\r\n") for line in fh]

    mappings = _collect_mappings(raw_lines)
    lines = _transform(raw_lines, mappings, action_map)
    text = "\n".join(lines) + "\n"

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
