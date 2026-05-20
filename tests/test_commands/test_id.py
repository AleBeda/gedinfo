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


def test_id_single_match():
    code, out, err = run_cmd(["id", "Robert", str(FIXTURES / "refinements.ged")])
    assert code == 0
    assert out == "I005\tRobert Smith\n"


def test_id_multiple_matches_last_name():
    code, out, err = run_cmd(["id", "smith", str(FIXTURES / "refinements.ged")])
    assert code == 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 3
    assert lines == [
        "I001\tJohn Smith",
        "I002\tMary Smithson",
        "I005\tRobert Smith",
    ]


def test_id_first_name_partial():
    code, out, err = run_cmd(["id", "ali", str(FIXTURES / "refinements.ged")])
    assert code == 0
    assert out == "I004\tAlice Brown\n"


def test_id_no_match():
    code, out, err = run_cmd(["id", "xyz", str(FIXTURES / "refinements.ged")])
    assert code == 0
    assert out == ""


def test_id_nameless_not_returned():
    code, out, err = run_cmd(["id", "smith", str(FIXTURES / "refinements.ged")])
    assert "I006" not in out


def test_id_slash_syntax():
    code1, out1, err1 = run_cmd(["id", "/Smith/", str(FIXTURES / "refinements.ged")])
    code2, out2, err2 = run_cmd(["id", "Smith", str(FIXTURES / "refinements.ged")])
    assert code1 == 0 and code2 == 0
    assert out1 == out2


def test_id_case_insensitive():
    code1, out1, err1 = run_cmd(["id", "SMITH", str(FIXTURES / "refinements.ged")])
    code2, out2, err2 = run_cmd(["id", "smith", str(FIXTURES / "refinements.ged")])
    assert out1 == out2


def test_id_missing_file():
    code, out, err = run_cmd(["id", "John", str(FIXTURES / "nonexistent.ged")])
    assert code == 1
    assert err.strip() != ""


def test_id_tab_separator():
    code, out, err = run_cmd(["id", "Robert", str(FIXTURES / "refinements.ged")])
    assert code == 0
    line = out.strip()
    parts = line.split("\t")
    assert len(parts) == 2
    assert parts[0] == "I005"
    assert parts[1].strip() == "Robert Smith"


def test_id_first_then_last():
    # "Robert Smith" → tokens ["robert", "smith"] → only Robert Smith matches
    code, out, err = run_cmd(["id", "Robert Smith", str(FIXTURES / "refinements.ged")])
    assert code == 0
    assert out == "I005\tRobert Smith\n"


def test_id_last_then_first():
    # reversed order gives identical results
    code, out, err = run_cmd(["id", "Smith Robert", str(FIXTURES / "refinements.ged")])
    assert code == 0
    assert out == "I005\tRobert Smith\n"


def test_id_comma_separated():
    # comma treated as separator; "Smith, Robert" == "Robert Smith"
    code, out, err = run_cmd(["id", "Smith, Robert", str(FIXTURES / "refinements.ged")])
    assert code == 0
    assert out == "I005\tRobert Smith\n"


def test_id_multiword_narrows_results():
    # "smith" alone returns 3 results; adding "robert" narrows to 1
    _, out_single, _ = run_cmd(["id", "smith", str(FIXTURES / "refinements.ged")])
    _, out_multi, _ = run_cmd(["id", "smith robert", str(FIXTURES / "refinements.ged")])
    assert len(out_single.strip().splitlines()) == 3
    assert len(out_multi.strip().splitlines()) == 1


def test_id_composite_name(tmp_path):
    # composite first name and last name: all parts must match
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME Jean Paul /von Meyer/\n"
        "0 @I2@ INDI\n"
        "1 NAME Jean /Smith/\n"
        "0 TRLR\n"
    )
    f = tmp_path / "composite.ged"
    f.write_text(content)
    # all four tokens must match → only I1 qualifies
    code, out, _ = run_cmd(["id", "Jean Paul von Meyer", str(f)])
    assert code == 0
    assert "I1" in out and "I2" not in out


def test_id_composite_reversed(tmp_path):
    # reversed token order gives the same result
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME Jean Paul /von Meyer/\n"
        "0 @I2@ INDI\n"
        "1 NAME Jean /Smith/\n"
        "0 TRLR\n"
    )
    f = tmp_path / "composite.ged"
    f.write_text(content)
    code, out, _ = run_cmd(["id", "von Meyer, Jean Paul", str(f)])
    assert code == 0
    assert "I1" in out and "I2" not in out
