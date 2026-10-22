package dev.mcbookshelf.ward.commands;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.ComponentArgument;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentUtils;

import dev.mcbookshelf.ward.test.TestExecutor;

public final class LogCommand {
	private LogCommand() {
	}

	public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
		dispatcher.register(Commands.literal("log")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Commands.argument("message", ComponentArgument.textComponent(context))
						.executes(LogCommand::log)));
	}

	private static int log(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		Component message;

		try {
			message = ComponentArgument.getResolvedComponent(context, "message");
		} catch (CommandSyntaxException e) {
			message = ComponentUtils.fromMessage(e.getRawMessage());
		}

		TestExecutor.current().log(message);
		return 0;
	}
}
