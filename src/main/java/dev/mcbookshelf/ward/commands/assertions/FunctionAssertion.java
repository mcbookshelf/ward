package dev.mcbookshelf.ward.commands.assertions;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.context.ContextChain;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.FunctionInstantiationException;
import net.minecraft.commands.arguments.item.FunctionArgument;
import net.minecraft.commands.execution.ChainModifiers;
import net.minecraft.commands.execution.CustomCommandExecutor;
import net.minecraft.commands.execution.EntryAction;
import net.minecraft.commands.execution.ExecutionControl;
import net.minecraft.commands.execution.tasks.CallFunction;
import net.minecraft.commands.execution.tasks.FallthroughTask;
import net.minecraft.commands.execution.tasks.IsolatedCall;
import net.minecraft.commands.functions.CommandFunction;
import net.minecraft.commands.functions.InstantiatedFunction;
import net.minecraft.network.chat.ComponentUtils;
import net.minecraft.server.commands.ExecuteCommand;
import net.minecraft.server.commands.FunctionCommand;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;
import dev.mcbookshelf.ward.test.TestExecutor;

class FunctionAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("function")
				.then(Commands.argument("function", FunctionArgument.functions())
						.suggests(FunctionCommand.SUGGEST_FUNCTION)
						.executes(new AssertFunction(mode))));
	}

	private record AssertFunction(Mode mode) implements CustomCommandExecutor.CommandAdapter<CommandSourceStack> {
		@Override
		public void run(
				CommandSourceStack sender,
				ContextChain<CommandSourceStack> currentStep,
				ChainModifiers modifiers,
				ExecutionControl<CommandSourceStack> output) {
			try {
				runGuarded(sender, currentStep, output);
			} catch (CommandSyntaxException e) {
				sender.handleError(e, modifiers.isForked(), output.tracer());
				sender.callback().onFailure();
			}
		}

		private void runGuarded(
				CommandSourceStack sender,
				ContextChain<CommandSourceStack> currentStep,
				ExecutionControl<CommandSourceStack> output) throws CommandSyntaxException {
			TestExecutor test = TestExecutor.current();
			CommandContext<CommandSourceStack> context = currentStep.getTopContext().copyFor(sender);
			String name = Assertion.getRawArgument(context, "function");
			List<InstantiatedFunction<CommandSourceStack>> functions;

			try {
				functions = instantiate(context, sender.dispatcher());
			} catch (CommandSyntaxException e) {
				throw test.failure(ComponentUtils.fromMessage(e.getRawMessage()));
			}

			int[] returned = {0};
			Function<CommandSourceStack, EntryAction<CommandSourceStack>> call = source -> {
				CommandSourceStack functionSource = FunctionCommand.modifySenderForExecution(source.clearCallbacks());

				return new IsolatedCall<>(control -> {
					returned[0] = 0;

					for (InstantiatedFunction<CommandSourceStack> function : functions) {
						control.queueNext(new CallFunction<>(function, control.currentFrame().returnValueConsumer(), true).bind(functionSource));
					}

					control.queueNext(FallthroughTask.instance());
				}, (success, result) -> returned[0] = result);
			};

			this.mode.check(test, sender, output, call, () -> {
				return AssertResult.of(returned[0] != 0, negated -> Messages.translatable(
						negated ? "ward.assert.not_function" : "ward.assert.function",
						name, returned[0]));
			});
		}

		private static List<InstantiatedFunction<CommandSourceStack>> instantiate(
				CommandContext<CommandSourceStack> context,
				CommandDispatcher<CommandSourceStack> dispatcher) throws CommandSyntaxException {
			List<InstantiatedFunction<CommandSourceStack>> functions = new ArrayList<>();

			for (CommandFunction<CommandSourceStack> function : FunctionArgument.getFunctions(context, "function")) {
				try {
					functions.add(function.instantiate(null, dispatcher));
				} catch (FunctionInstantiationException e) {
					throw ExecuteCommand.ERROR_FUNCTION_CONDITION_INSTANTATION_FAILURE.create(function.id(), e.messageComponent());
				}
			}

			return functions;
		}
	}
}
