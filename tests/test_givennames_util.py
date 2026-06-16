from gedinfo.commands.givennames import _split_field


def test_split_spaces():
    assert _split_field("John David") == ["John", "David"]


def test_split_commas():
    assert _split_field("John, David") == ["John", "David"]


def test_split_slashes():
    assert _split_field("John/David") == ["John", "David"]


def test_composite_dash():
    assert _split_field("John-David") == ["John-David"]


def test_blank_returns_empty():
    assert _split_field("   ") == []


def test_empty_returns_empty():
    assert _split_field("") == []
