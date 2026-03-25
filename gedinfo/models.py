"""Domain model dataclasses for GEDCOM data.

This module defines simple `Individual`, `Family`, and `GedcomData`
classes used throughout the project.  All classes are plain dataclasses
with appropriate default factories to avoid shared mutable state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class Individual:
    """Representation of a GEDCOM individual record.

    Attributes:
        id: GEDCOM cross-reference ID, e.g. "@I001@".
        first_name: Given name part of the NAME tag or ``None``.
        last_name: Surname part of the NAME tag or ``None``.
        sex: One of ``"M"``, ``"F"`` or ``"U"`` (unknown).
        family_ids_as_child: List of family IDs where the individual is a child.
        family_ids_as_spouse: List of family IDs where the individual is a spouse.
    """

    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    sex: Literal["M", "F", "U"] = "U"
    family_ids_as_child: list[str] = field(default_factory=list)
    family_ids_as_spouse: list[str] = field(default_factory=list)
    living: bool | None = None

    """
    living: bool | None

    Indicates the parsed value of a custom `_LIVING` tag on the INDI record.

    - `True`  : `_LIVING` tag present with a truthy value (y, yes, true, 1)
    - `False` : `_LIVING` tag present with a non-empty, non-truthy value
    - `None`  : `_LIVING` tag absent or present with an empty/whitespace value
    """


@dataclass
class Family:
    """Representation of a GEDCOM family record.

    Attributes:
        id: GEDCOM cross-reference ID, e.g. "@F001@".
        husband_id: ID of the husband individual or ``None``.
        wife_id: ID of the wife individual or ``None``.
        child_ids: List of children individual IDs.
    """

    id: str
    husband_id: Optional[str] = None
    wife_id: Optional[str] = None
    child_ids: list[str] = field(default_factory=list)


@dataclass
class GedcomData:
    """Container holding all parsed GEDCOM individuals and families.

    Attributes:
        individuals: Mapping from ID to ``Individual``.
        families: Mapping from ID to ``Family``.
    """

    individuals: dict[str, Individual] = field(default_factory=dict)
    families: dict[str, Family] = field(default_factory=dict)
