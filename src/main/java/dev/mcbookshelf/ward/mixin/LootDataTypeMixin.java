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

import dev.mcbookshelf.ward.LoadDiagnostic;
import dev.mcbookshelf.ward.ReportManager;
import dev.mcbookshelf.ward.Ward;

/**
 * Turns a crash during loot element validation into a diagnostic for that element. Validation
 * calls {@code Holder.value()}, which throws on references left unbound by
 * {@code MappedRegistryMixin}.
 */
@Mixin(LootDataType.class)
public class LootDataTypeMixin {
	@WrapOperation(method = "runValidation(Lnet/minecraft/world/level/storage/loot/ValidationContextSource;Lnet/minecraft/resources/ResourceKey;Lnet/minecraft/world/level/storage/loot/Validatable;)V", at = @At(value = "INVOKE", target = "Lnet/minecraft/world/level/storage/loot/Validatable;validate(Lnet/minecraft/world/level/storage/loot/ValidationContext;)V"))
	private void ward$catchValidationCrash(
			Validatable value,
			ValidationContext context,
			Operation<Void> original,
			@Local(argsOnly = true) ResourceKey<?> key) {
		try {
			original.call(value, context);
		} catch (Exception e) {
			Ward.LOGGER.error("Failed to validate {} from {}", key.registry(), key.identifier(), e);
			ReportManager.report(LoadDiagnostic.error(
					key.registry().toString(),
					key.identifier().toString(),
					LoadDiagnostic.describe(e)));
		}
	}
}
