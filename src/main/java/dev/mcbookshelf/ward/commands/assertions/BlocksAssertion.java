package dev.mcbookshelf.ward.commands.assertions;

import java.util.OptionalInt;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.server.commands.ExecuteCommand;
import net.minecraft.server.level.ServerLevel;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;

class BlocksAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("blocks").then(Commands.argument("start", BlockPosArgument.blockPos())
				.then(Commands.argument("end", BlockPosArgument.blockPos())
						.then(Commands.argument("destination", BlockPosArgument.blockPos())
								.then(Commands.literal("all").executes(ctx -> mode.check(ctx, attempt -> check(attempt, false))))
								.then(Commands.literal("masked").executes(ctx -> mode.check(ctx, attempt -> check(attempt, true))))))));
	}

	private static AssertResult check(CommandContext<CommandSourceStack> context, boolean skipAir) throws CommandSyntaxException {
		ServerLevel level = context.getSource().getLevel();
		BlockPos start = BlockPosArgument.getLoadedBlockPos(context, "start");
		BlockPos end = BlockPosArgument.getLoadedBlockPos(context, "end");
		BlockPos destination = BlockPosArgument.getLoadedBlockPos(context, "destination");
		OptionalInt matched = ExecuteCommand.checkRegions(level, start, end, destination, skipAir);
		int count = matched.isPresent() ? Math.max(matched.getAsInt(), 1) : 0;

		return AssertResult.of(count, negated -> Messages.translatable(
				negated ? "ward.assert.not_blocks" : "ward.assert.blocks",
				start.toShortString(), end.toShortString(), destination.toShortString()));
	}
}
