package dev.mcbookshelf.ward.mixin;

import java.util.Map;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.core.registries.Registries;
import net.minecraft.resources.RegistryLoadTask;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceManagerRegistryLoadTask;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.Ward;

@Mixin(RegistryLoadTask.class)
public class RegistryLoadTaskMixin {
	/**
	 * Every element is loaded by the time the first registry freezes, so the shared map holds all their errors.
	 */
	@Inject(method = "freezeRegistry", at = @At("HEAD"))
	private void reportElementErrors(Map<ResourceKey<?>, Exception> loadingErrors, CallbackInfoReturnable<Boolean> info) {
		if (!((Object) this instanceof ResourceManagerRegistryLoadTask<?>)) {
			return;
		}

		loadingErrors.entrySet().removeIf(entry -> {
			ResourceKey<?> key = entry.getKey();

			if (key.registry().equals(Registries.ROOT_REGISTRY_NAME)) {
				return false;
			}

			Exception error = entry.getValue();
			Ward.LOGGER.error("Failed to load {} from {}", key.registry(), key.identifier(), error);
			String reason = error.getCause() == null ? "" : ": " + Messages.describe(error.getCause());
			Reporter.loadError(key.registry().toString(), key.identifier().toString(), Messages.describe(error) + reason);
			return true;
		});
	}
}
