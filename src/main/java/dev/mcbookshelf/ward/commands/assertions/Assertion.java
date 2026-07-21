package dev.mcbookshelf.ward.commands.assertions;

import java.util.function.Supplier;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.context.ParsedCommandNode;
import com.mojang.brigadier.context.StringRange;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.tree.ArgumentCommandNode;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.ComponentUtils;

import dev.mcbookshelf.ward.AssertResult;
import dev.mcbookshelf.ward.TestExecutor;

public interface Assertion {
	/**
	 * Attaches this assertion's command nodes to the root literal.
	 */
	void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context context);

	/**
	 * Returns the raw text the user typed for an argument.
	 */
	static String getRawArgument(CommandContext<?> ctx, String name) {
		for (ParsedCommandNode<?> node : ctx.getNodes()) {
			if (node.getNode() instanceof ArgumentCommandNode<?, ?> argNode && argNode.getName().equals(name)) {
				StringRange range = node.getRange();
				return ctx.getInput().substring(range.getStart(), range.getEnd());
			}
		}

		throw new IllegalArgumentException("No such argument '" + name + "' exists on this command");
	}

	record Context(
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext buildContext,
			boolean immediate,
			boolean negated) {
		/**
		 * Runs the check now (assert) or every tick (await), depending on the mode.
		 */
		int apply(ResultSupplier check) throws CommandSyntaxException {
			TestExecutor test = TestExecutor.current();

			if (this.immediate) return test.assertThat(check::get, this.negated);
			test.awaitThat(check::get, this.negated);
			return Command.SINGLE_SUCCESS;
		}

		/**
		 * Like {@link #apply}, for a first result computed by the command engine.
		 */
		void deliver(TestExecutor test, AssertResult first, Supplier<AssertResult> poll) {
			if (this.immediate) {
				test.assertThat(first, this.negated);
			} else {
				test.awaitThat(first, this.negated, poll);
			}
		}
	}

	@FunctionalInterface
	interface ResultSupplier {
		AssertResult getOrThrow() throws CommandSyntaxException;

		default AssertResult get() {
			try {
				return getOrThrow();
			} catch (CommandSyntaxException e) {
				return AssertResult.error(ComponentUtils.fromMessage(e.getRawMessage()));
			}
		}
	}
}
