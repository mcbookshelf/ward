package dev.mcbookshelf.ward.commands;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.TimeArgument;

import dev.mcbookshelf.ward.TestExecutor;
import dev.mcbookshelf.ward.commands.assertions.Assertion;
import dev.mcbookshelf.ward.commands.assertions.Assertions;

public final class AwaitCommand {
	private AwaitCommand() {
	}

	public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
		Assertion.Context root = new Assertion.Context(dispatcher, context, false, false);
		Assertion.Context not = new Assertion.Context(dispatcher, context, false, true);

		dispatcher.register(Assertions.build(Commands.literal("await")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Assertions.build(Commands.literal("not"), not))
				.then(Commands.literal("delay").then(Commands.argument("time", TimeArgument.time())
						.executes(AwaitCommand::delay))), root));
	}

	private static int delay(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		int time = IntegerArgumentType.getInteger(context, "time");
		TestExecutor.current().await(time);
		return Command.SINGLE_SUCCESS;
	}
}
