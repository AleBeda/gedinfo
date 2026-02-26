# gedinfo

A command-line utility for querying GEDCOM genealogy files.

Installation
------------

Install the package (editable/dev mode for development):

```bash
pip install -e ".[dev]"
```

Or install the package into the active environment:

```bash
pip install .
```

Running
-------

The package exposes a `gedinfo` console script. You can also run it via
`python -m gedinfo` when developing. Examples:

```bash
gedinfo name @I001@ tests/fixtures/simple.ged
gedinfo id "John Smith" tests/fixtures/simple.ged
gedinfo names ids.txt tests/fixtures/simple.ged
gedinfo ancestors -g 3 @I004@ tests/fixtures/deep.ged
```

Testing
-------

Run the test suite using `pytest` from the project root:

```bash
pytest -q
```

Formatting & linting
--------------------

Development dependencies include `ruff` and `black`. To check formatting and
linting run:

```bash
ruff check gedinfo/ tests/
black --check gedinfo/ tests/
```

Project status
--------------

Implemented so far:

- Project skeleton, packaging and tests
- Domain model (`gedinfo/models.py`)
- GEDCOM parser (`gedinfo/parser.py`) and parsing tests
- Query utilities (`gedinfo/queries.py`) and tests
- CLI skeleton (`gedinfo/cli.py`) and basic commands: `name`, `id`, `names`
- `ancestors`, `roots`, and `leaves` commands (implemented)

Next steps: continue implementing remaining commands (`stat`, `disjoint`) and polishing tests and coverage.
