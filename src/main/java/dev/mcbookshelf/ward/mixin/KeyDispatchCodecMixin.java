package dev.mcbookshelf.ward.mixin;

import com.google.gson.JsonElement;
import com.llamalad7.mixinextras.injector.ModifyReturnValue;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.DynamicOps;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.MapLike;
import com.mojang.serialization.codecs.KeyDispatchCodec;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

import dev.mcbookshelf.ward.coverage.Coverage;
import dev.mcbookshelf.ward.coverage.DataCoverage;

/**
 * Every value with a type member is decoded here, whatever its registry.
 */
@Mixin(value = KeyDispatchCodec.class, remap = false)
public class KeyDispatchCodecMixin<K, V> {
	@Shadow
	@Final
	private MapCodec<K> keyCodec;

	@ModifyReturnValue(method = "decode", at = @At("RETURN"))
	private <T> DataResult<V> countDecoded(DataResult<V> result, DynamicOps<T> ops, MapLike<T> input) {
		if (!Coverage.isEnabled()) {
			return result;
		}

		T type = this.keyCodec.keys(ops).findFirst().map(input::get).orElse(null);
		return type instanceof JsonElement member ? DataCoverage.decoded(result, member) : result;
	}

	@ModifyVariable(method = "encode", at = @At("HEAD"), argsOnly = true)
	private V unwrapRecording(V value) {
		return DataCoverage.unwrap(value);
	}
}
