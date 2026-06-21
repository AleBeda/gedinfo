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


def test_fam_default():
    code, out, err = run_cmd(["fam", str(FIXTURES / "relatives.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines == [
        "F000\tI002\tJohn Smith\tI003\tJane Doe\tBob Smith",
        "F001\tI001\tBob Smith\tI004\tAlice Brown\tCharlie Smith, Diana Smith",
        "F002\tI001\tBob Smith\tI007\tEve Green\t(none)",
        "F003\tI001\tBob Smith\t(none)\tEddie Smith",
    ]


def test_fam_id_only():
    code, out, err = run_cmd(["fam", "-i", str(FIXTURES / "relatives.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines == [
        "F000\tI002\tI003\tI001",
        "F001\tI001\tI004\tI005, I006",
        "F002\tI001\tI007\t(none)",
        "F003\tI001\t(none)\tI008",
    ]


def test_fam_name_only():
    code, out, err = run_cmd(["fam", "-n", str(FIXTURES / "relatives.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines[0] == "F000\tJohn Smith\tJane Doe\tBob Smith"


def test_fam_sort_name():
    # Regression: --sort name previously crashed concatenating a tuple and a list.
    code, out, err = run_cmd(["fam", "-s", "name", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert err == ""
    assert out.strip()


def test_fam_sort_id():
    code, out, err = run_cmd(["fam", "-s", "id", str(FIXTURES / "relatives.ged")])
    assert code == 0
    ids = [line.split("\t", 1)[0] for line in out.splitlines() if line.strip()]
    assert ids == ["F000", "F001", "F002", "F003"]


def test_fam_conflicting_flags():
    code, out, err = run_cmd(["fam", "-i", "-n", str(FIXTURES / "relatives.ged")])
    assert code == 1
    assert "Conflicting output flags" in err
