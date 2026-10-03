package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.ModifyReturnValue;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.commands.ExecutionCommandSource;
import net.minecraft.commands.functions.CommandFunction;
import net.minecraft.commands.functions.PlainTextFunction;

import dev.mcbookshelf.ward.coverage.FunctionCoverage;

@Mixin(CommandFunction.class)
public interface CommandFunctionMixin {
	/**
	 * A macro has no commands yet: MacroFunctionMixin stamps each of its instances.
	 */
	@ModifyReturnValue(method = "fromLines", at = @At("RETURN"))
	private static <T extends ExecutionCommandSource<T>> CommandFunction<T> stampCoverage(CommandFunction<T> function) {
		if (function instanceof PlainTextFunction<T> plain) {
			FunctionCoverage.stamp(plain.id(), plain.entries());
		}

		return function;
	}
}
