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


def test_roots_spouse_suppresses_adam():
    code, out, err = run_cmd(["roots", "-s", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I001\t" not in out
    assert "I003\t" in out


def test_roots_spouse_suppresses_multispouse():
    code, out, err = run_cmd(["roots", "-s", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I008\t" not in out


def test_roots_spouse_no_suppression_when_spouse_has_no_parents():
    code, out, err = run_cmd(["roots", "-s", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I003\t" in out  # Karl /Root/
    assert "I004\t" in out  # Sophie /Unknown/


def test_roots_spouse_no_suppression_for_isolated():
    code, out, err = run_cmd(["roots", "-s", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I007\t" in out  # Otto /Orphan/


def test_roots_spouse_output_format_default():
    code, out, err = run_cmd(["roots", "-s", str(FIXTURES / "spouse.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    # Check that each line matches the default format
    for line in lines:
        parts = line.split("\t")
        assert len(parts) == 2
        assert parts[0].startswith("I")
        assert not parts[0].startswith("@")
        assert not parts[0].endswith("@")


def test_roots_spouse_output_format_id_only():
    code, out, err = run_cmd(["roots", "-s", "-i", str(FIXTURES / "spouse.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert "I001" not in out
    assert "I008" not in out
    for line in lines:
        assert line.startswith("I")
        assert not line.startswith("@")
        assert not line.endswith("@")


def test_roots_spouse_output_format_name_only():
    code, out, err = run_cmd(["roots", "-s", "-n", str(FIXTURES / "spouse.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert "Adam Root" not in out
    assert "MultiSpouse Root" not in out


def test_roots_spouse_combined_with_conflicting_output_flags():
    code, out, err = run_cmd(["roots", "-s", "-i", "-n", str(FIXTURES / "spouse.ged")])
    assert code == 1
    assert "Conflicting output flags" in err


def test_roots_without_spouse_flag_unchanged():
    code, out, err = run_cmd(["roots", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I001\t" in out
    assert "I008\t" in out


def test_roots_spouse_empty_ged():
    code, out, err = run_cmd(["roots", "-s", str(FIXTURES / "empty.ged")])
    assert code == 0
    assert out.strip() == ""
