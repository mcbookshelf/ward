package dev.mcbookshelf.ward.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.server.PlayerAdvancements;

import dev.mcbookshelf.ward.coverage.Coverage;
import dev.mcbookshelf.ward.coverage.DataCoverage;

@Mixin(PlayerAdvancements.class)
public class PlayerAdvancementsMixin {
	/**
	 * Only a newly awarded criterion counts: an event can match one that is already granted.
	 */
	@Inject(method = "award", at = @At("RETURN"))
	private void recordCriterion(
			AdvancementHolder holder,
			String criterion,
			CallbackInfoReturnable<Boolean> info) {
		if (Coverage.isEnabled() && info.getReturnValueZ()) {
			DataCoverage.recordCriterion(holder.id().toString(), criterion);
		}
	}
}
