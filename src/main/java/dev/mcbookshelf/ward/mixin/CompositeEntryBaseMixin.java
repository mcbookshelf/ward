package dev.mcbookshelf.ward.mixin;

import java.util.function.Consumer;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.entries.CompositeEntryBase;
import net.minecraft.world.level.storage.loot.entries.LootPoolEntry;

import dev.mcbookshelf.ward.accessor.RunCounterHolder;

/**
 * Same as {@code LootPoolSingletonContainerMixin}, for composite entries (alternatives, group, sequence).
 */
@Mixin(CompositeEntryBase.class)
public class CompositeEntryBaseMixin {
	@Inject(method = "expand", at = @At("HEAD"))
	private void recordReached(LootContext context, Consumer<LootPoolEntry> output, CallbackInfoReturnable<Boolean> cir) {
		int[] counters = ((RunCounterHolder) this).ward$runCounters();

		if (counters != null) {
			counters[0]++;
		}
	}

	@WrapOperation(method = "expand", at = @At(value = "INVOKE", target = "Lnet/minecraft/world/level/storage/loot/entries/CompositeEntryBase;canRun(Lnet/minecraft/world/level/storage/loot/LootContext;)Z"))
	private boolean recordRan(CompositeEntryBase entry, LootContext context, Operation<Boolean> original) {
		boolean allowed = original.call(entry, context);
		int[] counters = ((RunCounterHolder) this).ward$runCounters();

		if (allowed && counters != null) {
			counters[1]++;
		}

		return allowed;
	}
}
