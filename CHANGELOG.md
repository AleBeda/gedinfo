# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.24.0]
### Added
- `gedinfo/dates.py`: structured GEDCOM date parsing (`parse_gedcom_date` →
  `GedcomDate`) covering qualifiers (`ABT`, `EST`, `CAL`, `BEF`, `AFT`) and
  ranges (`BET … AND …`, `FROM … TO …`). Never raises; unparseable text is
  preserved verbatim.
- `gedinfo/lines.py`: shared lexical layer for raw GEDCOM lines, now used by
  the parser and the raw-line commands (`anonymize`, `strip`).
- `gedinfo/reports.py`: shared aggregate computations (`collect_stats`) so the
  CLI `stat` command and the TUI statistics screen show identical numbers.
- `gedinfo/errors.py`: `UserError` taxonomy for user-facing error messages.
- Design-invariants section in `CLAUDE.md` and `tests/test_conventions.py`
  enforcing them (cycle-safe traversals, single-home helpers, no bare
  `ValueError`, single-sourced version string).

### Fixed
- Parser no longer misattributes a source citation's `DATE` (e.g. `3 DATE`
  under `2 SOUR` inside `BIRT`) as the birth/death/marriage date, and no
  longer lets nested identity tags (`NAME`, `SEX`, `FAMC`, `FAMS`, `GIVN`)
  clobber individual records from deeper levels.
- `get_ancestors` (used by `lastnames`) no longer hangs on files containing
  parent cycles and no longer degrades exponentially under pedigree collapse.
- `relationship` completes on heavily endogamous trees: path enumeration is
  breadth-first and capped at the 1000 shortest lineages, with a note printed
  to stderr when the cap is hit.
- `anonymize` now maps `GIVN`/`SURN` values through the same pass-1 mappings
  as `NAME`, so a person's fake given name and surname are consistent across
  tags (and respect the individual's sex). Same-seed output differs from
  previous releases as a result.

### Changed
- `calendar` now lists anniversaries for qualified full dates (e.g.
  `ABT 12 MAR 1850`); partial dates are still skipped.
- The TUI statistics screen applies the same root-suppression filters as
  `gedinfo stat` and gains a Living line; its given-names screen shows
  per-sex frequency counts like the CLI command.
- Genuine programming errors now surface as tracebacks instead of terse
  one-line messages; user-facing errors are unchanged (message, exit code 1).
- The version string is single-sourced from `gedinfo.__version__`
  (`pyproject.toml` reads it dynamically).

## [0.23.0]
### Added
- `strip` command removing GEDCOM lines matching specified tag(s), along with
  their lower-ranking (child) lines. Warns on stderr when stripping a tag that
  can damage GEDCOM structure (`INDI`, `FAM`, `FAMS`, `FAMC`, `HUSB`, `WIFE`,
  `CHIL`, `NAME`, `GIVN`, `SURN`, `HEAD`, `TRLR`).

### Fixed
- `strip` and `anonymize` now preserve the input file's original line-ending
  style (CRLF or LF) in their output instead of always normalizing to LF.
  Previously, processing a CRLF-encoded GEDCOM file made every output line
  differ from the input byte-for-byte, so tools like `diff` reported the
  entire file as replaced instead of showing the actual changes.

### Changed
- `tags` output gains a fourth column: a one-line summary of each standard
  GEDCOM 5.5.1 tag, sourced from the specification's Appendix A. Empty for
  non-standard tags. The tag data file moved from `gedcom551_tags.txt` to
  `gedcom551_tags.tsv` (tag + summary) as the single source of truth for the
  standard-tag set.

## [0.22.0]
### Added
- `License` section in the README and a License section pointing at `LICENSE`.
- CI, license, and Python-version badges in the README.
- `[build-system]` table and richer package metadata (authors, license, URLs,
  classifiers, keywords) in `pyproject.toml`.
- README documentation for the `fam` command.

### Fixed
- `fam --sort name` no longer crashes (tuple/list concatenation in
  `family_name_key`).

### Changed
- `anonymize` no longer auto-installs `faker`; it now aborts with a clear message
  if the dependency is missing.
- Reorganized the README command reference into purpose-based groups.
- Privatized the LLM workflow artifacts: `prompts/` and `metaprompts/` moved under
  the untracked `.claude/` directory, and `CLAUDE.md` split into a public architecture
  document plus a private `.claude/CLAUDE.local.md` workflow companion. Project history
  was rewritten to remove these private files ahead of the first public release.

## [0.21.0]
### Added
- Configurable custom GEDCOM tags (no built-in defaults) via layered
  `settings.toml` / `.gedinfo.toml` files.

## [0.20.0]
### Added
- `relationship` command showing common-ancestor lineage paths between two
  individuals.

## [0.19.0]
### Added
- `gen` command counting ancestor and descendant generations for an individual.

## [0.18.0]
### Added
- `explore` command and spouse family information in the TUI.

## [0.17.0]
### Added
- Interactive terminal UI (TUI) mode.

## [0.16.1]
### Added
- Generation-depth count in the `stat` command.

## [0.16.0]
### Added
- `diff` command comparing two GEDCOM files.

## [0.15.0]
### Added
- `tags` command listing GEDCOM tags with occurrence counts and a non-standard flag.

## [0.14.0]
### Added
- `noname` command and CLI consistency improvements across commands.

## [0.13.0]
### Added
- `calendar` command listing birth, death, and marriage anniversaries.

## [0.12.0]
### Added
- `anonymize` command producing a privacy-safe derivative with fake names and
  locations (deterministic; seedable).

## [0.11.0]
### Added
- `relatives` command showing an individual's immediate family.

## [0.10.0]
### Added
- `ancestors` and `descendants` commands with generation limits and long/sort modes.

## [0.8.0]
### Added
- `indi`, `males`, `females`, and `nosex` listing commands.

## [0.5.0]
### Added
- `givennames` command with frequency counts, fuzzy variant grouping, and
  direction control.

## [0.4.0]
### Added
- `_LIVING` support and the `living` command.

## [0.3.0]
### Added
- Unknown/suppression rework with `-s`/`-u`/`-a` flags across listing commands.
