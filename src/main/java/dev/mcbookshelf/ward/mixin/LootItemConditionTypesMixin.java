package dev.mcbookshelf.ward.mixin;

import com.mojang.serialization.MapCodec;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyArg;

import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraft.world.level.storage.loot.predicates.LootItemConditionTypes;

import dev.mcbookshelf.ward.DataCoverage;

@Mixin(LootItemConditionTypes.class)
public class LootItemConditionTypesMixin {
	/**
	 * Wraps every condition type's codec for coverage, so conditions record in every context they appear in.
	 */
	@ModifyArg(method = "bootstrap", at = @At(value = "INVOKE", target = "Lnet/minecraft/core/Registry;register(Lnet/minecraft/core/Registry;Ljava/lang/String;Ljava/lang/Object;)Ljava/lang/Object;"), index = 2)
	@SuppressWarnings("unchecked")
	private static Object wrapCodec(Object codec) {
		return DataCoverage.wrapCondition((MapCodec<? extends LootItemCondition>) codec);
	}
}
