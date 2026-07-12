from gedinfo.dates import GedcomDate, parse_gedcom_date, sort_key

# (raw, expected GedcomDate or None)
CASES = [
    (None, None),
    ("", None),
    ("   ", None),
    ("5 MAY 1950", GedcomDate(raw="5 MAY 1950", year=1950, month=5, day=5)),
    ("MAY 1950", GedcomDate(raw="MAY 1950", year=1950, month=5)),
    ("1950", GedcomDate(raw="1950", year=1950)),
    ("850", GedcomDate(raw="850", year=850)),
    ("ABT 1850", GedcomDate(raw="ABT 1850", qualifier="ABT", year=1850)),
    ("EST 1850", GedcomDate(raw="EST 1850", qualifier="EST", year=1850)),
    ("CAL 1850", GedcomDate(raw="CAL 1850", qualifier="CAL", year=1850)),
    (
        "BEF 12 MAR 1850",
        GedcomDate(raw="BEF 12 MAR 1850", qualifier="BEF", year=1850, month=3, day=12),
    ),
    ("AFT 1900", GedcomDate(raw="AFT 1900", qualifier="AFT", year=1900)),
    (
        "BET 1900 AND 1910",
        GedcomDate(raw="BET 1900 AND 1910", qualifier="BET", year=1900, year2=1910),
    ),
    (
        "FROM 1900 TO 1910",
        GedcomDate(raw="FROM 1900 TO 1910", qualifier="FROM", year=1900, year2=1910),
    ),
    ("FROM 1900", GedcomDate(raw="FROM 1900", qualifier="FROM", year=1900)),
    ("TO 1910", GedcomDate(raw="TO 1910", qualifier="TO", year=1910)),
    (
        "INT 1750 (approx)",
        GedcomDate(raw="INT 1750 (approx)", qualifier="INT", year=1750),
    ),
    ("garbage text", GedcomDate(raw="garbage text")),
    ("before the war", GedcomDate(raw="before the war")),
    # 2-digit day
    ("25 DEC 1888", GedcomDate(raw="25 DEC 1888", year=1888, month=12, day=25)),
    # lowercase input
    ("abt 1850", GedcomDate(raw="abt 1850", qualifier="ABT", year=1850)),
    # extra internal whitespace
    (
        "5   MAY   1950",
        GedcomDate(raw="5   MAY   1950", year=1950, month=5, day=5),
    ),
    # invalid month name
    ("5 FOO 1950", GedcomDate(raw="5 FOO 1950")),
    # day without a month is not valid GEDCOM grammar
    ("5 1950", GedcomDate(raw="5 1950")),
    # out of scope: dual years, calendar escapes, non-English months
    ("1732/33", GedcomDate(raw="1732/33")),
    ("@#DHEBREW@ 5 TSH 5750", GedcomDate(raw="@#DHEBREW@ 5 TSH 5750")),
]


def test_parse_gedcom_date_table():
    for raw, expected in CASES:
        assert parse_gedcom_date(raw) == expected, f"failed for {raw!r}"


def test_parse_never_raises_on_arbitrary_input():
    for raw in ["", " ", "()", "BET", "FROM", "TO", "INT", "1", "AND", "@#!@#"]:
        parse_gedcom_date(raw)  # must not raise


def test_sort_key_year_only_before_year_month():
    year_only = parse_gedcom_date("1950")
    year_month = parse_gedcom_date("MAY 1950")
    assert sort_key(year_only) < sort_key(year_month)


def test_sort_key_year_month_before_year_month_day():
    year_month = parse_gedcom_date("MAY 1950")
    full = parse_gedcom_date("5 MAY 1950")
    assert sort_key(year_month) < sort_key(full)


def test_sort_key_year_only_before_year_month_day():
    year_only = parse_gedcom_date("1950")
    full = parse_gedcom_date("5 MAY 1950")
    assert sort_key(year_only) < sort_key(full)


def test_sort_key_unparseable_sorts_last():
    dates = [
        parse_gedcom_date("5 MAY 1950"),
        parse_gedcom_date("1950"),
        parse_gedcom_date("garbage"),
    ]
    ordered = sorted(dates, key=sort_key)
    assert ordered[-1].raw == "garbage"


def test_sort_key_range_uses_first_endpoint():
    earlier = parse_gedcom_date("BET 1900 AND 1950")
    later = parse_gedcom_date("BET 1905 AND 1910")
    assert sort_key(earlier) < sort_key(later)
