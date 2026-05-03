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


def test_indi_default():
    code, out, err = run_cmd(["indi", str(FIXTURES / "simple.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines == [
        "I001\tJohn Smith",
        "I002\tMary Jones",
        "I003\tAlice Smith",
        "I004\tBob Smith",
    ]


def test_indi_id_only():
    code, out, err = run_cmd(["indi", "-i", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["I001", "I002", "I003", "I004"]


def test_indi_name_only():
    code, out, err = run_cmd(["indi", "-n", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == [
        "John Smith",
        "Mary Jones",
        "Alice Smith",
        "Bob Smith",
    ]


def test_indi_conflicting_flags():
    code, out, err = run_cmd(["indi", "-i", "-n", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "Conflicting output flags" in err
