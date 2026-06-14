import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
# descendants.ged: John(I001)+Jane(I002) -> Peter(I003)+Anna(I004)
#                  Peter(I003)+Mary(I005) -> Tom(I006)+Sue(I007)
DESC = str(FIXTURES / "descendants.ged")


def run_gen(*args):
    result = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + list(args),
        capture_output=True, text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def test_root_individual():
    # I001: no ancestors, 2 descendant generations (children + grandchildren)
    code, out, _ = run_gen("gen", "I001", DESC)
    assert code == 0
    assert out == "ancestors: 0\tdescendants: 2\ttotal: 3"


def test_middle_individual():
    # I003: 1 ancestor generation (parents), 1 descendant generation (children)
    code, out, _ = run_gen("gen", "I003", DESC)
    assert code == 0
    assert out == "ancestors: 1\tdescendants: 1\ttotal: 3"


def test_leaf_individual():
    # I006: 2 ancestor generations (parents + grandparents), no descendants
    code, out, _ = run_gen("gen", "I006", DESC)
    assert code == 0
    assert out == "ancestors: 2\tdescendants: 0\ttotal: 3"


def test_generations_alias():
    code_gen, out_gen, _ = run_gen("gen", "I003", DESC)
    code_alias, out_alias, _ = run_gen("generations", "I003", DESC)
    assert code_gen == 0
    assert out_gen == out_alias


def test_unknown_id():
    code, _, err = run_gen("gen", "I999", DESC)
    assert code == 1
    assert "unknown" in err.lower() or "I999" in err
