package dev.mcbookshelf.ward;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonIOException;
import com.google.gson.JsonObject;
import com.mojang.brigadier.CommandDispatcher;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.loader.api.FabricLoader;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.synchronization.ArgumentUtils;
import net.minecraft.data.registries.VanillaRegistries;
import net.minecraft.world.flag.FeatureFlags;

import dev.mcbookshelf.ward.commands.AssertCommand;
import dev.mcbookshelf.ward.commands.AwaitCommand;
import dev.mcbookshelf.ward.commands.DummyCommand;
import dev.mcbookshelf.ward.commands.FailCommand;
import dev.mcbookshelf.ward.commands.SucceedCommand;

public class Ward implements ModInitializer {
	public static final String MOD_ID = "ward";
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

	public static final @Nullable String PORT_FILE = System.getProperty("ward.daemon");
	public static final @Nullable String GENERATE_COMMANDS = System.getProperty("ward.generate.commands");

	public static final boolean DAEMON = PORT_FILE != null;
	public static final boolean AUDIT = Boolean.getBoolean("ward.audit");

	@Override
	public void onInitialize() {
		CommandRegistrationCallback.EVENT.register((dispatcher, context, _) -> registerCommands(dispatcher, context));
	}

	public static String version() {
		return FabricLoader.getInstance().getModContainer(MOD_ID).orElseThrow().getMetadata().getVersion().getFriendlyString();
	}

	public static void registerCommands(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
		FailCommand.register(dispatcher, context);
		SucceedCommand.register(dispatcher, context);
		AssertCommand.register(dispatcher, context);
		AwaitCommand.register(dispatcher, context);
		DummyCommand.register(dispatcher, context);
	}

	public static void exportCommandTree(Path outputDir) {
		CommandBuildContext context = CommandBuildContext.simple(
				VanillaRegistries.createReloadableLookup(VanillaRegistries.createWorldLookup()),
				FeatureFlags.DEFAULT_FLAGS);
		CommandDispatcher<CommandSourceStack> dispatcher = new CommandDispatcher<>();
		registerCommands(dispatcher, context);

		JsonObject tree = ArgumentUtils.serializeNodeToJson(dispatcher, dispatcher.getRoot());
		Path output = outputDir.resolve(version().split("\\+", 2)[0] + ".json");

		try {
			Files.createDirectories(outputDir);

			try (BufferedWriter writer = Files.newBufferedWriter(output)) {
				GSON.toJson(tree, writer);
				writer.write("\n");
			}

			LOGGER.info("Exported command tree to {}", output.toAbsolutePath());
		} catch (IOException | JsonIOException e) {
			LOGGER.error("Failed to export command tree", e);
			System.exit(-1);
		}
	}
}
