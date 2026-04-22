import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
GED = str(FIXTURES / "givennames.ged")


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_basic_output():
    code, out, err = run_cmd(["givennames", "--direction", "asc", "@I001@", GED])
    assert code == 0
    assert "Masculine names:" in out
    assert "Feminine names:" in out
    # I002 contributes "abraham" (from first_name) and "avraham" (from GIVN) — distinct tokens
    assert "abraham" in out
    assert "avraham" in out
    # I004 contributes "moshe"
    assert "moshe" in out
    # I003 contributes "sarah"
    assert "sarah" in out
    # I005 contributes "miriam"
    assert "miriam" in out
    # Counts are 1 per individual — each name appears with count 1
    lines = out.splitlines()
    masc_lines = [l for l in lines if "\t" in l and l.split("\t")[1] == "abraham"]
    assert masc_lines and masc_lines[0].split("\t")[0] == "1"
    moshe_lines = [l for l in lines if "\t" in l and l.split("\t")[1] == "moshe"]
    assert moshe_lines and moshe_lines[0].split("\t")[0] == "1"
    sarah_lines = [l for l in lines if "\t" in l and l.split("\t")[1] == "sarah"]
    assert sarah_lines and sarah_lines[0].split("\t")[0] == "1"
    miriam_lines = [l for l in lines if "\t" in l and l.split("\t")[1] == "miriam"]
    assert miriam_lines and miriam_lines[0].split("\t")[0] == "1"


def test_g1_no_output():
    # -g 1 means only generation 1 (subject itself), subject is not included → no output
    code, out, err = run_cmd(["givennames", "-g", "1", "--direction", "asc", "@I001@", GED])
    assert code == 0
    assert out.strip() == ""


def test_g2_parents_only():
    # -g 2: only generation 2 (direct parents I002, I003) counted; I004/I005 not included
    code, out, err = run_cmd(["givennames", "-g", "2", "--direction", "asc", "@I001@", GED])
    assert code == 0
    assert "Masculine names:" in out
    assert "Feminine names:" in out
    # I002 (M): abraham, avraham
    assert "abraham" in out
    assert "avraham" in out
    # I003 (F): sarah
    assert "sarah" in out
    # I004/I005 not included
    assert "moshe" not in out
    assert "miriam" not in out


def test_invalid_g_zero():
    code, out, err = run_cmd(["givennames", "-g", "0", "--direction", "asc", "@I001@", GED])
    assert code == 1
    assert "Invalid generations value" in err


def test_unknown_id():
    code, out, err = run_cmd(["givennames", "--direction", "asc", "@I999@", GED])
    assert code == 1
    assert "Unknown individual ID" in err


def test_second_flag():
    # --second includes NAM2 tags; I004 has NAM2 "Raphael" → raphael in masculine
    code, out, err = run_cmd(["givennames", "--second", "--direction", "asc", "@I001@", GED])
    assert code == 0
    assert "raphael" in out.lower()


def test_second_flag_short():
    # -s is the short form of --second
    code, out, err = run_cmd(["givennames", "-s", "--direction", "asc", "@I001@", GED])
    assert code == 0
    assert "raphael" in out.lower()


def test_second_flag_not_present_by_default():
    # Without --second, raphael should NOT appear
    code, out, err = run_cmd(["givennames", "--direction", "asc", "@I001@", GED])
    assert code == 0
    assert "raphael" not in out.lower()


def test_hebrew_flag():
    # --hebrew includes NAMH tags; I005 has NAMH "מרים" → appears in feminine
    code, out, err = run_cmd(["givennames", "--hebrew", "--direction", "asc", "@I001@", GED])
    assert code == 0
    assert "מרים" in out


def test_hebrew_flag_short():
    # -e is the short form of --hebrew
    code, out, err = run_cmd(["givennames", "-e", "--direction", "asc", "@I001@", GED])
    assert code == 0
    assert "מרים" in out


def test_hebrew_flag_not_present_by_default():
    # Without --hebrew, מרים should NOT appear (it only comes from NAMH)
    code, out, err = run_cmd(["givennames", "--direction", "asc", "@I001@", GED])
    assert code == 0
    assert "מרים" not in out


def test_all_flag():
    # -a should give same names as --second --hebrew combined
    code_a, out_a, _ = run_cmd(["givennames", "-a", "--direction", "asc", "@I001@", GED])
    code_b, out_b, _ = run_cmd(["givennames", "--second", "--hebrew", "--direction", "asc", "@I001@", GED])
    assert code_a == 0
    assert code_b == 0
    assert out_a == out_b


def test_fuzzy_groups_variants(tmp_path):
    # Create a fixture where two ancestors both have names that are variants of "abraham"
    # I002 = Abraham (M, parent), I006 = Abram (M, another parent via different family)
    content = (
        "0 HEAD\n"
        "0 @I001@ INDI\n"
        "1 NAME Probe /Test/\n"
        "1 SEX M\n"
        "1 FAMC @F001@\n"
        "1 FAMC @F002@\n"
        "0 @I002@ INDI\n"
        "1 NAME Abraham /Cohen/\n"
        "1 SEX M\n"
        "0 @I003@ INDI\n"
        "1 NAME Abram /Levi/\n"
        "1 SEX M\n"
        "0 @F001@ FAM\n"
        "1 HUSB @I002@\n"
        "1 CHIL @I001@\n"
        "0 @F002@ FAM\n"
        "1 HUSB @I003@\n"
        "1 CHIL @I001@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "fuzzy.ged"
    f.write_text(content, encoding="utf-8")
    code, out, err = run_cmd(["givennames", "-f", "--direction", "asc", "@I001@", str(f)])
    assert code == 0
    # "abraham" and "abram" are both variants of "abraham" in the variants file
    # They should be grouped: total=2, canonical="abraham", with detail
    assert "abraham" in out
    # The grouped line should show total count 2 and include both variants
    lines = out.splitlines()
    abraham_lines = [l for l in lines if "abraham" in l and "\t" in l]
    assert abraham_lines
    # Should show count 2 (both ancestors contribute)
    assert abraham_lines[0].startswith("2\t")
    # Since there are two variants, a parenthetical detail should appear
    assert "abram" in abraham_lines[0]


def test_fuzzy_single_variant(tmp_path):
    # A name not in the variants file should be printed without parenthetical
    content = (
        "0 HEAD\n"
        "0 @I001@ INDI\n"
        "1 NAME Probe /Test/\n"
        "1 SEX M\n"
        "1 FAMC @F001@\n"
        "0 @I002@ INDI\n"
        "1 NAME Zxqwerty /Unknown/\n"
        "1 SEX M\n"
        "0 @F001@ FAM\n"
        "1 HUSB @I002@\n"
        "1 CHIL @I001@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "single.ged"
    f.write_text(content, encoding="utf-8")
    code, out, err = run_cmd(["givennames", "-f", "--direction", "asc", "@I001@", str(f)])
    assert code == 0
    assert "zxqwerty" in out
    # No parenthetical detail for a name with only one variant
    lines = [l for l in out.splitlines() if "zxqwerty" in l]
    assert lines
    assert "(" not in lines[0]


def test_givn_deduplication(tmp_path):
    # When NAME given portion and GIVN contain the same string, count should be 1
    content = (
        "0 HEAD\n"
        "0 @I001@ INDI\n"
        "1 NAME Probe /Test/\n"
        "1 SEX M\n"
        "1 FAMC @F001@\n"
        "0 @I002@ INDI\n"
        "1 NAME Abraham /Cohen/\n"
        "1 GIVN Abraham\n"
        "1 SEX M\n"
        "0 @F001@ FAM\n"
        "1 HUSB @I002@\n"
        "1 CHIL @I001@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "dedup.ged"
    f.write_text(content, encoding="utf-8")
    code, out, err = run_cmd(["givennames", "--direction", "asc", "@I001@", str(f)])
    assert code == 0
    lines = [l for l in out.splitlines() if "\t" in l and l.split("\t")[1] == "abraham"]
    assert lines
    # count should be 1, not 2 (deduplication within-individual via set)
    assert lines[0].split("\t")[0] == "1"


def test_unknown_sex_section(tmp_path):
    # Individual with SEX U (or unrecognized) should appear in "Unknown sex" section
    content = (
        "0 HEAD\n"
        "0 @I001@ INDI\n"
        "1 NAME Probe /Test/\n"
        "1 SEX M\n"
        "1 FAMC @F001@\n"
        "0 @I002@ INDI\n"
        "1 NAME Jordan /Test/\n"
        "1 SEX U\n"
        "0 @F001@ FAM\n"
        "1 HUSB @I002@\n"
        "1 CHIL @I001@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "unknown_sex.ged"
    f.write_text(content, encoding="utf-8")
    code, out, err = run_cmd(["givennames", "--direction", "asc", "@I001@", str(f)])
    assert code == 0
    assert "Unknown sex:" in out
    assert "jordan" in out


def test_sibling_excluded():
    # I006 (Abram /Cohen/) is a sibling of I002, NOT an ancestor of I001
    # "abram" should NOT appear in basic output for @I001@
    code, out, err = run_cmd(["givennames", "--direction", "asc", "@I001@", GED])
    assert code == 0
    lines = out.splitlines()
    name_tokens = [l.split("\t")[1] for l in lines if "\t" in l]
    assert "abram" not in name_tokens


def test_name_split_spaces(tmp_path):
    # NAME "John David /X/" → both "john" and "david" appear as separate names
    content = (
        "0 HEAD\n"
        "0 @I001@ INDI\n"
        "1 NAME Probe /Test/\n"
        "1 SEX M\n"
        "1 FAMC @F001@\n"
        "0 @I002@ INDI\n"
        "1 NAME John David /X/\n"
        "1 SEX M\n"
        "0 @F001@ FAM\n"
        "1 HUSB @I002@\n"
        "1 CHIL @I001@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "multifirst.ged"
    f.write_text(content, encoding="utf-8")
    code, out, err = run_cmd(["givennames", "--direction", "asc", "@I001@", str(f)])
    assert code == 0
    assert "john" in out
    assert "david" in out


def test_blank_name_ignored(tmp_path):
    # Individual with NAME tag containing only spaces → no names counted
    content = (
        "0 HEAD\n"
        "0 @I001@ INDI\n"
        "1 NAME Probe /Test/\n"
        "1 SEX M\n"
        "1 FAMC @F001@\n"
        "0 @I002@ INDI\n"
        "1 NAME  \n"
        "1 SEX M\n"
        "0 @F001@ FAM\n"
        "1 HUSB @I002@\n"
        "1 CHIL @I001@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "blankname.ged"
    f.write_text(content, encoding="utf-8")
    code, out, err = run_cmd(["givennames", "--direction", "asc", "@I001@", str(f)])
    assert code == 0
    # No name sections should appear since the ancestor has no names
    assert out.strip() == ""


def test_direction_desc_basic():
    # Default direction is desc; I004's descendants include I002, I006, I001 (all M)
    code, out, err = run_cmd(["givennames", "@I004@", GED])
    assert code == 0
    assert "Masculine names:" in out
    assert "abraham" in out      # from I002
    assert "avraham" in out      # from I002's GIVN
    assert "abram" in out        # from I006
    assert "probe" in out        # from I001


def test_direction_desc_explicit():
    # Explicit --direction desc is equivalent to the default
    code_default, out_default, _ = run_cmd(["givennames", "@I004@", GED])
    code_explicit, out_explicit, _ = run_cmd(
        ["givennames", "--direction", "desc", "@I004@", GED]
    )
    assert code_default == 0
    assert code_explicit == 0
    assert out_default == out_explicit


def test_direction_asc_short():
    # -d asc is the short form and should match --direction asc
    code_long, out_long, _ = run_cmd(
        ["givennames", "--direction", "asc", "@I001@", GED]
    )
    code_short, out_short, _ = run_cmd(
        ["givennames", "-d", "asc", "@I001@", GED]
    )
    assert code_long == 0
    assert code_short == 0
    assert out_long == out_short


def test_direction_desc_g2():
    # -g 2 with --direction desc: only direct children of I004 (I002, I006),
    # not grandchildren (I001)
    code, out, err = run_cmd(
        ["givennames", "--direction", "desc", "-g", "2", "@I004@", GED]
    )
    assert code == 0
    assert "abraham" in out   # I002
    assert "abram" in out     # I006
    assert "probe" not in out  # I001 is generation 3, excluded


def test_direction_desc_subject_no_descendants():
    # A leaf node has no descendants; output should be empty
    code, out, err = run_cmd(["givennames", "@I001@", GED])
    assert code == 0
    assert out.strip() == ""


def test_direction_invalid():
    # An invalid direction value should produce an error exit
    code, out, err = run_cmd(
        ["givennames", "--direction", "sideways", "@I001@", GED]
    )
    assert code != 0
