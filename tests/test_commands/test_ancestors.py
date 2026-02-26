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


def test_ancestors_unlimited():
    code, out, err = run_cmd(["ancestors", "@I004@", str(FIXTURES / "deep.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["Elder"]


def test_ancestors_g1():
    code, out, err = run_cmd(["ancestors", "-g", "1", "@I004@", str(FIXTURES / "deep.ged")])
    assert code == 0
    assert out.strip() == ""


def test_ancestors_g2():
    code, out, err = run_cmd(["ancestors", "-g", "2", "@I004@", str(FIXTURES / "deep.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["Elder"]


def test_ancestors_invalid_g_zero():
    code, out, err = run_cmd(["ancestors", "-g", "0", "@I004@", str(FIXTURES / "deep.ged")])
    assert code == 1
    assert "Invalid generations value" in err


def test_ancestors_unknown_id():
    code, out, err = run_cmd(["ancestors", "@I999@", str(FIXTURES / "deep.ged")])
    assert code == 1
    assert "Unknown individual ID" in err
