package dev.mcbookshelf.ward.commands;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;

import dev.mcbookshelf.ward.TestExecutor;

public final class SucceedCommand {
	private SucceedCommand() {
	}

	public static void register(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
		dispatcher.register(Commands.literal("succeed")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(_ -> {
					TestExecutor.current().succeed();
					return Command.SINGLE_SUCCESS;
				}));
	}
}
