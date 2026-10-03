package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.ModifyExpressionValue;
import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.world.level.storage.loot.entries.LootPoolEntryContainer;

import dev.mcbookshelf.ward.coverage.RunCounterHolder;

/**
 * Reached when its pool asks it to expand, ran when its conditions let it.
 */
@Mixin(LootPoolEntryContainer.class)
public class LootPoolEntryContainerMixin implements RunCounterHolder {
	@Unique
	private int @Nullable [] ward$runCounters;

	@Override
	public void ward$runCounters(int[] counters) {
		this.ward$runCounters = counters;
	}

	@ModifyExpressionValue(method = "expand", at = @At(value = "INVOKE", target = "Lnet/minecraft/world/level/storage/loot/entries/LootPoolEntryContainer;canRun(Lnet/minecraft/world/level/storage/loot/LootContext;)Z"))
	private boolean recordRun(boolean ran) {
		if (this.ward$runCounters != null) {
			this.ward$runCounters[0]++;

			if (ran) {
				this.ward$runCounters[1]++;
			}
		}

		return ran;
	}
}
