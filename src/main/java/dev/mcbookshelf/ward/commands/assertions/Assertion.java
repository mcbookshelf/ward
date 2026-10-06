package dev.mcbookshelf.ward.commands.assertions;

import java.util.function.Function;
import java.util.function.Supplier;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.context.ParsedCommandNode;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.tree.ArgumentCommandNode;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.execution.EntryAction;
import net.minecraft.commands.execution.ExecutionControl;

import dev.mcbookshelf.ward.test.AssertResult;
import dev.mcbookshelf.ward.test.TestExecutor;

public interface Assertion {
	void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode);

	static String getRawArgument(CommandContext<?> ctx, String name) {
		for (ParsedCommandNode<?> node : ctx.getNodes()) {
			if (node.getNode() instanceof ArgumentCommandNode<?, ?> argNode && argNode.getName().equals(name)) {
				return node.getRange().get(ctx.getInput());
			}
		}

		throw new IllegalArgumentException("No such argument '" + name + "' exists on this command");
	}

	@FunctionalInterface
	interface Check {
		AssertResult getOrThrow(CommandContext<CommandSourceStack> context) throws CommandSyntaxException;

		default AssertResult get(CommandContext<CommandSourceStack> context) {
			try {
				return getOrThrow(context);
			} catch (CommandSyntaxException e) {
				return AssertResult.error(e);
			}
		}
	}

	record Mode(boolean immediate, boolean negated) {
		int check(CommandContext<CommandSourceStack> context, Check check) throws CommandSyntaxException {
			TestExecutor test = TestExecutor.current();
			return check(test, check.get(context), () -> check.get(context.copyFor(test.follow(context.getSource()))));
		}

		int check(TestExecutor test, AssertResult first, Supplier<AssertResult> poll) {
			if (this.immediate) return test.assertThat(first, this.negated);
			test.awaitThat(first, poll, this.negated);
			return Command.SINGLE_SUCCESS;
		}

		void check(
				TestExecutor test,
				CommandSourceStack source,
				ExecutionControl<CommandSourceStack> output,
				Function<CommandSourceStack, EntryAction<CommandSourceStack>> action,
				Supplier<AssertResult> result) {
			output.queueNext(action.apply(source));
			output.queueNext((context, frame) -> check(test, result.get(), () -> {
				CommandSourceStack live = test.follow(source);
				test.rerun(live, action.apply(live));
				return result.get();
			}));
		}
	}
}
