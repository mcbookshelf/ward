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

import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.coverage.Coverage;
import dev.mcbookshelf.ward.coverage.DataCoverage;

@Mixin(ReloadableServerRegistries.class)
public class ReloadableServerRegistriesMixin {
	/**
	 * Fabric's loot API can rebuild a table after its decode: only the registered instance rolls.
	 */
	@Inject(method = "validateLootRegistries", at = @At("HEAD"))
	private static void stampLootTables(HolderLookup.Provider registries, CallbackInfo info) {
		if (!Coverage.isEnabled()) {
			return;
		}

		registries.lookup(Registries.LOOT_TABLE).ifPresent(tables -> tables.listElements()
				.forEach(table -> DataCoverage.stampRegistered(table.key(), table.value())));
	}

	@WrapOperation(method = "validateLootRegistries", at = @At(value = "INVOKE", target = "Lnet/minecraft/util/ProblemReporter$Collector;forEach(Ljava/util/function/BiConsumer;)V"))
	private static void catchLootValidationError(
			ProblemReporter.Collector collector,
			BiConsumer<String, ProblemReporter.Problem> consumer,
			Operation<Void> original) {
		original.call(collector, consumer.andThen((path, problem) -> {
			// Problem paths render as "{<element id>@<registry>}<path>", e.g. "{blocks/stone@minecraft:loot_table}.pools[0]" (RootElementPathElement)
			int start = path.indexOf('{');
			int end = path.indexOf('}', start + 1);
			int at = start < 0 || end < 0 ? -1 : path.indexOf('@', start);
			boolean rooted = at >= 0 && at < end;
			String kind = rooted ? path.substring(at + 1, end) : "loot";
			String id = rooted ? path.substring(start + 1, at) : path;
			String message = rooted && end + 2 < path.length()
					? String.format("%s (at %s)", problem.description(), path.substring(end + 2))
					: problem.description();

			if (problem.isFatal()) {
				Reporter.loadError(kind, id, message);
			} else {
				Reporter.loadWarning(kind, id, message);
			}
		}));
	}
}
