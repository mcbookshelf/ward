package dev.mcbookshelf.ward.mixin;

import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;

import net.minecraft.world.level.storage.loot.entries.LootPoolEntryContainer;

import dev.mcbookshelf.ward.accessor.RunCounterHolder;

/**
 * Holds the entry's run counters. Entries without counters (vanilla data, or coverage off) record nothing.
 * The recording itself happens in the two {@code expand} implementations, see {@code LootPoolSingletonContainerMixin} and {@code CompositeEntryBaseMixin}.
 */
@Mixin(LootPoolEntryContainer.class)
public class LootPoolEntryContainerMixin implements RunCounterHolder {
	@Unique
	private int @Nullable [] ward$runCounters;

	@Override
	public int @Nullable [] ward$runCounters() {
		return this.ward$runCounters;
	}

	@Override
	public void ward$runCounters(int[] counters) {
		this.ward$runCounters = counters;
	}
}
