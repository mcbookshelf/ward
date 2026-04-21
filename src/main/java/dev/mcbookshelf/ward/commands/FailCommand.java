package dev.mcbookshelf.ward.commands;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.mcbookshelf.ward.TestContext;
import dev.mcbookshelf.ward.accessor.TestContextAccessor;
import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.ComponentArgument;
import net.minecraft.network.chat.Component;

/**
 * The fail command for explicitly failing a test.
 */
public final class FailCommand {

    private FailCommand() {
    }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
        dispatcher.register(Commands.literal("fail")
            .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
            .executes(FailCommand::failWithoutMessage)
            .then(Commands.argument("message", ComponentArgument.textComponent(context))
                .executes(FailCommand::failWithMessage))
        );
    }

    private static int failWithMessage(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        TestContext test = ((TestContextAccessor) context.getSource()).ward$getContext();
        test.fail(ComponentArgument.getResolvedComponent(context, "message"));
        return 0;
    }

    private static int failWithoutMessage(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        ((TestContextAccessor) context.getSource()).ward$getContext().fail(Component.translatable("ward.fail"));
        return 0;
    }
}
