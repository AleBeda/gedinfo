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
    code, out, err = run_cmd(
        ["ancestors", "-g", "1", "@I004@", str(FIXTURES / "deep.ged")]
    )
    assert code == 0
    assert out.strip() == ""


def test_ancestors_g2():
    code, out, err = run_cmd(
        ["ancestors", "-g", "2", "@I004@", str(FIXTURES / "deep.ged")]
    )
    assert code == 0
    assert out.strip().splitlines() == ["Elder"]


def test_ancestors_invalid_g_zero():
    code, out, err = run_cmd(
        ["ancestors", "-g", "0", "@I004@", str(FIXTURES / "deep.ged")]
    )
    assert code == 1
    assert "Invalid generations value" in err


def test_ancestors_unknown_id():
    code, out, err = run_cmd(["ancestors", "@I999@", str(FIXTURES / "deep.ged")])
    assert code == 1
    assert "Unknown individual ID" in err


def test_ancestors_cycle(tmp_path):
    # create a circular parent-child reference: A is parent of B and B is parent of A
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME A /One/\n"
        "1 FAMS @F1@\n"
        "0 @I2@ INDI\n"
        "1 NAME B /Two/\n"
        "1 FAMS @F1@\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I1@\n"
        "1 WIFE @I2@\n"
        "1 CHIL @I2@\n"
        "0 @F2@ FAM\n"
        "1 HUSB @I2@\n"
        "1 WIFE @I1@\n"
        "1 CHIL @I1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "cycle.ged"
    f.write_text(content)
    code, out, err = run_cmd(["ancestors", "@I1@", str(f)])
    assert code == 0
    # should finish quickly and not crash; surnames may include both


def test_debug_flag_shows_traceback():
    # invoke with a missing file to trigger FileNotFoundError and use --debug
    code, out, err = run_cmd(["--debug", "name", "@I001@", "nonexistent.ged"])
    assert code != 0
    assert "Traceback" in err
