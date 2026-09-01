package dev.mcbookshelf.ward.commands.assertions;

import java.util.function.Predicate;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.SlotSourceArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.commands.arguments.item.ItemPredicateArgument;
import net.minecraft.commands.arguments.selector.EntitySelector;
import net.minecraft.server.commands.ExecuteCommand;
import net.minecraft.server.commands.item.BlockItemAccessor;
import net.minecraft.server.commands.item.EntityItemAccessor;
import net.minecraft.server.commands.item.ItemAccessor;
import net.minecraft.world.item.ItemStack;

import dev.mcbookshelf.ward.AssertResult;

class ItemsAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("items")
				.then(Commands.literal("entity").then(Commands.argument("entities", EntityArgument.entities())
						.then(Commands.argument("slots", SlotSourceArgument.slotSource(context))
								.then(Commands.argument("predicate", ItemPredicateArgument.itemPredicate(context))
										.executes(ctx -> runForEntity(ctx, mode))))))
				.then(Commands.literal("block").then(Commands.argument("pos", BlockPosArgument.blockPos())
						.then(Commands.argument("slots", SlotSourceArgument.slotSource(context))
								.then(Commands.argument("predicate", ItemPredicateArgument.itemPredicate(context))
										.executes(ctx -> runForBlock(ctx, mode)))))));
	}

	private static int runForEntity(CommandContext<CommandSourceStack> context, Mode mode) throws CommandSyntaxException {
		EntitySelector selector = context.getArgument("entities", EntitySelector.class);

		return mode.check(() -> count(context, new EntityItemAccessor(selector.findEntities(context.getSource()))));
	}

	private static int runForBlock(CommandContext<CommandSourceStack> context, Mode mode) throws CommandSyntaxException {
		return mode.check(() -> count(context, new BlockItemAccessor(BlockPosArgument.getLoadedBlockPos(context, "pos"))));
	}

	private static AssertResult count(CommandContext<CommandSourceStack> context, ItemAccessor<?> accessor) throws CommandSyntaxException {
		SlotSourceArgument.Result slots = SlotSourceArgument.getSlotSource(context, "slots");
		Predicate<ItemStack> predicate = ItemPredicateArgument.getItemPredicate(context, "predicate");
		int count = ExecuteCommand.countItems(context.getSource(), accessor, slots, predicate);

		return AssertResult.of(count, "items", Assertion.getRawArgument(context, "predicate"), count);
	}
}
