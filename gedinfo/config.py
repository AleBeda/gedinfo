"""Runtime configuration for customizable (non-standard) GEDCOM tag names.

Tag names have NO built-in defaults. They are resolved by layering two
optional settings files (lowest to highest precedence):

  1. user-global   ~/.config/gedinfo/settings.toml   (or $XDG_CONFIG_HOME)
  2. per-directory  .gedinfo.toml  beside the GEDCOM file

Each layer may override individual keys. A key left unconfigured stays None;
commands that need it raise ConfigError via require_tag().
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .errors import UserError

# Generic function keys recognised in the [gedcom_custom_tags] settings table.
_VALID_KEYS: frozenset[str] = frozenset(
    {
        "living",
        "secondary_name",
        "alternate_name",
    }
)

# Example tag values, shown only in error messages and documentation.
_EXAMPLE_TAGS: dict[str, str] = {
    "living": "_LIVING",
    "secondary_name": "NAM2",
    "alternate_name": "NAMH",
}


@dataclass(frozen=True)
class TagConfig:
    """Resolved custom GEDCOM tag names. ``None`` means unconfigured."""

    living: Optional[str] = None
    secondary_name: Optional[str] = None
    alternate_name: Optional[str] = None


class ConfigError(UserError):
    """Raised for invalid settings files or when a needed tag is unconfigured."""


def user_settings_path() -> Path:
    """Return the path to the user-global settings file.

    Honors ``$XDG_CONFIG_HOME`` (read at call time), falling back to
    ``~/.config``.
    """
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "gedinfo" / "settings.toml"


def _read_section(path: Path) -> dict[str, str]:
    """Return the ``[gedcom_custom_tags]`` table from ``path``.

    Only valid keys are kept; values are coerced to ``str``. Returns an empty
    dict when the file is absent. Raises ``ConfigError`` on malformed TOML.
    """
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"Invalid settings file {path}: {exc}")
    section = data.get("gedcom_custom_tags", {})
    if not isinstance(section, dict):
        return {}
    return {k: str(v) for k, v in section.items() if k in _VALID_KEYS}


def load_tag_config(gedcom_path: str | Path | None = None) -> TagConfig:
    """Resolve the custom tag configuration by layering the settings files.

    Built-in (empty) < user-global < per-directory ``.gedinfo.toml`` beside the
    GEDCOM file. Later layers override individual keys. Configured values are
    uppercased (the parser compares tags uppercased); absent keys stay ``None``.
    """
    mapping: dict[str, str] = {}
    mapping.update(_read_section(user_settings_path()))
    if gedcom_path is not None:
        dir_file = Path(gedcom_path).resolve().parent / ".gedinfo.toml"
        mapping.update(_read_section(dir_file))

    return TagConfig(
        living=mapping["living"].upper() if "living" in mapping else None,
        secondary_name=(
            mapping["secondary_name"].upper() if "secondary_name" in mapping else None
        ),
        alternate_name=(
            mapping["alternate_name"].upper() if "alternate_name" in mapping else None
        ),
    )


def require_tag(cfg: TagConfig, key: str) -> str:
    """Return the configured tag for ``key`` or raise an actionable error.

    Raises ``ConfigError`` (with guidance on which settings file to edit and
    what to write) when the tag is unconfigured.
    """
    value = getattr(cfg, key)
    if value:
        return value
    example = _EXAMPLE_TAGS[key]
    raise ConfigError(
        f'No GEDCOM tag is configured for "{key}".\n\n'
        "This command needs to know which tag in your GEDCOM file corresponds "
        f'to "{key}". Declare it in one of these files (the per-directory file '
        "takes precedence):\n\n"
        "  ./.gedinfo.toml                          "
        "(applies to GEDCOM files in this directory)\n"
        f"  {user_settings_path()}   "
        "(applies to all your GEDCOM files)\n\n"
        "Add:\n\n"
        "  [gedcom_custom_tags]\n"
        f'  {key} = "{example}"   # replace with the tag your file actually uses'
    )
