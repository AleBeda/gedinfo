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


def test_names_all_found(tmp_path):
    ids = tmp_path / "ids.txt"
    ids.write_text("@I001@\n@I002@\n")
    code, out, err = run_cmd(["names", str(ids), str(FIXTURES / "simple.ged")])
    assert code == 0
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    assert lines == ["John Smith", "Mary Jones"]
    assert err == ""


def test_names_partial_found(tmp_path):
    ids = tmp_path / "ids2.txt"
    ids.write_text("@I001@\n@I999@\n")
    code, out, err = run_cmd(["names", str(ids), str(FIXTURES / "simple.ged")])
    assert code == 0
    lines = [l.rstrip() for l in out.splitlines()]
    assert lines == ["John Smith", "@I999@: (not found)"]


def test_names_ids_file_missing():
    code, out, err = run_cmd(["names", "no_such_file.txt", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "IDs file not found" in err
