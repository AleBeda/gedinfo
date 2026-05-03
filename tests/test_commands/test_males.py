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


def test_males_default():
    code, out, err = run_cmd(["males", str(FIXTURES / "simple.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines == ["I001\tJohn Smith", "I004\tBob Smith"]


def test_males_id_only():
    code, out, err = run_cmd(["males", "-i", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["I001", "I004"]


def test_males_name_only():
    code, out, err = run_cmd(["males", "-n", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["John Smith", "Bob Smith"]


def test_males_conflicting_flags():
    code, out, err = run_cmd(["males", "-i", "-n", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "Conflicting output flags" in err
