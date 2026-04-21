package dev.mcbookshelf.ward.commands;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;

/**
 * The assert command for testing conditions in Ward tests.
 */
public final class AssertCommand {

    private AssertCommand() {
    }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
        AssertBuilder root = new AssertBuilder(context, AssertBuilder.Mode.ASSERT_TRUE);
        AssertBuilder not = new AssertBuilder(context, AssertBuilder.Mode.ASSERT_FALSE);

        dispatcher.register(root.build(Commands.literal("assert")
            .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
            .then(not.build(Commands.literal("not")))));
    }
}
