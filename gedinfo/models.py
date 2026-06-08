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
        living: Parsed value of ``_LIVING`` tag; ``True``, ``False``, or ``None``.
        givn: Values of all ``GIVN`` sub-tags (additional given-name fields).
        nam2: Values of all ``NAM2`` tags (second/additional name fields).
        namh: Values of all ``NAMH`` tags (Hebrew name fields).
        birth_date: Value of the ``DATE`` sub-tag under ``BIRT``, or ``None``.
        death_date: Value of the ``DATE`` sub-tag under ``DEAT``, or ``None``.
    """

    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    sex: Literal["M", "F", "U"] = "U"
    family_ids_as_child: list[str] = field(default_factory=list)
    family_ids_as_spouse: list[str] = field(default_factory=list)
    living: bool | None = None
    givn: list[str] = field(default_factory=list)   # values of all GIVN sub-tags
    nam2: list[str] = field(default_factory=list)   # values of all NAM2 tags
    namh: list[str] = field(default_factory=list)   # values of all NAMH tags
    birth_date: Optional[str] = None
    death_date: Optional[str] = None
    notes: list[str] = field(default_factory=list)


@dataclass
class Family:
    """Representation of a GEDCOM family record.

    Attributes:
        id: GEDCOM cross-reference ID, e.g. "@F001@".
        husband_id: ID of the husband individual or ``None``.
        wife_id: ID of the wife individual or ``None``.
        child_ids: List of children individual IDs.
        marriage_date: Value of the ``DATE`` sub-tag under ``MARR``, or ``None``.
    """

    id: str
    husband_id: Optional[str] = None
    wife_id: Optional[str] = None
    child_ids: list[str] = field(default_factory=list)
    marriage_date: Optional[str] = None
    notes: list[str] = field(default_factory=list)


@dataclass
class GedcomData:
    """Container holding all parsed GEDCOM individuals and families.

    Attributes:
        individuals: Mapping from ID to ``Individual``.
        families: Mapping from ID to ``Family``.
    """

    individuals: dict[str, Individual] = field(default_factory=dict)
    families: dict[str, Family] = field(default_factory=dict)
