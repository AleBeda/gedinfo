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


def test_name_success():
    code, out, err = run_cmd(["name", "@I001@", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip() == "John Smith"
    assert err == ""


def test_name_not_found():
    code, out, err = run_cmd(["name", "@I999@", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "not found" in err.lower()
