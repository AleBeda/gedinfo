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
        ln.split("PLAC ", 1)[1].strip() for ln in out.splitlines() if "PLAC " in ln
    ]
    assert len(plac_values) == 3
    assert (
        len(set(plac_values)) == 1
    )  # all three occurrences map to the same fake place


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


def test_preserves_crlf_line_endings(tmp_path):
    content = Path(GED).read_text().replace("\n", "\r\n")
    f = tmp_path / "crlf.ged"
    f.write_bytes(content.encode("utf-8"))
    out_file = tmp_path / "out.ged"
    code, stdout, _ = run_cmd(["anonymize", "-o", str(out_file), str(f)])
    assert code == 0
    assert stdout == ""
    out_bytes = out_file.read_bytes()
    assert b"\r\n" in out_bytes
    assert b"\n" not in out_bytes.replace(b"\r\n", b"")


def test_preserves_lf_line_endings(tmp_path):
    out_file = tmp_path / "out.ged"
    code, _, _ = run_cmd(["anonymize", "-o", str(out_file), GED])
    assert code == 0
    out_bytes = out_file.read_bytes()
    assert b"\r\n" not in out_bytes
    assert b"\n" in out_bytes


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


def test_empty_name_preserved(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I001@ INDI\n1 NAME //\n1 SEX M\n"
        "0 @I002@ INDI\n1 NAME John /Smith/\n1 SEX M\n"
        "0 TRLR\n"
    )
    f = tmp_path / "empty.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["anonymize", str(f)])
    assert code == 0
    name_lines = [ln for ln in out.splitlines() if "1 NAME" in ln]
    # I001 has NAME // — the NAME tag must be stripped entirely from the output
    assert len(name_lines) == 1
    assert "//" not in name_lines[0]
    # I002 should get a real fake name (not "John" or "Smith")
    assert "John" not in name_lines[0] and "Smith" not in name_lines[0]


def test_seed_option():
    _, out0, _ = run_cmd(["anonymize", GED])  # default seed 0
    _, out42, _ = run_cmd(["anonymize", "--seed", "42", GED])
    assert out0 != out42


def test_seed_deterministic():
    _, out1, _ = run_cmd(["anonymize", "--seed", "42", GED])
    _, out2, _ = run_cmd(["anonymize", "--seed", "42", GED])
    assert out1 == out2


def test_no_last_name_preserved(tmp_path):
    content = "0 HEAD\n0 @I001@ INDI\n1 NAME John\n1 SEX M\n0 TRLR\n"
    f = tmp_path / "nolast.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["anonymize", str(f)])
    assert code == 0
    name_lines = [ln for ln in out.splitlines() if "1 NAME" in ln]
    assert len(name_lines) == 1
    # No slashes — the fake individual also has no last name
    assert "/" not in name_lines[0]
    assert "John" not in name_lines[0]


def test_no_first_name_preserved(tmp_path):
    content = "0 HEAD\n0 @I001@ INDI\n1 NAME /Smith/\n1 SEX M\n0 TRLR\n"
    f = tmp_path / "nofirst.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["anonymize", str(f)])
    assert code == 0
    name_lines = [ln for ln in out.splitlines() if "1 NAME" in ln]
    assert len(name_lines) == 1
    name_val = name_lines[0].split("1 NAME ", 1)[1].strip()
    # Starts with / and has no given name before the first slash
    assert name_val.startswith("/")
    assert name_val.split("/")[0].strip() == ""
    assert "Smith" not in name_val


def test_givn_surn_consistent(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I001@ INDI\n"
        "1 NAME John /Smith/\n"
        "2 GIVN John\n"
        "2 SURN Smith\n"
        "1 SEX M\n"
        "0 @I002@ INDI\n"
        "1 NAME John /Jones/\n"
        "2 GIVN John\n"
        "2 SURN Jones\n"
        "1 SEX M\n"
        "0 TRLR\n"
    )
    f = tmp_path / "givn_surn.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["anonymize", str(f)])
    assert code == 0

    lines = out.splitlines()
    records = []
    cur: dict = {}
    for ln in lines:
        if ln.startswith("0 @I"):
            if cur:
                records.append(cur)
            cur = {}
        elif "1 NAME " in ln:
            cur["name"] = ln.split("1 NAME ", 1)[1].strip()
        elif "2 GIVN " in ln:
            cur["givn"] = ln.split("2 GIVN ", 1)[1].strip()
        elif "2 SURN " in ln:
            cur["surn"] = ln.split("2 SURN ", 1)[1].strip()
    if cur:
        records.append(cur)

    assert len(records) == 2
    for rec in records:
        assert "/" in rec["name"]
        last = rec["name"].split("/")[1].strip()
        # SURN must equal the surname component of the same person's NAME line
        assert rec["surn"] == last

    # Same original GIVN ("John") on both individuals -> same fake GIVN
    assert records[0]["givn"] == records[1]["givn"]


def test_compound_name_tokens_unique(tmp_path):
    content = "0 HEAD\n0 @I001@ INDI\n1 NAME Mary Jane /Smith Jones/\n1 SEX F\n0 TRLR\n"
    f = tmp_path / "compound.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["anonymize", str(f)])
    assert code == 0
    name_lines = [ln for ln in out.splitlines() if "1 NAME" in ln]
    assert len(name_lines) == 1
    name_val = name_lines[0].split("1 NAME ", 1)[1].strip()
    # Parse first and last components
    parts = name_val.split("/")
    first_tokens = parts[0].strip().split() if parts[0].strip() else []
    last_tokens = (
        parts[1].strip().split() if len(parts) > 1 and parts[1].strip() else []
    )
    # Token counts must match the original
    assert len(first_tokens) == 2
    assert len(last_tokens) == 2
    # All tokens within each component must be distinct
    assert len(set(first_tokens)) == 2, f"Duplicate first-name tokens: {first_tokens}"
    assert len(set(last_tokens)) == 2, f"Duplicate last-name tokens: {last_tokens}"
