import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_roots_default():
    code, out, err = run_cmd(["roots", str(FIXTURES / "simple.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines == ["I001\tJohn Smith", "I002\tMary Jones"]


def test_roots_id_only():
    code, out, err = run_cmd(["roots", "-i", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["I001", "I002"]


def test_roots_name_only():
    code, out, err = run_cmd(["roots", "-n", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["John Smith", "Mary Jones"]


def test_roots_conflicting_flags():
    code, out, err = run_cmd(["roots", "-i", "-n", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "Conflicting output flags" in err


def test_roots_default_suppresses_spouse_roots():
    code, out, err = run_cmd(["roots", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I001\t" not in out
    assert "I008\t" not in out
    assert "I003\t" in out
    assert "I018\t" in out


def test_roots_default_suppresses_unknowns():
    code, out, err = run_cmd(["roots", str(FIXTURES / "spouse.ged")])
    assert "I022\t" not in out
    assert "I023\t" not in out


def test_roots_spouse_flag_includes_spouse_roots():
    code, out, err = run_cmd(["roots", "--spouse", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I001\t" in out
    assert "I008\t" in out
    assert "I022\t" not in out
    assert "I023\t" not in out


def test_roots_unknowns_flag_includes_unknowns():
    code, out, err = run_cmd(["roots", "-u", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I022\t" in out
    assert "I023\t" not in out
    assert "I001\t" not in out


def test_roots_spouse_and_unknowns_flags_combined():
    code, out, err = run_cmd(["roots", "--spouse", "-u", str(FIXTURES / "spouse.ged")])
    assert code == 0
    for id in ["I001\t", "I008\t", "I022\t", "I023\t"]:
        assert id in out


def test_roots_all_flag():
    code, out, err = run_cmd(["roots", "-a", str(FIXTURES / "spouse.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    # compute expected raw roots from parser to avoid hard-coded fixture counts
    from gedinfo import parser, queries
    data = parser.parse(FIXTURES / "spouse.ged")
    expected = len(queries.get_roots(data))
    assert len(lines) == expected
    for id in ["I001\t", "I008\t", "I022\t", "I023\t"]:
        assert id in out


def test_roots_all_with_spouse_is_error():
    code, out, err = run_cmd(["roots", "-a", "--spouse", str(FIXTURES / "spouse.ged")])
    assert code == 1
    assert "--all cannot be combined with --spouse or --unknown" in err


def test_roots_all_with_unknowns_is_error():
    code, out, err = run_cmd(["roots", "-a", "-u", str(FIXTURES / "spouse.ged")])
    assert code == 1
    assert "--all cannot be combined with --spouse or --unknown" in err


def test_roots_output_format_default_mode():
    code, out, err = run_cmd(["roots", str(FIXTURES / "spouse.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    for line in lines:
        parts = line.split("\t")
        assert len(parts) == 2


def test_roots_output_id_only_with_filter():
    code, out, err = run_cmd(["roots", "--spouse", "-i", str(FIXTURES / "spouse.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert "I001" in "\n".join(lines)


def test_roots_output_name_only_with_filter():
    code, out, err = run_cmd(["roots", "--unknown", "-n", str(FIXTURES / "spouse.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    # should contain names only (no leading I... ids)
    for line in lines:
        assert not line.startswith("I") or "\t" not in line


def test_roots_conflicting_output_flags_still_error():
    code, out, err = run_cmd(["roots", "-i", "-n", str(FIXTURES / "spouse.ged")])
    assert code == 1


def test_roots_empty_ged_with_all_flags():
    code, out, err = run_cmd(["roots", "-a", str(FIXTURES / "empty.ged")])
    assert code == 0
    assert out.strip() == ""


def test_roots_nameless_parents_in_law_not_suppressed():
    code, out, err = run_cmd(["roots", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I018\t" in out
