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

Once installed, the `gedinfo` command is available on your PATH. During
development you can either invoke the module directly or use the provided
wrapper script at `bin/gedinfo` (make sure `bin` is on your PATH or call it
with `./bin/gedinfo`).

```
gedinfo [--version] [--debug] <command> [options] <arguments>
```

**Global options**

- `--version`  Print the package version and exit
- `--debug`    Show a full Python traceback on error instead of a terse
               message

**Commands**

- `name <indi_id> <gedcom_file>`
- `id <name> <gedcom_file>`
- `names <ids_file> <gedcom_file>`
- `ancestors [-g N] <indi_id> <gedcom_file>`
- `roots [-i|-n] <gedcom_file>`
- `leaves [-i|-n] <gedcom_file>`
- `stat <gedcom_file>`
- `disjoint [-i|-n] <gedcom_file>`

Examples:

```bash
# using the wrapper script
./bin/gedinfo name @I001@ tests/fixtures/simple.ged
./bin/gedinfo id "John Smith" tests/fixtures/simple.ged
./bin/gedinfo names ids.txt tests/fixtures/simple.ged
./bin/gedinfo ancestors -g 3 @I004@ tests/fixtures/deep.ged
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
- `ancestors`, `roots`, `leaves`, and `stat` commands (implemented)

Next steps: continue implementing remaining commands (`disjoint`) and polishing tests and coverage.
