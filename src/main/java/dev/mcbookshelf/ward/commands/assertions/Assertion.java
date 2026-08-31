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
	void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context assertion);

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
		int check(ResultSupplier check) throws CommandSyntaxException {
			return check(TestExecutor.current(), check.get(), check::get);
		}

		/**
		 * Like {@link #check(ResultSupplier)}, for a first result already computed by the command engine.
		 */
		int check(TestExecutor test, AssertResult first, Supplier<AssertResult> poll) {
			if (this.immediate) return test.assertThat(first, this.negated);
			test.awaitThat(first, poll, this.negated);
			return Command.SINGLE_SUCCESS;
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
