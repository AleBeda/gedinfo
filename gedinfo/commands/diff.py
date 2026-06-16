"""`gedinfo diff` subcommand implementation."""

from __future__ import annotations

import sys
from typing import Any

from ..parser import parse
from ..queries import display_name, id_sort_key
from ..models import Family, GedcomData
from ._output import validate_output_mode, strip_id_delimiters, add_output_options


_CORE_INDI_FIELDS = ["first_name", "last_name", "birth_date", "death_date"]
_EXTRA_INDI_FIELDS = ["sex", "living", "givn", "secondary_names", "alternate_names", "notes"]
_CORE_FAM_FIELDS = ["husband_id", "wife_id", "child_ids", "marriage_date"]
_EXTRA_FAM_FIELDS = ["notes"]
_ID_FIELDS = {"husband_id", "wife_id"}
_LIST_FIELDS = {"child_ids", "givn", "secondary_names", "alternate_names", "notes"}


def _family_name(fam: Family, data: GedcomData) -> str:
    parts = []
    if fam.husband_id:
        husb = data.individuals.get(fam.husband_id)
        if husb:
            parts.append(display_name(husb))
    if fam.wife_id:
        wife = data.individuals.get(fam.wife_id)
        if wife:
            parts.append(display_name(wife))
    return " & ".join(parts) if parts else "(unknown)"


def _format_value(val: Any, field_name: str) -> str:
    if val is None:
        return ""
    if field_name in _LIST_FIELDS:
        items = list(val)
        if field_name == "child_ids":
            items = [strip_id_delimiters(x) for x in items]
        return ", ".join(str(x) for x in items)
    if field_name in _ID_FIELDS:
        return strip_id_delimiters(str(val))
    return str(val)


def _changed_fields(obj1: Any, obj2: Any, fields: list[str]) -> list[tuple[str, Any, Any]]:
    changes = []
    for f in fields:
        v1 = getattr(obj1, f)
        v2 = getattr(obj2, f)
        if v1 != v2:
            changes.append((f, v1, v2))
    return changes


def _print_entry(label: str, code: str, mode: str, long: bool,
                 changes: list[tuple[str, Any, Any]]) -> None:
    id_part, name_part = label.split("\t", 1)
    if mode == "id":
        print(f"{id_part}\t{code}")
    elif mode == "name":
        print(f"{name_part}\t{code}")
    else:
        print(f"{label}\t{code}")
    if long and changes:
        for field_name, old_val, new_val in changes:
            print(f"  {field_name}")
            print(f"    < {_format_value(old_val, field_name)}")
            print(f"    > {_format_value(new_val, field_name)}")


def register(subparsers: Any) -> None:
    """Register the ``diff`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "diff",
        help="Compare two GEDCOM files",
        description="Compare two GEDCOM files and report added, removed, or changed individuals and families",
    )
    add_output_options(sub)
    sub.add_argument("-l", "--long", action="store_true",
                     help="Show changed field details for CHG entries")
    sub.add_argument("-s", "--sort", choices=["id", "name"], default="id",
                     help="Sort output: 'id' (default) or 'name'")
    sub.add_argument("-a", "--all", action="store_true", dest="all_fields",
                     help="Compare all model fields including sex, living, name variants, and notes")
    sub.add_argument("gedcom1", help="First GEDCOM file")
    sub.add_argument("gedcom2", help="Second GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo diff`` is run."""
    mode = validate_output_mode(args)
    if args.long and getattr(args, "id", False):
        print("Conflicting output flags: -i and --long are not compatible", file=sys.stderr)
        sys.exit(1)
    if args.long and getattr(args, "name", False):
        print("Conflicting output flags: -n and --long are not compatible", file=sys.stderr)
        sys.exit(1)

    data1 = parse(args.gedcom1)
    data2 = parse(args.gedcom2)

    indi_fields = list(_CORE_INDI_FIELDS)
    fam_fields = list(_CORE_FAM_FIELDS)
    if args.all_fields:
        indi_fields += _EXTRA_INDI_FIELDS
        fam_fields += _EXTRA_FAM_FIELDS

    # individuals
    all_indi_ids = set(data1.individuals) | set(data2.individuals)
    indi_diff: list[tuple[Any, Any, str, list]] = []
    for eid in all_indi_ids:
        i1 = data1.individuals.get(eid)
        i2 = data2.individuals.get(eid)
        if i1 and not i2:
            indi_diff.append((i1, None, "DEL", []))
        elif i2 and not i1:
            indi_diff.append((None, i2, "INS", []))
        else:
            changes = _changed_fields(i1, i2, indi_fields)
            if changes:
                indi_diff.append((i1, i2, "CHG", changes))

    # families
    all_fam_ids = set(data1.families) | set(data2.families)
    fam_diff: list[tuple[Any, Any, str, list]] = []
    for fid in all_fam_ids:
        f1 = data1.families.get(fid)
        f2 = data2.families.get(fid)
        if f1 and not f2:
            fam_diff.append((f1, None, "DEL", []))
        elif f2 and not f1:
            fam_diff.append((None, f2, "INS", []))
        else:
            changes = _changed_fields(f1, f2, fam_fields)
            if changes:
                fam_diff.append((f1, f2, "CHG", changes))

    # sort
    def indi_sort_key(entry: tuple) -> Any:
        obj = entry[0] or entry[1]
        if args.sort == "name":
            return display_name(obj).lower()
        return id_sort_key(obj.id)

    def fam_sort_key(entry: tuple) -> Any:
        obj = entry[0] or entry[1]
        ref_data = data1 if entry[0] else data2
        if args.sort == "name":
            return _family_name(obj, ref_data).lower()
        return id_sort_key(obj.id)

    indi_diff.sort(key=indi_sort_key)
    fam_diff.sort(key=fam_sort_key)

    # output
    for i1, i2, code, changes in indi_diff:
        obj = i1 or i2
        label = f"{strip_id_delimiters(obj.id)}\t{display_name(obj)}"
        _print_entry(label, code, mode, args.long, changes)

    for f1, f2, code, changes in fam_diff:
        obj = f1 or f2
        ref_data = data1 if f1 else data2
        name = _family_name(obj, ref_data)
        label = f"{strip_id_delimiters(obj.id)}\t{name}"
        _print_entry(label, code, mode, args.long, changes)
