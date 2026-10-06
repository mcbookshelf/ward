package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.storage.loot.LootDataType;
import net.minecraft.world.level.storage.loot.Validatable;
import net.minecraft.world.level.storage.loot.ValidationContext;

import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.Ward;

@Mixin(LootDataType.class)
public class LootDataTypeMixin {
	/**
	 * Validation calls Holder.value(), which throws on a reference MappedRegistryMixin left unbound.
	 */
	@WrapOperation(method = "runValidation(Lnet/minecraft/world/level/storage/loot/ValidationContextSource;Lnet/minecraft/resources/ResourceKey;Lnet/minecraft/world/level/storage/loot/Validatable;)V", at = @At(value = "INVOKE", target = "Lnet/minecraft/world/level/storage/loot/Validatable;validate(Lnet/minecraft/world/level/storage/loot/ValidationContext;)V"))
	private void catchValidationCrash(
			Validatable value,
			ValidationContext context,
			Operation<Void> original,
			@Local(argsOnly = true) ResourceKey<?> key) {
		try {
			original.call(value, context);
		} catch (Exception e) {
			Ward.LOGGER.error("Failed to validate {} from {}", key.registry(), key.identifier(), e);
			Reporter.loadError(key.registry().toString(), key.identifier().toString(), e);
		}
	}
}
