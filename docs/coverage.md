# Test coverage

Coverage shows which parts of your packs the tests run.

```sh
mcward test --coverage
```

The summary prints after the results. It counts three things:

- **Commands** in `function` files.
- **Conditions** in JSON files: predicates, loot tables, item modifiers,
  advancements, number providers.
- **Parts that run** in JSON files: the rolls and entries of a loot table,
  loot functions, number providers, slot sources and advancement criteria.

The report only covers the namespace you test. `mcward test mypack:*`
reports `mypack`.

## Report files

`--coverage-report` writes the line-by-line detail to a file:

```sh
mcward test --coverage-report html                # coverage.html
mcward test --coverage-report lcov:out/cov.lcov   # custom path
```

- **`html`**: one self-contained page. Open it to find what still needs a test.
- **`lcov`**: for editor extensions like Coverage Gutters and services like Codecov.

Use the option twice to write both. With several versions, you get one file
per version.

## Require a minimum

A run can fail when coverage is too low. Set the percentage in a `ward.toml`
file in the folder where you run the tests:

```toml
[coverage]
minimum = 80
```

The run then ends with an error and exit code 1:

```
Coverage: 72.4% (181/250, 40/52 files)

Coverage 72.4% is below the minimum of 80%
```

The minimum is checked against the figure on the `Coverage:` line, on every
run that measures coverage. A run without `--coverage` checks nothing. With
several versions, each one has to reach it.

`--coverage-min 90` sets the minimum for one run, whatever the file says. It
turns coverage on by itself.

### Per namespace

A good total can hide a namespace that is barely tested. Give `minimum` a
table to also set what each namespace has to reach on its own:

```toml
[coverage]
minimum = { total = 80, namespace = 60 }
```

```
Coverage: 84.1% (420/500, 61/70 files)
  bs.health   91.0%   91/100  12/12 files
  bs.math     52.3%   68/130   9/14 files

Coverage 52.3% of bs.math is below the minimum of 60% per namespace
```

Either key can be left out. `minimum = 80` is the short form of
`{ total = 80 }`, and `--coverage-min` only replaces the total.

## Ignore code

Some commands never run during tests. Mark them in the function file:

```mcfunction
# @coverage ignore
say only the next command is ignored

# @coverage off
say everything from here on is ignored
say until the file ends or coverage turns back on
# @coverage on
```

JSON files have no comments. Put their rules in a `ward.toml` file in the
folder where you run the tests:

```toml
[coverage]
ignore = [
  "mypack:debug/*",
  { kind = "predicate", id = "mypack:generated/*" },
  { kind = "loot_table", id = "mypack:chest", nodes = ["pools[0].entries[2]", "pools[1].*"] },
  { kind = "function", id = "mypack:chest/fill", lines = [5, 6] },
]
```

- A plain string ignores every file matching the id, functions and JSON alike.
- `kind` limits a rule to one folder (`predicate`, `loot_table`, `function`, ...).
- `nodes` keeps the file but ignores the given JSON paths.
- `lines` ignores lines of a function, as numbered in the report.

`*` is a wildcard in ids, kinds and node paths.
