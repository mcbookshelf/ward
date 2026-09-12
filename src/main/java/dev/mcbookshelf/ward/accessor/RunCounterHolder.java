package dev.mcbookshelf.ward.accessor;

import org.jspecify.annotations.Nullable;

/**
 * Implemented by {@code LootTableMixin} and {@code LootPoolEntryContainerMixin}: the decoded value carries its own [reached, ran] counters.
 */
public interface RunCounterHolder {
	int @Nullable [] ward$runCounters();

	void ward$runCounters(int[] counters);
}
