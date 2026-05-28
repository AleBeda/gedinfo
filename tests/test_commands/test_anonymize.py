import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
GED = str(FIXTURES / "anonymize.ged")


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_basic_structure():
    code, out, _ = run_cmd(["anonymize", GED])
    assert code == 0
    assert out.startswith("0 HEAD")
    assert "0 @I001@ INDI" in out
    assert "0 @F001@ FAM" in out
    assert "0 TRLR" in out


def test_names_anonymized():
    code, out, _ = run_cmd(["anonymize", GED])
    assert code == 0
    assert "John" not in out
    assert "Jane" not in out
    assert "Smith" not in out
    assert "1 NAME " in out


def test_consistent_last_name():
    code, out, _ = run_cmd(["anonymize", GED])
    assert code == 0
    last_names = []
    for line in out.splitlines():
        if "1 NAME " in line:
            name_val = line.split("1 NAME ", 1)[1].strip()
            if "/" in name_val:
                last_names.append(name_val.split("/")[1].strip())
    # I001 (John Smith) and I002 (Jane Smith) both had "Smith" → same fake last name
    assert len(last_names) == 3
    assert last_names[0] == last_names[1]


def test_dates_preserved():
    code, out, _ = run_cmd(["anonymize", GED])
    assert code == 0
    assert "1 JAN 1900" in out
    assert "10 FEB 1905" in out
    assert "15 JUN 1925" in out


def test_sex_preserved():
    code, out, _ = run_cmd(["anonymize", GED])
    assert code == 0
    assert "1 SEX M" in out
    assert "1 SEX F" in out


def test_plac_anonymized():
    code, out, _ = run_cmd(["anonymize", GED])
    assert code == 0
    assert "Livorno" not in out
    assert "Italy" not in out
    assert "PLAC" in out


def test_plac_consistent():
    code, out, _ = run_cmd(["anonymize", GED])
    assert code == 0
    plac_values = [
        ln.split("PLAC ", 1)[1].strip()
        for ln in out.splitlines()
        if "PLAC " in ln
    ]
    assert len(plac_values) == 3
    assert len(set(plac_values)) == 1  # all three occurrences map to the same fake place


def test_note_anonymized():
    code, out, _ = run_cmd(["anonymize", GED])
    assert code == 0
    assert "A short note." not in out
    assert "1 NOTE " in out


def test_occu_stripped():
    code, out, _ = run_cmd(["anonymize", GED])
    assert code == 0
    assert "OCCU" not in out


def test_head_stripped_and_rebuilt():
    code, out, _ = run_cmd(["anonymize", GED])
    assert code == 0
    assert "SomeApp" not in out
    assert "VERS 5.5.1" in out
    assert "CHAR UTF-8" in out


def test_deterministic():
    _, out1, _ = run_cmd(["anonymize", GED])
    _, out2, _ = run_cmd(["anonymize", GED])
    assert out1 == out2


def test_output_flag(tmp_path):
    out_file = str(tmp_path / "out.ged")
    code, stdout, _ = run_cmd(["anonymize", "-o", out_file, GED])
    assert code == 0
    assert stdout == ""
    content = Path(out_file).read_text()
    assert "0 HEAD" in content
    assert "0 TRLR" in content


def test_keep_option():
    code, out, _ = run_cmd(["anonymize", "--keep", "OCCU", GED])
    assert code == 0
    assert "OCCU" in out
    assert "Farmer" in out


def test_remove_option():
    code, out, _ = run_cmd(["anonymize", "--remove", "DATE", GED])
    assert code == 0
    assert "DATE" not in out


def test_fake_date_option():
    code, out, _ = run_cmd(["anonymize", "--fake", "DATE", GED])
    assert code == 0
    # DATE lines should still be present
    date_lines = [ln for ln in out.splitlines() if "DATE" in ln]
    assert len(date_lines) >= 1
    # Fake dates should be in GEDCOM date format (D+ MON YYYY)
    import re
    date_pattern = re.compile(r"\d+ [A-Z]{3} \d{4}")
    for ln in date_lines:
        assert date_pattern.search(ln), f"Date not in expected format: {ln!r}"
    # Original dates should be replaced
    assert "1 JAN 1900" not in out


def test_conflict_error():
    code, _, err = run_cmd(["anonymize", "--keep", "DATE", "--remove", "DATE", GED])
    assert code == 1
    assert "DATE" in err


def test_unknown_file():
    code, _, err = run_cmd(["anonymize", "nonexistent.ged"])
    assert code == 1
    assert "nonexistent.ged" in err.lower() or "not found" in err.lower()
