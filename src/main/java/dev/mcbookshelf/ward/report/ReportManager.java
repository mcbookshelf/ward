package dev.mcbookshelf.ward.report;

import net.minecraft.gametest.framework.GameTestInfo;
import net.minecraft.gametest.framework.GlobalTestReporter;
import net.minecraft.gametest.framework.TestReporter;

import java.util.ArrayList;
import java.util.List;

public class ReportManager {

    private static final List<Reporter> REPORTERS = new ArrayList<>();
    private static final TestReporterProxy PROXY = new TestReporterProxy();

    public static void clear() {
        REPORTERS.clear();
    }

    public static void register(Reporter reporter) {
        GlobalTestReporter.replaceWith(PROXY);
        REPORTERS.add(reporter);
    }

    public static void report(ReportEntry entry) {
        REPORTERS.forEach(reporter -> reporter.report(entry));
    }

    private static class TestReporterProxy implements TestReporter {
        @Override
        public void onTestFailed(GameTestInfo testInfo) {
            report(new ReportEntry.Test(testInfo, false));
        }

        @Override
        public void onTestSuccess(GameTestInfo testInfo) {
            report(new ReportEntry.Test(testInfo, true));
        }

        @Override
        public void finish() {
            REPORTERS.forEach(Reporter::finish);
        }
    }
}
