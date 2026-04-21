package dev.mcbookshelf.ward.commands;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.context.ParsedCommandNode;
import com.mojang.brigadier.context.StringRange;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.exceptions.Dynamic3CommandExceptionType;
import com.mojang.brigadier.tree.ArgumentCommandNode;
import dev.mcbookshelf.ward.ChatRecorder;
import dev.mcbookshelf.ward.TestContext;
import dev.mcbookshelf.ward.accessor.TestContextAccessor;
import net.minecraft.advancements.criterion.MinMaxBounds;
import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.*;
import net.minecraft.commands.arguments.blocks.BlockPredicateArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.commands.arguments.item.ItemPredicateArgument;
import net.minecraft.commands.arguments.selector.EntitySelector;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.commands.data.BlockDataAccessor;
import net.minecraft.server.commands.data.DataAccessor;
import net.minecraft.server.commands.data.DataCommands;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.SlotAccess;
import net.minecraft.world.entity.SlotProvider;
import net.minecraft.world.inventory.SlotRange;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.pattern.BlockInWorld;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.scores.Objective;
import net.minecraft.world.scores.ReadOnlyScoreInfo;
import net.minecraft.world.scores.ScoreHolder;
import net.minecraft.world.scores.Scoreboard;

import it.unimi.dsi.fastutil.ints.IntList;

import java.util.Collection;
import java.util.Optional;
import java.util.function.BiPredicate;
import java.util.function.Predicate;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Builds assertion commands for game tests with support for negation and await modes.
 * <p>
 * Immediate assertions ({@code /assert}) fail instantly when conditions aren't met.
 * Polling awaits ({@code /await}) retry every tick until timeout or success.
 * The {@link Mode} determines execution strategy and expected result.
 */
public class AssertBuilder {

    private static final Dynamic3CommandExceptionType ERROR_SOURCE_NOT_A_CONTAINER = new Dynamic3CommandExceptionType((x, y, z) -> Component.translatableEscape("commands.item.source.not_a_container", x, y, z));

    private final CommandBuildContext context;
    private final Mode mode;

    public AssertBuilder (CommandBuildContext context, Mode mode) {
        this.context = context;
        this.mode = mode;
    }

    /**
     * Registers all assertion subcommands.
     */
    public LiteralArgumentBuilder<CommandSourceStack> build(LiteralArgumentBuilder<CommandSourceStack> builder) {

        for (DataCommands.DataProvider provider : DataCommands.SOURCE_PROVIDERS) {
            builder.then(provider.wrap(Commands.literal("data"), p -> p.then(
                Commands.argument("path", NbtPathArgument.nbtPath())
                    .executes(ctx -> this.assertData(ctx, provider)))));
        }

        return builder
            .then(Commands.literal("biome")
                .then(Commands.argument("pos", BlockPosArgument.blockPos())
                    .then(Commands.argument("biome", ResourceOrTagArgument.resourceOrTag(context, Registries.BIOME))
                        .executes(this::assertBiome))))
            .then(Commands.literal("block")
                .then(Commands.argument("pos", BlockPosArgument.blockPos())
                    .then(Commands.argument("block", BlockPredicateArgument.blockPredicate(context))
                        .executes(this::assertBlock))))
            .then(Commands.literal("chat")
                .then(Commands.argument("pattern", MessageArgument.message())
                    .executes(this::assertChat)
                    .then(Commands.argument("players", EntityArgument.players())
                        .executes(this::assertChatPlayers))))
            .then(Commands.literal("entity")
                .then(Commands.argument("entities", EntityArgument.entities())
                    .executes(ctx -> this.assertEntity(ctx, false))
                    .then(Commands.literal("inside")
                        .executes(ctx -> this.assertEntity(ctx, true)))))
            .then(Commands.literal("items")
                .then(Commands.literal("entity")
                    .then(Commands.argument("entities", EntityArgument.entities())
                        .then(Commands.argument("slots", SlotsArgument.slots())
                            .then(Commands.argument("predicate", ItemPredicateArgument.itemPredicate(context))
                                .executes(this::assertItemsEntity)))))
                .then(Commands.literal("block")
                    .then(Commands.argument("pos", BlockPosArgument.blockPos())
                        .then(Commands.argument("slots", SlotsArgument.slots())
                            .then(Commands.argument("predicate", ItemPredicateArgument.itemPredicate(context))
                                .executes(this::assertItemsBlock))))))
            .then(Commands.literal("predicate")
                .then(Commands.argument("predicate", ResourceOrIdArgument.lootPredicate(context))
                    .executes(this::assertPredicate)))
            .then(Commands.literal("score")
                .then(Commands.argument("target", ScoreHolderArgument.scoreHolder())
                    .suggests(ScoreHolderArgument.SUGGEST_SCORE_HOLDERS)
                    .then(Commands.argument("target_objective", ObjectiveArgument.objective())
                        .then(buildScore(Integer::equals, "="))
                        .then(buildScore((a, b) -> a < b, "<"))
                        .then(buildScore((a, b) -> a <= b, "<="))
                        .then(buildScore((a, b) -> a > b, ">"))
                        .then(buildScore((a, b) -> a >= b, ">="))
                        .then(Commands.literal("matches")
                            .then(Commands.argument("range", RangeArgument.intRange())
                                .executes(this::assertScoreRange))))));
    }

    /**
     * Builds a score comparison subcommand for a specific operator.
     */
    private LiteralArgumentBuilder<CommandSourceStack> buildScore(BiPredicate<Integer, Integer> predicate, String op) {
        return Commands.literal(op)
            .then(Commands.argument("source", ScoreHolderArgument.scoreHolder())
                .suggests(ScoreHolderArgument.SUGGEST_SCORE_HOLDERS)
                .then(Commands.argument("source_objective", ObjectiveArgument.objective())
                    .executes(ctx -> this.assertScore(ctx, predicate, op))));
    }

    /**
     * Asserts that a biome at a position matches the expected biome or tag.
     */
    private int assertBiome(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        BlockPos pos = BlockPosArgument.getLoadedBlockPos(context, "pos");
        ResourceOrTagArgument.Result<Biome> expect = ResourceOrTagArgument.getResourceOrTag(context, "biome", Registries.BIOME);
        ServerLevel level = context.getSource().getLevel();

        return this.mode.apply(TestContextAccessor.getContext(context), () -> {
            Holder<Biome> found = level.getBiome(pos);

            return new TestContext.AssertResult(expect.test(found) ? 1 : 0, negated -> {
                String key = getTranslationKey("biome", negated);
                return Component.translatable(key, expect.asPrintable(), pos.toShortString(), found.getRegisteredName());
            });
        });
    }

    /**
     * Asserts that a block at a position matches the expected block predicate.
     */
    private int assertBlock(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        BlockPos pos = BlockPosArgument.getLoadedBlockPos(context, "pos");
        Predicate<BlockInWorld> expect = BlockPredicateArgument.getBlockPredicate(context, "block");
        ServerLevel level = context.getSource().getLevel();

        return this.mode.apply(TestContextAccessor.getContext(context), () -> {
            BlockInWorld blockInWorld = new BlockInWorld(level, pos, true);

            return new TestContext.AssertResult(expect.test(blockInWorld) ? 1 : 0, negated -> {
                String key = getTranslationKey("block", negated);
                String input = getRawArgument(context, "block");
                return Component.translatable(key, input, pos.toShortString(), getFullBlock(level, pos));
            });
        });
    }

    /**
     * Asserts that NBT data exists at the specified path.
     */
    private int assertData(CommandContext<CommandSourceStack> context, DataCommands.DataProvider provider) throws CommandSyntaxException {
        NbtPathArgument.NbtPath path = NbtPathArgument.getPath(context, "path");

        return this.mode.apply(TestContextAccessor.getContext(context), () -> {
            DataAccessor accessor = provider.access(context);
            CompoundTag data = accessor.getData();

            return new TestContext.AssertResult(path.countMatching(data), negated -> {
                String key = getTranslationKey("data", negated);
                return Component.translatable(key, path.asString(), data.toString());
            });
        });
    }

    /**
     * Asserts that chat messages matching a pattern were received.
     */
    private int assertChat(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        String patternString = MessageArgument.getMessage(context, "pattern").getString();
        Pattern pattern = Pattern.compile(patternString);

        return this.mode.apply(TestContextAccessor.getContext(context), () -> {
            int count = (int) ChatRecorder.get().stream().filter(msg -> pattern.matcher(msg).find()).count();

            return new TestContext.AssertResult(count, negated -> {
                String key = getTranslationKey("chat", negated);
                return Component.translatable(key, patternString, count);
            });
        });
    }

    /**
     * Asserts that chat messages matching a pattern were received by specific players.
     */
    private int assertChatPlayers(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        String patternString = MessageArgument.getMessage(context, "pattern").getString();
        Pattern pattern = Pattern.compile(patternString);

        return this.mode.apply(TestContextAccessor.getContext(context), () -> {
            int count = (int) EntityArgument.getPlayers(context, "players").stream()
                .flatMap(player -> ChatRecorder.get(player.getUUID()).stream())
                .filter(msg -> pattern.matcher(msg).find())
                .count();

            return new TestContext.AssertResult(count, negated -> {
                String key = getTranslationKey("chat", negated);
                return Component.translatable(key, patternString, count);
            });
        });
    }

    /**
     * Asserts that entities matching a selector exist.
     *
     * @param inside if true, only counts entities inside test bounds
     */
    private int assertEntity(CommandContext<CommandSourceStack> context, boolean inside) throws CommandSyntaxException {
        EntitySelector selector = context.getArgument("entities", EntitySelector.class);
        TestContext test = TestContextAccessor.getContext(context);
        AABB bounds = test.getBounds().inflate(1);

        return this.mode.apply(test, () -> {
            Collection<? extends Entity> entities = selector.findEntities(context.getSource());
            int count = inside
                ? (int) entities.stream().filter(e -> bounds.contains(e.position())).count()
                : entities.size();

            return new TestContext.AssertResult(count, negated -> {
                String key = getTranslationKey("entity" + (inside ? "_inside" : ""), negated);
                String input = getRawArgument(context, "entities");
                return Component.translatable(key, input, count);
            });
        });
    }

    /**
     * Asserts that a loot predicate passes when evaluated.
     */
    private int assertPredicate(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        Holder<LootItemCondition> predicate = ResourceOrIdArgument.getLootPredicate(context, "predicate");
        ServerLevel level = context.getSource().getLevel();
        Entity entity = context.getSource().getEntity();
        Vec3 pos = context.getSource().getPosition();

        return this.mode.apply(TestContextAccessor.getContext(context), () -> {
            LootParams lootParams = new LootParams.Builder(level)
                .withOptionalParameter(LootContextParams.THIS_ENTITY, entity)
                .withParameter(LootContextParams.ORIGIN, pos)
                .create(LootContextParamSets.COMMAND);
            LootContext lootContext = new LootContext.Builder(lootParams).create(Optional.empty());
            lootContext.pushVisitedElement(LootContext.createVisitedEntry(predicate.value()));

            return new TestContext.AssertResult(predicate.value().test(lootContext) ? 1 : 0, negated -> {
                String key = getTranslationKey("predicate", negated);
                return Component.translatable(key, predicate.getRegisteredName());
            });
        });
    }

    /**
     * Asserts that items matching a predicate exist in entity inventory slots.
     */
    private int assertItemsEntity(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        EntitySelector selector = context.getArgument("entities", EntitySelector.class);
        SlotRange slots = SlotsArgument.getSlots(context, "slots");
        Predicate<ItemStack> predicate = ItemPredicateArgument.getItemPredicate(context, "predicate");

        return this.mode.apply(TestContextAccessor.getContext(context), () -> {
            int count = countItems(selector.findEntities(context.getSource()), slots, predicate);

            return new TestContext.AssertResult(count, negated -> {
                String key = getTranslationKey("items", negated);
                String input = getRawArgument(context, "predicate");
                return Component.translatable(key, input, count);
            });
        });
    }

    /**
     * Asserts that items matching a predicate exist in block container slots.
     */
    private int assertItemsBlock(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        BlockPos pos = BlockPosArgument.getLoadedBlockPos(context, "pos");
        SlotRange slots = SlotsArgument.getSlots(context, "slots");
        Predicate<ItemStack> predicate = ItemPredicateArgument.getItemPredicate(context, "predicate");

        return this.mode.apply(TestContextAccessor.getContext(context), () -> {
            int count = countItems(context.getSource(), pos, slots, predicate);

            return new TestContext.AssertResult(count, negated -> {
                String key = getTranslationKey("items", negated);
                String input = getRawArgument(context, "predicate");
                return Component.translatable(key, input, count);
            });
        });
    }

    /**
     * Asserts that a scoreboard comparison between two scores holds true.
     *
     * @param op the operator symbol (=, <, <=, >, >=) used for error messages
     */
    private int assertScore(CommandContext<CommandSourceStack> context, BiPredicate<Integer, Integer> operation, String op) throws CommandSyntaxException {
        Scoreboard scoreboard = context.getSource().getServer().getScoreboard();

        return this.mode.apply(TestContextAccessor.getContext(context), () -> {
            ScoreHolder target = ScoreHolderArgument.getName(context, "target");
            ScoreHolder source = ScoreHolderArgument.getName(context, "source");
            Objective targetObjective = ObjectiveArgument.getObjective(context, "target_objective");
            Objective sourceObjective = ObjectiveArgument.getObjective(context, "source_objective");

            ReadOnlyScoreInfo targetScore = scoreboard.getPlayerScoreInfo(target, targetObjective);
            ReadOnlyScoreInfo sourceScore = scoreboard.getPlayerScoreInfo(source, sourceObjective);
            int count = (targetScore != null && sourceScore != null && operation.test(targetScore.value(), sourceScore.value())) ? 1 : 0;

            return new TestContext.AssertResult(count, negated -> Component.translatable(
                getTranslationKey("score", negated),
                target.getScoreboardName(),
                targetObjective.getName(),
                op,
                source.getScoreboardName(),
                sourceObjective.getName(),
                targetScore != null ? targetScore.value() : "undefined",
                op,
                sourceScore != null ? sourceScore.value() : "undefined"
            ));
        });
    }

    /**
     * Asserts that a score value matches the specified range.
     */
    private int assertScoreRange(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        MinMaxBounds.Ints range = RangeArgument.Ints.getRange(context, "range");
        Scoreboard scoreboard = context.getSource().getServer().getScoreboard();

        return this.mode.apply(TestContextAccessor.getContext(context), () -> {
            ScoreHolder target = ScoreHolderArgument.getName(context, "target");
            Objective targetObjective = ObjectiveArgument.getObjective(context, "target_objective");

            ReadOnlyScoreInfo scoreInfo = scoreboard.getPlayerScoreInfo(target, targetObjective);
            int count = (scoreInfo != null && range.matches(scoreInfo.value())) ? 1 : 0;

            return new TestContext.AssertResult(count, negated -> Component.translatable(
                getTranslationKey("score_range", negated),
                target.getScoreboardName(),
                targetObjective.getName(),
                range.toString(),
                scoreInfo != null ? scoreInfo.value() : "undefined"
            ));
        });
    }

    /**
     * Counts total items matching a predicate across entity inventory slots.
     */
    private static int countItems(Iterable<? extends SlotProvider> sources, SlotRange slotRange, Predicate<ItemStack> predicate) {
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

    /**
     * Counts total items matching a predicate in block container slots.
     */
    private static int countItems(CommandSourceStack source, BlockPos pos, SlotRange slotRange, Predicate<ItemStack> predicate) throws CommandSyntaxException {
        if (source.getLevel().getBlockEntity(pos) instanceof Container container) {
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
        } else {
            throw ERROR_SOURCE_NOT_A_CONTAINER.create(pos.getX(), pos.getY(), pos.getZ());
        }
    }

    /**
     * Formats a block as a string including ID, properties, and NBT data.
     *
     * @return formatted string like "minecraft:chest[facing=north]{Items:[...]}"
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

    /**
     * Extracts the original input text for a command argument.
     *
     * @return the user's input string as typed
     */
    private static String getRawArgument(CommandContext<?> ctx, String name) {
        for (ParsedCommandNode<?> node : ctx.getNodes()) {
            if (node.getNode() instanceof ArgumentCommandNode<?, ?> argNode) {
                if (argNode.getName().equals(name)) {
                    StringRange range = node.getRange();
                    return ctx.getInput().substring(range.getStart(), range.getEnd());
                }
            }
        }
        throw new IllegalArgumentException("No such argument '" + name + "' exists on this command");
    }

    /**
     * Formats a message key for an assertion type.
     */
    private static String getTranslationKey(String type, boolean negated) {
        return "ward.assert." + (negated ? "not_" : "") + type;
    }

    /**
     * Supplier that can throw CommandSyntaxException during assertion checks.
     */
    @FunctionalInterface
    private interface ResultSupplier {
        TestContext.AssertResult getOrThrow() throws CommandSyntaxException;

        default TestContext.AssertResult get() {
            try {
                return getOrThrow();
            } catch (CommandSyntaxException e) {
                return new TestContext.AssertResult(0, _ -> Component.literal(e.getMessage()));
            }
        }
    }

    /**
     * Execution modes for assertions combining negation and timing.
     */
    public enum Mode {
        /** Immediate assertion expecting count > 0. */
        ASSERT_TRUE {
            @Override int apply(TestContext test, ResultSupplier check) {
                return test.assertTrue(check::get);
            }
        },
        /** Immediate assertion expecting count == 0. */
        ASSERT_FALSE {
            @Override int apply(TestContext test, ResultSupplier check) {
                return test.assertFalse(check::get);
            }
        },
        /** Polling assertion expecting count > 0. */
        AWAIT_TRUE {
            @Override int apply(TestContext test, ResultSupplier check) {
                test.awaitTrue(check::get);
                return Command.SINGLE_SUCCESS;
            }
        },
        /** Polling assertion expecting count == 0. */
        AWAIT_FALSE {
            @Override int apply(TestContext test, ResultSupplier check) {
                test.awaitFalse(check::get);
                return Command.SINGLE_SUCCESS;
            }
        };

        /**
         * Applies this mode's execution strategy to a check.
         *
         * @return command success count (actual count for ASSERT modes, 1 for AWAIT modes)
         */
        abstract int apply(TestContext test, ResultSupplier check);
    }
}
