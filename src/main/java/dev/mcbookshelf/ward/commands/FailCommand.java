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

import dev.mcbookshelf.ward.TestExecutor;

public final class FailCommand {
	private FailCommand() {
	}

	public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
		dispatcher.register(Commands.literal("fail")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(_ -> fail(Component.translatable("ward.fail")))
				.then(Commands.argument("message", ComponentArgument.textComponent(context))
						.executes(FailCommand::failWithArgument)));
	}

	private static int fail(Component message) throws CommandSyntaxException {
		TestExecutor.current().fail(message);
		return 0;
	}

	private static int failWithArgument(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		try {
			return fail(ComponentArgument.getResolvedComponent(context, "message"));
		} catch (CommandSyntaxException e) {
			return fail(ComponentUtils.fromMessage(e.getRawMessage()));
		}
	}
}
