package dev.mcbookshelf.ward.commands.assertions;

import java.util.List;
import java.util.function.Consumer;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.context.ContextChain;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import org.jspecify.annotations.Nullable;

import net.minecraft.advancements.predicates.MinMaxBounds;
import net.minecraft.commands.CommandResultCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.RangeArgument;
import net.minecraft.commands.execution.ChainModifiers;
import net.minecraft.commands.execution.CustomModifierExecutor;
import net.minecraft.commands.execution.ExecutionContext;
import net.minecraft.commands.execution.ExecutionControl;
import net.minecraft.commands.execution.tasks.BuildContexts;
import net.minecraft.commands.execution.tasks.FallthroughTask;
import net.minecraft.commands.execution.tasks.IsolatedCall;

import dev.mcbookshelf.ward.AssertResult;
import dev.mcbookshelf.ward.TestExecutor;

class RunAssertion implements Assertion {
	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context context) {
		root.then(buildRun(context, false));
		root.then(Commands.literal("result")
				.then(Commands.argument("range", RangeArgument.intRange())
						.then(buildRun(context, true))));
	}

	private static LiteralArgumentBuilder<CommandSourceStack> buildRun(Context context, boolean ranged) {
		return Commands.literal("run").fork(context.dispatcher().getRoot(), new AssertRun(context, ranged));
	}

	private record AssertRun(Context assertion, boolean ranged) implements CustomModifierExecutor.ModifierAdapter<CommandSourceStack> {
		@Override
		public void apply(
				CommandSourceStack originalSource,
				List<CommandSourceStack> sources,
				ContextChain<CommandSourceStack> currentStep,
				ChainModifiers modifiers,
				ExecutionControl<CommandSourceStack> output) {
			if (sources.isEmpty()) {
				return;
			}

			try {
				TestExecutor test = TestExecutor.current();
				CommandContext<CommandSourceStack> context = currentStep.getTopContext().copyFor(originalSource);
				MinMaxBounds.Ints range = this.ranged ? RangeArgument.Ints.getRange(context, "range") : null;
				String rawRange = this.ranged ? Assertion.getRawArgument(context, "range") : null;
				String input = currentStep.getTopContext().getInput();
				ContextChain<CommandSourceStack> tail = currentStep.nextStage();
				List<CommandSourceStack> captured = List.copyOf(sources);

				queueTail(output, input, tail, modifiers, originalSource, captured, range, rawRange, result ->
						this.assertion.deliver(test, result, () -> pollTail(input, tail, captured, range, rawRange)));
			} catch (CommandSyntaxException e) {
				originalSource.handleError(e, modifiers.isForked(), output.tracer());
			}
		}

		private static void queueTail(
				ExecutionControl<CommandSourceStack> output,
				String input,
				ContextChain<CommandSourceStack> tail,
				ChainModifiers modifiers,
				CommandSourceStack originalSource,
				List<CommandSourceStack> sources,
				MinMaxBounds.@Nullable Ints range,
				@Nullable String rawRange,
				Consumer<AssertResult> onResult) {
			int[] fires = {0};
			int[] misses = {0};
			int[] found = {0};
			List<CommandSourceStack> wrapped = sources.stream()
					.map(source -> counting(source, range, fires, misses, found))
					.toList();

			output.queueNext(new IsolatedCall<>(control -> {
				control.queueNext(new BuildContexts.Continuation<>(input, tail, modifiers, originalSource, wrapped));
				control.queueNext(FallthroughTask.instance());
			}, CommandResultCallback.EMPTY));

			output.queueNext(new IsolatedCall<>(control -> {
				onResult.accept(runResult(rawRange, fires[0], misses[0], found[0]));
				control.queueNext(FallthroughTask.instance());
			}, CommandResultCallback.EMPTY));
		}

		private static AssertResult pollTail(
				String input,
				ContextChain<CommandSourceStack> tail,
				List<CommandSourceStack> sources,
				MinMaxBounds.@Nullable Ints range,
				String rawRange) {
			int[] fires = {0};
			int[] misses = {0};
			int[] found = {0};

			for (CommandSourceStack source : sources) {
				CommandSourceStack capturing = counting(source, range, fires, misses, found);
				Commands.executeCommandInContext(capturing, ctx ->
						ExecutionContext.queueInitialCommandExecution(ctx, input, tail, capturing, CommandResultCallback.EMPTY));
			}

			return runResult(rawRange, fires[0], misses[0], found[0]);
		}

		private static CommandSourceStack counting(
				CommandSourceStack source,
				MinMaxBounds.@Nullable Ints range,
				int[] fires,
				int[] misses,
				int[] found) {
			return source.withCallback((success, result) -> {
				fires[0]++;
				found[0] = result;

				if (!matches(range, success, result)) {
					misses[0]++;
				}
			}, CommandResultCallback::chain);
		}

		private static boolean matches(MinMaxBounds.@Nullable Ints range, boolean success, int result) {
			return range == null ? success : range.matches(result);
		}

		private static AssertResult runResult(@Nullable String rawRange, int fires, int misses, int found) {
			int satisfied = fires > 0 && misses == 0 ? 1 : 0;
			return rawRange == null
					? AssertResult.of(satisfied, "run")
					: AssertResult.of(satisfied, "result", rawRange, found);
		}
	}
}
