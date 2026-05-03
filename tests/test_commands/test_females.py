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


def test_females_default():
    code, out, err = run_cmd(["females", str(FIXTURES / "simple.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines == ["I002\tMary Jones", "I003\tAlice Smith"]


def test_females_id_only():
    code, out, err = run_cmd(["females", "-i", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["I002", "I003"]


def test_females_name_only():
    code, out, err = run_cmd(["females", "-n", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["Mary Jones", "Alice Smith"]


def test_females_conflicting_flags():
    code, out, err = run_cmd(["females", "-i", "-n", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "Conflicting output flags" in err
