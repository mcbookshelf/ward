"""Run the Ward integration suite.

Installs and starts the dev environment through mcward itself (the same code
paths as the CLI), tests the fixture packs over the bridge, and compares the
aggregated session against tests/expected.toml.
"""

import os
import sys
import tomllib
from pathlib import Path

from mcward import (
    CoverageIgnores,
    EnvironmentManager,
    InstalledEnvironment,
    RunningEnvironment,
    TestSession,
    resolve_coverage,
    resolve_functions,
    resolve_resources,
    run_tests,
)

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
PACKS = [TESTS / "packs" / "ward", TESTS / "packs" / "broken", TESTS / "packs" / "overlay"]
IGNORES = CoverageIgnores.load(TESTS)

EVENT_TIMEOUT = 600  # seconds without any test event before giving up
STATUS_COLORS = {"passed": "32", "failed": "31", "skipped": "33"}


def color(text: str, code: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m"


def step(message: str) -> None:
    print(color(f"> {message}", "1"), flush=True)


def detail(message: str) -> None:
    print(f"  {message}", flush=True)


def main() -> int:
    os.chdir(ROOT)
    environment = prepare_environment()
    log = environment.directory / "logs" / "latest.log"

    step("Running tests over the bridge")
    detail(f"server log: {log}")
    running = environment.start()
    try:
        session = stream_run(running)
    finally:
        running.stop()

    if session.aborted:
        fail_with_log(log, next(iter(session.aborted.values())))
    return check_session(session, TESTS / "expected.toml")


def prepare_environment() -> InstalledEnvironment:
    """Reinstall the dev environment, like mcward install dev --force."""
    env = EnvironmentManager().get("dev")
    step(f"Installing environment {env.version}")
    detail(f"directory: {env.directory}")

    if isinstance(env, RunningEnvironment):
        detail("stopping the running dev daemon")
        env = env.stop()
    if isinstance(env, InstalledEnvironment):
        env = env.uninstall()

    return env.install()


def stream_run(running: RunningEnvironment) -> TestSession:
    """Run the fixture packs, echoing each test result as it completes."""
    reported: set[str] = set()
    session = TestSession([running.version])

    # The default selector also proves vanilla built-ins stay out of daemon runs
    for session in run_tests(
        PACKS,
        [running],
        selector="*:*",
        coverage=True,
        timeout=EVENT_TIMEOUT,
    ):
        for batch in session.batches:
            for result in batch.results:
                outcome = result.outcomes.get(running.version)
                if outcome and result.name not in reported:
                    reported.add(result.name)
                    status = outcome.status.value
                    duration = color(f"({outcome.time}ms)", "2")
                    detail(f"{result.name} {color(status, STATUS_COLORS[status])} {duration}")

    return session


def fail_with_log(log: Path, message: str) -> None:
    print(f"\n{color('FAIL:', '1;31')} {message}", file=sys.stderr)
    print(f"\n--- last server output ({log}) ---", file=sys.stderr)
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-40:]:
        print(f"  {line}", file=sys.stderr)
    raise SystemExit(1)


def check_session(session: TestSession, expected_file: Path) -> int:
    """Compare the aggregated test session against the expected manifest."""
    step(f"Comparing against {expected_file.relative_to(ROOT).as_posix()}")
    expected = tomllib.loads(expected_file.read_text(encoding="utf-8"))
    version = session.versions[0]
    results = {result.name: result for batch in session.batches for result in batch.results}
    problems: list[str] = []

    tests: dict[str, tuple[str, str]] = {}
    for name in expected.get("passed", []):
        tests[name] = ("passed", "")
    for status in ("failed", "skipped"):
        for name, message in expected.get(status, {}).items():
            tests[name] = (status, message)
    for name, (status, message) in tests.items():
        if name not in results:
            problems.append(f"missing test: {name}")
            continue
        outcome = results[name].outcomes[version]
        result = outcome.status.value
        if result != status:
            problems.append(f"{name}: expected {status}, got {result} ({outcome.error})")
        elif message not in outcome.error:
            problems.append(f"{name}: message {outcome.error!r} missing {message!r}")
    for name in results.keys() - tests.keys():
        problems.append(f"unexpected test in run: {name}")

    diagnostics = list(session.diagnostics)
    for kind, ids in expected.get("diagnostics", {}).items():
        for id in ids:
            if not any(kind in d.kind and id in d.id for d in diagnostics):
                problems.append(f"missing diagnostic: {kind} for {id}")

    coverage = expected.get("coverage", {})
    problems += check_coverage(session, version, coverage)
    problems += check_absent(session, version, expected.get("absent", []))
    conditions = expected.get("conditions", {})
    problems += check_nodes(session, version, conditions, "nodes")
    runs = expected.get("runs", {})
    problems += check_nodes(session, version, runs, "runs")

    if problems:
        failure = f"run does not match {expected_file.name}"
        print(f"\n{color('FAIL:', '1;31')} {failure}", file=sys.stderr)
        for problem in problems:
            print(f"  {color('-', '31')} {problem}", file=sys.stderr)
        return 1

    counts = (
        f"{len(tests)} tests, {len(diagnostics)} diagnostics, {len(coverage)} coverage, "
        f"{len(conditions)} condition and {len(runs)} run reports as expected"
    )
    print(f"\n{color('OK:', '1;32')} {counts}")
    return 0


def check_coverage(session: TestSession, version, expected: dict) -> list[str]:
    """Compare per-function line categories against the expected manifest."""
    if not expected:
        return []
    coverage = session.coverage.get(version)
    if coverage is None:
        return ["missing coverage event: the run reported no coverage"]

    problems = []
    functions = resolve_functions(coverage, PACKS, ignores=IGNORES)
    reports = {report.name: report for report in functions}
    for name, spec in expected.items():
        report = reports.get(name)
        if report is None:
            problems.append(f"missing coverage for {name}")
            continue
        actual = {
            "executed": [line.line for line in report.lines if line.executed],
            "guarded": [line.line for line in report.lines if line.reached and not line.executed],
            "unreached": [line.line for line in report.lines if not line.reached],
        }
        for category, lines in spec.items():
            if (found := actual.get(category)) != lines:
                problems.append(f"{name}: {category} lines {found}, expected {lines}")
    return problems


def check_absent(session: TestSession, version, names: list[str]) -> list[str]:
    """Elements the ignore markers and tests/ward.toml must keep out of the report."""
    if not names:
        return []
    coverage = session.coverage.get(version)
    if coverage is None:
        return ["missing coverage event: the run reported no coverage"]

    reported = {r.name for r in resolve_coverage(coverage, PACKS, ignores=IGNORES).reports}
    return [f"{name} should be ignored but is in the report" for name in names if name in reported]


def check_nodes(session: TestSession, version, expected: dict, field: str) -> list[str]:
    """Compare per-resource node counts (conditions or runs) against the manifest."""
    if not expected:
        return []
    coverage = session.coverage.get(version)
    if coverage is None:
        return ["missing coverage event: the run reported no coverage"]

    problems = []
    resolved = resolve_resources(coverage, PACKS, ignores=IGNORES)
    resources = {resource.name: resource for resource in resolved}
    for name, nodes in expected.items():
        resource = resources.get(name)
        if resource is None:
            problems.append(f"missing {field} for {name}")
            continue
        recorded = getattr(resource, field)
        actual = {node.path: list(node.counts) for node in recorded}
        if actual != nodes:
            problems.append(f"{name}: {field} {actual}, expected {nodes}")
        elif any(node.lines is None for node in recorded):
            problems.append(f"{name}: some {field} did not resolve to line spans")
    return problems


if __name__ == "__main__":
    sys.exit(main())
