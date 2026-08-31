package dev.mcbookshelf.ward.commands.assertions;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.DimensionArgument;
import net.minecraft.server.level.ServerLevel;

import dev.mcbookshelf.ward.AssertResult;

class DimensionAssertion implements Assertion {
	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context assertion) {
		root.then(Commands.literal("dimension").then(Commands.argument("dimension", DimensionArgument.dimension())
				.executes(ctx -> run(ctx, assertion))));
	}

	private static int run(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		ServerLevel level = context.getSource().getLevel();

		return assertion.check(() -> {
			ServerLevel expect = DimensionArgument.getDimension(context, "dimension");

			return AssertResult.of(expect == level ? 1 : 0, "dimension",
					expect.dimension().identifier().toString(), level.dimension().identifier().toString());
		});
	}
}
