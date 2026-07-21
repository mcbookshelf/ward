package dev.mcbookshelf.ward.commands.assertions;

import java.util.function.Predicate;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.exceptions.Dynamic3CommandExceptionType;
import it.unimi.dsi.fastutil.ints.IntList;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.SlotsArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.commands.arguments.item.ItemPredicateArgument;
import net.minecraft.commands.arguments.selector.EntitySelector;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.Container;
import net.minecraft.world.entity.SlotAccess;
import net.minecraft.world.entity.SlotProvider;
import net.minecraft.world.inventory.SlotRange;
import net.minecraft.world.item.ItemStack;

import dev.mcbookshelf.ward.AssertResult;

class ItemsAssertion implements Assertion {
	private static final Dynamic3CommandExceptionType ERROR_SOURCE_NOT_A_CONTAINER = new Dynamic3CommandExceptionType(
			(x, y, z) -> Component.translatableEscape("commands.item.source.not_a_container", x, y, z));

	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context context) {
		root.then(Commands.literal("items")
				.then(Commands.literal("entity").then(Commands.argument("entities", EntityArgument.entities())
						.then(Commands.argument("slots", SlotsArgument.slots())
								.then(Commands.argument("predicate", ItemPredicateArgument.itemPredicate(context.buildContext()))
										.executes(ctx -> runForEntity(ctx, context))))))
				.then(Commands.literal("block").then(Commands.argument("pos", BlockPosArgument.blockPos())
						.then(Commands.argument("slots", SlotsArgument.slots())
								.then(Commands.argument("predicate", ItemPredicateArgument.itemPredicate(context.buildContext()))
										.executes(ctx -> runForBlock(ctx, context)))))));
	}

	private static int runForEntity(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		EntitySelector selector = context.getArgument("entities", EntitySelector.class);
		SlotRange slots = SlotsArgument.getSlots(context, "slots");
		Predicate<ItemStack> predicate = ItemPredicateArgument.getItemPredicate(context, "predicate");

		return assertion.apply(() -> {
			int count = countEntityItems(selector.findEntities(context.getSource()), slots, predicate);
			return AssertResult.of(count, "items", Assertion.getRawArgument(context, "predicate"), count);
		});
	}

	private static int runForBlock(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		SlotRange slots = SlotsArgument.getSlots(context, "slots");
		Predicate<ItemStack> predicate = ItemPredicateArgument.getItemPredicate(context, "predicate");

		return assertion.apply(() -> {
			BlockPos pos = BlockPosArgument.getLoadedBlockPos(context, "pos");
			int count = countBlockItems(context.getSource(), pos, slots, predicate);
			return AssertResult.of(count, "items", Assertion.getRawArgument(context, "predicate"), count);
		});
	}

	private static int countEntityItems(Iterable<? extends SlotProvider> sources, SlotRange slotRange, Predicate<ItemStack> predicate) {
		int count = 0;

		for (SlotProvider slotProvider : sources) {
			IntList slots = slotRange.slots();

			for (int i = 0; i < slots.size(); i++) {
				int slotId = slots.getInt(i);
				SlotAccess slot = slotProvider.getSlot(slotId);

				if (slot != null) {
					ItemStack contents = slot.get();

					if (predicate.test(contents)) {
						count += contents.getCount();
					}
				}
			}
		}

		return count;
	}

	private static int countBlockItems(CommandSourceStack source, BlockPos pos, SlotRange slotRange, Predicate<ItemStack> predicate) throws CommandSyntaxException {
		if (!(source.getLevel().getBlockEntity(pos) instanceof Container container)) {
			throw ERROR_SOURCE_NOT_A_CONTAINER.create(pos.getX(), pos.getY(), pos.getZ());
		}

		int count = 0;
		int size = container.getContainerSize();
		IntList slots = slotRange.slots();

		for (int i = 0; i < slots.size(); ++i) {
			int slot = slots.getInt(i);

			if (slot >= 0 && slot < size) {
				ItemStack itemStack = container.getItem(slot);

				if (predicate.test(itemStack)) {
					count += itemStack.getCount();
				}
			}
		}

		return count;
	}
}
