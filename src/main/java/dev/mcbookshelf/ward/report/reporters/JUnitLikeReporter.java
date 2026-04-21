package dev.mcbookshelf.ward.report.reporters;

import dev.mcbookshelf.ward.report.ReportEntry;
import dev.mcbookshelf.ward.report.Reporter;
import net.minecraft.gametest.framework.GameTestInfo;
import net.minecraft.util.Util;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerException;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.File;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.Objects;

public class JUnitLikeReporter implements Reporter {

    private final Document document;
    private final Element loadTestSuite;
    private final Element gameTestSuite;
    private final File destination;

    // Counters for test suite attributes
    private int loadTests = 0;
    private int loadFailures = 0;
    private int loadSkipped = 0;
    private int gameTests = 0;
    private int gameFailures = 0;
    private int gameSkipped = 0;
    private long gameTestsTotalTime = 0; // Accumulated test time in milliseconds

    public JUnitLikeReporter(File destination) throws ParserConfigurationException {
        this.destination = destination;
        this.document = DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument();
        Element testSuites = this.document.createElement("testsuites");
        this.document.appendChild(testSuites);

        // Create test suite for diagnostics (load errors/warnings)
        this.loadTestSuite = this.document.createElement("testsuite");
        this.loadTestSuite.setAttribute("name", "diagnostics");
        this.loadTestSuite.setAttribute("timestamp", DateTimeFormatter.ISO_INSTANT.format(Instant.now()));
        testSuites.appendChild(this.loadTestSuite);

        // Create test suite for game tests
        this.gameTestSuite = this.document.createElement("testsuite");
        this.gameTestSuite.setAttribute("name", "gametests");
        this.gameTestSuite.setAttribute("timestamp", DateTimeFormatter.ISO_INSTANT.format(Instant.now()));
        testSuites.appendChild(this.gameTestSuite);
    }

    @Override
    public void report(ReportEntry entry) {
        switch (entry) {
            case ReportEntry.Load load -> reportLoad(load);
            case ReportEntry.Test test -> reportTest(test);
        }
    }

    private void reportLoad(ReportEntry.Load load) {
        Element testCase = this.document.createElement("testcase");
        testCase.setAttribute("name", load.id());
        testCase.setAttribute("classname", load.type());
        testCase.setAttribute("time", "0");

        // Create failure/warning element based on severity
        String elementName = switch (load.severity()) {
            case Error -> {
                loadFailures++;
                yield "failure";
            }
            case Warn -> {
                loadSkipped++;
                yield "skipped";
            }
        };

        Element result = this.document.createElement(elementName);
        result.setAttribute("message", load.message());
        testCase.appendChild(result);

        this.loadTestSuite.appendChild(testCase);
        loadTests++;
    }

    private void reportTest(ReportEntry.Test test) {
        GameTestInfo testInfo = test.info();
        String name = testInfo.id().toString();

        Element testCase = this.document.createElement("testcase");
        testCase.setAttribute("name", name);
        testCase.setAttribute("classname", testInfo.getTest().batch().getRegisteredName());
        testCase.setAttribute("time", String.valueOf(testInfo.getRunTime() / 1000.0));

        // Accumulate test time for suite total
        gameTestsTotalTime += testInfo.getRunTime();

        if (!test.passed()) {
            String message = Util.describeError(Objects.requireNonNull(test.info().getError()));
            Element result = this.document.createElement(testInfo.isRequired() ? "failure" : "skipped");
            result.setAttribute("message", message);
            testCase.appendChild(result);

            if (testInfo.isRequired()) {
                gameFailures++;
            } else {
                gameSkipped++;
            }
        }

        this.gameTestSuite.appendChild(testCase);
        gameTests++;
    }

    @Override
    public void finish() {
        // Set load test suite attributes
        this.loadTestSuite.setAttribute("time", "0");
        this.loadTestSuite.setAttribute("tests", String.valueOf(loadTests));
        this.loadTestSuite.setAttribute("failures", String.valueOf(loadFailures));
        this.loadTestSuite.setAttribute("skipped", String.valueOf(loadSkipped));

        // Set game test suite attributes (uses accumulated test times)
        String gameTime = String.valueOf(gameTestsTotalTime / 1000.0);
        this.gameTestSuite.setAttribute("time", gameTime);
        this.gameTestSuite.setAttribute("tests", String.valueOf(gameTests));
        this.gameTestSuite.setAttribute("failures", String.valueOf(gameFailures));
        this.gameTestSuite.setAttribute("skipped", String.valueOf(gameSkipped));

        try {
            save(this.destination);
        } catch (TransformerException e) {
            throw new Error("Couldn't save test report", e);
        }
    }

    private void save(File file) throws TransformerException {
        TransformerFactory transformerFactory = TransformerFactory.newInstance();
        Transformer transformer = transformerFactory.newTransformer();
        DOMSource source = new DOMSource(this.document);
        StreamResult result = new StreamResult(file);
        transformer.transform(source, result);
    }
}
