package dev.mcbookshelf.ward.commands.assertions;

import java.util.function.Predicate;
import java.util.stream.Collectors;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.blocks.BlockPredicateArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.commands.data.BlockDataAccessor;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.pattern.BlockInWorld;
import net.minecraft.world.level.block.state.properties.Property;

import dev.mcbookshelf.ward.AssertResult;

class BlockAssertion implements Assertion {
	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context context) {
		root.then(Commands.literal("block").then(Commands.argument("pos", BlockPosArgument.blockPos())
				.then(Commands.argument("block", BlockPredicateArgument.blockPredicate(context.buildContext()))
						.executes(ctx -> run(ctx, context)))));
	}

	private static int run(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		ServerLevel level = context.getSource().getLevel();
		Predicate<BlockInWorld> expect = BlockPredicateArgument.getBlockPredicate(context, "block");

		return assertion.apply(() -> {
			BlockPos pos = BlockPosArgument.getLoadedBlockPos(context, "pos");
			BlockInWorld blockInWorld = new BlockInWorld(level, pos, true);

			return AssertResult.of(expect.test(blockInWorld) ? 1 : 0, "block",
					Assertion.getRawArgument(context, "block"), pos.toShortString(), getFullBlock(level, pos));
		});
	}

	/**
	 * Formats a block like {@code minecraft:chest[facing=north]{Items:[...]}}.
	 */
	private static String getFullBlock(ServerLevel level, BlockPos pos) {
		BlockState state = level.getBlockState(pos);
		BlockEntity entity = level.getBlockEntity(pos);

		StringBuilder result = new StringBuilder(BuiltInRegistries.BLOCK.wrapAsHolder(state.getBlock()).getRegisteredName());
		String props = state.getValues().map(Property.Value::toString).collect(Collectors.joining(","));

		if (!props.isEmpty()) result.append('[').append(props).append(']');
		if (entity != null) result.append(new BlockDataAccessor(entity, pos).getData());

		return result.toString();
	}
}
