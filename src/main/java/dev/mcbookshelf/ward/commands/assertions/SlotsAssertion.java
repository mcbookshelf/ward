package dev.mcbookshelf.ward.commands.assertions;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

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

import dev.mcbookshelf.ward.AssertResult;

class SlotsAssertion implements Assertion {
	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context assertion) {
		root.then(Commands.literal("slots")
				.then(Commands.literal("entity").then(Commands.argument("entities", EntityArgument.entities())
						.then(Commands.argument("slots", SlotSourceArgument.slotSource(assertion.buildContext()))
								.executes(ctx -> runForEntity(ctx, assertion)))))
				.then(Commands.literal("block").then(Commands.argument("pos", BlockPosArgument.blockPos())
						.then(Commands.argument("slots", SlotSourceArgument.slotSource(assertion.buildContext()))
								.executes(ctx -> runForBlock(ctx, assertion))))));
	}

	private static int runForEntity(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		EntitySelector selector = context.getArgument("entities", EntitySelector.class);

		return assertion.check(() -> count(context, new EntityItemAccessor(selector.findEntities(context.getSource()))));
	}

	private static int runForBlock(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		return assertion.check(() -> count(context, new BlockItemAccessor(BlockPosArgument.getLoadedBlockPos(context, "pos"))));
	}

	private static AssertResult count(CommandContext<CommandSourceStack> context, ItemAccessor<?> accessor) throws CommandSyntaxException {
		SlotSourceArgument.Result slots = SlotSourceArgument.getSlotSource(context, "slots");
		int count = ExecuteCommand.countSlots(context.getSource(), accessor, slots);

		return AssertResult.of(count, "slots", Assertion.getRawArgument(context, "slots"), count);
	}
}
