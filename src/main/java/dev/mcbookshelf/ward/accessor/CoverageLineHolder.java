package dev.mcbookshelf.ward.accessor;

import org.jspecify.annotations.Nullable;

import dev.mcbookshelf.ward.CoverageRecorder;

/**
 * Implemented by {@code ContextChainMixin}: the chain carries its own coverage line.
 */
public interface CoverageLineHolder {
	CoverageRecorder.@Nullable Line ward$coverageLine();

	void ward$coverageLine(CoverageRecorder.Line line);
}
