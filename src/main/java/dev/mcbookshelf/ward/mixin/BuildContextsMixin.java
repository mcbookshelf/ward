package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.ModifyExpressionValue;
import com.mojang.brigadier.context.ContextChain;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.commands.ExecutionCommandSource;
import net.minecraft.commands.execution.tasks.BuildContexts;

import dev.mcbookshelf.ward.coverage.FunctionCoverage;

@Mixin(BuildContexts.class)
public class BuildContextsMixin<T extends ExecutionCommandSource<T>> {
	@Shadow
	@Final
	private ContextChain<T> command;

	/**
	 * Function entries and top-level commands trace their start, a continuation of the same command does not.
	 */
	@Inject(method = "traceCommandStart", at = @At("HEAD"))
	private void recordReached(CallbackInfo info) {
		FunctionCoverage.recordReached(this.command);
	}

	/**
	 * Right after the emptiness check: a command with no source is skipped.
	 */
	@ModifyExpressionValue(method = "execute(Lnet/minecraft/commands/ExecutionCommandSource;Ljava/util/List;Lnet/minecraft/commands/execution/ExecutionContext;Lnet/minecraft/commands/execution/Frame;Lnet/minecraft/commands/execution/ChainModifiers;)V", allow = 1, at = @At(value = "INVOKE", target = "Ljava/util/List;isEmpty()Z"))
	private boolean recordExecuted(boolean empty) {
		if (!empty) {
			FunctionCoverage.recordExecuted(this.command);
		}

		return empty;
	}
}
