"""End-to-end tests for configurable custom GEDCOM tags (abort vs graceful)."""

import os
import subprocess
import sys


def run_cmd(args, cwd_config_dir):
    """Run gedinfo with XDG_CONFIG_HOME pointed at an empty dir (no user-global)."""
    env = {**os.environ, "XDG_CONFIG_HOME": str(cwd_config_dir)}
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


_GED = (
    "0 HEAD\n"
    "0 @I001@ INDI\n"
    "1 NAME Jane /Doe/\n"
    "1 SEX F\n"
    "1 _LIVING Y\n"
    "0 TRLR\n"
)


def _setup(tmp_path):
    """Create a GEDCOM file and an empty config dir; return (ged_path, empty_dir)."""
    ged = tmp_path / "tree.ged"
    ged.write_text(_GED, encoding="utf-8")
    empty = tmp_path / "empty_config"
    empty.mkdir()
    return ged, empty


def test_living_aborts_without_config(tmp_path):
    ged, empty = _setup(tmp_path)
    code, out, err = run_cmd(["living", str(ged)], empty)
    assert code == 1
    assert "living" in err
    assert "[gedcom_custom_tags]" in err
    assert ".gedinfo.toml" in err


def test_living_works_with_config(tmp_path):
    ged, empty = _setup(tmp_path)
    (tmp_path / ".gedinfo.toml").write_text(
        '[gedcom_custom_tags]\nliving = "_LIVING"\n', encoding="utf-8"
    )
    code, out, err = run_cmd(["living", str(ged)], empty)
    assert code == 0
    assert "Jane" in out


def test_givennames_second_aborts_without_config(tmp_path):
    ged, empty = _setup(tmp_path)
    code, out, err = run_cmd(
        ["givennames", "--second-name", "@I001@", str(ged)], empty
    )
    assert code == 1
    assert "secondary_name" in err


def test_givennames_plain_works_without_config(tmp_path):
    ged, empty = _setup(tmp_path)
    code, out, err = run_cmd(["givennames", "@I001@", str(ged)], empty)
    assert code == 0


def test_stat_graceful_without_config(tmp_path):
    ged, empty = _setup(tmp_path)
    code, out, err = run_cmd(["stat", str(ged)], empty)
    assert code == 0
    assert "Living: (no living tag configured)" in out


def test_anonymize_strips_living_without_config(tmp_path):
    ged, empty = _setup(tmp_path)
    code, out, err = run_cmd(["anonymize", str(ged)], empty)
    assert code == 0
    assert "_LIVING" not in out


def test_anonymize_keeps_living_with_config(tmp_path):
    ged, empty = _setup(tmp_path)
    (tmp_path / ".gedinfo.toml").write_text(
        '[gedcom_custom_tags]\nliving = "_LIVING"\n', encoding="utf-8"
    )
    code, out, err = run_cmd(["anonymize", str(ged)], empty)
    assert code == 0
    assert "_LIVING" in out
