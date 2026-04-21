package dev.mcbookshelf.ward.commands;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;
import dev.mcbookshelf.ward.accessor.TestContextAccessor;
import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;

/**
 * The succeed command for explicitly succeeding a test early.
 */
public final class SucceedCommand {

    private SucceedCommand() {
    }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
        dispatcher.register(Commands.literal("succeed")
            .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
            .executes(ctx -> {
                ((TestContextAccessor) ctx.getSource()).ward$getContext().succeed();
                return Command.SINGLE_SUCCESS;
            })
        );
    }
}
