package dev.mcbookshelf.ward.mixin;

import java.util.function.BiConsumer;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.Registries;
import net.minecraft.server.ReloadableServerRegistries;
import net.minecraft.util.ProblemReporter;

import dev.mcbookshelf.ward.CoverageRecorder;
import dev.mcbookshelf.ward.DataCoverage;
import dev.mcbookshelf.ward.LoadDiagnostic;
import dev.mcbookshelf.ward.ReportManager;

@Mixin(ReloadableServerRegistries.class)
public class ReloadableServerRegistriesMixin {
	/**
	 * Fabric's loot API may rebuild loot tables after decode, dropping the roll counters
	 * stamped on the original instance: re-stamp the ones that actually got registered.
	 */
	@Inject(method = "validateLootRegistries", at = @At("HEAD"))
	private static void stampLootTables(HolderLookup.Provider registries, CallbackInfo ci) {
		if (!CoverageRecorder.isEnabled()) {
			return;
		}

		registries.lookup(Registries.LOOT_TABLE).ifPresent(lookup -> lookup.listElements().forEach(
				holder -> DataCoverage.stampRegistered(
						holder.key().registry().toString(),
						holder.key().identifier().toString(),
						holder.value())));
	}

	@WrapOperation(method = "validateLootRegistries", at = @At(value = "INVOKE", target = "Lnet/minecraft/util/ProblemReporter$Collector;forEach(Ljava/util/function/BiConsumer;)V"))
	private static void catchLootValidationError(
			ProblemReporter.Collector collector,
			BiConsumer<String, ProblemReporter.Problem> consumer,
			Operation<Void> original) {
		original.call(collector, consumer);
		collector.forEach((id, problem) -> {
			// Problem paths render as "{<element id>@<registry>}<path>", e.g. "{blocks/stone@minecraft:loot_table}.pools[0]" (RootElementPathElement)
			int end = id.indexOf('}');
			String path = id.substring(end + 2);
			String[] parts = id.substring(id.indexOf('{') + 1, end).split("@");
			String message = String.format("%s (at %s)", problem.description(), path);
			ReportManager.report(LoadDiagnostic.warn(parts[1], parts[0], message));
		});
	}
}
