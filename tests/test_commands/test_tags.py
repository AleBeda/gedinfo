import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
GED = str(FIXTURES / "tags.ged")


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _parse_lines(out: str) -> list[tuple[str, str, str, str]]:
    """Return list of (tag, count_str, flag, summary) for each output line."""
    result = []
    for line in out.splitlines():
        parts = line.split("\t")
        assert len(parts) == 4, f"expected 4 tab-separated fields, got: {line!r}"
        result.append((parts[0], parts[1], parts[2], parts[3]))
    return result


def test_output_is_sorted():
    code, out, _ = run_cmd(["tags", GED])
    assert code == 0
    rows = _parse_lines(out)
    tags = [r[0] for r in rows]
    assert tags == sorted(tags)


def test_four_columns_always():
    code, out, _ = run_cmd(["tags", GED])
    assert code == 0
    for line in out.splitlines():
        assert line.count("\t") == 3, f"expected exactly 3 tabs in: {line!r}"


def test_standard_tag_empty_flag():
    code, out, _ = run_cmd(["tags", GED])
    assert code == 0
    rows = {r[0]: r[2] for r in _parse_lines(out)}
    assert rows["NAME"] == ""
    assert rows["SEX"] == ""
    assert rows["BIRT"] == ""


def test_nonstandard_tag_flag():
    code, out, _ = run_cmd(["tags", GED])
    assert code == 0
    rows = {r[0]: r[2] for r in _parse_lines(out)}
    assert rows["_LIVING"] == "not in GEDCOM 5.5.1"
    assert rows["_UID"] == "not in GEDCOM 5.5.1"


def test_standard_tag_has_summary():
    code, out, _ = run_cmd(["tags", GED])
    assert code == 0
    rows = {r[0]: r[3] for r in _parse_lines(out)}
    assert rows["NAME"] == (
        "A word or combination of words used to help identify an individual, "
        "title, or other item."
    )
    assert rows["SEX"] == "Indicates the sex of an individual--male or female."
    assert rows["BIRT"] == "The event of entering into life."


def test_nonstandard_tag_empty_summary():
    code, out, _ = run_cmd(["tags", GED])
    assert code == 0
    rows = {r[0]: r[3] for r in _parse_lines(out)}
    assert rows["_LIVING"] == ""
    assert rows["_UID"] == ""


def test_count_value():
    code, out, _ = run_cmd(["tags", GED])
    assert code == 0
    rows = {r[0]: r[1].strip() for r in _parse_lines(out)}
    assert rows["NAME"] == "3"
    assert rows["_LIVING"] == "2"
    assert rows["_UID"] == "1"


def test_count_right_justified():
    code, out, _ = run_cmd(["tags", GED])
    assert code == 0
    rows = _parse_lines(out)
    widths = {len(r[1]) for r in rows}
    assert len(widths) == 1, f"count fields have inconsistent widths: {widths}"


def test_unknown_file():
    code, out, err = run_cmd(["tags", "nonexistent.ged"])
    assert code == 1
    assert out == ""
    assert err.strip() != ""
