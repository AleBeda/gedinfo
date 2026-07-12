"""`gedinfo anonymize` subcommand implementation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple

from ..config import load_tag_config
from ..errors import UserError
from ..lines import read_raw_lines, split_line

_MAX_LEN_ITERS: int = 20  # max retries for length-bounded fake generation

_KEEP_TAGS: frozenset[str] = frozenset(
    {
        "SEX",
        "DATE",
        "HUSB",
        "WIFE",
        "CHIL",
        "FAMC",
        "FAMS",
        "BIRT",
        "DEAT",
        "MARR",
        "DIV",
        "BAPM",
        "CHR",
        "CREM",
        "BURI",
        "EMIG",
        "IMMI",
        "NATU",
        "ADOP",
        "CONF",
        "GRAD",
        "RETI",
        "WILL",
        "CENS",
        "RESI",
    }
)
_ANON_TAGS: frozenset[str] = frozenset(
    {
        "NAME",
        "GIVN",
        "SURN",
        "PLAC",
        "ADDR",
        "CITY",
        "STAE",
        "CTRY",
        "POST",
        "NOTE",
        "CONT",
        "CONC",
    }
)
_MINIMAL_HEAD: list[str] = ["0 HEAD", "1 GEDC", "2 VERS 5.5.1", "1 CHAR UTF-8"]


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


def _default_action(tag_up: str) -> str:
    if tag_up in _KEEP_TAGS:
        return "keep"
    if tag_up in _ANON_TAGS:
        return "anon"
    return "strip"


def _resolve_action(tag_up: str, action_map: dict[str, str]) -> str:
    return action_map.get(tag_up) or _default_action(tag_up)


class _Anonymizer:
    """Holds the seeded ``Faker`` instance and the pass-1 replacement mappings
    used to anonymize a GEDCOM file."""

    def __init__(self, seed: int = 0) -> None:
        try:
            from faker import Faker  # type: ignore[import-not-found]
        except ImportError as e:
            raise UserError(
                "The 'anonymize' command requires the 'faker' package. "
                "Install gedinfo's dependencies (e.g. `pip install gedinfo` "
                "or `pip install faker`) and try again."
            ) from e
        Faker.seed(seed)
        self.fake = Faker()
        self.mappings: dict = {}

    def _shortest_within(self, gen_fn, max_len: int) -> str:
        """Call gen_fn up to _MAX_LEN_ITERS times; return first result ≤ max_len chars,
        or the shortest seen if none fits within the limit."""
        best = gen_fn()
        for _ in range(_MAX_LEN_ITERS - 1):
            if len(best) <= max_len:
                break
            candidate = gen_fn()
            if len(candidate) < len(best):
                best = candidate
        return best

    def _gen_fake_first(self, sex: str, orig_tokens: list[str]) -> str:
        method = (
            self.fake.first_name_male
            if sex == "M"
            else self.fake.first_name_female
            if sex == "F"
            else self.fake.first_name
        )
        used: set[str] = set()
        parts: list[str] = []
        for t in orig_tokens:
            if not t:
                parts.append("")
                continue
            name = self._shortest_within(method, len(t))
            if name in used:
                for _ in range(_MAX_LEN_ITERS):
                    candidate = method()
                    if candidate not in used:
                        name = candidate
                        break
            used.add(name)
            parts.append(name)
        return " ".join(parts)

    def _gen_fake_last(self, orig_tokens: list[str]) -> str:
        used: set[str] = set()
        parts: list[str] = []
        for t in orig_tokens:
            if not t:
                parts.append("")
                continue
            name = self._shortest_within(self.fake.last_name, len(t))
            if name in used:
                for _ in range(_MAX_LEN_ITERS):
                    candidate = self.fake.last_name()
                    if candidate not in used:
                        name = candidate
                        break
            used.add(name)
            parts.append(name)
        return " ".join(parts)

    def _gen_fake_place(self, original: str) -> str:
        components = [c.strip() for c in original.split(",")]
        return ", ".join(
            self._shortest_within(self.fake.city, len(c)) if c else c
            for c in components
        )

    def _build_name_entry(
        self,
        name_value: str,
        sex: str,
        name_map: dict[str, str],
        last_name_map: dict[str, str],
    ) -> None:
        first, last = _split_gedcom_name(name_value)
        # Empty name (e.g. "//"): store sentinel so the NAME line is stripped from output.
        if first is None and last is None:
            name_map[name_value] = ""
            return
        first_tokens = first.split() if first else []
        last_tokens = last.split() if last else []
        if last is not None:
            if last not in last_name_map:
                last_name_map[last] = (
                    self._gen_fake_last(last_tokens) if last_tokens else ""
                )
            fake_last = last_name_map[last]
            fake_first = self._gen_fake_first(sex, first_tokens) if first_tokens else ""
            if fake_first:
                name_map[name_value] = f"{fake_first} /{fake_last}/"
            else:
                name_map[name_value] = f"/{fake_last}/"
        else:
            # No last name in original — generate only a fake first name, no slashes
            fake_first = self._gen_fake_first(sex, first_tokens) if first_tokens else ""
            name_map[name_value] = fake_first

    def _collect_mappings(self, raw_lines: list[str]) -> dict:
        last_name_map: dict[str, str] = {}
        name_map: dict[str, str] = {}
        given_map: dict[str, str] = {}
        place_map: dict[str, str] = {}
        addr_map: dict[str, str] = {}
        city_map: dict[str, str] = {}
        stae_map: dict[str, str] = {}
        ctry_map: dict[str, str] = {}
        post_map: dict[str, str] = {}

        cur_sex = "U"
        cur_name: Optional[str] = None
        cur_givn: list[str] = []
        cur_surn: list[str] = []
        in_indi = False

        def flush() -> None:
            nonlocal cur_sex, cur_name, cur_givn, cur_surn, in_indi
            if in_indi and cur_name is not None and cur_name not in name_map:
                self._build_name_entry(cur_name, cur_sex, name_map, last_name_map)
            if in_indi:
                for v in cur_surn:
                    last_name_map.setdefault(v, self._gen_fake_last(v.split()))
                # If two individuals share a given name with different sexes,
                # first-seen wins (setdefault) — acceptable, not worth tracking
                # per-value sex just to resolve this rare edge case.
                for v in cur_givn:
                    given_map.setdefault(v, self._gen_fake_first(cur_sex, v.split()))
            cur_sex = "U"
            cur_name = None
            cur_givn = []
            cur_surn = []

        for line in raw_lines:
            level, tag, value, xref = split_line(line)
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
                place_map[v] = self._gen_fake_place(v)
            elif tag_up == "ADDR" and v not in addr_map:
                addr_map[v] = self._shortest_within(self.fake.street_address, len(v))
            elif tag_up == "CITY" and v not in city_map:
                city_map[v] = self._shortest_within(self.fake.city, len(v))
            elif tag_up == "STAE" and v not in stae_map:
                stae_map[v] = self._shortest_within(self.fake.state_abbr, len(v))
            elif tag_up == "CTRY" and v not in ctry_map:
                ctry_map[v] = self._shortest_within(self.fake.country, len(v))
            elif tag_up == "POST" and v not in post_map:
                post_map[v] = self._shortest_within(self.fake.postcode, len(v))
            # Collect individual identity fields
            if in_indi:
                if tag_up == "SEX":
                    s = v.upper()
                    if s in ("M", "F"):
                        cur_sex = s
                elif tag_up == "NAME" and cur_name is None:
                    cur_name = v
                elif tag_up == "GIVN":
                    cur_givn.append(v)
                elif tag_up == "SURN":
                    cur_surn.append(v)

        flush()

        self.mappings = {
            "name_map": name_map,
            "given_map": given_map,
            "last_name_map": last_name_map,
            "place_map": place_map,
            "addr_map": addr_map,
            "city_map": city_map,
            "stae_map": stae_map,
            "ctry_map": ctry_map,
            "post_map": post_map,
        }
        return self.mappings

    def _anonymize_value(self, tag_up: str, value: str) -> str:
        mappings = self.mappings
        if tag_up == "NAME":
            v = value.strip()
            return mappings["name_map"].get(v, v)
        if tag_up == "GIVN":
            v = value.strip()
            return mappings["given_map"].get(v) or (
                self._gen_fake_first("U", v.split()) if v else v
            )
        if tag_up == "SURN":
            v = value.strip()
            return mappings["last_name_map"].get(v) or (
                self._gen_fake_last(v.split()) if v else v
            )
        if tag_up == "PLAC":
            v = value.strip()
            if not v:
                return v
            return mappings["place_map"].get(v) or self._gen_fake_place(v)
        if tag_up == "ADDR":
            v = value.strip()
            return mappings["addr_map"].get(v) or (
                self._shortest_within(self.fake.street_address, len(v)) if v else v
            )
        if tag_up == "CITY":
            v = value.strip()
            return mappings["city_map"].get(v) or (
                self._shortest_within(self.fake.city, len(v)) if v else v
            )
        if tag_up == "STAE":
            v = value.strip()
            return mappings["stae_map"].get(v) or (
                self._shortest_within(self.fake.state_abbr, len(v)) if v else v
            )
        if tag_up == "CTRY":
            v = value.strip()
            return mappings["ctry_map"].get(v) or (
                self._shortest_within(self.fake.country, len(v)) if v else v
            )
        if tag_up == "POST":
            v = value.strip()
            return mappings["post_map"].get(v) or (
                self._shortest_within(self.fake.postcode, len(v)) if v else v
            )
        if tag_up in ("NOTE", "CONT", "CONC"):
            n = max(1, len(value.split()))
            return self.fake.sentence(nb_words=n).rstrip(".")
        return value

    def _fake_value(self, tag_up: str, value: str) -> str:
        if tag_up == "DATE":
            d = self.fake.date_of_birth()
            return f"{d.day} {d.strftime('%b').upper()} {d.year}"
        if tag_up in (
            "NAME",
            "GIVN",
            "SURN",
            "PLAC",
            "ADDR",
            "CITY",
            "STAE",
            "CTRY",
            "POST",
        ):
            return self._anonymize_value(tag_up, value)
        n = max(1, len(value.split()))
        return self.fake.sentence(nb_words=n).rstrip(".")

    def _transform(
        self,
        raw_lines: list[str],
        action_map: dict[str, str],
    ) -> list[str]:
        out: list[str] = []
        in_head = False
        head_emitted = False
        ctx_anon = False  # True when most recent level-1 tag resolves to anon/fake

        for line in raw_lines:
            if not line.strip():
                continue
            level, tag, value, xref = split_line(line)
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
                fake_v = self._anonymize_value(tag_up, value)
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
                    fake_v = self._anonymize_value(tag_up, value)
                    if not fake_v:
                        continue  # empty sentinel (e.g. name "//") — strip the tag
                    out.append(f"{level} {tag_up} {fake_v}")
            elif action == "fake":
                if not value.strip():
                    out.append(line)
                else:
                    out.append(f"{level} {tag_up} {self._fake_value(tag_up, value)}")

        return out


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``anonymize`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "anonymize",
        help="Output an anonymized version of a GEDCOM file",
        description="Output an anonymized version of a GEDCOM file",
    )
    sub.add_argument(
        "-o",
        "--output",
        help="Write output to FILE instead of stdout",
        metavar="FILE",
    )
    sub.add_argument(
        "--keep",
        action="append",
        default=[],
        metavar="FIELD",
        help="Keep FIELD unchanged (repeatable)",
    )
    sub.add_argument(
        "--remove",
        action="append",
        default=[],
        metavar="FIELD",
        help="Strip FIELD from output (repeatable)",
    )
    sub.add_argument(
        "--fake",
        action="append",
        default=[],
        metavar="FIELD",
        help="Anonymize FIELD with realistic fake data (repeatable)",
    )
    sub.add_argument(
        "--seed",
        type=int,
        default=0,
        metavar="NUMBER",
        help="Random seed for deterministic output (default: 0)",
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args) -> None:
    """Handler invoked when ``gedinfo anonymize`` is run."""
    seed = getattr(args, "seed", 0)
    anon = _Anonymizer(seed)

    keep_set = {f.upper() for f in (args.keep or [])}
    remove_set = {f.upper() for f in (args.remove or [])}
    fake_set = {f.upper() for f in (args.fake or [])}

    conflicts = (
        (keep_set & remove_set) | (keep_set & fake_set) | (remove_set & fake_set)
    )
    if conflicts:
        raise UserError(
            f"Conflicting options for field(s): {', '.join(sorted(conflicts))}"
        )

    action_map: dict[str, str] = {}
    for f in keep_set:
        action_map[f] = "keep"
    for f in remove_set:
        action_map[f] = "strip"
    for f in fake_set:
        action_map[f] = "fake"

    cfg = load_tag_config(args.gedcom_file)
    if cfg.living:
        action_map.setdefault(cfg.living, "keep")

    raw_lines, line_ending = read_raw_lines(args.gedcom_file)

    anon._collect_mappings(raw_lines)
    lines = anon._transform(raw_lines, action_map)
    text = line_ending.join(lines) + line_ending

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8", newline="")
    else:
        print(text, end="")
