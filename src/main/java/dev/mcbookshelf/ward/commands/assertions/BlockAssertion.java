package dev.mcbookshelf.ward.commands.assertions;

import java.util.function.Predicate;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.blocks.BlockPredicateArgument;
import net.minecraft.commands.arguments.blocks.BlockStateParser;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.server.commands.data.BlockDataAccessor;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.pattern.BlockInWorld;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;

class BlockAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("block").then(Commands.argument("pos", BlockPosArgument.blockPos())
				.then(Commands.argument("block", BlockPredicateArgument.blockPredicate(context))
						.executes(ctx -> mode.check(ctx, BlockAssertion::check)))));
	}

	private static AssertResult check(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		ServerLevel level = context.getSource().getLevel();
		Predicate<BlockInWorld> expect = BlockPredicateArgument.getBlockPredicate(context, "block");
		BlockPos pos = BlockPosArgument.getLoadedBlockPos(context, "pos");
		BlockInWorld blockInWorld = new BlockInWorld(level, pos, true);

		return AssertResult.of(expect.test(blockInWorld), negated -> Messages.translatable(
				negated ? "ward.assert.not_block" : "ward.assert.block",
				Assertion.getRawArgument(context, "block"), pos.toShortString(), getFormattedBlock(level, pos)));
	}

	private static String getFormattedBlock(ServerLevel level, BlockPos pos) {
		String block = BlockStateParser.serialize(level.getBlockState(pos));
		BlockEntity entity = level.getBlockEntity(pos);

		return entity == null ? block : block + new BlockDataAccessor(entity, pos).getData();
	}
}
