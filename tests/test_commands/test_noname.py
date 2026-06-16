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


def test_noname_empty():
    code, out, err = run_cmd(["noname", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip() == ""


def test_noname_finds_unnamed(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME John /Smith/\n1 SEX M\n"
        "0 @I2@ INDI\n1 SEX F\n"
        "0 @I3@ INDI\n1 SEX U\n"
        "0 TRLR\n"
    )
    f = tmp_path / "noname.ged"
    f.write_text(content)
    code, out, err = run_cmd(["noname", str(f)])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 2
    ids = [l.split("\t")[0] for l in lines]
    assert "I2" in ids
    assert "I3" in ids
    assert "I1" not in ids


def test_noname_id_only(tmp_path):
    content = "0 HEAD\n0 @I1@ INDI\n1 SEX M\n0 TRLR\n"
    f = tmp_path / "noname_id.ged"
    f.write_text(content)
    code, out, err = run_cmd(["noname", "-i", str(f)])
    assert code == 0
    assert out.strip() == "I1"


def test_noname_name_only(tmp_path):
    content = "0 HEAD\n0 @I1@ INDI\n1 SEX M\n0 TRLR\n"
    f = tmp_path / "noname_name.ged"
    f.write_text(content)
    code, out, err = run_cmd(["noname", "-n", str(f)])
    assert code == 0
    assert out.strip() == "(unknown)"


def test_noname_conflicting_flags():
    code, out, err = run_cmd(["noname", "-i", "-n", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "Conflicting output flags" in err


def test_noname_no_names_file():
    code, out, err = run_cmd(["noname", str(FIXTURES / "no_names.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) >= 2
