import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
GED = str(FIXTURES / "relatives.ged")


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _lines(out):
    return out.rstrip("\n").splitlines()


def test_default_output():
    code, out, _ = run_cmd(["relatives", "@I001@", GED])
    assert code == 0
    labels = [ln.split("\t")[0] for ln in _lines(out) if "\t" in ln]
    assert "self:" in labels


def test_parent_labels():
    code, out, _ = run_cmd(["relatives", "@I001@", GED])
    assert code == 0
    labels = [ln.split("\t")[0] for ln in _lines(out) if "\t" in ln]
    assert "father:" in labels
    assert "mother:" in labels


def test_self_label():
    code, out, _ = run_cmd(["relatives", "@I001@", GED])
    assert code == 0
    self_lines = [ln for ln in _lines(out) if ln.startswith("self:\t")]
    assert len(self_lines) == 1
    assert "I001" in self_lines[0]


def test_spouse_label():
    code, out, _ = run_cmd(["relatives", "@I001@", GED])
    assert code == 0
    labels = [ln.split("\t")[0] for ln in _lines(out) if "\t" in ln]
    assert "wife:" in labels


def test_child_labels():
    code, out, _ = run_cmd(["relatives", "@I001@", GED])
    assert code == 0
    labels = [ln.split("\t")[0] for ln in _lines(out) if "\t" in ln]
    assert "son:" in labels
    assert "daughter:" in labels


def test_unknown_cospouse_header():
    code, out, _ = run_cmd(["relatives", "@I001@", GED])
    assert code == 0
    assert "(unknown spouse):" in out


def test_unknown_cospouse_child_label():
    code, out, _ = run_cmd(["relatives", "@I001@", GED])
    assert code == 0
    labels = [ln.split("\t")[0] for ln in _lines(out) if "\t" in ln]
    assert "child:" in labels


def test_empty_family_no_unknown_header():
    # F002 (Eve Green, no children) must NOT add an extra (unknown spouse): header
    code, out, _ = run_cmd(["relatives", "@I001@", GED])
    assert code == 0
    # Only one (unknown spouse): line — from F003
    assert out.count("(unknown spouse):") == 1


def test_long_mode():
    code, out, _ = run_cmd(["relatives", "-l", "@I001@", GED])
    assert code == 0
    data_lines = [ln for ln in _lines(out) if "\t" in ln]
    for ln in data_lines:
        parts = ln.split("\t")
        assert len(parts) == 6, f"Expected 6 columns, got {len(parts)}: {ln!r}"


def test_id_flag():
    code, out, _ = run_cmd(["relatives", "-i", "@I001@", GED])
    assert code == 0
    data_lines = [ln for ln in _lines(out) if "\t" in ln]
    for ln in data_lines:
        parts = ln.split("\t")
        assert len(parts) == 2  # label + id only
    assert any("I001" in ln for ln in data_lines)


def test_name_flag():
    code, out, _ = run_cmd(["relatives", "-n", "@I001@", GED])
    assert code == 0
    data_lines = [ln for ln in _lines(out) if "\t" in ln]
    assert any("Bob Smith" in ln for ln in data_lines)
    self_line = next(ln for ln in data_lines if ln.startswith("self:\t"))
    assert "I001" not in self_line


def test_birth_flag():
    code, out, _ = run_cmd(["relatives", "-b", "@I001@", GED])
    assert code == 0
    self_line = next(ln for ln in _lines(out) if ln.startswith("self:\t"))
    assert "3 APR 1930" in self_line


def test_death_flag():
    code, out, _ = run_cmd(["relatives", "-d", "@I001@", GED])
    assert code == 0
    father_line = next(ln for ln in _lines(out) if ln.startswith("father:\t"))
    assert "1 JAN 1970" in father_line


def test_marriage_parents():
    code, out, _ = run_cmd(["relatives", "-m", "@I001@", GED])
    assert code == 0
    lines = _lines(out)
    father_line = next(ln for ln in lines if ln.startswith("father:\t"))
    mother_line = next(ln for ln in lines if ln.startswith("mother:\t"))
    assert "15 JUN 1925" in father_line
    assert "15 JUN 1925" in mother_line


def test_marriage_spouse():
    code, out, _ = run_cmd(["relatives", "-m", "@I001@", GED])
    assert code == 0
    wife_line = next(ln for ln in _lines(out) if ln.startswith("wife:\t"))
    assert "10 OCT 1955" in wife_line


def test_marriage_self_blank():
    code, out, _ = run_cmd(["relatives", "-m", "@I001@", GED])
    assert code == 0
    self_line = next(ln for ln in _lines(out) if ln.startswith("self:\t"))
    assert self_line.split("\t")[-1] == ""


def test_marriage_child_blank():
    code, out, _ = run_cmd(["relatives", "-m", "@I001@", GED])
    assert code == 0
    child_lines = [
        ln for ln in _lines(out) if ln.split("\t")[0] in ("son:", "daughter:", "child:")
    ]
    for ln in child_lines:
        assert ln.split("\t")[-1] == ""


def test_parent_unknown_sex(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME Child /One/\n1 SEX M\n1 FAMC @F1@\n"
        "0 @I2@ INDI\n1 NAME Parent /Two/\n1 SEX U\n1 FAMS @F1@\n"
        "0 @F1@ FAM\n1 HUSB @I2@\n1 CHIL @I1@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "u.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["relatives", "@I1@", str(f)])
    assert code == 0
    labels = [ln.split("\t")[0] for ln in out.strip().splitlines() if "\t" in ln]
    assert "parent:" in labels


def test_child_unknown_sex(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n1 NAME Subject /One/\n1 SEX M\n1 FAMS @F1@\n"
        "0 @I2@ INDI\n1 NAME Spouse /Two/\n1 SEX F\n1 FAMS @F1@\n"
        "0 @I3@ INDI\n1 NAME Kid /One/\n1 SEX U\n1 FAMC @F1@\n"
        "0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n1 CHIL @I3@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "u2.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["relatives", "@I1@", str(f)])
    assert code == 0
    labels = [ln.split("\t")[0] for ln in out.strip().splitlines() if "\t" in ln]
    assert "child:" in labels


def test_unknown_id():
    code, _, err = run_cmd(["relatives", "@I999@", GED])
    assert code == 1
    assert "Unknown individual ID" in err
