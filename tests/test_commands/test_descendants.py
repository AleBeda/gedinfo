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


# descendants.ged has I001 (John Smith) as subject with 4 descendants:
# gen 2: I003 (Peter Smith, path "s"), I004 (Anna Smith, path "d")
# gen 3: I006 (Tom Smith, path "ss"), I007 (Sue Smith, path "sd")


def test_short_mode():
    code, out, _ = run_cmd(["descendants", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 5  # subject + 4 descendants
    assert lines[0].startswith("I001")


def test_short_g1():
    code, out, _ = run_cmd(["descendants", "-g", "1", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("I001")


def test_short_g2():
    code, out, _ = run_cmd(["descendants", "-g", "2", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 3  # subject + I003 + I004
    ids = [ln.split("\t")[0] for ln in lines]
    assert "I001" in ids and "I003" in ids and "I004" in ids


def test_short_id_only():
    code, out, _ = run_cmd(["descendants", "-i", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 5
    assert all("\t" not in ln for ln in lines)
    assert "I001" in lines


def test_short_name_only():
    code, out, _ = run_cmd(["descendants", "-n", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 5
    assert all("\t" not in ln for ln in lines)
    assert any("Smith" in ln for ln in lines)


def test_subject_in_output():
    code, out, _ = run_cmd(["descendants", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    assert "I001" in out


def test_long_all():
    code, out, _ = run_cmd(["descendants", "-l", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 5
    # subject (gen 1, empty path) must be first in default (generation) sort
    first = lines[0].split("\t")
    assert first[0] == "1" and first[1] == ""


def test_long_g2():
    code, out, _ = run_cmd(["descendants", "-l", "-g", "2", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    assert len(lines) == 3  # gen 1 + 2
    gens = [int(ln.split("\t")[0]) for ln in lines]
    assert max(gens) == 2


def test_long_path_notation():
    code, out, _ = run_cmd(["descendants", "-l", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    paths = [ln.split("\t")[1] for ln in out.strip().splitlines()]
    assert "" in paths   # subject
    assert "s" in paths  # son
    assert "d" in paths  # daughter
    assert "ss" in paths  # grandson
    assert "sd" in paths  # granddaughter


def test_long_sort_generation():
    code, out, _ = run_cmd(["descendants", "-l", "-s", "generation", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    gens = [int(ln.split("\t")[0]) for ln in lines]
    assert gens == sorted(gens)
    assert gens[0] == 1


def test_long_sort_path():
    code, out, _ = run_cmd(["descendants", "-l", "-s", "path", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    paths = [ln.split("\t")[1] for ln in lines]
    # subject (empty path) first; sons ("s") before daughters ("d")
    assert paths[0] == ""
    s_indices = [i for i, p in enumerate(paths[1:]) if p.startswith("s")]
    d_indices = [i for i, p in enumerate(paths[1:]) if p.startswith("d")]
    assert s_indices and d_indices
    assert max(s_indices) < min(d_indices)


def test_long_sort_name():
    code, out, _ = run_cmd(["descendants", "-l", "-s", "name", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    last_names = [ln.split("\t")[2].strip() for ln in lines]
    named = [n for n in last_names if n != "(unknown)"]
    assert named == sorted(named, key=str.lower)


def test_long_sort_id():
    code, out, _ = run_cmd(["descendants", "-l", "-s", "id", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 0
    lines = out.strip().splitlines()
    ids = [ln.split("\t")[-1] for ln in lines]
    assert ids == sorted(ids)


def test_long_unknown_suppressed(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME Parent /One/\n"
        "1 SEX M\n"
        "1 FAMS @F1@\n"
        "0 @I2@ INDI\n"
        "1 SEX F\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I1@\n"
        "1 CHIL @I2@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "nameless.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["descendants", "-l", "@I1@", str(f)])
    assert code == 0
    assert "(unknown)" not in out


def test_long_unknown_included(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME Parent /One/\n"
        "1 SEX M\n"
        "1 FAMS @F1@\n"
        "0 @I2@ INDI\n"
        "1 SEX F\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I1@\n"
        "1 CHIL @I2@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "nameless.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["descendants", "-l", "-u", "@I1@", str(f)])
    assert code == 0
    assert "(unknown)" in out


def test_sort_requires_long():
    code, _, err = run_cmd(["descendants", "-s", "name", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 1
    assert "--sort requires --long" in err


def test_long_with_id_flag():
    code, _, err = run_cmd(["descendants", "-l", "-i", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 1
    assert "--long cannot be combined with --id or --name" in err


def test_long_with_name_flag():
    code, _, err = run_cmd(["descendants", "-l", "-n", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 1
    assert "--long cannot be combined with --id or --name" in err


def test_invalid_g():
    code, _, err = run_cmd(["descendants", "-g", "0", "@I001@", str(FIXTURES / "descendants.ged")])
    assert code == 1
    assert "Invalid generations value" in err


def test_unknown_id():
    code, _, err = run_cmd(["descendants", "@I999@", str(FIXTURES / "descendants.ged")])
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
    code, _, _ = run_cmd(["descendants", "@I1@", str(f)])
    assert code == 0
