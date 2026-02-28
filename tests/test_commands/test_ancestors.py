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


def test_long_no_g():
    code, out, err = run_cmd([
        "ancestors",
        "-l",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    # should contain 5 branch-tip ancestors
    assert len(lines) == 5
    # ensure intermediate ancestors not present
    assert "@I002@" not in out and "@I003@" not in out and "@I004@" not in out
    # default sort for --long is by path
    expected_order = ["mm", "mp", "pm", "pp?", "ppp"]
    got_paths = [ln.split("\t")[1] for ln in lines]
    assert got_paths == expected_order
    # check specific line for @I009@
    for ln in lines:
        if ln.endswith("@I009@"):
            assert ln == "4\tpp?\tSvensson\t@I009@"


def test_long_g3():
    code, out, err = run_cmd([
        "ancestors",
        "-l",
        "-g",
        "3",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    assert len(lines) == 4
    got_paths = [ln.split("\t")[1] for ln in lines]
    assert got_paths == ["mm", "mp", "pm", "pp"]


def test_long_g2():
    code, out, err = run_cmd([
        "ancestors",
        "-l",
        "-g",
        "2",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    assert len(lines) == 2
    got_paths = [ln.split("\t")[1] for ln in lines]
    assert got_paths == ["m", "p"]


def test_long_sort_generation():
    code, out, err = run_cmd([
        "ancestors",
        "-l",
        "-s",
        "generation",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    gens = [int(ln.split("\t")[0]) for ln in lines]
    assert gens[:3] == [3, 3, 3]
    assert gens[3:] == [4, 4]
    # within generation 3, paths should be mm, mp, pm
    gen3_paths = [ln.split("\t")[1] for ln in lines if ln.split("\t")[0] == "3"]
    assert gen3_paths == ["mm", "mp", "pm"]


def test_long_sort_name():
    code, out, err = run_cmd([
        "ancestors",
        "-l",
        "-s",
        "name",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    last_names = [ln.split("\t")[2] for ln in lines]
    assert last_names == ["Bauer", "Muller", "Novak", "Svensson", "Weber"]


def test_long_sort_id():
    code, out, err = run_cmd([
        "ancestors",
        "-l",
        "-s",
        "id",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    ids = [ln.split("\t")[3] for ln in lines]
    assert ids == ["@I005@", "@I006@", "@I007@", "@I008@", "@I009@"]


def test_long_unknown_last_name(tmp_path):
    # create a ged where a branch-tip has no last name
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME John /Doe/\n"
        "1 FAMC @F1@\n"
        "0 @I2@ INDI\n"
        "1 NAME /\n"
        "1 FAMS @F1@\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I1@\n"
        "1 WIFE @I2@\n"
        "1 CHIL @I3@\n"
        "0 @I3@ INDI\n"
        "1 NAME Alice /Smith/\n"
        "1 FAMC @F1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "tmp.ged"
    f.write_text(content)
    code, out, err = run_cmd(["ancestors", "-l", "@I3@", str(f)])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    # husband is a root and has last name '', should print (unknown)
    assert any("(unknown)" in ln for ln in lines)


def test_sort_without_long():
    code, out, err = run_cmd([
        "ancestors",
        "-s",
        "name",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 1
    assert "--sort requires --long" in err


def test_long_empty_output():
    code, out, err = run_cmd([
        "ancestors",
        "-l",
        "@I001@",
        str(FIXTURES / "simple.ged"),
    ])
    assert code == 0
    assert out.strip() == ""


def test_long_with_existing_g_validation():
    code, out, err = run_cmd([
        "ancestors",
        "-l",
        "-g",
        "0",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 1
    assert "Invalid generations value" in err
