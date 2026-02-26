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
    lines = [l for l in out.splitlines() if l.strip()]
    assert lines == ["@I001@  John Smith", "@I002@  Mary Jones"]


def test_roots_id_only():
    code, out, err = run_cmd(["roots", "-i", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["@I001@", "@I002@"]


def test_roots_name_only():
    code, out, err = run_cmd(["roots", "-n", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["John Smith", "Mary Jones"]


def test_roots_conflicting_flags():
    code, out, err = run_cmd(["roots", "-i", "-n", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "Conflicting output flags" in err
