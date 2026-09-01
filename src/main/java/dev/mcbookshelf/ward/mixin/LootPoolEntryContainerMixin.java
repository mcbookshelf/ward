package dev.mcbookshelf.ward.mixin;

import java.util.function.Consumer;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.entries.LootPoolEntry;
import net.minecraft.world.level.storage.loot.entries.LootPoolEntryContainer;

import dev.mcbookshelf.ward.accessor.RunCounterHolder;

/**
 * An entry is reached when its pool asks it to expand and ran when its condition lets it.
 * Entries without counters (vanilla data, or coverage off) record nothing.
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

	@Inject(method = "expand", at = @At("HEAD"))
	private void recordReached(LootContext context, Consumer<LootPoolEntry> output, CallbackInfoReturnable<Boolean> cir) {
		if (this.ward$runCounters != null) {
			this.ward$runCounters[0]++;
		}
	}

	@WrapOperation(method = "expand", at = @At(value = "INVOKE", target = "Lnet/minecraft/world/level/storage/loot/entries/LootPoolEntryContainer;expandRaw(Lnet/minecraft/world/level/storage/loot/LootContext;Ljava/util/function/Consumer;)Z"))
	private boolean recordRan(
			LootPoolEntryContainer entry,
			LootContext context,
			Consumer<LootPoolEntry> output,
			Operation<Boolean> original) {
		if (this.ward$runCounters != null) {
			this.ward$runCounters[1]++;
		}

		return original.call(entry, context, output);
	}
}
