import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"


def run_cmd(args):
    proc = subprocess.run(
        ["gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_id_single():
    code, out, err = run_cmd(["id", "John Smith", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip() == "I001"
    assert err == ""


def test_id_no_match():
    code, out, err = run_cmd(["id", "Nobody", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip() == ""
