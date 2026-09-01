package dev.mcbookshelf.ward.mixin;

import java.util.List;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.mojang.brigadier.context.ContextChain;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.commands.ExecutionCommandSource;
import net.minecraft.commands.execution.tasks.BuildContexts;

import dev.mcbookshelf.ward.CoverageRecorder;

@Mixin(BuildContexts.class)
public class BuildContextsMixin<T extends ExecutionCommandSource<T>> {
	@Shadow
	@Final
	private ContextChain<T> command;

	/**
	 * Records the command as executed once it dispatches with at least one source, right after the emptiness check that skips it otherwise.
	 */
	@WrapOperation(method = "execute(Lnet/minecraft/commands/ExecutionCommandSource;Ljava/util/List;Lnet/minecraft/commands/execution/ExecutionContext;Lnet/minecraft/commands/execution/Frame;Lnet/minecraft/commands/execution/ChainModifiers;)V", at = @At(value = "INVOKE", target = "Ljava/util/List;isEmpty()Z"))
	private boolean recordExecuted(List<T> sources, Operation<Boolean> original) {
		boolean empty = original.call(sources);

		if (!empty && CoverageRecorder.isEnabled()) {
			CoverageRecorder.recordExecuted(this.command);
		}

		return empty;
	}
}
