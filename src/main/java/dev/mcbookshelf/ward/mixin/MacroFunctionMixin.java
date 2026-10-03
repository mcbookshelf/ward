package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.ModifyReturnValue;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.commands.ExecutionCommandSource;
import net.minecraft.commands.functions.InstantiatedFunction;
import net.minecraft.commands.functions.MacroFunction;
import net.minecraft.resources.Identifier;

import dev.mcbookshelf.ward.coverage.FunctionCoverage;

@Mixin(MacroFunction.class)
public class MacroFunctionMixin<T extends ExecutionCommandSource<T>> {
	@Shadow
	@Final
	private Identifier id;

	/**
	 * An instance has an id of its own: its commands count for the macro they come from.
	 */
	@ModifyReturnValue(method = "substituteAndParse", at = @At("RETURN"))
	private InstantiatedFunction<T> stampCoverage(InstantiatedFunction<T> function) {
		FunctionCoverage.stamp(this.id, function.entries());
		return function;
	}
}
