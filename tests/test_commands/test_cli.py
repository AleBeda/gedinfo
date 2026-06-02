import sys
from pathlib import Path

import pytest

from gedinfo import cli

FIXTURES = Path(__file__).parent.parent / "fixtures"


def run_main(monkeypatch, capsys, args):
    # simulate command line invocation and capture exit codes
    monkeypatch.setattr(sys, "argv", ["gedinfo"] + args)
    try:
        cli.main()
        code = 0
    except SystemExit as exc:
        code = exc.code
    out, err = capsys.readouterr()
    return code, out, err


def test_cli_version(monkeypatch, capsys):
    # include a dummy sub-command so argparse doesn't complain about missing command
    code, out, err = run_main(
        monkeypatch,
        capsys,
        ["--version", "name", "@I001@", str(FIXTURES / "simple.ged")],
    )
    assert code == 0
    assert "gedinfo 0.15.0" in out
    # ensure subcommand isn't executed when version flag is present
    assert "John Smith" not in out


def test_cli_name(monkeypatch, capsys):
    code, out, err = run_main(
        monkeypatch, capsys, ["name", "@I001@", str(FIXTURES / "simple.ged")]
    )
    assert code == 0
    assert "John Smith" in out


def test_cli_stat(monkeypatch, capsys):
    code, out, err = run_main(
        monkeypatch, capsys, ["stat", str(FIXTURES / "simple.ged")]
    )
    assert code == 0
    assert "Individuals:" in out


def test_cli_invalid(monkeypatch, capsys):
    # trigger error path without debug
    code, out, err = run_main(
        monkeypatch, capsys, ["name", "@I999@", "nonexistent.ged"]
    )
    assert code == 1
    assert "file not found" in err.lower()


def test_cli_debug_flag(monkeypatch, capsys):
    # with debug the underlying exception should propagate instead of being
    # caught and formatted
    with pytest.raises(Exception):
        run_main(monkeypatch, capsys, ["--debug", "name", "@I999@", "nonexistent.ged"])


def test_direct_command_runs(tmp_path):
    # exercise each command's run() directly to bump coverage
    from types import SimpleNamespace
    from gedinfo import commands

    gedfile = str(FIXTURES / "simple.ged")
    # name
    args = SimpleNamespace(indi_id="@I001@", gedcom_file=gedfile)
    commands.name.run(args)
    # id
    args = SimpleNamespace(name="John Smith", gedcom_file=gedfile)
    commands.id_.run(args)
    # names: create ids file
    ids_f = tmp_path / "ids.txt"
    ids_f.write_text("@I001@\n@I003@\n")
    args = SimpleNamespace(ids_file=str(ids_f), gedcom_file=gedfile)
    commands.names.run(args)
    # lastnames
    args = SimpleNamespace(indi_id="@I004@", gedcom_file=gedfile, generations=None)
    commands.lastnames.run(args)
    # roots/leaves/stat/disjoint with default flags
    for mod in (commands.roots, commands.leaves, commands.stat, commands.disjoint):
        # prepare args object
        if mod is commands.stat:
            args = SimpleNamespace(gedcom_file=gedfile)
        else:
            args = SimpleNamespace(gedcom_file=gedfile, id=False, name=False)
        mod.run(args)
      # indi/males/females/nosex with default flags
    for mod in (commands.indi, commands.males, commands.females, commands.nosex):
        args = SimpleNamespace(gedcom_file=gedfile, id=False, name=False)
        mod.run(args)
