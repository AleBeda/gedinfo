import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
GED = str(FIXTURES / "strip.ged")


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_strip_simple_tag():
    code, out, _ = run_cmd(["strip", "OCCU", GED])
    assert code == 0
    assert "0 @I001@ INDI" in out
    assert "1 NAME John /Smith/" in out


def test_strip_removes_line():
    code, out, _ = run_cmd(["strip", "NOTE", GED])
    assert code == 0
    assert "NOTE" not in out


def test_strip_removes_children():
    code, out, _ = run_cmd(["strip", "BIRT", GED])
    assert code == 0
    assert "BIRT" not in out
    assert "1 JAN 1900" not in out
    assert "Livorno, Italy" not in out
    # MARR's own DATE must survive
    assert "15 JUN 1925" in out


def test_strip_removes_cont_child_of_note():
    code, out, _ = run_cmd(["strip", "NOTE", GED])
    assert code == 0
    assert "More details here." not in out


def test_strip_sibling_notes_independent():
    code, out, _ = run_cmd(["strip", "NOTE", GED])
    assert code == 0
    assert "First note." not in out
    assert "Second note." not in out
    assert "1 NAME Jane /Doe/" in out


def test_strip_givn_surn():
    code, out, _ = run_cmd(["strip", "GIVN", "SURN", GED])
    assert code == 0
    assert "GIVN" not in out
    assert "SURN" not in out
    assert "1 NAME John /Smith/" in out


def test_strip_multiple_fields():
    code, out, _ = run_cmd(["strip", "NOTE", "BIRT", GED])
    assert code == 0
    assert "NOTE" not in out
    assert "BIRT" not in out


def test_strip_case_insensitive():
    code, out, _ = run_cmd(["strip", "note", GED])
    assert code == 0
    assert "NOTE" not in out


def test_strip_warning_for_risky_tag():
    code, out, err = run_cmd(["strip", "NAME", GED])
    assert code == 0
    assert "NAME" in err
    assert out != ""


def test_strip_warning_multiple_risky_tags():
    code, _, err = run_cmd(["strip", "FAMS", "FAMC", GED])
    assert code == 0
    assert "FAMS" in err
    assert "FAMC" in err
    assert len(err.strip().splitlines()) == 2


def test_strip_no_warning_for_safe_tag():
    code, _, err = run_cmd(["strip", "NOTE", GED])
    assert code == 0
    assert err == ""


def test_strip_head_trlr_warning():
    code, out, err = run_cmd(["strip", "HEAD", GED])
    assert code == 0
    assert "HEAD" in err
    assert not out.startswith("0 HEAD")
    assert "0 @I001@ INDI" in out


def test_strip_husb_wife_chil_warning():
    code, out, err = run_cmd(["strip", "HUSB", GED])
    assert code == 0
    assert "HUSB" in err
    assert "1 HUSB @I001@" not in out
    assert "1 WIFE @I002@" in out
    assert "1 CHIL @I003@" in out


def test_strip_output_flag(tmp_path):
    out_file = str(tmp_path / "out.ged")
    code, stdout, _ = run_cmd(["strip", "-o", out_file, "NOTE", GED])
    assert code == 0
    assert stdout == ""
    content = Path(out_file).read_text()
    assert "NOTE" not in content
    assert "0 TRLR" in content


def test_strip_unknown_file():
    code, _, err = run_cmd(["strip", "NOTE", "nonexistent.ged"])
    assert code == 1
    assert "nonexistent.ged" in err.lower() or "not found" in err.lower()


def test_strip_preserves_unrelated_structure():
    code, out, _ = run_cmd(["strip", "SOUR", GED])
    assert code == 0
    assert "0 @I001@ INDI" in out
    assert "0 @F001@ FAM" in out
    assert "0 TRLR" in out
