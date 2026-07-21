package dev.mcbookshelf.ward.mixin;

import java.util.Map;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.resources.RegistryDataLoader;
import net.minecraft.resources.ResourceKey;

import dev.mcbookshelf.ward.LoadDiagnostic;
import dev.mcbookshelf.ward.ReportManager;
import dev.mcbookshelf.ward.Ward;

/**
 * Reports each registry element that fails to parse, instead of letting one broken element crash
 * the whole load. Draining the error map at both {@code isEmpty()} guards (which is why there is
 * no ordinal) makes vanilla skip its throw and keep whatever loaded. References to the missing
 * elements are handled by {@code MappedRegistryMixin}.
 */
@Mixin(RegistryDataLoader.class)
public class RegistryDataLoaderMixin {
	/**
	 * Reports and drains the errors. {@code lambda$load$2} is the freeze-and-validate stage of
	 * {@code load}.
	 */
	@WrapOperation(method = "lambda$load$2", at = @At(value = "INVOKE", target = "Ljava/util/Map;isEmpty()Z"))
	private static boolean ward$reportAndContinue(Map<ResourceKey<?>, Exception> errors, Operation<Boolean> original) {
		errors.forEach((key, error) -> {
			// Draining the map skips vanilla's own error logging, so replace it too
			Ward.LOGGER.error("Failed to load {} from {}", key.registry(), key.identifier(), error);
			ReportManager.report(LoadDiagnostic.error(
					key.registry().toString(),
					key.identifier().toString(),
					LoadDiagnostic.describe(error)));
		});
		errors.clear();
		return original.call(errors);
	}
}
