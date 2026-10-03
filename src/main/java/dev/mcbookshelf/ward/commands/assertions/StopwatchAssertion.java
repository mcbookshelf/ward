package dev.mcbookshelf.ward.commands.assertions;

import java.util.Locale;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.advancements.predicates.MinMaxBounds;
import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.IdentifierArgument;
import net.minecraft.commands.arguments.RangeArgument;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.commands.StopwatchCommand;
import net.minecraft.world.Stopwatch;
import net.minecraft.world.Stopwatches;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;

class StopwatchAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("stopwatch").then(Commands.argument("id", IdentifierArgument.id())
				.suggests(StopwatchCommand.SUGGEST_STOPWATCHES)
				.then(Commands.argument("range", RangeArgument.floatRange())
						.executes(ctx -> mode.check(ctx, StopwatchAssertion::check)))));
	}

	private static AssertResult check(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		MinecraftServer server = context.getSource().getServer();
		MinMaxBounds.Doubles range = RangeArgument.Floats.getRange(context, "range");
		Identifier id = IdentifierArgument.getId(context, "id");
		Stopwatch stopwatch = server.getStopwatches().get(id);
		if (stopwatch == null) throw StopwatchCommand.ERROR_DOES_NOT_EXIST.create(id);

		double elapsed = stopwatch.elapsedSeconds(Stopwatches.currentTime());

		return AssertResult.of(range.matches(elapsed), negated -> Messages.translatable(
				negated ? "ward.assert.not_stopwatch" : "ward.assert.stopwatch",
				id.toString(), Assertion.getRawArgument(context, "range"), String.format(Locale.ROOT, "%.2f", elapsed)));
	}
}
