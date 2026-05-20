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


# long_ancestors.ged has I001 (Jan Novak) as subject with 8 ancestors across 4 generations:
# gen 2: I002 (Pieter Novak, p), I003 (Anna Muller, m)
# gen 3: I004 (Hans Novak, pp), I005 (Greta Bauer, pm), I006 (Ernst Muller, mp), I007 (Lena Weber, mm)
# gen 4: I008 (Otto Novak, ppp), I009 (Unknown Svensson, pp?)


def test_short_mode():
    code, out, _ = run_cmd(["ancestors", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 9  # subject + 8 ancestors
    # subject must appear first
    assert lines[0].startswith("I001")


def test_short_g1():
    code, out, _ = run_cmd(["ancestors", "-g", "1", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("I001")


def test_short_g2():
    code, out, _ = run_cmd(["ancestors", "-g", "2", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 3  # subject + 2 parents
    ids = [ln.split("\t")[0] for ln in lines]
    assert "I001" in ids and "I002" in ids and "I003" in ids


def test_short_id_only():
    code, out, _ = run_cmd(["ancestors", "-i", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 9
    assert all("\t" not in ln for ln in lines)
    assert "I001" in lines


def test_short_name_only():
    code, out, _ = run_cmd(["ancestors", "-n", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 9
    assert all("\t" not in ln for ln in lines)
    assert any("Novak" in ln for ln in lines)


def test_subject_in_output():
    code, out, _ = run_cmd(["ancestors", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    assert "I001" in out


def test_long_all():
    code, out, _ = run_cmd(["ancestors", "-l", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 9
    # default sort: generation then path; subject (gen 1) must be first
    first = lines[0].split("\t")
    assert first[0] == "1" and first[1] == ""
    # check 4-column format for a non-subject line
    cols = lines[1].split("\t")
    assert len(cols) >= 4


def test_long_g3():
    code, out, _ = run_cmd(["ancestors", "-l", "-g", "3", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 7  # gen 1 + 2 + 4
    gens = [int(ln.split("\t")[0]) for ln in lines]
    assert max(gens) == 3


def test_long_sort_generation():
    code, out, _ = run_cmd(["ancestors", "-l", "-s", "generation", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    gens = [int(ln.split("\t")[0]) for ln in lines]
    assert gens == sorted(gens)
    assert gens[0] == 1


def test_long_sort_path():
    code, out, _ = run_cmd(["ancestors", "-l", "-s", "path", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    # subject (empty path) must be first
    assert lines[0].split("\t")[1] == ""
    # "p" before "m" paths
    paths = [ln.split("\t")[1] for ln in lines[1:]]
    p_indices = [i for i, p in enumerate(paths) if p.startswith("p")]
    m_indices = [i for i, p in enumerate(paths) if p.startswith("m")]
    assert p_indices and m_indices
    assert max(p_indices) < min(m_indices)


def test_long_sort_name():
    code, out, _ = run_cmd(["ancestors", "-l", "-s", "name", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    last_names = [ln.split("\t")[2].strip() for ln in lines]
    named = [n for n in last_names if n != "(unknown)"]
    assert named == sorted(named, key=str.lower)


def test_long_sort_id():
    code, out, _ = run_cmd(["ancestors", "-l", "-s", "id", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    ids = [ln.split("\t")[-1] for ln in lines]
    assert ids == sorted(ids)


def test_long_unknown_suppressed(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME Child /One/\n"
        "1 FAMC @F1@\n"
        "0 @I2@ INDI\n"
        "1 SEX M\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I2@\n"
        "1 CHIL @I1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "nameless.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["ancestors", "-l", "@I1@", str(f)])
    assert code == 0
    assert "(unknown)" not in out


def test_long_unknown_included(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME Child /One/\n"
        "1 FAMC @F1@\n"
        "0 @I2@ INDI\n"
        "1 SEX M\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I2@\n"
        "1 CHIL @I1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "nameless.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["ancestors", "-l", "-u", "@I1@", str(f)])
    assert code == 0
    assert "(unknown)" in out


def test_sort_requires_long():
    code, out, err = run_cmd(["ancestors", "-s", "name", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 1
    assert "--sort requires --long" in err


def test_id_name_conflict():
    code, _, err = run_cmd(["ancestors", "-i", "-n", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 1


def test_long_with_id_flag():
    code, _, err = run_cmd(["ancestors", "-l", "-i", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 1
    assert "--long cannot be combined with --id or --name" in err


def test_long_with_name_flag():
    code, _, err = run_cmd(["ancestors", "-l", "-n", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 1
    assert "--long cannot be combined with --id or --name" in err


def test_invalid_g():
    code, _, err = run_cmd(["ancestors", "-g", "0", "@I001@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 1
    assert "Invalid generations value" in err


def test_unknown_id():
    code, _, err = run_cmd(["ancestors", "@I999@", str(FIXTURES / "long_ancestors.ged")])
    assert code == 1
    assert "Unknown individual ID" in err


def test_cycle_safe(tmp_path):
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
    code, _, _ = run_cmd(["ancestors", "@I1@", str(f)])
    assert code == 0
