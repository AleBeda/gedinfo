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


def test_stat_simple():
    code, out, err = run_cmd(["stat", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert err == ""
    expected = [
        "Individuals: 4",
        "  Males: 2",
        "  Females: 2",
        "  Unknown sex: 0",
        "  Roots (no parents): 2",
        "  Leaves (no children): 2",
        "  No name: 0",
        "  Incomplete name: 0",
        "",
        "Families: 1",
        "  Families with unnamed/incomplete parent: 0",
        "  Families with no children: 0",
        "",
        "Disjoint forests: 1",
    ]
    assert out.strip().splitlines() == expected


def test_stat_empty():
    code, out, err = run_cmd(["stat", str(FIXTURES / "empty.ged")])
    assert code == 0
    assert err == ""
    expected = [
        "Individuals: 0",
        "  Males: 0",
        "  Females: 0",
        "  Unknown sex: 0",
        "  Roots (no parents): 0",
        "  Leaves (no children): 0",
        "  No name: 0",
        "  Incomplete name: 0",
        "",
        "Families: 0",
        "  Families with unnamed/incomplete parent: 0",
        "  Families with no children: 0",
        "",
        "Disjoint forests: 0",
    ]
    assert out.strip().splitlines() == expected


def test_stat_no_names():
    code, out, err = run_cmd(["stat", str(FIXTURES / "no_names.ged")])
    assert code == 0
    assert err == ""
    # two individuals have no name (I001, I004), two have incomplete names (I002, I003)
    expected = [
        "Individuals: 4",
        "  Males: 0",  # only I004 has SEX F, the rest default to U
        "  Females: 1",
        "  Unknown sex: 3",
        "  Roots (no parents): 4",
        "  Leaves (no children): 4",
        "  No name: 2",
        "  Incomplete name: 2",
        "",
        "Families: 0",
        "  Families with unnamed/incomplete parent: 0",
        "  Families with no children: 0",
        "",
        "Disjoint forests: 4",
    ]
    assert out.strip().splitlines() == expected


def test_stat_multi_tree():
    code, out, err = run_cmd(["stat", str(FIXTURES / "multi_tree.ged")])
    assert code == 0
    assert err == ""
    expected = [
        "Individuals: 4",
        "  Males: 3",
        "  Females: 1",
        "  Unknown sex: 0",
        "  Roots (no parents): 2",
        "  Leaves (no children): 2",
        "  No name: 0",
        "  Incomplete name: 0",
        "",
        "Families: 2",
        "  Families with unnamed/incomplete parent: 0",
        "  Families with no children: 0",
        "",
        "Disjoint forests: 2",
    ]
    assert out.strip().splitlines() == expected
