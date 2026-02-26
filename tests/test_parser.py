import os
from pathlib import Path

import pytest

from gedinfo import parser
from gedinfo.parser import GedcomParseError
from gedinfo.models import Individual, Family

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
