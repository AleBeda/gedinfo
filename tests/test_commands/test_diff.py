import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
GED_A = str(FIXTURES / "diff_a.ged")
GED_B = str(FIXTURES / "diff_b.ged")


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _rows(out: str) -> list[list[str]]:
    return [line.split("\t") for line in out.splitlines() if line and not line.startswith(" ")]


def test_basic_chg_del_ins():
    code, out, err = run_cmd(["diff", GED_A, GED_B])
    assert code == 0
    rows = {r[0]: r[-1] for r in _rows(out)}
    assert rows["I001"] == "CHG"
    assert rows["I004"] == "DEL"
    assert rows["I005"] == "INS"
    assert rows["F001"] == "CHG"
    assert rows["F002"] == "DEL"
    assert rows["F003"] == "INS"


def test_unchanged_individual_not_in_output():
    code, out, _ = run_cmd(["diff", GED_A, GED_B])
    assert code == 0
    ids = [r[0] for r in _rows(out)]
    assert "I002" not in ids
    assert "I003" not in ids


def test_no_diff_identical_files():
    code, out, err = run_cmd(["diff", GED_A, GED_A])
    assert code == 0
    assert out == ""


def test_id_flag():
    code, out, _ = run_cmd(["diff", "-i", GED_A, GED_B])
    assert code == 0
    rows = _rows(out)
    # each row has exactly 2 fields: ID and code
    for row in rows:
        assert len(row) == 2, f"expected 2 fields, got: {row}"
    ids = {r[0] for r in rows}
    assert "I001" in ids
    assert "I004" in ids
    assert "I005" in ids


def test_name_flag():
    code, out, _ = run_cmd(["diff", "-n", GED_A, GED_B])
    assert code == 0
    rows = _rows(out)
    # each row has exactly 2 fields: name and code
    for row in rows:
        assert len(row) == 2, f"expected 2 fields, got: {row}"
    names = {r[0] for r in rows}
    assert "John Smith" in names
    assert "Bob Smith" in names
    assert "New Person" in names


def test_long_chg_shows_field_details():
    code, out, _ = run_cmd(["diff", "-l", GED_A, GED_B])
    assert code == 0
    lines = out.splitlines()
    # find the I001 entry and check that field details follow
    idx = next(i for i, l in enumerate(lines) if l.startswith("I001"))
    assert lines[idx + 1].startswith("  birth_date")
    assert lines[idx + 2].startswith("    < 1 JAN 1800")
    assert lines[idx + 3].startswith("    > 2 JAN 1800")


def test_long_del_ins_no_field_details():
    code, out, _ = run_cmd(["diff", "-l", GED_A, GED_B])
    assert code == 0
    lines = out.splitlines()
    # DEL entry (I004) should be followed by I005 or another top-level line, not indented details
    idx = next(i for i, l in enumerate(lines) if l.startswith("I004"))
    if idx + 1 < len(lines):
        assert not lines[idx + 1].startswith("  "), "DEL entry should have no field details"


def test_long_family_chg_shows_child_ids():
    code, out, _ = run_cmd(["diff", "-l", GED_A, GED_B])
    assert code == 0
    lines = out.splitlines()
    idx = next(i for i, l in enumerate(lines) if l.startswith("F001"))
    detail_block = "\n".join(lines[idx:idx + 10])
    assert "child_ids" in detail_block
    assert "I003, I004" in detail_block
    assert "> I003" in detail_block


def test_sort_name():
    code, out, _ = run_cmd(["diff", "--sort", "name", GED_A, GED_B])
    assert code == 0
    rows = _rows(out)
    indi_rows = [r for r in rows if r[0][0] == "I"]
    names = [r[1] for r in indi_rows]
    assert names == sorted(names, key=str.lower)


def test_all_flag_sex_change():
    # Create a scenario where sex differs: compare diff_a (I001 sex M) against a file
    # where sex is different. We use diff_b which has I001 sex M — same, so no sex CHG.
    # Use --all with identical files to confirm no output.
    code, out, _ = run_cmd(["diff", "--all", GED_A, GED_A])
    assert code == 0
    assert out == ""


def test_all_flag_picks_up_extra_field(tmp_path):
    # Write two files where sex differs for the same individual
    a = tmp_path / "a.ged"
    b = tmp_path / "b.ged"
    a.write_text("0 HEAD\n1 SOUR x\n0 @I001@ INDI\n1 NAME Jo /S/\n1 SEX M\n0 TRLR\n")
    b.write_text("0 HEAD\n1 SOUR x\n0 @I001@ INDI\n1 NAME Jo /S/\n1 SEX F\n0 TRLR\n")
    # Without --all: no CHG (sex is not a core field)
    code, out, _ = run_cmd(["diff", str(a), str(b)])
    assert code == 0
    assert out == ""
    # With --all: CHG for I001
    code, out, _ = run_cmd(["diff", "--all", str(a), str(b)])
    assert code == 0
    assert "I001" in out
    assert "CHG" in out


def test_conflict_i_and_long():
    code, out, err = run_cmd(["diff", "-i", "-l", GED_A, GED_B])
    assert code == 1
    assert "--long" in err or "-i" in err


def test_conflict_n_and_long():
    code, out, err = run_cmd(["diff", "-n", "-l", GED_A, GED_B])
    assert code == 1
    assert "--long" in err or "-n" in err


def test_conflict_i_and_n():
    code, out, err = run_cmd(["diff", "-i", "-n", GED_A, GED_B])
    assert code == 1
    assert err.strip() != ""


def test_unknown_file():
    code, out, err = run_cmd(["diff", "nonexistent.ged", GED_B])
    assert code == 1
    assert out == ""
    assert err.strip() != ""


def test_individuals_before_families():
    code, out, _ = run_cmd(["diff", GED_A, GED_B])
    assert code == 0
    lines = [l for l in out.splitlines() if not l.startswith(" ")]
    indi_lines = [l for l in lines if l.startswith("I")]
    fam_lines = [l for l in lines if l.startswith("F")]
    if indi_lines and fam_lines:
        last_indi = lines.index(indi_lines[-1])
        first_fam = lines.index(fam_lines[0])
        assert last_indi < first_fam


def test_default_sort_is_by_id():
    code, out, _ = run_cmd(["diff", GED_A, GED_B])
    assert code == 0
    rows = _rows(out)
    indi_ids = [r[0] for r in rows if r[0].startswith("I")]
    fam_ids = [r[0] for r in rows if r[0].startswith("F")]
    # numeric ID order: I001 < I004 < I005
    nums_i = [int(x[1:]) for x in indi_ids]
    assert nums_i == sorted(nums_i)
    nums_f = [int(x[1:]) for x in fam_ids]
    assert nums_f == sorted(nums_f)


def test_family_name_in_output():
    code, out, _ = run_cmd(["diff", GED_A, GED_B])
    assert code == 0
    # F001 should show "John Smith & Mary Jones"
    fam_line = next(l for l in out.splitlines() if l.startswith("F001"))
    assert "John Smith & Mary Jones" in fam_line
    # F002 and F003 have no spouses
    fam_del = next(l for l in out.splitlines() if l.startswith("F002"))
    assert "(unknown)" in fam_del
