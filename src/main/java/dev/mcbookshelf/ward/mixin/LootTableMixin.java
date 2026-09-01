package dev.mcbookshelf.ward.mixin;

import java.util.function.Consumer;

import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.LootTable;

import dev.mcbookshelf.ward.accessor.RunCounterHolder;

@Mixin(LootTable.class)
public class LootTableMixin implements RunCounterHolder {
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

	/**
	 * Counts rolls for coverage: every roll funnels through the raw entry point.
	 * Tables without counters (vanilla data, or coverage off) record nothing.
	 */
	@Inject(method = "getRandomItemsRaw(Lnet/minecraft/world/level/storage/loot/LootContext;Ljava/util/function/Consumer;)V", at = @At("HEAD"))
	private void recordRoll(LootContext context, Consumer<ItemStack> output, CallbackInfo ci) {
		if (this.ward$runCounters != null) {
			this.ward$runCounters[0]++;
			this.ward$runCounters[1]++;
		}
	}
}
