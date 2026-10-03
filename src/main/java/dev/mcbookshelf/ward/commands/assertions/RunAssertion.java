package dev.mcbookshelf.ward.commands.assertions;

import java.util.List;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.context.ContextChain;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import org.jspecify.annotations.Nullable;

import net.minecraft.advancements.predicates.MinMaxBounds;
import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandResultCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.RangeArgument;
import net.minecraft.commands.execution.ChainModifiers;
import net.minecraft.commands.execution.CustomModifierExecutor;
import net.minecraft.commands.execution.EntryAction;
import net.minecraft.commands.execution.ExecutionControl;
import net.minecraft.commands.execution.TraceCallbacks;
import net.minecraft.commands.execution.tasks.BuildContexts;
import net.minecraft.commands.execution.tasks.FallthroughTask;
import net.minecraft.commands.execution.tasks.IsolatedCall;
import net.minecraft.resources.Identifier;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;
import dev.mcbookshelf.ward.test.TestExecutor;

class RunAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(buildRun(dispatcher, mode, false));
		root.then(Commands.literal("result")
				.then(Commands.argument("range", RangeArgument.intRange())
						.then(buildRun(dispatcher, mode, true))));
	}

	private static LiteralArgumentBuilder<CommandSourceStack> buildRun(
			CommandDispatcher<CommandSourceStack> dispatcher,
			Mode mode,
			boolean ranged) {
		return Commands.literal("run").fork(dispatcher.getRoot(), new AssertRun(mode, ranged));
	}

	private record AssertRun(Mode mode, boolean ranged) implements CustomModifierExecutor.ModifierAdapter<CommandSourceStack> {
		@Override
		public void apply(
				CommandSourceStack originalSource,
				List<CommandSourceStack> sources,
				ContextChain<CommandSourceStack> currentStep,
				ChainModifiers modifiers,
				ExecutionControl<CommandSourceStack> output) {
			if (sources.isEmpty()) return;

			try {
				TestExecutor test = TestExecutor.current();
				CommandContext<CommandSourceStack> context = currentStep.getTopContext().copyFor(originalSource);
				Tally tally = this.ranged
						? new Tally(test, RangeArgument.Ints.getRange(context, "range"), Assertion.getRawArgument(context, "range"))
						: new Tally(test, null, null);
				ChainModifiers unforked = modifiers.isReturn() ? ChainModifiers.DEFAULT.setReturn() : ChainModifiers.DEFAULT;
				Tail tail = new Tail(context.getInput(), currentStep.nextStage(), unforked, sources, tally);

				this.mode.check(test, originalSource, output, tail::run, tally::result);
			} catch (CommandSyntaxException e) {
				originalSource.handleError(e, false, output.tracer());
			}
		}
	}

	private record Tail(
			String input,
			ContextChain<CommandSourceStack> chain,
			ChainModifiers modifiers,
			List<CommandSourceStack> sources,
			Tally tally) {
		EntryAction<CommandSourceStack> run(CommandSourceStack original) {
			List<CommandSourceStack> counted = this.sources.stream().map(this.tally::counting).toList();

			return new IsolatedCall<>(control -> {
				this.tally.reset();
				control.tracer(this.tally);
				control.queueNext(new BuildContexts.Continuation<>(this.input, this.chain, this.modifiers, original, counted));
				control.queueNext(FallthroughTask.instance());
			}, CommandResultCallback.EMPTY);
		}
	}

	private static final class Tally implements TraceCallbacks {
		private final TestExecutor test;
		private final MinMaxBounds.@Nullable Ints range;
		private final @Nullable String rawRange;
		private int fires;
		private int misses;
		private int shown;
		private @Nullable String lastError;

		Tally(TestExecutor test, MinMaxBounds.@Nullable Ints range, @Nullable String rawRange) {
			this.test = test;
			this.range = range;
			this.rawRange = rawRange;
		}

		CommandSourceStack counting(CommandSourceStack source) {
			return this.test.follow(source).withCallback((success, result) -> {
				this.fires++;
				boolean miss = !(this.range == null ? success : this.range.matches(result));

				if (this.misses == 0) {
					this.shown = result;
				}

				if (miss) {
					this.misses++;
				}
			}, CommandResultCallback::chain);
		}

		void reset() {
			this.fires = 0;
			this.misses = 0;
			this.shown = 0;
			this.lastError = null;
		}

		AssertResult result() {
			boolean satisfied = this.fires > 0 && this.misses == 0;

			if (this.rawRange != null) {
				return this.fires == 0
						? AssertResult.of(false, _ -> Messages.translatable("ward.assert.result_none", this.rawRange))
						: AssertResult.of(satisfied, negated -> Messages.translatable(
								negated ? "ward.assert.not_result" : "ward.assert.result",
								this.rawRange, this.shown));
			}

			String error = satisfied ? null : this.lastError;

			return error == null
					? AssertResult.of(satisfied, negated -> Messages.translatable(negated ? "ward.assert.not_run" : "ward.assert.run"))
					: AssertResult.of(false, _ -> Messages.translatable("ward.assert.run_error", error));
		}

		@Override
		public void onError(String message) {
			this.lastError = message;
		}

		@Override
		public void onCommand(int depth, String command) {
		}

		@Override
		public void onReturn(int depth, String command, int result) {
		}

		@Override
		public void onCall(int depth, Identifier function, int size) {
		}

		@Override
		public void close() {
		}
	}
}
