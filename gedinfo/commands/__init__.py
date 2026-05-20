"""Command modules for gedinfo subcommands.

Expose submodules as attributes to allow direct invocation in tests
(e.g. ``from gedinfo import commands; commands.name.run(args)``).
"""

from . import name, id_, names, lastnames, roots, leaves, stat, disjoint, living, givennames, indi, males, females, nosex  # noqa: F401
