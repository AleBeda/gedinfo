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

Commands
--------

### name

Print the full name of an individual by their ID.

**Syntax:**
```
gedinfo name <indi_id> <gedcom_file>
```

**Arguments:**
- `<indi_id>`: The GEDCOM individual ID (with @ delimiters, e.g., I001)
- `<gedcom_file>`: Path to the GEDCOM file

**Output:**
Prints the name in the format: `First /Surname/`

**Example:**
```bash
$ gedinfo name I001 tests/fixtures/simple.ged
John /Smith/
```

### id

Search for individuals by partial name match.

**Syntax:**
```
gedinfo id <name> <gedcom_file>
```

**Arguments:**
- `<name>`: Name fragment to search for. Matched as a case-insensitive substring
  against first name and last name independently. Slash delimiters (//) around
  surnames are accepted and ignored.
- `<gedcom_file>`: Path to the GEDCOM file

**Output:**
Prints one line per matching individual in the format:
```
@I001@\tDisplay Name
```
(the ID includes `@` delimiters, followed by a tab and the display name).
Results are sorted by ID.

**Example:**
```bash
$ gedinfo id Smith tests/fixtures/refinements.ged
@I001@\tJohn Smith
@I002@\tMary Smithson
```
### names

Print the distinct last names of individuals whose IDs are listed in a file.

**Syntax:**
```
gedinfo names <ids_file> <gedcom_file>
```

**Arguments:**
- `<ids_file>`: Path to a file containing individual IDs (one per line, with @ delimiters)
- `<gedcom_file>`: Path to the GEDCOM file

**Output:**
Prints the distinct last names, one per line, in alphabetical order.

**Example:**
```bash
$ cat ids.txt
I001
I002
I004

$ gedinfo names ids.txt tests/fixtures/simple.ged
Johnson
Smith
```

### ancestors

Print the ancestors of an individual. Supports two output modes: short (names only) 
and long (detailed paths). In long mode, ancestors from each lineage branch are 
sorted from purely paternal lines (ppp) to purely maternal lines (mmm).

**Syntax:**
```
gedinfo ancestors [options] <indi_id> <gedcom_file>
```

**Arguments:**
- `<indi_id>`: The GEDCOM individual ID (with @ delimiters)
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-g N, --generations N`: Limit traversal to N generations (N ≥ 1). Generation 1 is the subject, 
  generation 2 is parents, generation 3 is grandparents, etc. If not specified, traverses all 
  generations.
- `-l, --long`: Enable long output mode. Shows detailed ancestor information including generation, 
  path (relationship notation), last name, and ID.
- `-s MODE, --sort MODE`: Sort the output by one of: `generation`, `path`, `name`, or `id`. 
  This option is only valid with `-l`. Default sort order depends on mode:
  - Long mode (`-l`): sorts by `path` (paternal to maternal)
  - Short mode: sorts by `name` (alphabetically)
- `-u, --unknown`: Include ancestors with no name (no NAME tag in the GEDCOM file).
  By default, nameless ancestors are suppressed. In short mode this flag has no visible effect
  (nameless ancestors have no last name to print). In `--long` mode, nameless ancestors 
  appear with '(unknown)' in the last-name field.

**Output (Short Mode - default):**
Prints the distinct last names of all ancestors, one per line, sorted alphabetically.
Nameless ancestors are always excluded (they have no last name to print).

**Output (Long Mode - with `-l`):**
Tab-separated values with four columns:
- Generation number (2 for parents, 3 for grandparents, etc.)
- Path (lowercase string of p/m/? characters, see below)
- Last name (or "(unknown)" if no surname and `-u` is set)
- Individual ID (without @ delimiters)

When the last name is fewer than 8 characters, an extra tab is added to align 
the ID column. By default, nameless ancestors are omitted from long-mode output;
use `-u/--unknown` to include them.

**Path Notation:**
The path string indicates the sex of each ancestor in the lineage:
- `p` — paternal (male parent)
- `m` — maternal (female parent)
- `?` — unknown or unspecified sex

For example, `pp` means paternal grandfather, `pm` means paternal grandmother, 
`mp` means maternal grandfather, `mm` means maternal grandmother.

**Branch-Tip Filtering:**
In long mode, only the most remote reachable ancestor in each lineage branch is 
shown. Intermediate ancestors are omitted. With `-g N`, ancestors at generation N 
and all roots encountered before that limit are printed.

**Examples:**

```bash
# Short mode: all ancestor surnames, alphabetical order
$ gedinfo ancestors I001 tests/fixtures/long_ancestors.ged
Bauer
Muller
Novak
Svensson
Weber

# Long mode: paternal to maternal sorting (default)
$ gedinfo ancestors -l I001 tests/fixtures/long_ancestors.ged
4       ppp     Novak           I008
4       pp?     Svensson        I009
3       pm      Bauer           I005
3       mp      Muller          I006
3       mm      Weber           I007

# Long mode: limit to 3 generations
$ gedinfo ancestors -l -g 3 I001 tests/fixtures/long_ancestors.ged
3       pp      Novak           I004
3       pm      Bauer           I005
3       mp      Muller          I006
3       mm      Weber           I007

# Long mode: sort by generation
$ gedinfo ancestors -l -s generation I001 tests/fixtures/long_ancestors.ged
3       pm      Bauer           I005
3       mp      Muller          I006
3       mm      Weber           I007
4       ppp     Novak           I008
4       pp?     Svensson        I009

# Long mode: sort by last name
$ gedinfo ancestors -l -s name I001 tests/fixtures/long_ancestors.ged
3       pm      Bauer           I005
3       mp      Muller          I006
4       ppp     Novak           I008
4       pp?     Svensson        I009
3       mm      Weber           I007
```

### roots

Print the root individuals (those with no recorded parents) in the GEDCOM file.

**Syntax:**
```
gedinfo roots [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-i`: Print IDs only (without @ delimiters), one per line
- `-n`: Print names only, one per line
- `-s, --spouse`: Suppress roots whose spouse has at least one recorded parent in the GEDCOM file. Useful for filtering out individuals who married into the tree and whose own parentage is simply unrecorded, rather than being true independent lineage starting points.
- (default): Print ID and name pairs in the format `ID	Name`

**Output:**
Root individuals sorted by ID.

**Examples:**

```bash
# IDs and names (default)
$ gedinfo roots tests/fixtures/simple.ged
I001	John /Smith/
I003	Jane /Johnson/

# IDs only
$ gedinfo roots -i tests/fixtures/simple.ged
I001
I003

# Names only
$ gedinfo roots -n tests/fixtures/simple.ged
John /Smith/
Jane /Johnson/
```

### leaves

Print the leaf individuals (those with no recorded children) in the GEDCOM file.

**Syntax:**
```
gedinfo leaves [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-i`: Print IDs only (without @ delimiters), one per line
- `-n`: Print names only, one per line
- (default): Print ID and name pairs in the format `ID	Name`

**Output:**
Leaf individuals sorted by ID.

**Examples:**

```bash
# IDs and names (default)
$ gedinfo leaves tests/fixtures/simple.ged
I002	Alice /Smith/
I005	Bob /Johnson/

# IDs only
$ gedinfo leaves -i tests/fixtures/simple.ged
I002
I005

# Names only
$ gedinfo leaves -n tests/fixtures/simple.ged
Alice /Smith/
Bob /Johnson/
```

### stat

Print statistics about the GEDCOM file, including:
- Number of individuals
- Number of families
- Number of roots (individuals with no parents)
- Number of leaves (individuals with no children)

**Syntax:**
```
gedinfo stat <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Output:**
Human-readable statistics summary.

**Example:**

```bash
$ gedinfo stat tests/fixtures/simple.ged
individuals: 5
families: 2
roots: 2
leaves: 3
```

### disjoint

Print the sizes of all connected components (disjoint family groups) in the GEDCOM file.

**Syntax:**
```
gedinfo disjoint [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-i`: Print IDs from each component (without @ delimiters), grouped by component
- `-n`: Print names from each component, grouped by component
- `-s, --spouse`: As per the roots command: suppress roots whose spouse has at least one recorded parent. If this suppression removes all roots from a connected component, that component is shown with a single placeholder line "(roots suppressed)" instead of individual entries.
- (default): Print the size of each component, one per line

**Output:**
The sizes of disjoint components, one per line. If `-i` or `-n` is specified, 
individuals are grouped by their component with a blank line between groups.

**Examples:**

```bash
# Component sizes (default)
$ gedinfo disjoint tests/fixtures/simple.ged
5
2

# IDs by component
$ gedinfo disjoint -i tests/fixtures/simple.ged
I001
I002
I003
I004

I005
I006

# Names by component
$ gedinfo disjoint -n tests/fixtures/simple.ged
John /Smith/
Alice /Smith/
Jane /Johnson/
Bob /Johnson/

Charlie /Brown/
Diana /Brown/
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

Project is now feature-complete with all commands (`name`, `id`, `names`, `ancestors`, `roots`, `leaves`, `stat`, `disjoint`) implemented and tested.  Final polishing included edge-case tests, coverage audit (now >95%), linting, formatting, and packaging checks.
