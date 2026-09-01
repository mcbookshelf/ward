package dev.mcbookshelf.ward.mixin;

import com.mojang.serialization.MapCodec;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyArg;

import net.minecraft.world.level.storage.loot.providers.number.floats.ContextFloatProvider;
import net.minecraft.world.level.storage.loot.providers.number.floats.ContextFloatProviderTypes;

import dev.mcbookshelf.ward.DataCoverage;

@Mixin(ContextFloatProviderTypes.class)
public class ContextFloatProviderTypesMixin {
	/**
	 * Wraps every provider type's codec for coverage.
	 * Inline constants bypass the dispatch and stay out: a bare number is not runnable logic.
	 */
	@ModifyArg(method = "bootstrap", at = @At(value = "INVOKE", target = "Lnet/minecraft/core/Registry;register(Lnet/minecraft/core/Registry;Ljava/lang/String;Ljava/lang/Object;)Ljava/lang/Object;"), index = 2)
	@SuppressWarnings("unchecked")
	private static Object wrapCodec(Object codec) {
		return DataCoverage.wrapFloatProvider((MapCodec<? extends ContextFloatProvider>) codec);
	}
}
