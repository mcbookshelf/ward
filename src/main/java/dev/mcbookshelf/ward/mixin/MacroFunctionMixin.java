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

import dev.mcbookshelf.ward.CoverageRecorder;

@Mixin(MacroFunction.class)
public class MacroFunctionMixin<T extends ExecutionCommandSource<T>> {
	@Shadow
	@Final
	private Identifier id;

	/**
	 * Instantiated macros carry a derived id; coverage maps it back to the source function.
	 */
	@ModifyReturnValue(method = "substituteAndParse", at = @At("RETURN"))
	private InstantiatedFunction<T> registerCoverageAlias(InstantiatedFunction<T> function) {
		if (CoverageRecorder.isEnabled()) {
			CoverageRecorder.registerMacroAlias(function.id(), this.id);
		}

		return function;
	}
}
