# gedinfo

A command-line utility for querying GEDCOM genealogy files.

Version: 0.4.2

Installation
------------

Installation is optional. You can run `gedinfo` directly from the repository using `./bin/gedinfo`.

To install the package (for convenience or development):

**Editable/dev mode** (recommended for development):
```bash
pip install -e ".[dev]"
```

**Standard installation**:
```bash
pip install .
```

Running
-------

You can run `gedinfo` in several ways:

- **Without installation**: Use the wrapper script directly: `./bin/gedinfo` or add `bin` to your PATH
- **After installation**: Once installed via pip, the `gedinfo` command is available on your PATH
- **As a module**: Invoke it directly with `python -m gedinfo`

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
- `-s, --spouse`: Include roots whose spouse has parents with at least one known name. By default such individuals are suppressed because they likely married into a documented family rather than representing an independent lineage starting point.
- `-u, --unknowns`: Include roots with no name at all (no NAME tag in the GEDCOM file). By default, nameless individuals are suppressed.
- `-a, --all`: Include all roots without any suppression. Equivalent to combining `--spouse` and `--unknowns`. Cannot be combined with `--spouse` or `--unknowns`.
- (default): Print ID and name pairs in the format `ID	Name`

### living

List individuals with a `_LIVING` flag.

**Syntax:**
```
gedinfo living [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-v, --invert`: Invert the match and list individuals who are not
  explicitly marked as living (includes those with `_LIVING` set to N/no/false,
  those with an empty `_LIVING` value, and those with no `_LIVING` tag).

**Output:**
Prints one line per matching individual using the same output modes as other
commands (use `-i`/`-n`/output options where available).

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
- `-s, --spouse`: As per the roots command: include roots whose spouse has parents with at least one known name. When this flag is passed and suppression removes all roots from a connected component, that component is shown with a single placeholder line "(roots suppressed)" instead of individual entries.
- `-u, --unknowns`: Include nameless roots (no NAME tag). By default nameless individuals are suppressed.
- `-a, --all`: Include all roots without suppression. Cannot be combined with `--spouse` or `--unknowns`.
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

### givennames

Print a frequency count of given names found among relatives in the chosen direction
(ancestors or descendants). Results are grouped into three sections — Masculine names,
Feminine names, Unknown sex — and empty sections are omitted. Within each section, names
are sorted descending by count, then ascending alphabetically.

**Syntax:**
```
gedinfo givennames [options] <indi_id> <gedcom_file>
```

**Arguments:**
- `<indi_id>`: The GEDCOM individual ID (with or without @ delimiters, e.g., I001 or @I001@)
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-g N, --generations N`: Limit traversal to N generations (N ≥ 1). Generation 1 is the
  subject, generation 2 is parents/children, generation 3 is grandparents/grandchildren, etc.
  If not specified, traverses all generations.
- `-s, --second`: Also include names from the `NAM2` GEDCOM field (second/additional names).
- `-e, --hebrew`: Also include names from the `NAMH` GEDCOM field (Hebrew names).
- `-a, --all_names`: Equivalent to `--second --hebrew`.
- `-f, --fuzzy`: Group name variants together using the bundled variants file
  (`gedinfo/data/name_variants.txt`). When multiple variants of the same name appear, they
  are counted and reported on one line with individual variant counts in parentheses.
- `-d DIRECTION, --direction DIRECTION`: Traversal direction: `asc` for ancestors, `desc` for
  descendants (default: `desc`).

**Output:**
Prints output lines in the format `<count>\t<name>`, grouped under section headers.
All names are lowercase.

Without `--fuzzy`:
```
Masculine names:
3	moshe
2	abraham

Feminine names:
4	sarah
1	miriam
```

With `--fuzzy` (when variants are grouped):
```
Masculine names:
3	abraham  (abraham: 2, abram: 1)
```
Names with no known variants print without the parenthetical.

**Name variants file:**
The bundled variants file at `gedinfo/data/name_variants.txt` contains Sephardic/Ashkenazic
Jewish name equivalences and can be edited directly. Each non-comment line is one equivalence
group of space-separated variants. Lines starting with or containing `#` are comments.

**Examples:**

```bash
# Descendants (default): given-name counts for all descendants of I001
$ gedinfo givennames I001 tests/fixtures/simple.ged

# Ancestors: given-name counts for all ancestors of I001
$ gedinfo givennames --direction asc I001 tests/fixtures/simple.ged
Masculine names:
2	john
1	james

Feminine names:
3	mary
1	anne

# Fuzzy grouping with secondary names, ancestors only
$ gedinfo givennames --direction asc -f -s I001 tests/fixtures/simple.ged
Masculine names:
3	john  (john: 2, yohanan: 1)
1	james
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
