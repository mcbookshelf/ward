# Test coverage

Coverage shows which parts of your packs the tests run.

```sh
mcward test --coverage
```

The summary prints after the results. It counts two things:

- **Commands** in `function` files.
- **Conditions** in JSON files: predicates, loot tables, item modifiers,
  advancements, number providers.

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
