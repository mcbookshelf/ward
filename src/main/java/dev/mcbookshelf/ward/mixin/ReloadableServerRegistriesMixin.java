package dev.mcbookshelf.ward.mixin;

import java.util.function.BiConsumer;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.server.ReloadableServerRegistries;
import net.minecraft.util.ProblemReporter;

import dev.mcbookshelf.ward.LoadDiagnostic;
import dev.mcbookshelf.ward.ReportManager;

@Mixin(ReloadableServerRegistries.class)
public class ReloadableServerRegistriesMixin {
	@WrapOperation(method = "validateLootRegistries", at = @At(value = "INVOKE", target = "Lnet/minecraft/util/ProblemReporter$Collector;forEach(Ljava/util/function/BiConsumer;)V"))
	private static void catchLootValidationError(
			ProblemReporter.Collector collector,
			BiConsumer<String, ProblemReporter.Problem> consumer,
			Operation<Void> original) {
		original.call(collector, consumer);
		collector.forEach((id, problem) -> {
			// Problem paths render as "{<element id>@<registry>}<path>", e.g.
			// "{blocks/stone@minecraft:loot_table}.pools[0]" (ProblemReporter.RootElementPathElement)
			int end = id.indexOf('}');
			String path = id.substring(end + 2);
			String[] parts = id.substring(id.indexOf('{') + 1, end).split("@");
			String message = String.format("%s (at %s)", problem.description(), path);
			ReportManager.report(LoadDiagnostic.warn(parts[1], parts[0], message));
		});
	}
}
