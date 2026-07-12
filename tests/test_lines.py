import pytest

from gedinfo.lines import detect_line_ending, read_raw_lines, split_line


# --- split_line -------------------------------------------------------------


def test_split_line_level0_xref():
    assert split_line("0 @I001@ INDI") == (0, "INDI", "", "@I001@")


def test_split_line_level0_xref_with_value():
    # A level-0 xref record carrying a value after the tag.
    assert split_line("0 @N1@ NOTE Some text") == (0, "NOTE", "Some text", "@N1@")


def test_split_line_tag_and_value():
    assert split_line("1 NAME John /Smith/") == (1, "NAME", "John /Smith/", None)


def test_split_line_tag_only():
    assert split_line("1 BIRT") == (1, "BIRT", "", None)


def test_split_line_malformed_level():
    assert split_line("banana NAME John") == (-1, "", "", None)


def test_split_line_empty_string():
    assert split_line("") == (-1, "", "", None)


# --- detect_line_ending -----------------------------------------------------


def test_detect_line_ending_crlf():
    assert detect_line_ending(["0 HEAD\r\n", "0 TRLR\r\n"]) == "\r\n"


def test_detect_line_ending_cr():
    assert detect_line_ending(["0 HEAD\r", "0 TRLR\r"]) == "\r"


def test_detect_line_ending_lf():
    assert detect_line_ending(["0 HEAD\n", "0 TRLR\n"]) == "\n"


def test_detect_line_ending_no_terminator():
    assert detect_line_ending(["0 HEAD"]) == "\n"


# --- read_raw_lines ---------------------------------------------------------


def test_read_raw_lines_missing_file(tmp_path):
    missing = tmp_path / "nope.ged"
    with pytest.raises(FileNotFoundError, match=f"File not found: {missing}"):
        read_raw_lines(missing)


def test_read_raw_lines_strips_bom(tmp_path):
    f = tmp_path / "bom.ged"
    f.write_bytes(b"\xef\xbb\xbf0 HEAD\n0 TRLR\n")
    lines, _ = read_raw_lines(f)
    assert lines[0] == "0 HEAD"


def test_read_raw_lines_crlf(tmp_path):
    f = tmp_path / "crlf.ged"
    f.write_bytes(b"0 HEAD\r\n0 TRLR\r\n")
    lines, ending = read_raw_lines(f)
    assert ending == "\r\n"
    assert lines == ["0 HEAD", "0 TRLR"]
