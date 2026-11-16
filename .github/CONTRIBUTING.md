# Contributing to Ward

Ward is a single repository with two deliverables: the Fabric mod (`src/`,
released to Modrinth) and the Python tooling (`packages/`, released to PyPI).
Releases are fully automated from the versions committed to the tree, see
[Releases and versioning](#releases-and-versioning).

## Development setup

Requirements: [uv](https://docs.astral.sh/uv/), [just](https://just.systems),
and a JDK (25+). Gradle comes with the wrapper.

```sh
uv sync --all-extras          # set up the Python workspace
just check                    # lint + types + unit tests
```

Dev tasks (run with `just <task>`; `just --list` shows everything):

| Task | What it does |
| --- | --- |
| `test` | Unit tests for all Python packages |
| `lint` | Check Python style with ruff (Java style is enforced by `build`) |
| `format` | Rewrite style: ruff for Python, spotless for Java imports/whitespace |
| `types` | Type-check with ty |
| `build` | Build the mod with gradle, including Java style checks (checkstyle) |
| `check` | The fast loop: `lint` + `types` + `test` |
| `verify` | Build the mod and run the integration suite |
| `ci` | Everything the CI pipeline proves |

### Integration suite

`just verify` builds the mod, installs a real Fabric server through the
mcward library, starts it in daemon mode, and tests the fixture packs from
`tests/packs/` (`ward`, the test pack, plus `broken` and `overlay`, two
intentionally invalid ones) over the bridge, through the same code paths as
`mcward test`. The aggregated results are compared against
`tests/expected.toml`.

If you add or change mod behavior, extend the fixture: add a test function
under `tests/packs/ward/data/ward/test/` and its expected result in
`tests/expected.toml`. Unknown results, missing tests and unexpected extras
all fail the suite.

## Layout

```
src/                  Fabric mod (Java)
packages/mcward       The mcward library (its pyproject is the root one)
packages/mcward-cli   The mcward command-line interface, installed by mcward[cli]
packages/mcward-beet  The beet plugin and beet test command, installed by mcward[beet]
tools/                Dev and release tooling (run with uv run tools/<name>.py)
tests/                Integration fixture packs and expected report
docs/                 User documentation
```

## Code style

Python follows ruff's defaults (`just lint`, `just format`). Java follows the
Fabric conventions (tabs, same-line braces, no line-length limit), enforced
by the root `checkstyle.xml` as part of every `just build`. `just format`
handles the mechanical parts (import order, whitespace); layout fixes are
guided by the checkstyle output.

## Releases and versioning

Releases are driven by the versions committed to the tree: bumping a version
file is the release request. On every push, `tools/release.py` tags and
publishes whatever version has no tag yet. Nothing else decides. There are
two independent streams:

- **Python packages**: `mcward`, `mcward-cli` and `mcward-beet` share the
  version of the root `pyproject.toml` and pin each other to it exactly. Bump
  it in your PR with `just bump python 1.2.0`, which also rewrites the pins;
  merging to `main` tags `v1.2.0` and publishes the three to PyPI.

- **The mod**: versioned by `gradle.properties`, with `mod_version` plus the
  targeted `minecraft_version`, tagged fabric-api style with the full version
  (`v1.2.3+26.1.2`) and published to Modrinth. Bump with
  `just bump java 1.2.3` when the mod changes; a new `minecraft_version`
  alone releases a compatibility build (same mod version, new build
  metadata), so `1.2.3+26.1.2` and `1.2.3+26.2` carry the exact same feature
  set. The mod releases from `main` and from maintenance branches. When an
  automated Minecraft bump does not build, check `loom_version` against
  <https://fabricmc.net/develop>.

The notes of a release list the commits since the previous tag of its stream
that touched its files: `packages/` and `pyproject.toml` for Python, `src/` and
the Gradle files for the mod. A change to both shows in both.

Follow semver when picking a version: new functionality bumps minor,
bugfixes bump patch, breaking changes bump major.

## Pull requests

- CI must be green: it runs the Java build, `just check`, packaging checks and
  the full integration suite on every push and PR.
- If the PR should ship, include the version bump; if it should wait for a
  batch, leave the version untouched and it releases with the next bump.
