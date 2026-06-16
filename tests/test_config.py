import pytest

from gedinfo.config import (
    ConfigError,
    TagConfig,
    load_tag_config,
    require_tag,
    user_settings_path,
)


def _write_user_settings(tmp_path, monkeypatch, body: str):
    """Point XDG_CONFIG_HOME at tmp_path and write a user-global settings file."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_dir = tmp_path / "gedinfo"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "settings.toml").write_text(body, encoding="utf-8")


def test_no_files_returns_all_none(tmp_path, monkeypatch):
    # Empty XDG dir → no user-global file, no per-directory file.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = load_tag_config(None)
    assert cfg == TagConfig(None, None, None)


def test_user_global_override(tmp_path, monkeypatch):
    _write_user_settings(
        tmp_path, monkeypatch, '[gedcom_custom_tags]\nliving = "_ALIVE"\n'
    )
    cfg = load_tag_config(None)
    assert cfg.living == "_ALIVE"
    assert cfg.secondary_name is None
    assert cfg.alternate_name is None


def test_per_directory_override(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
    work = tmp_path / "work"
    work.mkdir()
    (work / ".gedinfo.toml").write_text(
        '[gedcom_custom_tags]\nsecondary_name = "SNAME"\n', encoding="utf-8"
    )
    cfg = load_tag_config(work / "tree.ged")
    assert cfg.secondary_name == "SNAME"


def test_per_directory_beats_global(tmp_path, monkeypatch):
    # Global sets living and alternate_name; per-dir overrides living only.
    _write_user_settings(
        tmp_path,
        monkeypatch,
        '[gedcom_custom_tags]\nliving = "_GLOBAL"\nalternate_name = "ANAME"\n',
    )
    work = tmp_path / "work"
    work.mkdir()
    (work / ".gedinfo.toml").write_text(
        '[gedcom_custom_tags]\nliving = "_LOCAL"\n', encoding="utf-8"
    )
    cfg = load_tag_config(work / "tree.ged")
    assert cfg.living == "_LOCAL"          # per-dir wins
    assert cfg.alternate_name == "ANAME"   # global-only key still applies


def test_value_is_uppercased(tmp_path, monkeypatch):
    _write_user_settings(
        tmp_path, monkeypatch, '[gedcom_custom_tags]\nliving = "_alive"\n'
    )
    assert load_tag_config(None).living == "_ALIVE"


def test_unknown_keys_ignored(tmp_path, monkeypatch):
    _write_user_settings(
        tmp_path,
        monkeypatch,
        '[gedcom_custom_tags]\nbogus = "X"\nliving = "_LIVING"\n',
    )
    cfg = load_tag_config(None)
    assert cfg.living == "_LIVING"
    assert not hasattr(cfg, "bogus")


def test_malformed_toml_raises_config_error(tmp_path, monkeypatch):
    _write_user_settings(tmp_path, monkeypatch, "this is not = valid = toml")
    with pytest.raises(ConfigError):
        load_tag_config(None)


def test_config_error_is_value_error():
    assert issubclass(ConfigError, ValueError)


def test_require_tag_returns_value():
    cfg = TagConfig(living="_LIVING")
    assert require_tag(cfg, "living") == "_LIVING"


def test_require_tag_raises_with_guidance(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = TagConfig()
    with pytest.raises(ConfigError) as exc:
        require_tag(cfg, "living")
    msg = str(exc.value)
    assert "living" in msg
    assert "[gedcom_custom_tags]" in msg
    assert ".gedinfo.toml" in msg
    assert str(user_settings_path()) in msg
