package dev.mcbookshelf.ward.commands.assertions;

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
import net.minecraft.commands.arguments.selector.EntitySelector;
import net.minecraft.server.commands.ExecuteCommand;
import net.minecraft.server.commands.item.BlockItemAccessor;
import net.minecraft.server.commands.item.EntityItemAccessor;
import net.minecraft.server.commands.item.ItemAccessor;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;

class SlotsAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("slots")
				.then(Commands.literal("entity").then(Commands.argument("entities", EntityArgument.entities())
						.then(Commands.argument("slots", SlotSourceArgument.slotSource(context))
								.executes(ctx -> mode.check(ctx, SlotsAssertion::countForEntity)))))
				.then(Commands.literal("block").then(Commands.argument("pos", BlockPosArgument.blockPos())
						.then(Commands.argument("slots", SlotSourceArgument.slotSource(context))
								.executes(ctx -> mode.check(ctx, SlotsAssertion::countForBlock))))));
	}

	private static AssertResult countForBlock(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		return count(context, new BlockItemAccessor(BlockPosArgument.getLoadedBlockPos(context, "pos")));
	}

	private static AssertResult countForEntity(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		EntitySelector selector = context.getArgument("entities", EntitySelector.class);

		return count(context, new EntityItemAccessor(selector.findEntities(context.getSource())));
	}

	private static AssertResult count(CommandContext<CommandSourceStack> context, ItemAccessor<?> accessor) throws CommandSyntaxException {
		SlotSourceArgument.Result slots = SlotSourceArgument.getSlotSource(context, "slots");
		int count = ExecuteCommand.countSlots(context.getSource(), accessor, slots);

		return AssertResult.of(count, negated -> Messages.translatable(
				negated ? "ward.assert.not_slots" : "ward.assert.slots",
				Assertion.getRawArgument(context, "slots"), count));
	}
}
