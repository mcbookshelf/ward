package dev.mcbookshelf.ward.mixin;

import java.util.List;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.commands.ExecutionCommandSource;
import net.minecraft.commands.execution.UnboundEntryAction;
import net.minecraft.commands.execution.tasks.CallFunction;
import net.minecraft.commands.functions.InstantiatedFunction;

import dev.mcbookshelf.ward.CoverageRecorder;

@Mixin(CallFunction.class)
public class CallFunctionMixin<T extends ExecutionCommandSource<T>> {
	@Shadow
	@Final
	private InstantiatedFunction<T> function;

	/**
	 * Swaps in coverage-recording entries.
	 * Every way to run a function (commands, tags, schedules, macros) funnels through here.
	 */
	@WrapOperation(method = "execute(Lnet/minecraft/commands/ExecutionCommandSource;Lnet/minecraft/commands/execution/ExecutionContext;Lnet/minecraft/commands/execution/Frame;)V", at = @At(value = "INVOKE", target = "Lnet/minecraft/commands/functions/InstantiatedFunction;entries()Ljava/util/List;", ordinal = 0))
	private List<UnboundEntryAction<T>> instrumentEntries(
			InstantiatedFunction<T> instance,
			Operation<List<UnboundEntryAction<T>>> original) {
		List<UnboundEntryAction<T>> entries = original.call(instance);
		return CoverageRecorder.isEnabled() ? CoverageRecorder.instrument(instance, entries) : entries;
	}
}
