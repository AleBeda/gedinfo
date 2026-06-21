# Contributing to gedinfo

Thanks for your interest in improving `gedinfo`. This is a small, focused CLI for
querying GEDCOM genealogy files; contributions that keep it simple and well-tested
are very welcome.

## Development setup

Requires Python ≥ 3.11.

```bash
pip install -e ".[dev]"   # runtime deps + pytest, pytest-cov, ruff
pre-commit install        # optional: run lint/format on every commit
```

## Running the tool

```bash
python -m gedinfo <command> [options] <arguments>
./bin/gedinfo <command> ...        # wrapper that sets PYTHONPATH (no install needed)
```

## Tests

The test suite must pass before a change is merged:

```bash
python -m pytest          # full suite
python -m pytest --cov=gedinfo
```

Command tests live in `tests/test_commands/` and exercise the full CLI pipeline via
`subprocess`; unit tests for the parser and queries call functions directly. Add
fixtures (`.ged` files) under `tests/fixtures/`.

## Linting and formatting

[Ruff](https://docs.astral.sh/ruff/) handles both. CI runs:

```bash
ruff check .
ruff format --check .
```

To auto-fix locally: `ruff check --fix . && ruff format .`

## Adding a new command

1. Create `gedinfo/commands/<name>.py` exposing `register(subparsers)` and `run(args)`.
2. Import and register it in `gedinfo/cli.py`.
3. Add it to the import line in `gedinfo/commands/__init__.py`.
4. Document it in the README (command table + a section with a runnable example).
5. Add tests under `tests/test_commands/`.

## Pull requests

- Keep changes surgical and focused on a single concern.
- Update the README and `CHANGELOG.md` when behaviour changes.
- When bumping the version, update all four locations: `pyproject.toml`,
  `gedinfo/cli.py`, `README.md`, and `tests/test_commands/test_cli.py`.
- Use single-line commit messages unless more detail is genuinely essential.

## License

By contributing, you agree that your contributions will be licensed under the
project's [MIT License](LICENSE).
