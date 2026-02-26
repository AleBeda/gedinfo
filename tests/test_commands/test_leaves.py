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


def test_leaves_default():
    code, out, err = run_cmd(["leaves", str(FIXTURES / "simple.ged")])
    assert code == 0
    lines = [l for l in out.splitlines() if l.strip()]
    assert lines == ["@I003@  Alice Smith", "@I004@  Bob Smith"]


def test_leaves_id_only():
    code, out, err = run_cmd(["leaves", "-i", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["@I003@", "@I004@"]


def test_leaves_name_only():
    code, out, err = run_cmd(["leaves", "-n", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["Alice Smith", "Bob Smith"]
