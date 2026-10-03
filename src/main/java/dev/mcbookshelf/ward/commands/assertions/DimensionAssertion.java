package dev.mcbookshelf.ward.commands.assertions;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.DimensionArgument;
import net.minecraft.server.level.ServerLevel;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;

class DimensionAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("dimension").then(Commands.argument("dimension", DimensionArgument.dimension())
				.executes(ctx -> mode.check(ctx, DimensionAssertion::check))));
	}

	private static AssertResult check(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		ServerLevel level = context.getSource().getLevel();
		ServerLevel expect = DimensionArgument.getDimension(context, "dimension");

		return AssertResult.of(expect == level, negated -> Messages.translatable(
				negated ? "ward.assert.not_dimension" : "ward.assert.dimension",
				expect.dimension().identifier().toString(), level.dimension().identifier().toString()));
	}
}
