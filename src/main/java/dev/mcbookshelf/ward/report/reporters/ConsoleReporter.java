package dev.mcbookshelf.ward.report.reporters;

import dev.mcbookshelf.ward.Ward;
import dev.mcbookshelf.ward.report.ReportEntry;
import dev.mcbookshelf.ward.report.Reporter;
import net.minecraft.util.Util;

import java.util.Objects;

public class ConsoleReporter implements Reporter {

    @Override
    public void report(ReportEntry entry) {
        switch (entry) {
            case ReportEntry.Load load -> reportLoad(load);
            case ReportEntry.Test test -> reportTest(test);
        }
    }

    private void reportLoad(ReportEntry.Load load) {
        String formattedMessage = String.format("%s (%s): %s", load.id(), load.type(), load.message());

        switch (load.severity()) {
            case Error -> Ward.LOGGER.error(formattedMessage);
            case Warn -> Ward.LOGGER.warn(formattedMessage);
        }
    }

    private void reportTest(ReportEntry.Test test) {
        if (test.passed()) {
            return;
        }

        if (test.info().isRequired()) {
            Ward.LOGGER.error(
                "{} failed: {}",
                test.info().id(),
                Util.describeError(Objects.requireNonNull(test.info().getError()))
            );
        } else {
            Ward.LOGGER.warn(
                "(optional) {} failed: {}",
                test.info().id(),
                Util.describeError(Objects.requireNonNull(test.info().getError()))
            );
        }
    }
}
