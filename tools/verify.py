"""Run the Ward integration suite.

Installs and starts the dev environment through mcward itself (the same code
paths as the CLI), tests the fixture packs over the bridge, and compares the
aggregated session against tests/expected.toml.

One daemon serves every run: the fixtures, then the runs that must end with an
error, then the fixtures again, so state left over from a run shows up.
"""

import os
import sys
import tomllib
from pathlib import Path

from mcward import (
    CoverageConfig,
    EnvironmentManager,
    InstalledEnvironment,
    RunningEnvironment,
    TestSession,
    resolve_coverage,
    resolve_functions,
    resolve_resources,
    run_bench,
    run_tests,
)

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
PACKS = [TESTS / "packs" / "ward", TESTS / "packs" / "broken", TESTS / "packs" / "overlay"]
IGNORES = CoverageConfig.load(TESTS).ignores

# Runs that end with an error event instead of results: packs, selector, part of the error
ABORTED = [
    (PACKS, "ward:no_such_test", "No tests found matching selector"),
    ([TESTS / "packs" / "stop"], "*:*", "Server stopped before the run finished"),
]

EVENT_TIMEOUT = 600  # seconds without any test event before giving up
AUDIT_FAILURE = "Could not force-load"
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
    # The audit mode of the mod: every mixin target is loaded at start,
    # and each run encodes what a client would be sent
    os.environ["JAVA_TOOL_OPTIONS"] = "-Dward.audit=true"
    running = environment.start()
    started = log.read_text(encoding="utf-8", errors="replace")
    if unloaded := started.count(AUDIT_FAILURE):
        running.stop()
        fail_with_log(log, f"{unloaded} mixin targets failed the audit")
    try:
        first = stream_run(running, coverage=True)
        step("Running the aborted runs on the same daemon")
        problems = [problem for run in ABORTED if (problem := check_aborted(running, *run))]
        step("Running a bench on the same daemon")
        problems += check_bench(running)
        step("Running the tests again on the same daemon")
        second = stream_run(running, coverage=False)
    finally:
        running.stop()

    for session in (first, second):
        if session.aborted:
            fail_with_log(log, next(iter(session.aborted.values())))

    expected_file = TESTS / "expected.toml"
    step(f"Comparing against {expected_file.relative_to(ROOT).as_posix()}")
    expected = tomllib.loads(expected_file.read_text(encoding="utf-8"))
    problems += check_session(first, expected, coverage=True)
    problems += [f"second run: {p}" for p in check_session(second, expected, coverage=False)]

    if problems:
        failure = f"run does not match {expected_file.name}"
        print(f"\n{color('FAIL:', '1;31')} {failure}", file=sys.stderr)
        for problem in problems:
            print(f"  {color('-', '31')} {problem}", file=sys.stderr)
        return 1

    tests = len(expected.get("passed", []))
    tests += sum(len(expected.get(status, {})) for status in ("failed", "skipped"))
    counts = (
        f"{tests} tests in two runs, {len(ABORTED)} aborted runs, "
        f"{len(first.diagnostics)} diagnostics, {len(expected.get('coverage', {}))} coverage, "
        f"{len(expected.get('conditions', {}))} condition "
        f"and {len(expected.get('runs', {}))} run reports as expected"
    )
    print(f"\n{color('OK:', '1;32')} {counts}")
    return 0


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


def stream_run(running: RunningEnvironment, coverage: bool) -> TestSession:
    """Run the fixture packs, echoing each test result as it completes."""
    reported: set[str] = set()
    session = TestSession([running.version])

    # The default selector also proves vanilla built-ins stay out of daemon runs
    for session in run_tests(
        PACKS,
        [running],
        selector="*:*",
        coverage=coverage,
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


def check_aborted(
    running: RunningEnvironment, packs: list[Path], selector: str, error: str
) -> str | None:
    """Run packs that must end with an error event; the daemon has to stay usable after it."""
    *_, session = run_tests(packs, [running], selector=selector, timeout=EVENT_TIMEOUT)
    found = session.aborted.get(running.version)
    detail(f"{selector} on {', '.join(pack.name for pack in packs)}: {found}")
    if found is None:
        return f"{selector}: expected the run to abort with {error!r}, it finished"
    if error not in found:
        return f"{selector}: aborted with {found!r}, expected {error!r}"
    return None


def check_bench(running: RunningEnvironment) -> list[str]:
    """Bench a function, a function that does not exist and a command that does not parse."""
    commands = ["function ward:helper/pass", "function ward:helper/typo", "sya hi"]
    passed, typo, broken = run_bench(PACKS, running, commands, warmup=100, duration=200)
    for report in (passed, typo, broken):
        outcome = report.failed or f"{len(report.times)} samples, {report.commands} commands"
        detail(f"{report.name}: {outcome}")

    problems = []
    if not passed.times or passed.commands != 2 or passed.error:
        problems.append(f"bench: {passed.name} was not measured as a function of one command")
    if "Unknown function" not in (typo.error or ""):
        problems.append(f"bench: {typo.name} did not report its first run as failed")
    if not broken.failed or broken.times:
        problems.append(f"bench: {broken.name} should not parse, and was measured")
    return problems


def fail_with_log(log: Path, message: str) -> None:
    print(f"\n{color('FAIL:', '1;31')} {message}", file=sys.stderr)
    print(f"\n--- last server output ({log}) ---", file=sys.stderr)
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-40:]:
        print(f"  {line}", file=sys.stderr)
    raise SystemExit(1)


def check_session(session: TestSession, expected: dict, coverage: bool) -> list[str]:
    """Compare the aggregated test session against the expected manifest."""
    version = session.versions[0]
    results = {result.name: result for batch in session.batches for result in batch.results}
    problems: list[str] = []

    tests: dict[str, tuple[str, str | dict]] = {}
    for name in expected.get("passed", []):
        tests[name] = ("passed", "")
    for status in ("failed", "skipped"):
        for name, expect in expected.get(status, {}).items():
            tests[name] = (status, expect)
    for name, (status, expect) in tests.items():
        if name not in results:
            problems.append(f"missing test: {name}")
            continue
        # A failure is a part of its message, or a table that also gives its line and tick
        expect = {"message": expect} if isinstance(expect, str) else expect
        outcome = results[name].outcomes[version]
        result = outcome.status.value
        if result != status:
            problems.append(f"{name}: expected {status}, got {result} ({outcome.error})")
        elif expect["message"] not in outcome.error:
            problems.append(f"{name}: message {outcome.error!r} missing {expect['message']!r}")
        for field in ("line", "tick"):
            if field in expect and getattr(outcome, field) != expect[field]:
                found = getattr(outcome, field)
                problems.append(f"{name}: expected {field} {expect[field]}, got {found}")
    for name in results.keys() - tests.keys():
        problems.append(f"unexpected test in run: {name}")

    diagnostics = list(session.diagnostics)
    for kind, messages in expected.get("diagnostics", {}).items():
        for id, message in messages.items():
            found = [d.message for d in diagnostics if kind in d.kind and id in d.id]
            if not found:
                problems.append(f"missing diagnostic: {kind} for {id}")
            elif not any(message in text for text in found):
                problems.append(f"diagnostic {kind} for {id}: {found!r} missing {message!r}")
    known = [
        (kind, id) for kind, messages in expected.get("diagnostics", {}).items() for id in messages
    ]
    for d in diagnostics:
        if not any(kind in d.kind and id in d.id for kind, id in known):
            problems.append(f"unexpected diagnostic: {d.kind} {d.id}: {d.message}")

    if not coverage:
        if session.coverage.get(version) is not None:
            problems.append("coverage event in a run that did not ask for coverage")
        return problems

    problems += check_coverage(session, version, expected.get("coverage", {}))
    problems += check_absent(session, version, expected.get("absent", []))
    problems += check_nodes(session, version, expected.get("conditions", {}), "nodes")
    problems += check_nodes(session, version, expected.get("runs", {}), "runs")
    return problems


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
