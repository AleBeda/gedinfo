# gedinfo

A command-line utility for querying GEDCOM genealogy files.

Version: 0.16.1

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

| Command | Description |
|---------|-------------|
| [name](#name) | Print the full name of an individual by ID |
| [id](#id) | Search for individuals by partial name match |
| [names](#names) | Print distinct last names for a list of individual IDs |
| [ancestors](#ancestors) | List all ancestors of an individual |
| [descendants](#descendants) | List all descendants of an individual |
| [lastnames](#lastnames) | Print distinct ancestor surnames with lineage paths |
| [roots](#roots) | List root individuals (those with no recorded parents) |
| [living](#living) | List individuals with a `_LIVING` flag |
| [leaves](#leaves) | List leaf individuals (those with no recorded children) |
| [indi](#indi) | List all individuals in the file |
| [males](#males) | List all male individuals |
| [females](#females) | List all female individuals |
| [nosex](#nosex) | List individuals with unknown or unspecified sex |
| [noname](#noname) | List individuals with no name recorded |
| [stat](#stat) | Print file statistics (individual count, family count, roots, leaves) |
| [disjoint](#disjoint) | List the sizes of connected family components |
| [givennames](#givennames) | Frequency count of given names among ancestors or descendants |
| [relatives](#relatives) | Show the immediate family of an individual (parents, spouses, children) |
| [anonymize](#anonymize) | Output a privacy-safe derivative with fake names and locations |
| [calendar](#calendar) | List birth, death, and marriage anniversaries from a GEDCOM file |
| [tags](#tags) | List all GEDCOM tags found in a file with occurrence counts |
| [diff](#diff) | Compare two GEDCOM files |

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

Print the distinct last names of individuals whose IDs are listed in a file (or from stdin).

**Syntax:**
```
gedinfo names <ids_file> <gedcom_file>
```

**Arguments:**
- `<ids_file>`: Path to a file containing individual IDs (one per line, with @ delimiters), or `-` to read from stdin
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

List all ancestors of an individual, including the individual themselves (generation 1).

**Syntax:**
```
gedinfo ancestors [options] <indi_id> <gedcom_file>
```

**Arguments:**
- `<indi_id>`: The GEDCOM individual ID (with or without @ delimiters)
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-g N, --generations N`: Limit traversal to N generations (N ≥ 1). Generation 1 is the subject, generation 2 is parents, etc.
- `-l, --long`: Enable long output mode (generation, path, last name, ID). Cannot be combined with `-i` or `-n`.
- `-s MODE, --sort MODE`: Sort order for `--long` mode. Choices: `generation`, `path`, `name`, `id`. Default: `generation`. Requires `--long`.
- `-u, --unknown`: Include ancestors with no name in `--long` mode. By default, nameless ancestors are excluded from long-mode output.
- `-i`: Print IDs only (without @ delimiters), one per line (short mode only).
- `-n`: Print names only, one per line (short mode only).

**Output (short mode — default):**
One line per ancestor in BFS traversal order (subject first, then parents, grandparents, etc.).
Each line: `ID\tFull Name`. Use `-i` or `-n` for ID-only or name-only output.

**Output (long mode — with `-l`):**
Tab-separated values: generation, path, full name (first name then last name, or `(unknown)` if nameless and `-u` is set), ID.
The path uses `p` (father), `m` (mother), `?` (unknown sex) to describe the relationship chain from the subject.
When `-s name` is used, sorting is by last name (primary) then first name (secondary).

**Examples:**

```bash
# Short mode: all ancestors from I001
$ gedinfo ancestors I001 tests/fixtures/long_ancestors.ged
I001	Jan Novak
I002	Pieter Novak
I003	Anna Muller
I004	Hans Novak
I005	Greta Bauer
I006	Ernst Muller
I007	Lena Weber
I008	Otto Novak
I009	Unknown Svensson

# Long mode: all ancestors
$ gedinfo ancestors -l I001 tests/fixtures/long_ancestors.ged
1		Jan Novak	I001
2	p	Pieter Novak	I002
2	m	Anna Muller	I003
3	pp	Hans Novak	I004
3	pm	Greta Bauer	I005
3	mp	Ernst Muller	I006
3	mm	Lena Weber	I007
4	ppp	Otto Novak	I008
4	pp?	Unknown Svensson	I009

# Long mode: limit to 2 generations, sort by path
$ gedinfo ancestors -l -g 2 -s path I001 tests/fixtures/long_ancestors.ged
1		Jan Novak	I001
2	p	Pieter Novak	I002
2	m	Anna Muller	I003
```

### descendants

List all descendants of an individual, including the individual themselves (generation 1).

**Syntax:**
```
gedinfo descendants [options] <indi_id> <gedcom_file>
```

**Arguments:**
- `<indi_id>`: The GEDCOM individual ID (with or without @ delimiters)
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-g N, --generations N`: Limit traversal to N generations (N ≥ 1). Generation 1 is the subject, generation 2 is children, etc.
- `-l, --long`: Enable long output mode (generation, path, last name, ID). Cannot be combined with `-i` or `-n`.
- `-s MODE, --sort MODE`: Sort order for `--long` mode. Choices: `generation`, `path`, `name`, `id`. Default: `generation`. Requires `--long`.
- `-u, --unknown`: Include descendants with no name in `--long` mode. By default, nameless descendants are excluded from long-mode output.
- `-i`: Print IDs only (without @ delimiters), one per line (short mode only).
- `-n`: Print names only, one per line (short mode only).

**Output (short mode — default):**
One line per descendant in BFS traversal order (subject first, then children, grandchildren, etc.).
Each line: `ID\tFull Name`. Use `-i` or `-n` for ID-only or name-only output.

**Output (long mode — with `-l`):**
Tab-separated values: generation, path, full name (first name then last name, or `(unknown)` if nameless and `-u` is set), ID.
The path uses `s` (son/male), `d` (daughter/female), `?` (unknown sex) to describe the relationship chain from the subject.
When `-s name` is used, sorting is by last name (primary) then first name (secondary).

**Examples:**

```bash
# Short mode: all descendants from I001
$ gedinfo descendants I001 tests/fixtures/descendants.ged
I001	John Smith
I003	Peter Smith
I004	Anna Smith
I006	Tom Smith
I007	Sue Smith

# Long mode: all descendants, sorted by path
$ gedinfo descendants -l -s path I001 tests/fixtures/descendants.ged
1		John Smith	I001
2	s	Peter Smith	I003
3	ss	Tom Smith	I006
3	sd	Sue Smith	I007
2	d	Anna Smith	I004

# Long mode: limit to 2 generations
$ gedinfo descendants -l -g 2 I001 tests/fixtures/descendants.ged
1		John Smith	I001
2	s	Peter Smith	I003
2	d	Anna Smith	I004
```

### lastnames

Print the ancestors of an individual. Supports two output modes: short (names only) 
and long (detailed paths). In long mode, ancestors from each lineage branch are 
sorted from purely paternal lines (ppp) to purely maternal lines (mmm).

**Syntax:**
```
gedinfo lastnames [options] <indi_id> <gedcom_file>
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
- `-d DIRECTION, --direction DIRECTION`: Traversal direction: `ancestors`/`up` (default) or
  `descendants`/`down`. Controls whether surnames are collected from ancestors or descendants.

**Output (Short Mode - default):**
Prints the distinct last names of all traversed relatives, one per line, sorted alphabetically.
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
$ gedinfo lastnames I001 tests/fixtures/long_ancestors.ged
Bauer
Muller
Novak
Svensson
Weber

# Long mode: paternal to maternal sorting (default)
$ gedinfo lastnames -l I001 tests/fixtures/long_ancestors.ged
4       ppp     Novak           I008
4       pp?     Svensson        I009
3       pm      Bauer           I005
3       mp      Muller          I006
3       mm      Weber           I007

# Long mode: limit to 3 generations
$ gedinfo lastnames -l -g 3 I001 tests/fixtures/long_ancestors.ged
3       pp      Novak           I004
3       pm      Bauer           I005
3       mp      Muller          I006
3       mm      Weber           I007

# Long mode: sort by generation
$ gedinfo lastnames -l -s generation I001 tests/fixtures/long_ancestors.ged
3       pm      Bauer           I005
3       mp      Muller          I006
3       mm      Weber           I007
4       ppp     Novak           I008
4       pp?     Svensson        I009

# Long mode: sort by last name
$ gedinfo lastnames -l -s name I001 tests/fixtures/long_ancestors.ged
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
- `--spouse`: Include roots whose spouse has parents with at least one known name. By default such individuals are suppressed because they likely married into a documented family rather than representing an independent lineage starting point.
- `-u, --unknown`: Include roots with no name at all (no NAME tag in the GEDCOM file). By default, nameless individuals are suppressed.
- `-a, --all`: Include all roots without any suppression. Equivalent to combining `--spouse` and `--unknown`. Cannot be combined with `--spouse` or `--unknown`.
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

By default, two categories are suppressed (matching `roots` behaviour):
- **Nameless leaves** — individuals with no NAME tag
- **Married-in leaves** — individuals in a childless family whose spouse has children with another partner

**Syntax:**
```
gedinfo leaves [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-i`: Print IDs only (without @ delimiters), one per line
- `-n`: Print names only, one per line
- `-s, --sort {id,name}`: Sort output
- `--spouse`: Include married-in leaves (whose spouse has children with another partner). By default such individuals are suppressed.
- `-u, --unknown`: Include leaves with no name at all. By default, nameless individuals are suppressed.
- `-a, --all`: Include all leaves without any suppression. Cannot be combined with `--spouse` or `--unknown`.
- (default): Print ID and name pairs in the format `ID	Name`

**Output:**
Leaf individuals (after suppression filters) sorted by GEDCOM file order, or by sort key if `--sort` is given.

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

### indi

List all individuals in the GEDCOM file.

**Syntax:**
```
gedinfo indi [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-i`: Print IDs only (without @ delimiters), one per line
- `-n`: Print names only, one per line
- (default): Print ID and name pairs in the format `ID	Name`

**Output:**
All individuals sorted by ID.

**Examples:**

```bash
# IDs and names (default)
$ gedinfo indi tests/fixtures/simple.ged
I001	John Smith
I002	Mary Jones
I003	Alice Smith
I004	Bob Smith

# IDs only
$ gedinfo indi -i tests/fixtures/simple.ged
I001
I002
I003
I004

# Names only
$ gedinfo indi -n tests/fixtures/simple.ged
John Smith
Mary Jones
Alice Smith
Bob Smith
```

### males

List all male individuals (sex = M) in the GEDCOM file.

**Syntax:**
```
gedinfo males [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-i`: Print IDs only (without @ delimiters), one per line
- `-n`: Print names only, one per line
- (default): Print ID and name pairs in the format `ID	Name`

**Output:**
Male individuals sorted by ID.

**Examples:**

```bash
# IDs and names (default)
$ gedinfo males tests/fixtures/simple.ged
I001	John Smith
I004	Bob Smith

# IDs only
$ gedinfo males -i tests/fixtures/simple.ged
I001
I004

# Names only
$ gedinfo males -n tests/fixtures/simple.ged
John Smith
Bob Smith
```

### females

List all female individuals (sex = F) in the GEDCOM file.

**Syntax:**
```
gedinfo females [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-i`: Print IDs only (without @ delimiters), one per line
- `-n`: Print names only, one per line
- (default): Print ID and name pairs in the format `ID	Name`

**Output:**
Female individuals sorted by ID.

**Examples:**

```bash
# IDs and names (default)
$ gedinfo females tests/fixtures/simple.ged
I002	Mary Jones
I003	Alice Smith

# IDs only
$ gedinfo females -i tests/fixtures/simple.ged
I002
I003

# Names only
$ gedinfo females -n tests/fixtures/simple.ged
Mary Jones
Alice Smith
```

### nosex

List individuals with unknown or unspecified sex (no SEX tag) in the GEDCOM file.

**Syntax:**
```
gedinfo nosex [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-i`: Print IDs only (without @ delimiters), one per line
- `-n`: Print names only, one per line
- (default): Print ID and name pairs in the format `ID	Name`

**Output:**
Individuals with unknown sex sorted by ID.

**Examples:**

```bash
# IDs and names (default)
$ gedinfo nosex tests/fixtures/no_names.ged
I001	(unknown)
I002	Smith
I003	Jane

# IDs only
$ gedinfo nosex -i tests/fixtures/no_names.ged
I001
I002
I003

# Names only
$ gedinfo nosex -n tests/fixtures/no_names.ged
(unknown)
Smith
Jane
```

### noname

List all individuals with no name recorded (no NAME tag in the GEDCOM file).

**Syntax:**
```
gedinfo noname [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-i`: Print IDs only (without @ delimiters), one per line
- `-n`: Print names only, one per line
- `-s, --sort {id,name}`: Sort output
- (default): Print ID and `(unknown)` pairs in the format `ID	(unknown)`

**Output:**
Unnamed individuals in GEDCOM file order (or sorted if `--sort` is given).

### stat

Print statistics about the GEDCOM file, including:
- Number of individuals
- Number of families
- Number of roots (individuals with no parents)
- Number of leaves (individuals with no children)

**Syntax:**
```
gedinfo stat [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `--spouse`: Include spouse-suppressed roots in the root count (same criteria as `roots --spouse`).
- `-u, --unknown`: Include nameless roots in the root count.
- `-a, --all`: Include all roots in the count. Cannot be combined with `--spouse` or `--unknown`.

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
- `--spouse`: As per the roots command: include roots whose spouse has parents with at least one known name. When this flag is passed and suppression removes all roots from a connected component, that component is shown with a single placeholder line "(roots suppressed)" instead of individual entries.
- `-u, --unknown`: Include nameless roots (no NAME tag). By default nameless individuals are suppressed.
- `-a, --all`: Include all roots without suppression. Cannot be combined with `--spouse` or `--unknown`.
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
- `-2, --second`: Also include names from the `NAM2` GEDCOM field (second/additional names).
- `-s MODE, --sort MODE`: Sort order within each section. `frequency` (default) sorts by count
  descending, then alphabetically for ties. `name` sorts alphabetically regardless of count.
- `-e, --hebrew`: Also include names from the `NAMH` GEDCOM field (Hebrew names).
- `-a, --all_names`: Equivalent to `--second --hebrew`.
- `-f, --fuzzy`: Group name variants together using the bundled variants file
  (`gedinfo/data/name_variants.txt`). When multiple variants of the same name appear, they
  are counted and reported on one line with individual variant counts in parentheses.
- `-d DIRECTION, --direction DIRECTION`: Traversal direction: `ancestors` or `up` for ancestors,
  `descendants` or `down` for descendants (default: `descendants`).

**Output:**
Prints output lines in the format `<count>\t<name>`, grouped under section headers.
Names are printed with an initial capital letter.

Without `--fuzzy`:
```
Masculine names:
3	Moshe
2	Abraham

Feminine names:
4	Sarah
1	Miriam
```

With `--fuzzy` (when variants are grouped):
```
Masculine names:
3	Abraham  (Abraham: 2, Abram: 1)
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
$ gedinfo givennames --direction ancestors I001 tests/fixtures/simple.ged
Masculine names:
2	John
1	James

Feminine names:
3	Mary
1	Anne

# Ancestors sorted alphabetically by name
$ gedinfo givennames --direction ancestors --sort name I001 tests/fixtures/simple.ged
Masculine names:
1	James
2	John

Feminine names:
1	Anne
3	Mary

# Fuzzy grouping with secondary names, ancestors only
$ gedinfo givennames --direction ancestors -f -2 I001 tests/fixtures/simple.ged
Masculine names:
3	John  (John: 2, Yohanan: 1)
1	James
```

### relatives

Show the immediate family of an individual: parents, the individual themselves,
spouses, and children per spouse.

**Syntax:**
```
gedinfo relatives [options] <indi_id> <gedcom_file>
```

**Arguments:**
- `<indi_id>`: The GEDCOM individual ID (with or without @ delimiters)
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-i, --id`: Print IDs only (suppress names), one per relative
- `-n, --name`: Print names only (suppress IDs), one per relative
- `-b, --birth`: Also print birth date column
- `-d, --death`: Also print death date column
- `-m, --marriage`: Also print marriage date column (parents' marriage for parent rows; individual's marriage to that spouse for spouse rows; blank for self and children)
- `-l, --long`: Equivalent to `-b -d -m` (adds all date columns; ID and name follow the `-i`/`-n` convention)

If none of `-i`, `-n`, `-b`, `-d`, `-m`, `-l` is specified, the default output shows both ID and name.

**Output:**
One row per relative, tab-separated. The first column is a relationship label:
`father:`, `mother:`, `parent:` (unknown sex), `self:`, `husband:`, `wife:`,
`son:`, `daughter:`, `child:` (unknown sex). When the individual has children in a family with
no recorded other parent, a standalone `(unknown spouse):` header line is printed before those
children. Families with no other parent and no children are skipped.

**Example:**
```bash
$ gedinfo relatives @I001@ tests/fixtures/relatives.ged
father:	I002	John Smith
mother:	I003	Jane Doe
self:	I001	Bob Smith
wife:	I004	Alice Brown
son:	I005	Charlie Smith
daughter:	I006	Diana Smith
wife:	I007	Eve Green
(unknown spouse):
child:	I008	Eddie Smith

$ gedinfo relatives -l @I001@ tests/fixtures/relatives.ged
father:	I002	John Smith	1 JAN 1900	1 JAN 1970	15 JUN 1925
mother:	I003	Jane Doe	5 MAR 1905		15 JUN 1925
self:	I001	Bob Smith	3 APR 1930		
wife:	I004	Alice Brown	7 JUL 1932		10 OCT 1955
son:	I005	Charlie Smith			
daughter:	I006	Diana Smith			
wife:	I007	Eve Green			
(unknown spouse):
child:	I008	Eddie Smith			
```

### anonymize

Output an anonymized derivative of a GEDCOM file. Names, locations, and notes
are replaced with fake-but-realistic data while the family structure (IDs,
relationships, dates, sex) is preserved. The output is deterministic: the same
input always produces the same anonymized output.

**Syntax:**
```
gedinfo anonymize [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-o FILE` / `--output FILE`: write output to FILE instead of stdout
- `--keep FIELD`: keep FIELD unchanged (repeatable)
- `--remove FIELD`: strip FIELD from output (repeatable)
- `--fake FIELD`: anonymize FIELD with realistic fake data (repeatable)
- `--seed NUMBER`: seed for the random name/location generator (default: 0)

If the same GEDCOM field is specified in more than one of `--keep`, `--remove`,
or `--fake`, the command exits with an error naming the conflicting field.

**What is kept unchanged:**
- All date fields (`DATE`)
- Sex of individuals (`SEX`)
- All structural IDs and family links (`HUSB`, `WIFE`, `CHIL`, `FAMC`, `FAMS`)
- `_LIVING` fields
- Event container tags (`BIRT`, `DEAT`, `MARR`, etc.)

**What is anonymized:**
- Names (`NAME`, `GIVN`, `SURN`) — fake names matching the original structure:
  - Token count is preserved (two-word first name → two-word fake first name)
  - Name structure is preserved: first-name-only individuals have no slashes in
    output; last-name-only individuals retain the `/Surname/` format
  - Individuals with an empty name (`NAME //`) have the NAME tag stripped entirely
  - Individuals sharing the same original last name receive the same fake last name
  - Compound names (multiple tokens) always have distinct tokens — no repetition
  - Fake tokens are length-bounded: up to 20 attempts are made to find a token no
    longer than the original; the shortest candidate is used if none qualifies
- Locations (`PLAC`, `ADDR`, `CITY`, `STAE`, `CTRY`, `POST`) — fake place names
  with the same length-bounding as names; the same original value always maps to
  the same fake value
- Notes (`NOTE` and continuation lines)

**What is stripped:**
- GEDCOM header content (replaced with a minimal valid header)
- All other fields not listed above

**Example:**
```bash
$ gedinfo anonymize family.ged
0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I001@ INDI
1 NAME Richard /Sullivan/
1 SEX M
...

$ gedinfo anonymize --keep OCCU --remove DATE family.ged
$ gedinfo anonymize -o anonymized.ged family.ged
```

### calendar

List birth, death, and marriage anniversaries from a GEDCOM file, sorted by
month and day so that all events on the same calendar date are grouped together.

**Syntax:**
```
gedinfo calendar [options] <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Options:**
- `-o FILE` / `--output FILE`: write output to FILE instead of stdout
- `--today`: show only events whose day and month match today's date
- `--thismonth`: show only events in the current calendar month
- `--month MONTHNAME`: show only events in the specified month; `MONTHNAME` can be a full English name or 3-letter abbreviation in any case (e.g. `January`, `jan`, `JAN`)
- `--dateformat PATTERN`: strftime pattern for formatting dates (default: `%d %b %Y`, e.g. "01 Jan 1801")
- `--nosep`: suppress the blank line printed between groups of events on different days

`--today`, `--thismonth`, and `--month` are mutually exclusive; specifying more than one exits with an error.

**Output format:**
Each event is printed on one line with three TAB-separated fields:
1. Date (formatted with `--dateformat`)
2. Event type — `birth`, `death`, or `marriage` — left-padded to 8 characters
3. Name(s) — for births and deaths, the individual's full name; for marriages, both spouses joined by `&`

Events are sorted by month → day → year. A blank line is printed between groups
with different day-month values (suppressed with `--nosep`).

**Included / excluded:**
- Only dates with a complete day, month, and year are included (format: `D MON YYYY`)
- Year-only dates, month-year dates, and approximate/qualified dates (`ABT`, `BEF`, `AFT`, `BET…AND`) are silently skipped
- Individuals with no name produce `(unknown)` in their event row
- Missing spouses in a marriage produce `(unknown)` for that side

**Example:**
```bash
$ gedinfo calendar tests/fixtures/calendar.ged
01 Jan 1801	birth   	John Doe
02 Jan 1883	death   	John Doe

15 Mar 1820	birth   	Jane Smith
15 Mar 1855	birth   	Bob Jones

03 Apr 1930	death   	Bob Jones

05 Jun 1825	marriage	John Doe & Jane Smith
15 Jun 1900	birth   	Alice Brown

20 Sep 1870	marriage	(unknown) & Jane Smith

$ gedinfo calendar --today tests/fixtures/calendar.ged
$ gedinfo calendar --dateformat "%Y-%m-%d" --nosep tests/fixtures/calendar.ged
1801-01-01	birth   	John Doe
1883-01-02	death   	John Doe
1820-03-15	birth   	Jane Smith
1855-03-15	birth   	Bob Jones
1930-04-03	death   	Bob Jones
1825-06-05	marriage	John Doe & Jane Smith
1900-06-15	birth   	Alice Brown
1870-09-20	marriage	(unknown) & Jane Smith
```

### tags

List all GEDCOM tags found in a file, with occurrence counts and a flag for non-standard tags.

**Syntax:**
```
gedinfo tags <gedcom_file>
```

**Arguments:**
- `<gedcom_file>`: Path to the GEDCOM file

**Output:**
One line per unique tag found in the file, sorted alphabetically. Each line has three
TAB-separated fields:
1. Tag name
2. Occurrence count, right-justified
3. `not in GEDCOM 5.5.1` if the tag is non-standard; empty otherwise

Non-standard tags are those not listed in GEDCOM 5.5.1 Appendix A. Custom tags (e.g., `_LIVING`, `_UID`) are always non-standard.

**Example:**
```bash
$ gedinfo tags tests/fixtures/tags.ged
BIRT	2	
CHIL	1	
DATE	3	
DEAT	1	
FAM	1	
FAMC	1	
FAMS	2	
HEAD	1	
HUSB	1	
INDI	3	
NAME	3	
SEX	3	
TRLR	1	
WIFE	1	
_LIVING	2	not in GEDCOM 5.5.1
_UID	1	not in GEDCOM 5.5.1
```

### diff

Compare two GEDCOM files and report individuals and families that were added, removed, or changed. Comparison is ID-based: the same GEDCOM xref ID means the same entity.

**Syntax:**
```
gedinfo diff [options] <gedcom1> <gedcom2>
```

**Arguments:**
- `<gedcom1>`: First GEDCOM file
- `<gedcom2>`: Second GEDCOM file

**Options:**

| Option | Description |
|--------|-------------|
| `-l`, `--long` | For each `CHG` entry, show which fields changed and their old/new values |
| `-s {id,name}`, `--sort` | Sort output by `id` (default, numeric) or `name` (alphabetical) |
| `-i` | Print IDs only (not compatible with `-l`) |
| `-n` | Print names only (not compatible with `-l`) |
| `-a`, `--all` | Compare all model fields including sex, living status, name variants, and notes |

**Change codes:**
- `CHG` — exists in both files but at least one field differs
- `DEL` — exists in the first file only
- `INS` — exists in the second file only

**Output:**
One line per differing individual or family (individuals first, then families). Each line has three TAB-separated fields: ID, name, change code. Use `-i` or `-n` to suppress the ID or name column.

With `-l`, each `CHG` entry is followed by the changed field names and their old (`<`) / new (`>`) values, indented for readability.

**Example:**
```bash
$ gedinfo diff before.ged after.ged
I001    John Smith      CHG
I004    Bob Smith       DEL
I005    New Person      INS
F001    John Smith & Mary Jones CHG

$ gedinfo diff -l before.ged after.ged
I001    John Smith      CHG
  birth_date
    < 1 JAN 1800
    > 2 JAN 1800
I004    Bob Smith       DEL
I005    New Person      INS
F001    John Smith & Mary Jones CHG
  child_ids
    < I003, I004
    > I003
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
