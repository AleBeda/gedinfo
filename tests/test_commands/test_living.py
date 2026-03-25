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


def test_living_default():
    code, out, err = run_cmd(["living", str(FIXTURES / "living.ged")])
    assert code == 0
    assert err == ""
    lines = [l for l in out.splitlines() if l.strip()]
    from gedinfo import parser, queries

    data = parser.parse(FIXTURES / "living.ged")
    expected = len(queries.get_living(data))
    assert len(lines) == expected


def test_living_invert():
    code, out, err = run_cmd(["living", "-v", str(FIXTURES / "living.ged")])
    assert code == 0
    assert err == ""
    lines = [l for l in out.splitlines() if l.strip()]
    from gedinfo import parser, queries

    data = parser.parse(FIXTURES / "living.ged")
    expected = len(queries.get_not_living(data))
    assert len(lines) == expected
