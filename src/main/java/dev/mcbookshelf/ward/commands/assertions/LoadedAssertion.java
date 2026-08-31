package dev.mcbookshelf.ward.commands.assertions;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.server.commands.ExecuteCommand;
import net.minecraft.server.level.ServerLevel;

import dev.mcbookshelf.ward.AssertResult;

class LoadedAssertion implements Assertion {
	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context assertion) {
		root.then(Commands.literal("loaded").then(Commands.argument("pos", BlockPosArgument.blockPos())
				.executes(ctx -> run(ctx, assertion))));
	}

	private static int run(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		ServerLevel level = context.getSource().getLevel();

		return assertion.check(() -> {
			BlockPos pos = BlockPosArgument.getBlockPos(context, "pos");

			return AssertResult.of(ExecuteCommand.isChunkLoaded(level, pos) ? 1 : 0, "loaded", pos.toShortString());
		});
	}
}
