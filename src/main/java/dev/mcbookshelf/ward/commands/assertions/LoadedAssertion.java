package dev.mcbookshelf.ward.commands.assertions;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.server.commands.ExecuteCommand;
import net.minecraft.server.level.ServerLevel;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;

class LoadedAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("loaded").then(Commands.argument("pos", BlockPosArgument.blockPos())
				.executes(ctx -> mode.check(ctx, LoadedAssertion::check))));
	}

	private static AssertResult check(CommandContext<CommandSourceStack> context) {
		ServerLevel level = context.getSource().getLevel();
		BlockPos pos = BlockPosArgument.getBlockPos(context, "pos");

		return AssertResult.of(ExecuteCommand.isChunkLoaded(level, pos), negated -> Messages.translatable(
				negated ? "ward.assert.not_loaded" : "ward.assert.loaded",
				pos.toShortString()));
	}
}
