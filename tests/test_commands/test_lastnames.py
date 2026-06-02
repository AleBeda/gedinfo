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


def test_lastnames_unlimited():
    code, out, err = run_cmd(["lastnames", "@I004@", str(FIXTURES / "deep.ged")])
    assert code == 0
    assert out.strip().splitlines() == ["Elder"]


def test_lastnames_g1():
    code, out, err = run_cmd(
        ["lastnames", "-g", "1", "@I004@", str(FIXTURES / "deep.ged")]
    )
    assert code == 0
    assert out.strip() == ""


def test_lastnames_g2():
    code, out, err = run_cmd(
        ["lastnames", "-g", "2", "@I004@", str(FIXTURES / "deep.ged")]
    )
    assert code == 0
    assert out.strip().splitlines() == ["Elder"]


def test_lastnames_invalid_g_zero():
    code, out, err = run_cmd(
        ["lastnames", "-g", "0", "@I004@", str(FIXTURES / "deep.ged")]
    )
    assert code == 1
    assert "Invalid generations value" in err


def test_lastnames_unknown_id():
    code, out, err = run_cmd(["lastnames", "@I999@", str(FIXTURES / "deep.ged")])
    assert code == 1
    assert "Unknown individual ID" in err


def test_lastnames_cycle(tmp_path):
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
    code, out, err = run_cmd(["lastnames", "@I1@", str(f)])
    assert code == 0
    # should finish quickly and not crash; surnames may include both


def test_debug_flag_shows_traceback():
    # invoke with a missing file to trigger FileNotFoundError and use --debug
    code, out, err = run_cmd(["--debug", "name", "@I001@", "nonexistent.ged"])
    assert code != 0
    assert "Traceback" in err


def test_long_no_g():
    code, out, err = run_cmd([
        "lastnames",
        "-l",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    # should contain 5 branch-tip ancestors
    assert len(lines) == 5
    # ensure intermediate ancestors not present
    assert "I002" not in out and "I003" not in out and "I004" not in out
    # default sort for --long is by path (paternal to maternal: ppp first, mmm last)
    expected_order = ["ppp", "pp?", "pm", "mp", "mm"]
    got_paths = [ln.split("\t")[1] for ln in lines]
    assert got_paths == expected_order
    # check specific line for @I009@
    for ln in lines:
        if ln.endswith("I009"):
            assert ln == "4\tpp?\tSvensson\tI009"


def test_long_g3():
    code, out, err = run_cmd([
        "lastnames",
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
    assert got_paths == ["pp", "pm", "mp", "mm"]


def test_long_g2():
    code, out, err = run_cmd([
        "lastnames",
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
    assert got_paths == ["p", "m"]


def test_long_sort_generation():
    code, out, err = run_cmd([
        "lastnames",
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
    # within generation 3, paths should be pm, mp, mm (paternal to maternal)
    gen3_paths = [ln.split("\t")[1] for ln in lines if ln.split("\t")[0] == "3"]
    assert gen3_paths == ["pm", "mp", "mm"]


def test_long_sort_name():
    code, out, err = run_cmd([
        "lastnames",
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
        "lastnames",
        "-l",
        "-s",
        "id",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    ids = [ln.split("\t")[-1] for ln in lines]
    assert ids == ["I005", "I006", "I007", "I008", "I009"]


def test_long_unknown_last_name(tmp_path):
    # create a ged where a branch-tip has only last name (not fully nameless)
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME John /Doe/\n"
        "1 FAMC @F1@\n"
        "0 @I2@ INDI\n"
        "1 NAME /Smith/\n"
        "1 FAMS @F1@\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I1@\n"
        "1 WIFE @I2@\n"
        "1 CHIL @I3@\n"
        "0 @I3@ INDI\n"
        "1 NAME Alice /Brown/\n"
        "1 FAMC @F1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "tmp.ged"
    f.write_text(content)
    code, out, err = run_cmd(["lastnames", "-l", "@I3@", str(f)])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    # should find Smith (partial last name)
    assert any("Smith" in ln for ln in lines)


def test_long_unknown_shown_with_u_flag(tmp_path):
    # create a ged where a branch-tip is completely nameless
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME John /Doe/\n"
        "1 FAMC @F1@\n"
        "0 @I2@ INDI\n"
        "1 SEX M\n"
        "1 FAMS @F1@\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I2@\n"
        "1 WIFE @I1@\n"
        "1 CHIL @I3@\n"
        "0 @I3@ INDI\n"
        "1 NAME Alice /Smith/\n"
        "1 FAMC @F1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "tmp_u.ged"
    f.write_text(content)
    code, out, err = run_cmd(["lastnames", "-l", "-u", "@I3@", str(f)])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    # should include (unknown) with -u flag
    assert any("(unknown)" in ln for ln in lines)


def test_long_unknown_suppressed_by_default(tmp_path):
    # create a ged where a parent has no NAME (nameless ancestor)
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME Child /One/\n"
        "1 FAMC @F1@\n"
        "0 @I2@ INDI\n"
        "1 NAME Parent /Two/\n"
        "1 FAMS @F1@\n"
        "0 @I6@ INDI\n"
        "1 SEX M\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I6@\n"
        "1 WIFE @I2@\n"
        "1 CHIL @I1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "tmp2.ged"
    f.write_text(content)
    code, out, err = run_cmd(["lastnames", "-l", "@I1@", str(f)])
    assert code == 0
    # by default, nameless ancestor should be suppressed
    assert "(unknown)" not in out


def test_long_unknown_included_with_flag(tmp_path):
    # same ged as above but include -u to show nameless ancestors
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME Child /One/\n"
        "1 FAMC @F1@\n"
        "0 @I2@ INDI\n"
        "1 NAME Parent /Two/\n"
        "1 FAMS @F1@\n"
        "0 @I6@ INDI\n"
        "1 SEX M\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I6@\n"
        "1 WIFE @I2@\n"
        "1 CHIL @I1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "tmp3.ged"
    f.write_text(content)
    code, out, err = run_cmd(["lastnames", "-l", "-u", "@I1@", str(f)])
    assert code == 0
    assert "(unknown)" in out


def test_sort_without_long():
    code, out, err = run_cmd([
        "lastnames",
        "-s",
        "name",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 1
    assert "--sort requires --long" in err


def test_long_empty_output():
    code, out, err = run_cmd([
        "lastnames",
        "-l",
        "@I001@",
        str(FIXTURES / "simple.ged"),
    ])
    assert code == 0
    assert out.strip() == ""


def test_long_with_existing_g_validation():
    code, out, err = run_cmd([
        "lastnames",
        "-l",
        "-g",
        "0",
        "@I001@",
        str(FIXTURES / "long_ancestors.ged"),
    ])
    assert code == 1
    assert "Invalid generations value" in err


def test_direction_ancestors_default():
    # Default direction is ancestors — same as explicit --direction ancestors
    code_default, out_default, _ = run_cmd(["lastnames", "@I004@", str(FIXTURES / "deep.ged")])
    code_explicit, out_explicit, _ = run_cmd(["lastnames", "--direction", "ancestors", "@I004@", str(FIXTURES / "deep.ged")])
    assert code_default == 0
    assert code_explicit == 0
    assert out_default == out_explicit


def test_direction_up_alias():
    # 'up' is an alias for 'ancestors'
    code_a, out_a, _ = run_cmd(["lastnames", "--direction", "ancestors", "@I004@", str(FIXTURES / "deep.ged")])
    code_b, out_b, _ = run_cmd(["lastnames", "--direction", "up", "@I004@", str(FIXTURES / "deep.ged")])
    assert code_a == 0
    assert code_b == 0
    assert out_a == out_b


def test_direction_descendants_short_mode(tmp_path):
    # I1 has two children with different last names
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME Root /One/\n1 SEX M\n1 FAMS @F1@\n"
        "0 @I2@ INDI\n1 NAME Son /Alpha/\n1 SEX M\n1 FAMC @F1@\n"
        "0 @I3@ INDI\n1 NAME Daughter /Beta/\n1 SEX F\n1 FAMC @F1@\n"
        "0 @F1@ FAM\n1 HUSB @I1@\n1 CHIL @I2@\n1 CHIL @I3@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "desc_lastnames.ged"
    f.write_text(content)
    code, out, err = run_cmd(["lastnames", "--direction", "descendants", "@I1@", str(f)])
    assert code == 0
    names = out.strip().splitlines()
    assert "Alpha" in names
    assert "Beta" in names
    assert "One" not in names  # root's own surname not included


def test_direction_down_alias(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME Root /A/\n1 SEX M\n1 FAMS @F1@\n"
        "0 @I2@ INDI\n1 NAME Child /B/\n1 SEX M\n1 FAMC @F1@\n"
        "0 @F1@ FAM\n1 HUSB @I1@\n1 CHIL @I2@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "desc_down.ged"
    f.write_text(content)
    code_a, out_a, _ = run_cmd(["lastnames", "--direction", "descendants", "@I1@", str(f)])
    code_b, out_b, _ = run_cmd(["lastnames", "--direction", "down", "@I1@", str(f)])
    assert code_a == 0
    assert code_b == 0
    assert out_a == out_b


def test_direction_descendants_long_mode(tmp_path):
    # I1 has a child I2; I2 has no children → I2 is a branch tip
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME Root /Smith/\n1 SEX M\n1 FAMS @F1@\n"
        "0 @I2@ INDI\n1 NAME Child /Jones/\n1 SEX M\n1 FAMC @F1@\n"
        "0 @F1@ FAM\n1 HUSB @I1@\n1 CHIL @I2@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "desc_long.ged"
    f.write_text(content)
    code, out, err = run_cmd(["lastnames", "-l", "--direction", "descendants", "@I1@", str(f)])
    assert code == 0
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    assert len(lines) == 1
    assert "Jones" in lines[0]
    assert "I2" in lines[0]
