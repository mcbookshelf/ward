package dev.mcbookshelf.ward.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.server.PlayerAdvancements;

import dev.mcbookshelf.ward.DataCoverage;

@Mixin(PlayerAdvancements.class)
public class PlayerAdvancementsMixin {
	/**
	 * Only newly awarded criteria count, so the numbers stay deterministic when an event matches an already granted criterion.
	 */
	@Inject(method = "award", at = @At("RETURN"))
	private void recordCriterion(
			AdvancementHolder holder,
			String criterion,
			CallbackInfoReturnable<Boolean> cir) {
		if (cir.getReturnValueZ()) {
			DataCoverage.recordCriterion(holder.id().toString(), criterion);
		}
	}
}
