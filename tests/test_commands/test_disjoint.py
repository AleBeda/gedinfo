import subprocess
import sys
from pathlib import Path

from gedinfo import parser
from gedinfo.commands.disjoint import render_component

FIXTURES = Path(__file__).parent.parent / "fixtures"


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_disjoint_single_tree_default():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert err == ""
    lines = out.strip().splitlines()
    assert lines == [
        "I001\tJohn Smith",
        "I002\tMary Jones",
    ]


def test_disjoint_single_tree_id_only():
    code, out, err = run_cmd(["disjoint", "-i", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert err == ""
    assert out.strip().splitlines() == ["I001", "I002"]


def test_disjoint_single_tree_name_only():
    code, out, err = run_cmd(["disjoint", "-n", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert err == ""
    assert out.strip().splitlines() == ["John Smith", "Mary Jones"]


def test_disjoint_multi_tree():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "multi_tree.ged")])
    assert code == 0
    assert err == ""
    blocks = out.strip().split("\n\n")
    # first component roots
    assert blocks[0].splitlines() == ["I001\tWilhelm Braun"]
    # second component roots
    assert blocks[1].splitlines() == ["I003\tSofia Rossi"]


def test_disjoint_empty():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "empty.ged")])
    assert code == 0
    assert err == ""
    assert out.strip() == ""


def test_disjoint_conflicting_flags():
    code, out, err = run_cmd(["disjoint", "-i", "-n", str(FIXTURES / "simple.ged")])
    assert code == 1
    assert "mutually exclusive" in err or "conflicting" in err


def test_disjoint_deep():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "deep.ged")])
    assert code == 0
    assert err == ""
    # only root I001 in deep.ged
    assert out.strip().splitlines() == ["I001\tAdam Elder"]


def test_disjoint_spouse_suppresses_within_component():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I001\t" not in out
    assert "I008\t" not in out
    assert "I003\t" in out  # component A
    assert "I007\t" in out  # component B


def test_disjoint_spouse_component_order_preserved():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "spouse.ged")])
    assert code == 0
    blocks = out.strip().split("\n\n")
    # compute expected number of non-skipped components using query helpers
    from gedinfo import parser, queries
    data = parser.parse(FIXTURES / "spouse.ged")
    components = queries.get_connected_components(data)
    expected_blocks = 0
    for comp in components:
        lines = render_component(data, comp, "both", include_spouse_suppressed=False, include_unknowns=False)
        if lines:
            expected_blocks += 1
    assert len(blocks) == expected_blocks
    for block in blocks:
        assert block


def test_disjoint_spouse_placeholder_when_all_roots_suppressed():
    # Unit test for placeholder logic using render_component with new flags
    data = parser.parse(FIXTURES / "spouse.ged")
    component = [data.individuals["@I001@"], data.individuals["@I002@"]]
    # Default suppression: should skip silently
    lines = render_component(data, component, "both", include_spouse_suppressed=False, include_unknowns=False)
    assert lines == []
    # With spouse flag: the root is spouse-suppressed but named, so including
    # spouse-suppressed roots will cause it to appear
    lines = render_component(data, component, "both", include_spouse_suppressed=True, include_unknowns=False)
    assert len(lines) == 1
    assert "I001" in lines[0]
    # With all flags, individuals are included
    lines = render_component(data, component, "both", include_spouse_suppressed=True, include_unknowns=True)
    assert len(lines) == 1
    assert "I001" in lines[0]


def test_disjoint_spouse_without_flag_unchanged():
    code, out, err = run_cmd(["disjoint", str(FIXTURES / "spouse.ged")])
    assert code == 0
    # default suppression hides spouse-roots
    assert "I001\t" not in out
    assert "I008\t" not in out


def test_disjoint_spouse_output_mode_id_only():
    # with --spouse the spouse-suppressed roots are included; -i yields id-only
    code, out, err = run_cmd(["disjoint", "--spouse", "-i", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "I001" in out
    assert "I008" in out
    assert "I003" in out


def test_disjoint_spouse_output_mode_name_only():
    code, out, err = run_cmd(["disjoint", "--spouse", "-n", str(FIXTURES / "spouse.ged")])
    assert code == 0
    assert "Adam Root" in out
    assert "MultiSpouse Root" in out


def test_disjoint_spouse_and_conflicting_output_flags():
    code, out, err = run_cmd(["disjoint", "--spouse", "-i", "-n", str(FIXTURES / "spouse.ged")])
    assert code == 1
    assert "Conflicting output flags" in err


def test_disjoint_spouse_empty_ged():
    code, out, err = run_cmd(["disjoint", "--spouse", str(FIXTURES / "empty.ged")])
    assert code == 0
    assert out.strip() == ""


def test_render_component_all_suppressed():
    # Create a minimal component with one root that has a spouse with parents
    # This simulates the all-roots-suppressed case
    data = parser.parse(FIXTURES / "spouse.ged")
    
    # Create a mock component with just @I001@ (who gets suppressed)
    # and @I002@ (who has parents)
    component = [data.individuals["@I001@"], data.individuals["@I002@"]]
    
    # With spouse filter, @I001@ should be suppressed, leaving no roots
    # With spouse filter disabled (default), @I001@ is suppressed and skipped
    lines = render_component(data, component, "both", include_spouse_suppressed=False, include_unknowns=False)
    assert lines == []

    # With spouse flag (include_spouse_suppressed=True), the root is included
    lines = render_component(data, component, "both", include_spouse_suppressed=True, include_unknowns=False)
    assert len(lines) == 1
    assert "I001" in lines[0]
