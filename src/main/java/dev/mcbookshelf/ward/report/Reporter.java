package dev.mcbookshelf.ward.report;

public interface Reporter {

    void report(ReportEntry entry);

    default void finish() {}
}
