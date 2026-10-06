package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.Decoder;
import com.mojang.serialization.DynamicOps;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.resources.ResourceKey;
import net.minecraft.server.packs.resources.Resource;

import dev.mcbookshelf.ward.coverage.DataCoverage;

@Mixin(targets = "net.minecraft.resources.RegistryLoadTask$PendingRegistration")
public class PendingRegistrationMixin {
	/**
	 * What an element decodes is counted under the file it comes from.
	 */
	@WrapOperation(method = "loadFromResource", at = @At(value = "INVOKE", target = "Lcom/mojang/serialization/Decoder;parse(Lcom/mojang/serialization/DynamicOps;Ljava/lang/Object;)Lcom/mojang/serialization/DataResult;"))
	private static DataResult<?> tagElementDecode(
			Decoder<?> decoder,
			DynamicOps<?> ops,
			Object json,
			Operation<DataResult<?>> original,
			@Local(argsOnly = true) ResourceKey<?> elementKey,
			@Local(argsOnly = true) Resource resource) {
		return DataCoverage.track(elementKey, resource, json, () -> original.call(decoder, ops, json));
	}
}
