# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development setup

```bash
pip install -e ".[dev]"   # installs runtime deps (faker, textual) + pytest, pytest-cov, ruff
```

Runtime dependencies (declared in `pyproject.toml`): `faker` (used by the `anonymize`
command) and `textual` (used by the `explore` TUI). `faker` is imported lazily inside
`gedinfo/commands/anonymize.py`; if it is missing the command aborts with a message
asking the user to install it (it does **not** auto-install).

## Common commands

```bash
# Run gedinfo (no installation required)
python -m gedinfo
./bin/gedinfo                        # wrapper script that sets PYTHONPATH

# Launch interactive TUI
python -m gedinfo explore [FILE]
python -m gedinfo explore INDIID FILE   # start at a specific individual

# Tests
python -m pytest                     # full suite
python -m pytest tests/test_commands/test_lastnames.py::test_lastnames_g2   # single test
python -m pytest --cov=gedinfo       # with coverage

# Lint / format (Ruff handles both)
ruff check .          # lint
ruff format .         # format (use --check in CI / pre-commit)

# Showing non-printing characters in a file
cat -etv # Equivalent to `cat -A` on Linux, which is not available on MacOS
```

## Code conventions
### Python
Python code indentation is 4 spaces.
Doc strings are indented by exactly 4 spaces.

## Architecture

Data flows in one direction: **GEDCOM file → parser → models → queries → commands → stdout**.

### Core layers

**`gedinfo/models.py`** — Three plain dataclasses: `Individual`, `Family`, `GedcomData`. `GedcomData` holds `individuals: dict[str, Individual]` and `families: dict[str, Family]`, both keyed by GEDCOM xref IDs (e.g. `@I001@`). `Individual` carries `birth_date: Optional[str]` and `death_date: Optional[str]`; `Family` carries `marriage_date: Optional[str]`.

**`gedinfo/parser.py`** — Converts a GEDCOM file into a `GedcomData`. Intentionally lightweight: it only extracts fields the domain model needs and silently ignores everything else. The main parse loop collects all lines under a level-0 `INDI` or `FAM` record and passes each one (plus its numeric `level` and a `ctx: dict` tracking the current event context) to `_populate_individual` or `_populate_family`. The `ctx["event"]` key captures the enclosing event type (e.g. `BIRT`, `MARR`) so that `DATE` sub-tags can be stored on the right model field. Raises `GedcomParseError` on invalid files.

**`gedinfo/queries.py`** — Pure functions over `GedcomData` with no side effects. Contains BFS ancestor traversal (`get_ancestor_details`, `get_ancestors`), name/ID lookup, connected-component analysis, and filtering helpers. Unit-testable without touching the CLI or parser.

**`gedinfo/commands/`** — One module per subcommand. Each module exposes exactly two public names: `register(subparsers)` and `run(args)`. `register` wires up argparse; `run` calls `parse()` and query functions, then prints results. Shared output logic for the `-i`/`-n` (ID-only / name-only) flags lives in `commands/_output.py` and is used by `roots`, `leaves`, and `disjoint`. Notable commands: `ancestors` and `descendants` traverse the family graph with optional generation limit and long/sort modes; `relatives` shows the immediate family (parents, self, spouses, children) with optional date columns; `anonymize` is architecturally distinct — it operates directly on raw GEDCOM lines (bypassing the parser/model pipeline) using a two-pass approach: pass 1 builds consistent name and location replacement mappings, pass 2 transforms the file line by line. `strip` is similarly architecturally distinct: it operates on raw GEDCOM lines in a single pass, removing lines whose tag matches a user-specified set along with all deeper-level (child) lines nested under each removed line.

**`gedinfo/config.py`** — Resolves the names of non-standard ("custom") GEDCOM tags from layered settings files: user-global `~/.config/gedinfo/settings.toml` (honoring `$XDG_CONFIG_HOME`) overridden by a per-directory `.gedinfo.toml` beside the GEDCOM file. `TagConfig` holds `living`, `secondary_name`, `alternate_name` (all `Optional[str]`, **no defaults**). `parse()` resolves and attaches a `TagConfig` to `GedcomData`. Commands that need a tag call `require_tag()`, which raises `ConfigError` (a `ValueError` subclass, so `cli.py` prints it tersely) with guidance when the tag is unconfigured. `living` and `givennames --second-name/--alt-name` abort when their tag is missing; `stat` and `anonymize` degrade gracefully.

**`gedinfo/cli.py`** — Builds the top-level argparse dispatcher, imports all command modules, calls their `register()`, dispatches to `run()`, and wraps `GedcomParseError`, `FileNotFoundError`, and `ValueError` into terse stderr messages (full tracebacks surfaced only with `--debug`).

### Key conventions

- **GEDCOM IDs** always include `@` delimiters internally (e.g. `@I001@`). `normalise_id()` in `queries.py` accepts IDs with or without delimiters. Command output strips delimiters for display.
- **Generation counting**: 1 = the queried individual (the subject), 2 = parents, 3 = grandparents, etc. `get_ancestor_details` always excludes generation 1.
- **Sex values** on `Individual`: `"M"`, `"F"`, or `"U"` (unknown/missing).
- **ID sorting** is numeric by suffix via `id_sort_key()` in `queries.py` (so `I9 < I10 < I123`).
- **Argparse exit codes**: the project exits with code 1 on user errors (not code 2). Mutually exclusive flag conflicts are validated manually rather than through argparse groups to preserve this behaviour (see `_output.py`).

### Testing patterns

Command tests in `tests/test_commands/` invoke `python -m gedinfo` via `subprocess.run` and assert on stdout/stderr/return code — they test the full pipeline end to end. Unit tests in `tests/test_parser.py` and `tests/test_queries.py` call functions directly. Test fixtures (`.ged` files) live in `tests/fixtures/`.

When adding a new command: (1) create `gedinfo/commands/<name>.py` with `register` + `run`, (2) import and register it in `gedinfo/cli.py`, (3) add it to the `__init__.py` import line in `gedinfo/commands/__init__.py`.

### Version bumps

The version string is hardcoded in four places and must be updated together:
1. `pyproject.toml` — `version = "…"`
2. `gedinfo/cli.py` — hardcoded string in the `--version` handler
3. `README.md` — `Version: …` near the top
4. `tests/test_commands/test_cli.py` — the version assertion

## Project-specific workflow

If a file `.claude/CLAUDE.local.md` exists, read it for additional project-specific workflow
instructions (commit conventions, prompt/metaprompt workflow). It is optional and
intentionally not published; this document is self-contained without it.
