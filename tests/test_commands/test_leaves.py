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


def test_leaves_default():
    code, out, err = run_cmd(["leaves", str(FIXTURES / "simple.ged")])
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines == ["I003\tAlice Smith", "I004\tBob Smith"]


def test_leaves_id_only():
    code, out, err = run_cmd(["leaves", "-i", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["I003", "I004"]


def test_leaves_name_only():
    code, out, err = run_cmd(["leaves", "-n", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["Alice Smith", "Bob Smith"]


def test_leaves_conflicting_flags():
    code, out, err = run_cmd(["leaves", "-i", "-n", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "Conflicting output flags" in err


def test_leaves_default_suppresses_unknowns(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME John /Smith/\n1 SEX M\n"
        "0 @I2@ INDI\n1 SEX M\n"
        "0 TRLR\n"
    )
    f = tmp_path / "leaves_unknowns.ged"
    f.write_text(content)
    code, out, err = run_cmd(["leaves", str(f)])
    assert code == 0
    assert "I1" in out
    assert "I2" not in out


def test_leaves_unknown_flag_includes_unknowns(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME John /Smith/\n1 SEX M\n"
        "0 @I2@ INDI\n1 SEX M\n"
        "0 TRLR\n"
    )
    f = tmp_path / "leaves_unknowns2.ged"
    f.write_text(content)
    code, out, err = run_cmd(["leaves", "-u", str(f)])
    assert code == 0
    assert "I1" in out
    assert "I2" in out


def test_leaves_default_suppresses_spouse_suppressed(tmp_path):
    # I2 is a leaf married to I1 who has children with I3
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME Alice /One/\n1 SEX F\n1 FAMS @F1@\n1 FAMS @F2@\n"
        "0 @I2@ INDI\n1 NAME Bob /Two/\n1 SEX M\n1 FAMS @F2@\n"
        "0 @I3@ INDI\n1 NAME Child /One/\n1 SEX M\n1 FAMC @F1@\n"
        "0 @F1@ FAM\n1 WIFE @I1@\n1 CHIL @I3@\n"
        "0 @F2@ FAM\n1 HUSB @I2@\n1 WIFE @I1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "leaves_spouse.ged"
    f.write_text(content)
    code, out, err = run_cmd(["leaves", str(f)])
    assert code == 0
    # I2 is spouse-suppressed (married to I1 who has children elsewhere)
    assert "I2" not in out
    # I1 is not a leaf (has children in F1), so it shouldn't appear
    assert "I1" not in out


def test_leaves_spouse_flag_includes_spouse_suppressed(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME Alice /One/\n1 SEX F\n1 FAMS @F1@\n1 FAMS @F2@\n"
        "0 @I2@ INDI\n1 NAME Bob /Two/\n1 SEX M\n1 FAMS @F2@\n"
        "0 @I3@ INDI\n1 NAME Child /One/\n1 SEX M\n1 FAMC @F1@\n"
        "0 @F1@ FAM\n1 WIFE @I1@\n1 CHIL @I3@\n"
        "0 @F2@ FAM\n1 HUSB @I2@\n1 WIFE @I1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "leaves_spouse2.ged"
    f.write_text(content)
    code, out, err = run_cmd(["leaves", "--spouse", str(f)])
    assert code == 0
    assert "I2" in out


def test_leaves_all_flag(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME Alice /One/\n1 SEX F\n1 FAMS @F1@\n1 FAMS @F2@\n"
        "0 @I2@ INDI\n1 NAME Bob /Two/\n1 SEX M\n1 FAMS @F2@\n"
        "0 @I3@ INDI\n1 SEX M\n"
        "0 @I4@ INDI\n1 NAME Child /One/\n1 SEX M\n1 FAMC @F1@\n"
        "0 @F1@ FAM\n1 WIFE @I1@\n1 CHIL @I4@\n"
        "0 @F2@ FAM\n1 HUSB @I2@\n1 WIFE @I1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "leaves_all.ged"
    f.write_text(content)
    code, out, err = run_cmd(["leaves", "-a", str(f)])
    assert code == 0
    assert "I2" in out
    assert "I3" in out


def test_leaves_all_with_spouse_is_error(tmp_path):
    f = tmp_path / "e.ged"
    f.write_text("0 HEAD\n0 TRLR\n")
    code, out, err = run_cmd(["leaves", "-a", "--spouse", str(f)])
    assert code == 1
    assert "--all cannot be combined with --spouse or --unknown" in err


def test_leaves_all_with_unknown_is_error(tmp_path):
    f = tmp_path / "e2.ged"
    f.write_text("0 HEAD\n0 TRLR\n")
    code, out, err = run_cmd(["leaves", "-a", "-u", str(f)])
    assert code == 1
    assert "--all cannot be combined with --spouse or --unknown" in err
