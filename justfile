# Ward dev tasks — `just --list` shows everything

# Windows runs recipes through PowerShell; keep recipes single commands
[windows]
set shell := ["powershell.exe", "-NoProfile", "-Command"]

gradlew := if os() == "windows" { ".\\gradlew.bat" } else { "./gradlew" }

[private]
default:
    @just --list --unsorted

# Build the mod, enforcing Java style (checkstyle + spotless)
build:
    {{gradlew}} build

# Bump the version of a release stream: `just bump java 1.2.0`
bump stream version:
    uv run tools/bump.py {{stream}} {{version}}

# Fast feedback loop: lint + types + test (no server, no gradle)
check: lint types test

# Everything the CI pipeline proves: check + build + verify
ci: check build verify

# Fix style: ruff for Python, spotless for Java imports/whitespace
format:
    uv run ruff format packages/ tools/
    {{gradlew}} spotlessApply

# Check Python style with ruff (Java style is checked by `build`)
lint:
    uv run ruff check packages/ tools/
    uv run ruff format --check packages/ tools/

# Run the unit tests of every Python package
test:
    uv run pytest packages/mcward-core/tests packages/mcward-cli/tests packages/mcward-beet/tests

# Type-check the Python packages with ty
types:
    uv run ty check packages/

# Build the mod and run the integration suite
verify:
    uv run tools/verify.py
