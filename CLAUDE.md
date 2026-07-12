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

**`gedinfo/commands/`** — One module per subcommand. Each module exposes exactly two public names: `register(subparsers)` and `run(args)`. `register` wires up argparse; `run` calls `parse()` and query functions, then prints results. Shared output logic for the `-i`/`-n` (ID-only / name-only) flags lives in `commands/_output.py` and is used by `roots`, `leaves`, and `disjoint`. Notable commands: `ancestors` and `descendants` traverse the family graph with optional generation limit and long/sort modes; `relatives` shows the immediate family (parents, self, spouses, children) with optional date columns; `anonymize` is architecturally distinct — it operates directly on raw GEDCOM lines (bypassing the parser/model pipeline) using a two-pass approach: pass 1 builds consistent name and location replacement mappings, pass 2 transforms the file line by line. **Consistency contract:** every value pass 2 replaces must flow through the pass-1 maps so identical inputs map to identical fakes within a run; fresh generation in pass 2 is only a fallback for values pass 1 could not have seen. `strip` is similarly architecturally distinct: it operates on raw GEDCOM lines in a single pass, removing lines whose tag matches a user-specified set along with all deeper-level (child) lines nested under each removed line. Both raw-line commands share the lexical helpers in `lines.py`.

**`gedinfo/config.py`** — Resolves the names of non-standard ("custom") GEDCOM tags from layered settings files: user-global `~/.config/gedinfo/settings.toml` (honoring `$XDG_CONFIG_HOME`) overridden by a per-directory `.gedinfo.toml` beside the GEDCOM file. `TagConfig` holds `living`, `secondary_name`, `alternate_name` (all `Optional[str]`, **no defaults**). `parse()` resolves and attaches a `TagConfig` to `GedcomData`. Commands that need a tag call `require_tag()`, which raises `ConfigError` (a `ValueError` subclass, so `cli.py` prints it tersely) with guidance when the tag is unconfigured. `living` and `givennames --second-name/--alt-name` abort when their tag is missing; `stat` and `anonymize` degrade gracefully.

**`gedinfo/cli.py`** — Builds the top-level argparse dispatcher, registers every module named in `_COMMAND_MODULES` (list order = help output order), dispatches to `run()`, and wraps `UserError` and `FileNotFoundError` into terse stderr messages (full tracebacks surfaced only with `--debug`). A stray bare `ValueError` deliberately escapes as a traceback — that is how programming bugs stay visible.

**`gedinfo/errors.py`** — `UserError(ValueError)`, the base for every error whose message is meant for end users (`GedcomParseError` and `ConfigError` subclass it). Raise `UserError` for user-facing failures; never `raise ValueError` directly inside `gedinfo/` (`tests/test_conventions.py` enforces this).

**`gedinfo/lines.py`** — The shared lexical layer for raw GEDCOM lines: `split_line`, `detect_line_ending`, `read_raw_lines`. The parser and the raw-line commands (`anonymize`, `strip`) all use it. Never re-implement line splitting or line-ending detection — the project once had three drifting copies.

**`gedinfo/dates.py`** — Structured GEDCOM date parsing: `parse_gedcom_date` → `GedcomDate`, plus `sort_key`. Handles qualifiers (`ABT`, `EST`, `CAL`, `BEF`, `AFT`) and ranges (`BET … AND …`, `FROM … TO …`); it never raises — unparseable text yields a raw-only `GedcomDate`. Model date fields stay raw strings; consumers parse lazily. Never regex a GEDCOM date inside a command.

**`gedinfo/reports.py`** — Pure aggregate computations shared by the CLI and the TUI (e.g. `collect_stats`). If the CLI and the TUI both display a number, it must come from a single function here or in `queries.py` — the two front ends once drifted apart by computing "the same" statistics twice.

### Key conventions

- **GEDCOM IDs** always include `@` delimiters internally (e.g. `@I001@`). `normalise_id()` in `queries.py` accepts IDs with or without delimiters. Command output strips delimiters for display.
- **Generation counting**: 1 = the queried individual (the subject), 2 = parents, 3 = grandparents, etc. `get_ancestor_details` always excludes generation 1.
- **Sex values** on `Individual`: `"M"`, `"F"`, or `"U"` (unknown/missing).
- **ID sorting** is numeric by suffix via `id_sort_key()` in `queries.py` (so `I9 < I10 < I123`).
- **Argparse exit codes**: the project exits with code 1 on user errors (not code 2). Mutually exclusive flag conflicts are validated manually rather than through argparse groups to preserve this behaviour (see `_output.py`).

### Design invariants

Hard rules from the July 2026 architectural review (`.claude/FABLE_REPORT.md`). Each one exists because its violation was a real bug in this codebase; the fixes are pinned by tests. Check proposed changes against this list before implementing.

1. **Every family-graph traversal must be cycle-safe and bounded.** Use a `visited` set (or per-path sets plus a path cap when all distinct paths are needed — see `find_relationships`). Real GEDCOM files contain cousin marriages (exponential path counts) and occasionally corrupt parent cycles (infinite loops). Exercise any new traversal against `tests/fixtures/cycle.ged` and `tests/fixtures/endogamy.ged` and add it to the termination battery in `tests/test_conventions.py`.
2. **Parser tags are level-guarded.** Identity tags (`NAME`, `SEX`, `FAMC`, `FAMS`, custom tags) match at level 1 only; an event's `DATE` matches only directly beneath the event (a `3 DATE` inside a `2 SOUR` citation under `BIRT` is *not* the birth date). When teaching the parser a new tag, decide and guard the level(s) at which it is valid — never match a tag at any depth.
3. **One home per concern.** Raw line handling → `lines.py`; GEDCOM date parsing → `dates.py`; shared graph/model computations → `queries.py`; shared aggregates → `reports.py`; user-facing errors → `errors.py`. Before writing a helper, grep these modules for an existing one.
4. **Command output is a contract.** The command tests pin exact stdout/stderr/exit codes; a refactor must be byte-identical, and an output change must itself be the feature (stated in the plan, asserted in tests).
5. **`tests/test_conventions.py` mechanically enforces the greppable subset of these rules.** When you adopt a new invariant, extend that file — documentation alone does not survive contact with future sessions.

Command tests in `tests/test_commands/` invoke `python -m gedinfo` via `subprocess.run` and assert on stdout/stderr/return code — they test the full pipeline end to end. Unit tests in `tests/test_parser.py` and `tests/test_queries.py` call functions directly. Test fixtures (`.ged` files) live in `tests/fixtures/`.

When adding a new command: (1) create `gedinfo/commands/<name>.py` with `register` + `run`, (2) add the module name to `_COMMAND_MODULES` in `gedinfo/cli.py`, (3) add it to the `__init__.py` import line in `gedinfo/commands/__init__.py`. Any computation the TUI (or another command) might reuse belongs in `gedinfo/queries.py` (model objects) or `gedinfo/reports.py` (formatted aggregates), not inside `run()` — `run()` should only parse args, call those functions, and print.

### Version bumps

The version string lives in exactly two places and must be updated together:
1. `gedinfo/__init__.py` — `__version__`
2. `README.md` — `Version: …` near the top

## Project-specific workflow

If a file `.claude/CLAUDE.local.md` exists, read it for additional project-specific workflow
instructions (commit conventions, prompt/metaprompt workflow). It is optional and
intentionally not published; this document is self-contained without it.
