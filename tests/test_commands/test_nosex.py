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


def test_nosex_default():
    code, out, err = run_cmd(["nosex", str(FIXTURES / "no_names.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines == [
        "I001\t(unknown)",
        "I002\tSmith",
        "I003\tJane",
    ]


def test_nosex_id_only():
    code, out, err = run_cmd(["nosex", "-i", str(FIXTURES / "no_names.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["I001", "I002", "I003"]


def test_nosex_name_only():
    code, out, err = run_cmd(["nosex", "-n", str(FIXTURES / "no_names.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["(unknown)", "Smith", "Jane"]


def test_nosex_empty():
    code, out, err = run_cmd(["nosex", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip() == ""


def test_nosex_conflicting_flags():
    code, out, err = run_cmd(["nosex", "-i", "-n", str(FIXTURES / "no_names.ged")])
    assert code == 1
    assert "Conflicting output flags" in err
