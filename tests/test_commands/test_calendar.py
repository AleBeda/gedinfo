import datetime
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
GED = str(FIXTURES / "calendar.ged")


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _event_lines(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.strip()]


def test_all_events_present():
    code, out, _ = run_cmd(["calendar", GED])
    assert code == 0
    assert "01 Jan 1801\tbirth   \tJohn Doe" in out
    assert "02 Jan 1883\tdeath   \tJohn Doe" in out
    assert "15 Mar 1820\tbirth   \tJane Smith" in out
    assert "15 Mar 1855\tbirth   \tBob Jones" in out
    assert "03 Apr 1930\tdeath   \tBob Jones" in out
    assert "05 Jun 1825\tmarriage\tJohn Doe & Jane Smith" in out
    assert "15 Jun 1900\tbirth   \tAlice Brown" in out
    assert "20 Sep 1870\tmarriage\t(unknown) & Jane Smith" in out


def test_sort_order():
    code, out, _ = run_cmd(["calendar", "--nosep", GED])
    assert code == 0
    lines = _event_lines(out)
    dates = [ln.split("\t")[0] for ln in lines]
    assert dates == sorted(dates, key=lambda s: datetime.datetime.strptime(s, "%d %b %Y").timetuple()[1:3])


def test_same_day_sorted_by_year():
    code, out, _ = run_cmd(["calendar", "--nosep", GED])
    assert code == 0
    lines = _event_lines(out)
    mar_lines = [ln for ln in lines if "Mar" in ln]
    # 15 Mar 1820 (Jane Smith) must come before 15 Mar 1855 (Bob Jones)
    assert mar_lines.index(next(l for l in mar_lines if "Jane Smith" in l)) < \
           mar_lines.index(next(l for l in mar_lines if "Bob Jones" in l))


def test_blank_line_separator():
    code, out, _ = run_cmd(["calendar", GED])
    assert code == 0
    assert "\n\n" in out


def test_nosep():
    code, out, _ = run_cmd(["calendar", "--nosep", GED])
    assert code == 0
    assert "\n\n" not in out
    assert len(_event_lines(out)) == 8


def test_incomplete_dates_ignored():
    code, out, _ = run_cmd(["calendar", GED])
    assert code == 0
    assert "Skip" not in out


def test_missing_spouse_unknown():
    code, out, _ = run_cmd(["calendar", GED])
    assert code == 0
    assert "(unknown)" in out


def test_event_type_padding():
    code, out, _ = run_cmd(["calendar", GED])
    assert code == 0
    for line in _event_lines(out):
        fields = line.split("\t")
        assert len(fields) == 3
        assert len(fields[1]) == 8, f"Event type not 8 chars: {fields[1]!r}"


def test_dateformat():
    code, out, _ = run_cmd(["calendar", "--dateformat", "%Y-%m-%d", GED])
    assert code == 0
    assert "1801-01-01" in out
    assert "1883-01-02" in out
    assert "1930-04-03" in out


def test_output_flag(tmp_path):
    out_file = str(tmp_path / "cal.txt")
    code, stdout, _ = run_cmd(["calendar", "-o", out_file, GED])
    assert code == 0
    assert stdout == ""
    content = Path(out_file).read_text()
    assert "John Doe" in content
    assert "marriage" in content


def test_today():
    code, out, _ = run_cmd(["calendar", "--today", GED])
    assert code == 0
    today = datetime.date.today()
    today_str = today.strftime("%d %b")
    for line in _event_lines(out):
        assert line.startswith(today_str), f"Line not today's date: {line!r}"


def test_thismonth():
    code, out, _ = run_cmd(["calendar", "--thismonth", GED])
    assert code == 0
    month_str = datetime.date.today().strftime("%b")
    for line in _event_lines(out):
        assert f" {month_str} " in line, f"Line not in current month: {line!r}"


def test_month_by_full_name():
    # January events in the fixture: 01 Jan 1801 birth, 02 Jan 1883 death
    code, out, _ = run_cmd(["calendar", "--month", "January", GED])
    assert code == 0
    lines = _event_lines(out)
    assert all("Jan" in ln for ln in lines)
    assert any("John Doe" in ln and "birth" in ln for ln in lines)
    assert any("John Doe" in ln and "death" in ln for ln in lines)
    assert not any("Mar" in ln or "Apr" in ln or "Jun" in ln or "Sep" in ln for ln in lines)


def test_month_by_abbreviated_uppercase():
    code, out, _ = run_cmd(["calendar", "--month", "JAN", GED])
    assert code == 0
    lines = _event_lines(out)
    assert all("Jan" in ln for ln in lines)


def test_month_by_abbreviated_lowercase():
    code, out, _ = run_cmd(["calendar", "--month", "jan", GED])
    assert code == 0
    lines = _event_lines(out)
    assert all("Jan" in ln for ln in lines)


def test_month_by_mixed_case():
    code, out, _ = run_cmd(["calendar", "--month", "jAnUaRy", GED])
    assert code == 0
    lines = _event_lines(out)
    assert all("Jan" in ln for ln in lines)


def test_month_invalid():
    code, _, err = run_cmd(["calendar", "--month", "Foobar", GED])
    assert code == 1
    assert "foobar" in err.lower() or "unknown" in err.lower()


def test_today_thismonth_conflict():
    code, _, err = run_cmd(["calendar", "--today", "--thismonth", GED])
    assert code == 1
    assert "mutually exclusive" in err.lower()


def test_month_today_conflict():
    code, _, err = run_cmd(["calendar", "--month", "January", "--today", GED])
    assert code == 1
    assert "mutually exclusive" in err.lower()


def test_month_thismonth_conflict():
    code, _, err = run_cmd(["calendar", "--month", "January", "--thismonth", GED])
    assert code == 1
    assert "mutually exclusive" in err.lower()


def test_unknown_file():
    code, _, err = run_cmd(["calendar", "nonexistent.ged"])
    assert code == 1
    assert "nonexistent.ged" in err.lower() or "not found" in err.lower()
