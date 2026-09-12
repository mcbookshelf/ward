package dev.mcbookshelf.ward.mixin;

import com.mojang.serialization.MapCodec;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyArg;

import net.minecraft.world.item.slot.SlotSource;
import net.minecraft.world.item.slot.SlotSources;

import dev.mcbookshelf.ward.DataCoverage;

@Mixin(SlotSources.class)
public interface SlotSourcesMixin {
	/**
	 * Wraps every slot source type's codec for coverage.
	 */
	@ModifyArg(method = "bootstrap", at = @At(value = "INVOKE", target = "Lnet/minecraft/core/Registry;register(Lnet/minecraft/core/Registry;Ljava/lang/String;Ljava/lang/Object;)Ljava/lang/Object;"), index = 2)
	@SuppressWarnings("unchecked")
	private static Object wrapCodec(Object codec) {
		return DataCoverage.wrapSlotSource((MapCodec<? extends SlotSource>) codec);
	}
}
