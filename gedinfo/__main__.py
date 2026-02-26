"""Module entry-point to allow ``python -m gedinfo`` execution."""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
