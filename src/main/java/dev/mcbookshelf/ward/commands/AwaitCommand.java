package dev.mcbookshelf.ward.commands;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.mcbookshelf.ward.accessor.TestContextAccessor;
import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.TimeArgument;

/**
 * The await command for waiting until conditions are met.
 */
public final class AwaitCommand {

    private AwaitCommand() {
    }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
        AssertBuilder root = new AssertBuilder(context, AssertBuilder.Mode.AWAIT_TRUE);
        AssertBuilder not = new AssertBuilder(context, AssertBuilder.Mode.AWAIT_FALSE);

        dispatcher.register(root.build(Commands.literal("await")
            .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
            .then(not.build(Commands.literal("not")))
            .then(Commands.literal("delay")
                .then(Commands.argument("time", TimeArgument.time())
                    .executes(AwaitCommand::delay)))));
    }

    private static int delay(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        int time = IntegerArgumentType.getInteger(context, "time");
        ((TestContextAccessor) context.getSource()).ward$getContext().await(time);
        return Command.SINGLE_SUCCESS;
    }
}
