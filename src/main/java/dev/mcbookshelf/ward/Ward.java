package dev.mcbookshelf.ward;

import dev.mcbookshelf.ward.commands.*;
import dev.mcbookshelf.ward.commands.arguments.DirectionArgument;
import dev.mcbookshelf.ward.report.ReportManager;
import dev.mcbookshelf.ward.report.reporters.JUnitLikeReporter;
import net.fabricmc.api.ModInitializer;

import net.fabricmc.fabric.api.command.v2.ArgumentTypeRegistry;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.commands.synchronization.SingletonArgumentInfo;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.packs.repository.PackRepository;
import net.minecraft.world.level.storage.LevelStorageSource;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.xml.parsers.ParserConfigurationException;
import java.io.File;

/**
 * Main entrypoint for the Ward mod.
 * <p>
 * Ward is a testing framework for Minecraft data packs that integrates with
 * the GameTest framework to execute tests defined in .mcfunction files.
 */
public class Ward implements ModInitializer {

    public static final String MOD_ID = "Ward";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    public static final @Nullable String DAEMON = System.getProperty("ward.daemon");
    public static final @Nullable String REPORT = System.getProperty("ward.report");
    public static final boolean ENABLED = DAEMON != null || REPORT != null;

    @Override
    public void onInitialize() {
        // Register Ward commands argument types
        ArgumentTypeRegistry.registerArgumentType(
            Identifier.fromNamespaceAndPath("ward", "direction"),
            DirectionArgument.class,
            SingletonArgumentInfo.contextFree(DirectionArgument::new)
        );

        // Register Ward commands (fail, succeed, etc.)
        CommandRegistrationCallback.EVENT.register((dispatcher, context, _) -> {
            FailCommand.register(dispatcher, context);
            SucceedCommand.register(dispatcher, context);
            AssertCommand.register(dispatcher, context);
            AwaitCommand.register(dispatcher, context);
            DummyCommand.register(dispatcher, context);
        });
    }

    public static void runWardServer(LevelStorageSource.LevelStorageAccess storage, PackRepository packs) {
        if (REPORT != null) {
            try {
                ReportManager.register(new JUnitLikeReporter(new File(REPORT)));
            } catch (ParserConfigurationException e) {
                LOGGER.error("Failed to create JUnit reporter", e);
                System.exit(1);
            }
        }

        MinecraftServer.spin(thread -> WardServer.create(thread, storage, packs));
    }
}
