package dev.mcbookshelf.ward;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.ArgumentTypeRegistry;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import net.minecraft.commands.synchronization.SingletonArgumentInfo;
import net.minecraft.resources.Identifier;

import dev.mcbookshelf.ward.commands.AssertCommand;
import dev.mcbookshelf.ward.commands.AwaitCommand;
import dev.mcbookshelf.ward.commands.DummyCommand;
import dev.mcbookshelf.ward.commands.FailCommand;
import dev.mcbookshelf.ward.commands.SucceedCommand;
import dev.mcbookshelf.ward.commands.arguments.DirectionArgument;

public class Ward implements ModInitializer {
	public static final String MOD_ID = "ward";
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	public static final @Nullable String DAEMON = System.getProperty("ward.daemon");
	public static final boolean ENABLED = DAEMON != null;

	@Override
	public void onInitialize() {
		ArgumentTypeRegistry.registerArgumentType(
				Identifier.fromNamespaceAndPath("ward", "direction"),
				DirectionArgument.class,
				SingletonArgumentInfo.contextFree(DirectionArgument::new));

		CommandRegistrationCallback.EVENT.register((dispatcher, context, _) -> {
			FailCommand.register(dispatcher, context);
			SucceedCommand.register(dispatcher, context);
			AssertCommand.register(dispatcher, context);
			AwaitCommand.register(dispatcher, context);
			DummyCommand.register(dispatcher, context);
		});
	}
}
