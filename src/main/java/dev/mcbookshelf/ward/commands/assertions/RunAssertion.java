package dev.mcbookshelf.ward.commands.assertions;

import java.util.List;

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
import net.minecraft.network.chat.Component;

import dev.mcbookshelf.ward.TestExecutor;

/**
 * The run condition: the tail is a fully parsed command, like /execute run.
 *
 * <p>The condition tests the tail's reported outcome — its success flag, or its result value
 * against the range for the {@code result <range> run} form. Asserts redirect with a source whose
 * callback checks the outcome once the tail completes (the execute store mechanism); awaits
 * capture the parsed tail without running it and re-execute it every tick.
 */
class RunAssertion implements Assertion {
	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context context) {
		root.then(buildRun(context, false));
		root.then(Commands.literal("result")
				.then(Commands.argument("range", RangeArgument.intRange())
						.then(buildRun(context, true))));
	}

	private static LiteralArgumentBuilder<CommandSourceStack> buildRun(Context context, boolean ranged) {
		LiteralArgumentBuilder<CommandSourceStack> run = Commands.literal("run");

		if (context.immediate()) {
			return run.redirect(context.dispatcher().getRoot(), ctx -> assertingSource(ctx, context.mode(), ranged));
		}

		return run.fork(context.dispatcher().getRoot(), new AwaitRun(context, ranged));
	}

	/**
	 * Wraps the redirected source so the tail reports back to the test once it completes.
	 */
	private static CommandSourceStack assertingSource(
			CommandContext<CommandSourceStack> context,
			Mode mode,
			boolean ranged) throws CommandSyntaxException {
		TestExecutor test = TestExecutor.current();
		MinMaxBounds.Ints range = ranged ? RangeArgument.Ints.getRange(context, "range") : null;
		String rawRange = ranged ? Assertions.getRawArgument(context, "range") : null;
		boolean negated = mode == Mode.ASSERT_FALSE;

		return context.getSource().withCallback((success, result) -> {
			boolean satisfied = range == null ? success : range.matches(result);

			if (satisfied == negated) {
				test.fail(runMessage(rawRange, result, negated));
			}
		}, CommandResultCallback::chain);
	}

	private static Component runMessage(@Nullable String range, int result, boolean negated) {
		if (range == null) {
			return Component.translatable(Assertions.getTranslationKey("run", negated));
		}

		return Component.translatable(Assertions.getTranslationKey("result", negated), range, result);
	}

	/**
	 * Executes a captured tail for one source in its own context and reports the outcome. With a
	 * forked tail the callback fires per fork: all of them must satisfy.
	 */
	private static RunOutcome runTail(
			String input,
			ContextChain<CommandSourceStack> tail,
			CommandSourceStack source,
			MinMaxBounds.@Nullable Ints range) {
		int[] fires = {0};
		int[] misses = {0};
		int[] value = {0};

		CommandSourceStack capturing = source.withCallback((success, result) -> {
			fires[0]++;
			value[0] = result;

			if (!(range == null ? success : range.matches(result))) {
				misses[0]++;
			}
		}, CommandResultCallback::chain);

		Commands.executeCommandInContext(capturing, ctx ->
				ExecutionContext.queueInitialCommandExecution(ctx, input, tail, capturing, CommandResultCallback.EMPTY));
		return new RunOutcome(fires[0] > 0 && misses[0] == 0, value[0]);
	}

	private record RunOutcome(boolean satisfied, int result) {
	}

	/**
	 * Await variant of the run condition: nothing executes when the command is reached — the
	 * parsed tail is captured and re-executed against the sources every tick. Polling starts the
	 * tick after registration, since the registration check runs inside the active execution
	 * context where a nested command cannot resolve synchronously.
	 */
	private record AwaitRun(Context assertion, boolean ranged) implements CustomModifierExecutor.ModifierAdapter<CommandSourceStack> {
		@Override
		public void apply(
				CommandSourceStack originalSource,
				List<CommandSourceStack> sources,
				ContextChain<CommandSourceStack> currentStep,
				ChainModifiers modifiers,
				ExecutionControl<CommandSourceStack> output) {
			try {
				CommandContext<CommandSourceStack> context = currentStep.getTopContext().copyFor(originalSource);
				MinMaxBounds.Ints range = this.ranged ? RangeArgument.Ints.getRange(context, "range") : null;
				String rawRange = this.ranged ? Assertions.getRawArgument(context, "range") : null;
				String input = currentStep.getTopContext().getInput();
				ContextChain<CommandSourceStack> tail = currentStep.nextStage();
				List<CommandSourceStack> captured = List.copyOf(sources);
				boolean[] registering = {true};

				this.assertion.apply(() -> {
					// An errored result keeps both await modes polling
					if (registering[0]) {
						registering[0] = false;
						return TestExecutor.AssertResult.error(runMessage(rawRange, 0, false));
					}

					int satisfied = 0;
					int result = 0;

					for (CommandSourceStack source : captured) {
						RunOutcome outcome = runTail(input, tail, source, range);
						satisfied += outcome.satisfied() ? 1 : 0;
						result = outcome.result();
					}

					int found = result;
					return new TestExecutor.AssertResult(satisfied, negated -> runMessage(rawRange, found, negated));
				});
			} catch (CommandSyntaxException e) {
				originalSource.handleError(e, modifiers.isForked(), output.tracer());
			}
		}
	}
}
