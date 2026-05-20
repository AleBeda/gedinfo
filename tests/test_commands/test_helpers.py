import argparse
from types import SimpleNamespace

import pytest

from gedinfo.commands import lastnames
from gedinfo.commands import _output
from gedinfo.models import Individual


def test_lastnames_register_parsing():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    lastnames.register(subparsers)
    ns = parser.parse_args(["lastnames", "@I001@", "foo.ged"])
    assert hasattr(ns, "indi_id")
    assert hasattr(ns, "gedcom_file")
    assert hasattr(ns, "generations")
    assert hasattr(ns, "long")
    assert hasattr(ns, "sort")


def test_validate_output_mode_conflict(capsys):
    args = SimpleNamespace(id=True, name=True)
    with pytest.raises(SystemExit) as exc:
        _output.validate_output_mode(args)
    assert exc.value.code == 1


def test_validate_output_mode_values():
    assert _output.validate_output_mode(SimpleNamespace(id=True, name=False)) == "id"
    assert _output.validate_output_mode(SimpleNamespace(id=False, name=True)) == "name"
    assert _output.validate_output_mode(SimpleNamespace(id=False, name=False)) == "both"


def test_strip_and_format_individual():
    ind = Individual(id="@I123@", first_name="A", last_name="B")
    assert _output.strip_id_delimiters(ind.id) == "I123"
    assert _output.format_individual(ind, "id") == "I123"
    assert _output.format_individual(ind, "name") == "A B"
    assert _output.format_individual(ind, "both") == "I123\tA B"
