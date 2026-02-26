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


def test_disjoint_single_tree_default():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert err == ""
    lines = out.strip().splitlines()
    assert lines == [
        "@I001@  John Smith",
        "@I002@  Mary Jones",
    ]


def test_disjoint_single_tree_id_only():
    code, out, err = run_cmd(["disjoint", "-i", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert err == ""
    assert out.strip().splitlines() == ["@I001@", "@I002@"]


def test_disjoint_single_tree_name_only():
    code, out, err = run_cmd(["disjoint", "-n", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert err == ""
    assert out.strip().splitlines() == ["John Smith", "Mary Jones"]


def test_disjoint_multi_tree():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "multi_tree.ged")])
    assert code == 0
    assert err == ""
    blocks = out.strip().split("\n\n")
    # first component roots
    assert blocks[0].splitlines() == ["@I001@  Wilhelm Braun"]
    # second component roots
    assert blocks[1].splitlines() == ["@I003@  Sofia Rossi"]


def test_disjoint_empty():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "empty.ged")])
    assert code == 0
    assert err == ""
    assert out.strip() == ""


def test_disjoint_conflicting_flags():
    code, out, err = run_cmd(["disjoint", "-i", "-n", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "mutually exclusive" in err or "conflicting" in err


def test_disjoint_deep():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "deep.ged")])
    assert code == 0
    assert err == ""
    # only root I001 in deep.ged
    assert out.strip().splitlines() == ["@I001@  Adam Elder"]
