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

import dev.mcbookshelf.ward.coverage.RunCounterHolder;

@Mixin(LootTable.class)
public class LootTableMixin implements RunCounterHolder {
	@Unique
	private int @Nullable [] ward$runCounters;

	@Override
	public void ward$runCounters(int[] counters) {
		this.ward$runCounters = counters;
	}

	/**
	 * Every roll goes through this entry point.
	 */
	@Inject(method = "getRandomItemsRaw(Lnet/minecraft/world/level/storage/loot/LootContext;Ljava/util/function/Consumer;)V", at = @At("HEAD"))
	private void recordRoll(LootContext context, Consumer<ItemStack> output, CallbackInfo info) {
		if (this.ward$runCounters != null) {
			this.ward$runCounters[0]++;
			this.ward$runCounters[1]++;
		}
	}
}
