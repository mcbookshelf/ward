package dev.mcbookshelf.ward.report;

import net.minecraft.gametest.framework.GameTestInfo;

public sealed interface ReportEntry permits ReportEntry.Load, ReportEntry.Test {

    enum Severity { Error, Warn }

    record Load(Severity severity, String type, String id, String message) implements ReportEntry {}

    record Test(GameTestInfo info, boolean passed) implements ReportEntry {}

    static Load error(String type, String id, String message) {
        return new Load(Severity.Error, type, id, message);
    }

    static Load warn(String type, String id, String message) {
        return new Load(Severity.Warn, type, id, message);
    }
}

