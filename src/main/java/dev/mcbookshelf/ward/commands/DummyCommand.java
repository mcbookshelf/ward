package dev.mcbookshelf.ward.commands;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.BoolArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.exceptions.Dynamic2CommandExceptionType;
import com.mojang.brigadier.exceptions.DynamicCommandExceptionType;
import com.mojang.brigadier.exceptions.SimpleCommandExceptionType;
import com.mojang.brigadier.suggestion.SuggestionProvider;
import dev.mcbookshelf.ward.accessor.EntitySelectorAccessor;
import dev.mcbookshelf.ward.commands.arguments.DirectionArgument;
import dev.mcbookshelf.ward.dummy.Dummy;
import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.SlotArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.commands.arguments.coordinates.Vec3Argument;
import net.minecraft.commands.arguments.selector.EntitySelector;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.DisconnectionDetails;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.players.PlayerList;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;

import java.util.Objects;

/**
 * The dummy command for managing fake players in tests.
 */
public final class DummyCommand {

    private DummyCommand() {
    }

    public static final SimpleCommandExceptionType MISSING_NAME = new SimpleCommandExceptionType(
        Component.translatable("ward.dummy.missing_name"));
    public static final DynamicCommandExceptionType NAME_TAKEN = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.name_taken", name));
    public static final DynamicCommandExceptionType NOT_DUMMY = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.not_dummy", name));
    public static final DynamicCommandExceptionType MINE_BLOCK = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.mine_block", name));
    public static final DynamicCommandExceptionType NOT_ON_GROUND = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.not_on_ground", name));
    public static final DynamicCommandExceptionType ALREADY_SNEAKING = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.already_sneaking", name));
    public static final DynamicCommandExceptionType NOT_SNEAKING = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.not_sneaking", name));
    public static final DynamicCommandExceptionType ALREADY_SPRINTING = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.already_sprinting", name));
    public static final DynamicCommandExceptionType NOT_SPRINTING = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.not_sprinting", name));
    public static final DynamicCommandExceptionType USE_ITEM = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.use_item", name));
    public static final DynamicCommandExceptionType USE_ON_BLOCK = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.use_on_block", name));
    public static final DynamicCommandExceptionType USE_ON_ENTITY = new DynamicCommandExceptionType(name ->
        Component.translatable("ward.dummy.use_on_entity", name));
    public static final Dynamic2CommandExceptionType ALREADY_SELECTED = new Dynamic2CommandExceptionType((name, slot) ->
        Component.translatable("ward.dummy.already_selected", name, slot));

    public static final SuggestionProvider<CommandSourceStack> SUGGEST_NAME = (context, builder) -> {
        builder.suggest("@s");
        PlayerList playerList = context.getSource().getServer().getPlayerList();
        playerList.getPlayers().stream()
            .filter(p -> p instanceof Dummy)
            .forEach(p -> builder.suggest(p.getGameProfile().name()));
        return builder.buildFuture();
    };

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
        dispatcher.register(Commands.literal("dummy")
            .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
            .then(Commands.argument("name", EntityArgument.player())
                .suggests(SUGGEST_NAME)
                // dummy <name> spawn
                .then(Commands.literal("spawn").executes(DummyCommand::spawn))
                // dummy <name> leave
                .then(Commands.literal("leave").executes(DummyCommand::leave))
                // dummy <name> respawn
                .then(Commands.literal("respawn").executes(DummyCommand::respawn))
                // dummy <name> jump
                .then(Commands.literal("jump").executes(DummyCommand::jump))
                // dummy <name> swap
                .then(Commands.literal("swap").executes(DummyCommand::swap))
                // dummy <name> attack <entity>
                .then(Commands.literal("attack")
                    .then(Commands.argument("entity", EntityArgument.entity()).executes(DummyCommand::attack)))
                // dummy <name> mine <pos>
                .then(Commands.literal("mine")
                    .then(Commands.argument("pos", BlockPosArgument.blockPos()).executes(DummyCommand::mine)))
                // dummy <name> sneak <true|false>
                .then(Commands.literal("sneak")
                    .then(Commands.argument("active", BoolArgumentType.bool()).executes(DummyCommand::sneak)))
                // dummy <name> sprint <true|false>
                .then(Commands.literal("sprint")
                    .then(Commands.argument("active", BoolArgumentType.bool()).executes(DummyCommand::sprint)))
                // dummy <name> mainhand <slot>
                .then(Commands.literal("mainhand")
                    .then(Commands.argument("slot", IntegerArgumentType.integer(0, 8)).executes(DummyCommand::setMainHand)))
                // dummy <name> drop [from <slot>] [all]
                .then(Commands.literal("drop")
                    .executes(ctx -> dropFromMainHand(ctx, false))
                    .then(Commands.literal("all")
                        .executes(ctx -> dropFromMainHand(ctx, true)))
                    .then(Commands.literal("from")
                        .then(Commands.argument("slot", SlotArgument.slot())
                            .executes(ctx -> dropFromInventory(ctx, false))
                            .then(Commands.literal("all")
                                .executes(ctx -> dropFromInventory(ctx, true))))))
                // dummy <name> use [...]
                .then(Commands.literal("use").executes(DummyCommand::useItem)
                    // dummy <name> use block <pos> [<direction>]
                    .then(Commands.literal("block")
                        .then(Commands.argument("pos", Vec3Argument.vec3(false))
                            .executes(ctx -> useBlock(ctx, Direction.UP))
                            .then(Commands.argument("direction", new DirectionArgument())
                                .executes(ctx -> useBlock(ctx, ctx.getArgument("direction", Direction.class))))))
                    // dummy <name> use entity <entity> [<pos>]
                    .then(Commands.literal("entity")
                        .then(Commands.argument("entity", EntityArgument.entity())
                            .executes(ctx -> useEntity(ctx, null))
                            .then(Commands.argument("pos", Vec3Argument.vec3(false))
                                .executes(ctx -> useEntity(ctx, Vec3Argument.getVec3(ctx, "pos")))))))
            ));
    }

    private static int spawn(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        String name = getAvailableName(context);
        CommandSourceStack source = context.getSource();
        Dummy.create(name, source.getLevel(), source.getPosition(), source.getRotation());
        return Command.SINGLE_SUCCESS;
    }

    private static int leave(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Dummy dummy = getDummy(context);
        PlayerList players = context.getSource().getServer().getPlayerList();
        players.remove(dummy);
        dummy.connection.onDisconnect(new DisconnectionDetails(Component.literal("Removed by command")));
        return Command.SINGLE_SUCCESS;
    }

    private static int respawn(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Dummy dummy = getDummy(context);
        PlayerList players = context.getSource().getServer().getPlayerList();
        players.respawn(dummy, false, Entity.RemovalReason.KILLED);
        return Command.SINGLE_SUCCESS;
    }

    private static int jump(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Dummy dummy = getDummy(context);
        if (dummy.onGround()) {
            dummy.jumpFromGround();
            return Command.SINGLE_SUCCESS;
        }
        throw NOT_ON_GROUND.create(dummy.getName());
    }

    private static int swap(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Dummy dummy = getDummy(context);
        ItemStack offhandItem = dummy.getItemInHand(InteractionHand.OFF_HAND);
        dummy.setItemInHand(InteractionHand.OFF_HAND, dummy.getItemInHand(InteractionHand.MAIN_HAND));
        dummy.setItemInHand(InteractionHand.MAIN_HAND, offhandItem);
        return Command.SINGLE_SUCCESS;
    }

    private static int attack(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Dummy dummy = getDummy(context);
        Entity entity = EntityArgument.getEntity(context, "entity");
        dummy.attack(entity);
        dummy.swing(InteractionHand.MAIN_HAND);
        return Command.SINGLE_SUCCESS;
    }

    private static int mine(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Dummy dummy = getDummy(context);
        BlockPos pos = BlockPosArgument.getBlockPos(context, "pos");
        if (dummy.gameMode.destroyBlock(pos)) {
            return Command.SINGLE_SUCCESS;
        }
        throw MINE_BLOCK.create(dummy.getName());
    }

    private static int sneak(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Dummy dummy = getDummy(context);
        boolean active = BoolArgumentType.getBool(context, "active");
        if (dummy.isShiftKeyDown() != active) {
            dummy.setShiftKeyDown(active);
            return Command.SINGLE_SUCCESS;
        }
        throw (active ? ALREADY_SNEAKING : NOT_SNEAKING).create(dummy.getName());
    }

    private static int sprint(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Dummy dummy = getDummy(context);
        boolean active = BoolArgumentType.getBool(context, "active");
        if (dummy.isSprinting() != active) {
            dummy.setSprinting(active);
            return Command.SINGLE_SUCCESS;
        }
        throw (active ? ALREADY_SPRINTING : NOT_SPRINTING).create(dummy.getName());
    }

    private static int setMainHand(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Dummy dummy = getDummy(context);
        int slot = IntegerArgumentType.getInteger(context, "slot");
        if (dummy.getInventory().getSelectedSlot() != slot) {
            dummy.getInventory().setSelectedSlot(slot);
            return Command.SINGLE_SUCCESS;
        }
        throw ALREADY_SELECTED.create(dummy.getName(), slot);
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
        int count = stack ? inventory.getItem(slot).count() : 1;
        ItemStack removed = inventory.removeItem(slot, count);
        dummy.containerMenu.findSlot(inventory, slot).ifPresent((i) -> dummy.containerMenu.setRemoteSlot(i, inventory.getItem(slot)));
        dummy.drop(removed, false, false);
        return removed.count();
    }

    private static int useItem(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Dummy dummy = getDummy(context);
        for (InteractionHand hand : InteractionHand.values()) {
            ItemStack handItem = dummy.getItemInHand(hand);
            if (dummy.gameMode.useItem(dummy, dummy.level(), handItem, hand).consumesAction()) {
                return Command.SINGLE_SUCCESS;
            }
        }
        throw USE_ITEM.create(dummy.getName());
    }

    private static int useBlock(CommandContext<CommandSourceStack> ctx, Direction direction) throws CommandSyntaxException {
        Dummy dummy = getDummy(ctx);
        Vec3 pos = Vec3Argument.getVec3(ctx, "pos");
        for (InteractionHand hand : InteractionHand.values()) {
            ItemStack handItem = dummy.getItemInHand(hand);
            BlockHitResult blockHit = new BlockHitResult(pos, direction, BlockPos.containing(pos), false);
            InteractionResult result = dummy.gameMode.useItemOn(dummy, dummy.level(), handItem, hand, blockHit);
            if (result.consumesAction()) {
                dummy.swing(hand);
                return Command.SINGLE_SUCCESS;
            }
        }
        throw USE_ON_BLOCK.create(dummy.getName());
    }

    private static int useEntity(CommandContext<CommandSourceStack> ctx, Vec3 pos) throws CommandSyntaxException {
        Dummy dummy = getDummy(ctx);
        Entity entity = EntityArgument.getEntity(ctx, "entity");
        Vec3 location = Objects.requireNonNullElseGet(pos, entity::position);
        for (InteractionHand hand : InteractionHand.values()) {
            if (dummy.interactOn(entity, hand, location).consumesAction()) {
                return Command.SINGLE_SUCCESS;
            }
        }
        throw USE_ON_ENTITY.create(dummy.getName());
    }

    private static Dummy getDummy(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        ServerPlayer player = EntityArgument.getPlayer(context, "name");
        if (player instanceof Dummy dummy) return dummy;
        throw NOT_DUMMY.create(player.getName());
    }

    private static String getAvailableName(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        EntitySelector selector = context.getArgument("name", EntitySelector.class);
        String name = ((EntitySelectorAccessor) selector).ward$getPlayerName();
        if (name != null) {
            PlayerList players = context.getSource().getServer().getPlayerList();
            if (players.getPlayerByName(name) == null) return name;
            throw NAME_TAKEN.create(name);
        }
        throw MISSING_NAME.create();
    }
}
