package dev.mcbookshelf.ward;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonIOException;
import com.google.gson.JsonObject;
import com.mojang.brigadier.CommandDispatcher;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.ArgumentTypeRegistry;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.loader.api.FabricLoader;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.synchronization.ArgumentUtils;
import net.minecraft.commands.synchronization.SingletonArgumentInfo;
import net.minecraft.core.Direction;
import net.minecraft.data.registries.VanillaRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.world.flag.FeatureFlags;

import dev.mcbookshelf.ward.commands.AssertCommand;
import dev.mcbookshelf.ward.commands.AwaitCommand;
import dev.mcbookshelf.ward.commands.DummyCommand;
import dev.mcbookshelf.ward.commands.FailCommand;
import dev.mcbookshelf.ward.commands.SucceedCommand;
import dev.mcbookshelf.ward.commands.arguments.DirectionArgument;

public class Ward implements ModInitializer {
	public static final String MOD_ID = "ward";
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

	public static final @Nullable String DAEMON = System.getProperty("ward.daemon");
	public static final @Nullable String GENERATE_COMMANDS = System.getProperty("ward.generate.commands");

	public static final boolean ENABLED = DAEMON != null;

	@Override
	public void onInitialize() {
		ArgumentTypeRegistry.registerArgumentType(
				Identifier.fromNamespaceAndPath("ward", "direction"),
				DirectionArgument.class,
				SingletonArgumentInfo.contextFree(DirectionArgument::new));

		CommandRegistrationCallback.EVENT.register((dispatcher, context, _) -> registerCommands(dispatcher, context));
	}

	private static void registerCommands(CommandDispatcher<CommandSourceStack> dispatcher, CommandBuildContext context) {
		FailCommand.register(dispatcher, context);
		SucceedCommand.register(dispatcher, context);
		AssertCommand.register(dispatcher, context);
		AwaitCommand.register(dispatcher, context);
		DummyCommand.register(dispatcher, context);
	}

	public static void exportCommandTree() {
		CommandBuildContext context = CommandBuildContext.simple(
				VanillaRegistries.createReloadableLookup(VanillaRegistries.createWorldLookup()),
				FeatureFlags.DEFAULT_FLAGS);
		CommandDispatcher<CommandSourceStack> dispatcher = new CommandDispatcher<>();
		registerCommands(dispatcher, context);
		exportCommandTree(dispatcher, Path.of(GENERATE_COMMANDS));
	}

	private static void exportCommandTree(CommandDispatcher<CommandSourceStack> dispatcher, Path outputDir) {
		try {
			JsonObject commandTreeJson = ArgumentUtils.serializeNodeToJson(dispatcher, dispatcher.getRoot());
			inlineDirectionArguments(commandTreeJson);
			Path outputPath = outputDir.resolve(commandTreeVersion() + ".json");
			Files.createDirectories(outputDir);

			try (BufferedWriter writer = Files.newBufferedWriter(outputPath)) {
				GSON.toJson(commandTreeJson, writer);
				writer.write("\n");
			}

			LOGGER.info("Exported command tree to {}", outputPath.toAbsolutePath());
		} catch (IOException | JsonIOException e) {
			LOGGER.error("Failed to export command tree", e);
			System.exit(-1);
		}
	}

	private static void inlineDirectionArguments(JsonObject node) {
		JsonObject children = node.getAsJsonObject("children");
		if (children == null) return;

		for (String name : List.copyOf(children.keySet())) {
			JsonObject child = children.getAsJsonObject(name);
			inlineDirectionArguments(child);

			if (child.has("parser") && child.get("parser").getAsString().equals("ward:direction")) {
				children.remove(name);

				for (Direction direction : Direction.values()) {
					JsonObject literal = child.deepCopy();
					literal.remove("parser");
					literal.remove("properties");
					literal.addProperty("type", "literal");
					children.add(direction.getName(), literal);
				}
			}
		}
	}

	private static String commandTreeVersion() {
		String version = FabricLoader.getInstance()
				.getModContainer(MOD_ID)
				.orElseThrow()
				.getMetadata()
				.getVersion()
				.getFriendlyString();
		// Mc build metadata never changes the command tree
		return version.split("\\+", 2)[0];
	}
}
