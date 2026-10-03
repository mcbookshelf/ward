package dev.mcbookshelf.ward.daemon;

import java.net.Proxy;
import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.ForkJoinPool;
import java.util.function.BooleanSupplier;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import org.jspecify.annotations.Nullable;

import net.minecraft.CrashReport;
import net.minecraft.SystemReport;
import net.minecraft.commands.Commands;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTestTicker;
import net.minecraft.gizmos.GizmoCollector;
import net.minecraft.gizmos.Gizmos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.WorldLoader;
import net.minecraft.server.WorldStem;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.progress.LoggingLevelLoadListener;
import net.minecraft.server.notifications.EmptyNotificationService;
import net.minecraft.server.notifications.NotificationManager;
import net.minecraft.server.packs.repository.PackRepository;
import net.minecraft.server.permissions.LevelBasedPermissionSet;
import net.minecraft.server.permissions.PermissionSet;
import net.minecraft.server.players.NameAndId;
import net.minecraft.server.players.PlayerList;
import net.minecraft.util.Util;
import net.minecraft.util.datafix.DataFixers;
import net.minecraft.util.debugchart.LocalSampleLogger;
import net.minecraft.util.debugchart.SampleLogger;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.LevelSettings;
import net.minecraft.world.level.WorldDataConfiguration;
import net.minecraft.world.level.levelgen.WorldDimensions;
import net.minecraft.world.level.levelgen.WorldGenSettings;
import net.minecraft.world.level.levelgen.WorldOptions;
import net.minecraft.world.level.levelgen.presets.WorldPreset;
import net.minecraft.world.level.levelgen.presets.WorldPresets;
import net.minecraft.world.level.storage.LevelDataAndDimensions;
import net.minecraft.world.level.storage.LevelStorageSource;
import net.minecraft.world.level.storage.PrimaryLevelData;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.Ward;

public class WardServer extends MinecraftServer {
	private static final WorldOptions WORLD_OPTIONS = new WorldOptions(0L, false, false);

	private final LocalSampleLogger sampleLogger = new LocalSampleLogger(4);
	private final WardDaemon daemon;
	private final Runner.Options options;
	private @Nullable Runner runner;
	private boolean ended;
	private @Nullable Throwable failure;

	static WardServer create(
			WardDaemon daemon,
			Thread thread,
			LevelStorageSource.LevelStorageAccess storage,
			PackRepository packs,
			Runner.Options options) {
		WorldLoader.PackConfig packConfig = new WorldLoader.PackConfig(packs, WorldDataConfiguration.DEFAULT, false, true);
		WorldLoader.InitConfig initConfig = new WorldLoader.InitConfig(
				packConfig,
				Commands.CommandSelection.DEDICATED,
				LevelBasedPermissionSet.OWNER);

		try {
			WorldStem worldStem = Util.blockUntilDone(executor ->
					WorldLoader.load(initConfig, WardServer::createWorld, WorldStem::new, Util.backgroundExecutor(), executor)).get();
			return new WardServer(daemon, thread, storage, packs, worldStem, options);
		} catch (Exception e) {
			throw new RuntimeException("Failed to load datapacks: " + Messages.describe(e), e);
		}
	}

	private static WorldLoader.DataLoadOutput<LevelDataAndDimensions.WorldDataAndGenSettings> createWorld(WorldLoader.DataLoadContext context) {
		HolderLookup.RegistryLookup<WorldPreset> presets = context.datapackWorldRegistries().lookupOrThrow(Registries.WORLD_PRESET);
		WorldDimensions dimensions = presets.getOrThrow(WorldPresets.FLAT_ALL_DIMENSIONS).value().createWorldDimensions()
				.replaceOverworldGenerator(
						context.datapackWorldRegistries(),
						presets.getOrThrow(WorldPresets.FLAT).value().createWorldDimensions().overworld());
		WorldDimensions.Complete complete = dimensions.bake(context.datapackDimensions().lookupOrThrow(Registries.LEVEL_STEM));

		LevelSettings settings = new LevelSettings(
				"Ward Test Level",
				GameType.CREATIVE,
				LevelSettings.DifficultySettings.DEFAULT,
				true,
				context.dataConfiguration());
		PrimaryLevelData levelData = new PrimaryLevelData(settings, complete.specialWorldProperty(), complete.lifecycle());

		return new WorldLoader.DataLoadOutput<>(
				new LevelDataAndDimensions.WorldDataAndGenSettings(levelData, new WorldGenSettings(WORLD_OPTIONS, dimensions)),
				complete.dimensionsRegistryAccess());
	}

	private WardServer(
			WardDaemon daemon,
			Thread serverThread,
			LevelStorageSource.LevelStorageAccess storageSource,
			PackRepository packs,
			WorldStem worldStem,
			Runner.Options options) {
		super(
				serverThread,
				storageSource,
				packs,
				worldStem,
				Optional.empty(),
				Proxy.NO_PROXY,
				DataFixers.getDataFixer(),
				WardServices.offline(),
				LoggingLevelLoadListener.forDedicatedServer(),
				false,
				new NotificationManager());
		this.daemon = daemon;
		this.options = options;
	}

	@Override
	protected boolean initServer() {
		this.setPlayerList(new PlayerList(
				this,
				this.registries(),
				this.playerDataStorage,
				new EmptyNotificationService()) {
			@Override
			protected void save(ServerPlayer player) {
			}
		});
		Gizmos.withCollector(GizmoCollector.NOOP);

		this.loadLevel();

		this.setAutoSave(false);

		Ward.LOGGER.info("Ward test server started");
		return true;
	}

	@Override
	public boolean saveAllChunks(boolean silent, boolean flush, boolean force) {
		return true;
	}

	@Override
	protected void tickServer(BooleanSupplier haveTime) {
		if (this.daemon.clientGone()) {
			Ward.LOGGER.info("The client disconnected, stopping the run");
			this.ended = true;
			this.halt(false);
			return;
		}

		super.tickServer(haveTime);

		if (!this.tickRateManager().runsNormally()) {
			GameTestTicker.SINGLETON.tick();
		}

		try {
			if (this.runner == null) {
				this.runner = switch (this.options) {
					case TestRunner.Options tests -> new TestRunner(this, tests);
					case BenchRunner.Options bench -> new BenchRunner(this, bench);
				};
			}

			if (this.runner.tick()) {
				this.ended = true;
				this.halt(false);
			}
		} catch (CommandSyntaxException | RuntimeException e) {
			this.failure = e;
			this.halt(false);
		}
	}

	@Override
	protected void waitUntilNextTick() {
		if (!this.isRunning() || !(Util.backgroundExecutor().service() instanceof ForkJoinPool workers)) {
			this.runAllTasks();
			return;
		}

		long deadline = Util.getNanos() + this.tickRateManager().nanosecondsPerTick();
		this.managedBlock(() -> {
			this.runAllTasks();
			return workers.isQuiescent() || Util.getNanos() >= deadline;
		});
	}

	@Override
	protected void stopServer() {
		try {
			GameTestTicker.SINGLETON.clear();
		} finally {
			super.stopServer();
		}
	}

	@Override
	protected void onServerExit() {
		try {
			super.onServerExit();
		} finally {
			this.daemon.runEnded(this.ended ? null : Objects.requireNonNullElseGet(
					this.failure,
					() -> new IllegalStateException("Server stopped before the run finished")));
		}
	}

	@Override
	protected void onServerCrash(CrashReport report) {
		super.onServerCrash(report);
		this.daemon.crashed(report.getException());
	}

	@Override
	public LevelBasedPermissionSet operatorUserPermissions() {
		return LevelBasedPermissionSet.OWNER;
	}

	@Override
	public PermissionSet getFunctionCompilationPermissions() {
		return LevelBasedPermissionSet.OWNER;
	}

	@Override
	public boolean shouldRconBroadcast() {
		return false;
	}

	@Override
	protected SampleLogger getTickTimeLogger() {
		return this.sampleLogger;
	}

	@Override
	public boolean isTickTimeLoggingEnabled() {
		return false;
	}

	@Override
	public SystemReport fillServerSystemReport(SystemReport systemReport) {
		systemReport.setDetail("Type", "Ward Server");
		return systemReport;
	}

	@Override
	public boolean isDedicatedServer() {
		return false;
	}

	@Override
	public int getRateLimitPacketsPerSecond() {
		return 0;
	}

	@Override
	public int getCommandSpamThresholdSeconds() {
		return 0;
	}

	@Override
	public int getChatSpamThresholdSeconds() {
		return 0;
	}

	@Override
	public boolean useNativeTransport() {
		return false;
	}

	@Override
	public boolean isPublished() {
		return false;
	}

	@Override
	public boolean shouldInformAdmins() {
		return false;
	}

	@Override
	public boolean isSingleplayerOwner(NameAndId nameAndId) {
		return false;
	}

	@Override
	public int getMaxPlayers() {
		return 1;
	}

	@Override
	public <T> T getOrThrow(Key<T> key) {
		throw new UnsupportedOperationException("Data resources are unsupported on the ward server");
	}
}
