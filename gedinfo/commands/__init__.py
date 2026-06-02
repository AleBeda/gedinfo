"""Command modules for gedinfo subcommands.

Expose submodules as attributes to allow direct invocation in tests
(e.g. ``from gedinfo import commands; commands.name.run(args)``).
"""

from . import name, id_, names, lastnames, ancestors, descendants, roots, leaves, stat, disjoint, living, givennames, indi, males, females, nosex, noname, relatives, anonymize, calendar, tags  # noqa: F401
