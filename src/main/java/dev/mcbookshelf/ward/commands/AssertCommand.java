package dev.mcbookshelf.ward.commands;

import com.mojang.brigadier.CommandDispatcher;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;

import dev.mcbookshelf.ward.commands.assertions.Assertion;
import dev.mcbookshelf.ward.commands.assertions.Assertions;

public final class AssertCommand {
	private AssertCommand() {
	}

	public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
		Assertion.Context root = new Assertion.Context(dispatcher, context, true, false);
		Assertion.Context not = new Assertion.Context(dispatcher, context, true, true);

		dispatcher.register(Assertions.build(Commands.literal("assert")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Assertions.build(Commands.literal("not"), not)), root));
	}
}
