"""Mechanical guards for the design invariants documented in CLAUDE.md.

Each test here pins a rule from the July 2026 architectural review
(.claude/FABLE_REPORT.md) whose violation was a real bug. They grep the
source tree or exercise known-hostile fixtures so that re-introducing an
eliminated pattern fails the suite immediately instead of relying on
future contributors (human or LLM) reading the documentation.
"""

import re
from pathlib import Path

import gedinfo
from gedinfo import queries
from gedinfo.parser import parse

PKG_DIR = Path(gedinfo.__file__).parent
FIXTURES = Path(__file__).parent / "fixtures"


def _package_sources() -> list[Path]:
    return sorted(PKG_DIR.rglob("*.py"))


def test_no_bare_valueerror_raised_in_package():
    """User-facing errors must raise UserError (gedinfo/errors.py), never
    bare ValueError — the CLI's narrowed except clause would otherwise let
    the message escape as a traceback (or worse, a genuine bug would be
    silenced if the catch were widened again)."""
    offenders = [
        f"{path.relative_to(PKG_DIR.parent)}:{lineno}"
        for path in _package_sources()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"\braise ValueError\b", line)
    ]
    assert not offenders, f"raise UserError instead of ValueError: {offenders}"


def test_line_lexing_defined_only_in_lines_module():
    """Raw GEDCOM line splitting and line-ending detection live in
    gedinfo/lines.py only. The project once carried three drifting copies
    (parser, anonymize, strip); do not start a fourth."""
    banned = re.compile(
        r"def\s+_?(split_line|detect_line_ending|parse_line|read_raw_lines)\b"
    )
    offenders = [
        f"{path.relative_to(PKG_DIR.parent)}:{lineno}"
        for path in _package_sources()
        if path.name != "lines.py"
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if banned.search(line)
    ]
    assert not offenders, f"line lexing belongs in gedinfo/lines.py: {offenders}"


def test_version_hardcoded_only_in_package_init():
    """The version string lives in gedinfo/__init__.py (and the README);
    it must not creep back into cli.py, pyproject-adjacent code, or tests
    as a literal inside the package."""
    version = gedinfo.__version__
    offenders = [
        str(path.relative_to(PKG_DIR.parent))
        for path in _package_sources()
        if path.name != "__init__.py" and version in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"hardcoded version string found in: {offenders}"


def test_traversals_terminate_on_cyclic_data():
    """Every graph traversal must be cycle-safe. cycle.ged contains two
    individuals who are each other's parent — an unguarded traversal loops
    forever (this was a real bug in get_ancestors). Add new traversal
    functions to this battery."""
    data = parse(FIXTURES / "cycle.ged")
    queries.get_ancestors(data, "@I001@")
    queries.get_ancestor_details(data, "@I001@")
    queries.get_ancestor_last_names(data, "@I001@")
    queries.get_descendant_details(data, "@I001@")
    queries.find_relationships(data, "@I001@", "@I002@")
    queries.get_connected_components(data)
    queries.count_generations(data)
    queries.get_roots(data)
    queries.get_leaves(data)
