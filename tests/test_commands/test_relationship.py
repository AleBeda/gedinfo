import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
SIMPLE = str(FIXTURES / "simple.ged")
MULTI = str(FIXTURES / "multi_tree.ged")


def run_rel(*args):
    result = subprocess.run(
        [sys.executable, "-m", "gedinfo", "relationship"] + list(args),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr.strip()


def test_siblings():
    # I003 (Alice Smith) and I004 (Bob Smith) share parents I001 and I002
    code, out, _ = run_rel("I003", "I004", SIMPLE)
    assert code == 0
    expected = (
        "1  John Smith   John Smith\n"
        "2  Alice Smith  Bob Smith\n"
        "\n"
        "1  Mary Jones   Mary Jones\n"
        "2  Alice Smith  Bob Smith\n"
    )
    assert out == expected


def test_parent_child():
    # I001 (John Smith) is the direct father of I003 (Alice Smith)
    code, out, _ = run_rel("I001", "I003", SIMPLE)
    assert code == 0
    expected = "1  John Smith\n2  Alice Smith\n"
    assert out == expected


def test_no_relationship():
    # Wilhelm Braun (I001) and Sofia Rossi (I003) are in disconnected trees
    code, out, _ = run_rel("I001", "I003", MULTI)
    assert code == 0
    assert out == ""


def test_unknown_first_id():
    code, _, err = run_rel("I999", "I001", SIMPLE)
    assert code == 1
    assert "I999" in err or "unknown" in err.lower()


def test_unknown_second_id():
    code, _, err = run_rel("I001", "I999", SIMPLE)
    assert code == 1
    assert "I999" in err or "unknown" in err.lower()
