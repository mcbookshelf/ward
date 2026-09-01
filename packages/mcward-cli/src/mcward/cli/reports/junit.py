"""JUnit XML test results, for CI test tabs."""

from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement

from mcward import TestSession, TestStatus


def write_junit(session: TestSession, path: Path) -> None:
    """Write test results as JUnit XML, one testsuite per version."""
    suites = Element("testsuites")
    for version in session.versions:
        suite = SubElement(suites, "testsuite", name=version.name)
        tests = failures = skipped = elapsed = 0
        for batch in session.batches:
            for result in batch.results:
                outcome = result.outcomes.get(version)
                if outcome is None:
                    continue
                tests += 1
                elapsed += outcome.time
                case = SubElement(
                    suite,
                    "testcase",
                    name=result.name,
                    classname=batch.name,
                    time=f"{outcome.time / 1000:.3f}",
                )
                if outcome.status is TestStatus.FAILED:
                    failures += 1
                    SubElement(case, "failure", message=outcome.error)
                elif outcome.status is TestStatus.SKIPPED:
                    skipped += 1
                    SubElement(case, "skipped", message=outcome.error)

        errors = 0
        if message := session.aborted.get(version):
            errors = 1
            crashed = SubElement(suite, "testcase", name="run", classname="ward")
            SubElement(crashed, "error", message=message)

        suite.attrib.update(
            tests=str(tests),
            failures=str(failures),
            skipped=str(skipped),
            errors=str(errors),
            time=f"{elapsed / 1000:.3f}",
        )

    ElementTree(suites).write(path, encoding="utf-8", xml_declaration=True)
