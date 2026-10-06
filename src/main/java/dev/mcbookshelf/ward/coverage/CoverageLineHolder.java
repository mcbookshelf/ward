package dev.mcbookshelf.ward.coverage;

import org.jspecify.annotations.Nullable;

public interface CoverageLineHolder {
	FunctionCoverage.@Nullable Line ward$coverageLine();

	void ward$coverageLine(FunctionCoverage.Line line);
}
