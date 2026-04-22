"""Command modules for gedinfo subcommands.

Expose submodules as attributes to allow direct invocation in tests
(e.g. ``from gedinfo import commands; commands.name.run(args)``).
"""

from . import name, id_, names, ancestors, roots, leaves, stat, disjoint, living, givennames  # noqa: F401
