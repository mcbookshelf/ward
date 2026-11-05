package dev.mcbookshelf.ward.commands;

import java.util.Objects;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.BoolArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.ArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.suggestion.SuggestionProvider;
import org.jspecify.annotations.Nullable;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.SlotArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.commands.arguments.coordinates.Vec3Argument;
import net.minecraft.commands.arguments.selector.EntitySelector;
import net.minecraft.commands.execution.ExecutionContext;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.players.PlayerList;
import net.minecraft.util.Prediction;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.SlotAccess;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.SwingAnimation;
import net.minecraft.world.phys.Vec3;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.dummy.Dummy;
import dev.mcbookshelf.ward.test.TestExecutor;

public final class DummyCommand {
	private DummyCommand() {
	}

	private static final SuggestionProvider<CommandSourceStack> SUGGEST_NAME = (context, builder) -> {
		builder.suggest("@s");
		PlayerList playerList = context.getSource().getServer().getPlayerList();
		playerList.getPlayers().stream().filter(player -> player instanceof Dummy).forEach(player -> builder.suggest(player.getGameProfile().name()));
		return builder.buildFuture();
	};

	public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
		dispatcher.register(Commands.literal("dummy")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Commands.argument("name", EntityArgument.player()).suggests(SUGGEST_NAME)
						.then(Commands.literal("spawn").executes(asPacket(DummyCommand::spawn)))
						.then(Commands.literal("leave").executes(asPacket(DummyCommand::leave)))
						.then(Commands.literal("respawn").executes(asPacket(DummyCommand::respawn)))
						.then(Commands.literal("jump").executes(asPacket(DummyCommand::jump)))
						.then(Commands.literal("swap").executes(asPacket(DummyCommand::swap)))
						.then(Commands.literal("attack").then(Commands.argument("entity", EntityArgument.entity()).executes(asPacket(DummyCommand::attack))))
						.then(Commands.literal("mine").then(Commands.argument("pos", BlockPosArgument.blockPos()).executes(asPacket(DummyCommand::mine))))
						.then(Commands.literal("sneak").then(Commands.argument("active", BoolArgumentType.bool()).executes(asPacket(DummyCommand::sneak))))
						.then(Commands.literal("sprint").then(Commands.argument("active", BoolArgumentType.bool()).executes(asPacket(DummyCommand::sprint))))
						.then(Commands.literal("mainhand").then(Commands.argument("slot", IntegerArgumentType.integer(0, 8)).executes(asPacket(ctx -> selectSlot(ctx, 0)))))
						.then(Commands.literal("selectslot").then(Commands.argument("slot", IntegerArgumentType.integer(1, 9)).executes(asPacket(ctx -> selectSlot(ctx, 1)))))
						.then(Commands.literal("drop")
								.executes(asPacket(ctx -> dropFromMainHand(ctx, false)))
								.then(Commands.literal("all").executes(asPacket(ctx -> dropFromMainHand(ctx, true))))
								.then(Commands.literal("from").then(Commands.argument("slot", SlotArgument.slot())
										.executes(asPacket(ctx -> dropFromInventory(ctx, false)))
										.then(Commands.literal("all").executes(asPacket(ctx -> dropFromInventory(ctx, true)))))))
						.then(Commands.literal("use")
								.executes(asPacket(DummyCommand::useItem))
								.then(Commands.literal("item").executes(asPacket(DummyCommand::useItem)))
								.then(Commands.literal("block").then(useBlockDirections(Commands.argument("pos", Vec3Argument.vec3(false))
										.executes(asPacket(ctx -> useBlock(ctx, Direction.UP))))))
								.then(Commands.literal("entity").then(Commands.argument("entity", EntityArgument.entity())
										.executes(asPacket(ctx -> useEntity(ctx, null)))
										.then(Commands.argument("pos", Vec3Argument.vec3(false))
												.executes(asPacket(ctx -> useEntity(ctx, Vec3Argument.getVec3(ctx, "pos"))))))))));
	}

	private static <T extends ArgumentBuilder<CommandSourceStack, T>> T useBlockDirections(T pos) {
		for (Direction direction : Direction.values()) {
			pos.then(Commands.literal(direction.getName()).executes(asPacket(ctx -> useBlock(ctx, direction))));
		}

		return pos;
	}

	/**
	 * Runs the action like a client packet, outside the running command.
	 */
	private static Command<CommandSourceStack> asPacket(Command<CommandSourceStack> action) {
		return context -> {
			ExecutionContext<CommandSourceStack> running = Commands.CURRENT_EXECUTION_CONTEXT.get();
			Commands.CURRENT_EXECUTION_CONTEXT.set(null);

			try {
				return action.run(context);
			} finally {
				Commands.CURRENT_EXECUTION_CONTEXT.set(running);
			}
		};
	}

	private static int spawn(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		String name = getAvailableName(context);
		CommandSourceStack source = context.getSource();
		Dummy dummy = Dummy.create(name, source.getLevel(), source.getPosition(), source.getRotation());
		TestExecutor.trackDummy(dummy);
		return Command.SINGLE_SUCCESS;
	}

	private static int leave(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		getDummy(context).leave(Component.literal("Removed by command"));
		return Command.SINGLE_SUCCESS;
	}

	private static int respawn(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		if (!dummy.isDeadOrDying()) throw Messages.error("ward.dummy.not_dead", dummy.getName());
		dummy.respawn();
		return Command.SINGLE_SUCCESS;
	}

	private static int jump(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		if (!dummy.onGround()) throw Messages.error("ward.dummy.not_on_ground", dummy.getName());
		dummy.jumpFromGround();
		return Command.SINGLE_SUCCESS;
	}

	private static int swap(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		ItemStack offhandItem = dummy.getItemInHand(InteractionHand.OFF_HAND);
		dummy.setItemInHand(InteractionHand.OFF_HAND, dummy.getItemInHand(InteractionHand.MAIN_HAND));
		dummy.setItemInHand(InteractionHand.MAIN_HAND, offhandItem);
		dummy.stopUsingItem();
		return Command.SINGLE_SUCCESS;
	}

	private static int attack(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		Entity entity = EntityArgument.getEntity(context, "entity");
		dummy.attack(entity);
		dummy.swing(InteractionHand.MAIN_HAND, SwingAnimation.DEFAULT, false);
		return Command.SINGLE_SUCCESS;
	}

	private static int mine(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		BlockPos pos = BlockPosArgument.getBlockPos(context, "pos");
		if (!dummy.gameMode.destroyBlock(pos)) throw Messages.error("ward.dummy.mine_block", dummy.getName());
		return Command.SINGLE_SUCCESS;
	}

	private static int sneak(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		boolean active = BoolArgumentType.getBool(context, "active");
		if (dummy.isShiftKeyDown() == active) throw Messages.error(active ? "ward.dummy.already_sneaking" : "ward.dummy.not_sneaking", dummy.getName());
		dummy.press(active, dummy.getLastClientInput().sprint());
		return Command.SINGLE_SUCCESS;
	}

	private static int sprint(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		boolean active = BoolArgumentType.getBool(context, "active");
		if (dummy.isSprinting() == active) throw Messages.error(active ? "ward.dummy.already_sprinting" : "ward.dummy.not_sprinting", dummy.getName());
		dummy.press(dummy.getLastClientInput().shift(), active);
		dummy.setSprinting(active);
		return Command.SINGLE_SUCCESS;
	}

	/**
	 * Selects a hotbar slot counted from {@code first}: 0 for mainhand, 1 for packtest's selectslot.
	 */
	private static int selectSlot(CommandContext<CommandSourceStack> context, int first) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		int slot = IntegerArgumentType.getInteger(context, "slot");
		if (dummy.getInventory().getSelectedSlot() == slot - first) throw Messages.error("ward.dummy.already_selected", dummy.getName(), slot);
		dummy.getInventory().setSelectedSlot(slot - first);
		return Command.SINGLE_SUCCESS;
	}

	private static int dropFromMainHand(CommandContext<CommandSourceStack> context, boolean stack) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		int count = dummy.getInventory().getSelectedItem().count();
		dummy.drop(stack);
		return stack ? count : Math.min(count, 1);
	}

	private static int dropFromInventory(CommandContext<CommandSourceStack> context, boolean stack) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		Inventory inventory = dummy.getInventory();
		int slot = SlotArgument.getSlot(context, "slot");
		SlotAccess access = dummy.getSlot(slot);
		if (access == null) return 0;
		ItemStack current = access.get();
		ItemStack removed = current.split(stack ? current.count() : 1);
		access.set(current);
		dummy.containerMenu.findSlot(inventory, slot).ifPresent((i) -> dummy.containerMenu.setRemoteSlot(i, access.get()));
		dummy.drop(removed, true, Prediction.PREDICTED);
		return removed.count();
	}

	private static int useItem(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		if (!dummy.useItem()) throw Messages.error("ward.dummy.use_item", dummy.getName());
		return Command.SINGLE_SUCCESS;
	}

	private static int useBlock(CommandContext<CommandSourceStack> context, Direction direction) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		Vec3 pos = Vec3Argument.getVec3(context, "pos");
		if (!dummy.useOnBlock(pos, direction)) throw Messages.error("ward.dummy.use_on_block", dummy.getName());
		return Command.SINGLE_SUCCESS;
	}

	private static int useEntity(CommandContext<CommandSourceStack> context, @Nullable Vec3 pos) throws CommandSyntaxException {
		Dummy dummy = getDummy(context);
		Entity entity = EntityArgument.getEntity(context, "entity");
		Vec3 location = Objects.requireNonNullElseGet(pos, entity::position);
		if (!dummy.useOnEntity(entity, location)) throw Messages.error("ward.dummy.use_on_entity", dummy.getName());
		return Command.SINGLE_SUCCESS;
	}

	private static Dummy getDummy(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		ServerPlayer player = EntityArgument.getPlayer(context, "name");
		if (!(player instanceof Dummy dummy)) throw Messages.error("ward.dummy.not_dummy", player.getName());
		return dummy;
	}

	private static String getAvailableName(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		EntitySelector selector = context.getArgument("name", EntitySelector.class);
		String name = selector.playerName;
		if (name == null) throw Messages.error("ward.dummy.missing_name");
		PlayerList players = context.getSource().getServer().getPlayerList();
		if (players.getPlayerByName(name) != null) throw Messages.error("ward.dummy.name_taken", name);
		return name;
	}
}
