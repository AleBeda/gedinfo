from pathlib import Path

import pytest

from gedinfo import parser
from gedinfo.config import TagConfig
from gedinfo.parser import GedcomParseError

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> parser.GedcomData:
    return parser.parse(FIXTURES / name)


def test_parse_simple():
    data = load("simple.ged")
    assert len(data.individuals) == 4
    assert len(data.families) == 1
    john = data.individuals.get("@I001@")
    assert john is not None
    assert john.first_name == "John"
    assert john.last_name == "Smith"
    fam = data.families.get("@F001@")
    assert fam is not None
    assert fam.husband_id == "@I001@"
    assert set(fam.child_ids) == {"@I003@", "@I004@"}


def test_parse_multi_tree():
    data = load("multi_tree.ged")
    assert len(data.individuals) == 4
    assert len(data.families) == 2
    # check that no cross-links exist
    assert data.individuals["@I001@"].family_ids_as_spouse == ["@F001@"]
    assert data.individuals["@I004@"].family_ids_as_child == ["@F002@"]


def test_parse_no_names():
    data = load("no_names.ged")
    i1 = data.individuals["@I001@"]
    assert i1.first_name is None and i1.last_name is None
    i2 = data.individuals["@I002@"]
    assert i2.first_name is None and i2.last_name == "Smith"
    i3 = data.individuals["@I003@"]
    assert i3.first_name == "Jane" and i3.last_name is None
    i4 = data.individuals["@I004@"]
    assert i4.first_name is None and i4.last_name is None


def test_parse_deep():
    data = load("deep.ged")
    assert len(data.individuals) == 4
    assert len(data.families) == 3
    assert data.individuals["@I004@"].family_ids_as_child == ["@F003@"]
    assert data.families["@F002@"].husband_id == "@I002@"


def test_parse_empty():
    data = load("empty.ged")
    assert data.individuals == {}
    assert data.families == {}


def test_parse_crlf(tmp_path):
    orig = FIXTURES / "simple.ged"
    newfile = tmp_path / "crlf.ged"
    text = orig.read_text().replace("\n", "\r\n")
    newfile.write_text(text, newline="")
    data1 = load("simple.ged")
    data2 = parser.parse(newfile)
    assert data1.individuals.keys() == data2.individuals.keys()


def test_parse_missing_file():
    with pytest.raises(GedcomParseError):
        parser.parse(FIXTURES / "nonexistent.ged")


def test_parse_no_head(tmp_path):
    bad = tmp_path / "bad.ged"
    bad.write_text("0 @I1@ INDI\n")
    with pytest.raises(GedcomParseError):
        parser.parse(bad)


def test_parse_name_no_slashes(tmp_path):
    """NAME without slashes: last token becomes surname."""
    text = "0 HEAD\n0 @I001@ INDI\n1 NAME John Smith\n0 TRLR\n"
    f = tmp_path / "noslash.ged"
    f.write_text(text)
    data = parser.parse(f)
    indi = data.individuals["@I001@"]
    assert indi.first_name == "John"
    assert indi.last_name == "Smith"


def test_parse_name_empty(tmp_path):
    """Empty NAME field results in None for first and last names."""
    text = "0 HEAD\n0 @I001@ INDI\n1 NAME \n0 TRLR\n"
    f = tmp_path / "emptyname.ged"
    f.write_text(text)
    data = parser.parse(f)
    indi = data.individuals["@I001@"]
    assert indi.first_name is None and indi.last_name is None


def test_parse_sex_unknown_value(tmp_path):
    """Sex tag with non-M/F should default to 'U'."""
    text = "0 HEAD\n0 @I001@ INDI\n1 SEX X\n0 TRLR\n"
    f = tmp_path / "sexunknown.ged"
    f.write_text(text)
    data = parser.parse(f)
    assert data.individuals["@I001@"].sex == "U"


def test_parse_malformed_line():
    """Malformed level value in a line triggers the ValueError branch."""
    from gedinfo.parser import _parse_line

    lvl, tag, val, xref = _parse_line("X THIS IS BAD")
    assert lvl == -1
    assert tag == "THIS"
    assert val == "IS BAD"


def test_parse_encoding_replace(tmp_path):
    """Non-UTF-8 bytes are replaced rather than causing an error."""
    bad = b"0 HEAD\n1 NOTE \xff\xff\xff\n0 TRLR\n"
    f = tmp_path / "bad.ged"
    f.write_bytes(bad)
    data = parser.parse(f)
    assert len(data.individuals) == 0


def test_parse_living_fixture():
    data = load("living.ged")
    assert data.individuals["@I001@"].living is True
    assert data.individuals["@I002@"].living is True
    assert data.individuals["@I003@"].living is True
    assert data.individuals["@I004@"].living is False
    assert data.individuals["@I005@"].living is False
    assert data.individuals["@I006@"].living is False
    assert data.individuals["@I007@"].living is None
    assert data.individuals["@I008@"].living is None
    assert data.individuals["@I009@"].living is True
    assert data.individuals["@I010@"].living is True
    assert data.individuals["@I011@"].living is True


def test_parse_living_default_on_existing_fixtures():
    data = load("simple.ged")
    for indi in data.individuals.values():
        assert indi.living is None


def test_parse_living_last_write_wins(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I001@ INDI\n"
        "1 NAME Test /Person/\n"
        "1 _LIVING Y\n"
        "1 _LIVING N\n"
        "0 TRLR\n"
    )
    f = tmp_path / "twice.ged"
    f.write_text(content)
    data = parser.parse(f, tag_config=TagConfig(living="_LIVING"))
    assert data.individuals["@I001@"].living is False


def test_parse_givn(tmp_path):
    f = tmp_path / "t.ged"
    f.write_text("0 HEAD\n0 @I1@ INDI\n1 NAME John /Doe/\n2 GIVN John\n0 TRLR\n")
    data = parser.parse(str(f))
    assert data.individuals["@I1@"].givn == ["John"]


def test_parse_secondary_name(tmp_path):
    f = tmp_path / "t.ged"
    f.write_text("0 HEAD\n0 @I1@ INDI\n1 NAME Moshe /X/\n1 NAM2 Raphael\n0 TRLR\n")
    data = parser.parse(str(f), tag_config=TagConfig(secondary_name="NAM2"))
    assert data.individuals["@I1@"].secondary_names == ["Raphael"]


def test_parse_alternate_name(tmp_path):
    f = tmp_path / "t.ged"
    f.write_text("0 HEAD\n0 @I1@ INDI\n1 NAME X /Y/\n1 NAMH יוחנן\n0 TRLR\n")
    data = parser.parse(str(f), tag_config=TagConfig(alternate_name="NAMH"))
    assert data.individuals["@I1@"].alternate_names == ["יוחנן"]


def test_parse_custom_tag_names(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME Jane /Doe/\n"
        "1 _ALIVE Y\n"
        "1 SNAME Janie\n"
        "1 ANAME יוחנן\n"
        "0 TRLR\n"
    )
    f = tmp_path / "custom.ged"
    f.write_text(content)
    cfg = TagConfig(living="_ALIVE", secondary_name="SNAME", alternate_name="ANAME")
    data = parser.parse(str(f), tag_config=cfg)
    indi = data.individuals["@I1@"]
    assert indi.living is True
    assert indi.secondary_names == ["Janie"]
    assert indi.alternate_names == ["יוחנן"]
