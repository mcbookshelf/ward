package dev.mcbookshelf.ward;

import java.net.Proxy;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;

import com.google.common.base.Stopwatch;
import com.mojang.brigadier.StringReader;
import com.mojang.serialization.Lifecycle;

import net.minecraft.CrashReport;
import net.minecraft.SystemReport;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.ResourceSelectorArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.MappedRegistry;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTestBatch;
import net.minecraft.gametest.framework.GameTestBatchFactory;
import net.minecraft.gametest.framework.GameTestBatchListener;
import net.minecraft.gametest.framework.GameTestInstance;
import net.minecraft.gametest.framework.GameTestRunner;
import net.minecraft.gametest.framework.GameTestTicker;
import net.minecraft.gametest.framework.StructureGridSpawner;
import net.minecraft.gizmos.GizmoCollector;
import net.minecraft.gizmos.Gizmos;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.WorldLoader;
import net.minecraft.server.WorldStem;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.progress.LoggingLevelLoadListener;
import net.minecraft.server.notifications.EmptyNotificationService;
import net.minecraft.server.notifications.NotificationManager;
import net.minecraft.server.packs.repository.PackRepository;
import net.minecraft.server.permissions.LevelBasedPermissionSet;
import net.minecraft.server.permissions.PermissionSet;
import net.minecraft.server.players.NameAndId;
import net.minecraft.server.players.PlayerList;
import net.minecraft.util.RandomSource;
import net.minecraft.util.Util;
import net.minecraft.util.datafix.DataFixers;
import net.minecraft.util.debugchart.LocalSampleLogger;
import net.minecraft.util.debugchart.SampleLogger;
import net.minecraft.world.flag.FeatureFlagSet;
import net.minecraft.world.flag.FeatureFlags;
import net.minecraft.world.level.DataPackConfig;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelSettings;
import net.minecraft.world.level.WorldDataConfiguration;
import net.minecraft.world.level.dimension.LevelStem;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.level.levelgen.WorldDimensions;
import net.minecraft.world.level.levelgen.WorldGenSettings;
import net.minecraft.world.level.levelgen.WorldOptions;
import net.minecraft.world.level.levelgen.presets.WorldPresets;
import net.minecraft.world.level.storage.LevelData;
import net.minecraft.world.level.storage.LevelDataAndDimensions;
import net.minecraft.world.level.storage.LevelStorageSource;
import net.minecraft.world.level.storage.PrimaryLevelData;

/**
 * Headless game test server for a single run. It boots a fresh world, runs the selected tests
 * and halts. The {@link WardDaemon} creates one instance per run.
 */
public class WardServer extends MinecraftServer {
	private static final FeatureFlagSet ENABLED_FEATURES = FeatureFlags.REGISTRY.allFlags().subtract(FeatureFlagSet.of(FeatureFlags.REDSTONE_EXPERIMENTS, FeatureFlags.MINECART_IMPROVEMENTS));
	private static final WorldOptions WORLD_OPTIONS = new WorldOptions(0L, false, false);
	private static final int TEST_POSITION_RANGE = 14999992;
	private static final int TEST_HEIGHT_ABOVE_FLOOR = 5;
	private static final int STRUCTURE_GRID_SPACING = 8;

	private final LocalSampleLogger sampleLogger = new LocalSampleLogger(4);
	private final Stopwatch stopwatch = Stopwatch.createUnstarted();
	private final WardDaemon daemon;
	private final String selection;
	private boolean started;

	public static WardServer create(
			WardDaemon daemon,
			Thread thread,
			LevelStorageSource.LevelStorageAccess storage,
			PackRepository packs,
			String selection) {
		packs.reload();
		WorldDataConfiguration config = new WorldDataConfiguration(
				new DataPackConfig(selectPacks(packs), List.of()),
				ENABLED_FEATURES);

		LevelSettings settings = new LevelSettings(
				"Ward Test Level",
				GameType.CREATIVE,
				LevelSettings.DifficultySettings.DEFAULT,
				true,
				config);

		WorldLoader.PackConfig packConfig = new WorldLoader.PackConfig(
				packs,
				config,
				false,
				true);
		WorldLoader.InitConfig initConfig = new WorldLoader.InitConfig(
				packConfig,
				Commands.CommandSelection.DEDICATED,
				LevelBasedPermissionSet.OWNER);

		try {
			WorldStem worldStem = Util.blockUntilDone(executor -> WorldLoader.load(initConfig, context -> {
				Registry<LevelStem> noDatapack = new MappedRegistry<>(Registries.LEVEL_STEM, Lifecycle.stable()).freeze();

				WorldDimensions dimensions = context.datapackWorldRegistries()
						.lookupOrThrow(Registries.WORLD_PRESET)
						.getOrThrow(WorldPresets.FLAT)
						.value()
						.createWorldDimensions();

				WorldDimensions.Complete complete = dimensions.bake(noDatapack);
				PrimaryLevelData levelData = new PrimaryLevelData(
						settings,
						complete.specialWorldProperty(),
						complete.lifecycle());

				return new WorldLoader.DataLoadOutput<>(
						new LevelDataAndDimensions.WorldDataAndGenSettings(levelData, new WorldGenSettings(WORLD_OPTIONS, dimensions)),
						complete.dimensionsRegistryAccess());
			}, WorldStem::new, Util.backgroundExecutor(), executor)).get();

			return new WardServer(daemon, thread, storage, packs, worldStem, selection);
		} catch (Exception e) {
			// Propagates to WardDaemon.boot, which reports the failure to clients
			throw new RuntimeException("Failed to load datapacks: " + LoadDiagnostic.describe(e), e);
		}
	}

	private WardServer(
			WardDaemon daemon,
			Thread serverThread,
			LevelStorageSource.LevelStorageAccess storageSource,
			PackRepository packs,
			WorldStem worldStem,
			String selection) {
		super(
				serverThread,
				storageSource,
				packs,
				worldStem,
				Optional.of(new GameRules(ENABLED_FEATURES)),
				Proxy.NO_PROXY,
				DataFixers.getDataFixer(),
				WardServices.OFFLINE,
				LoggingLevelLoadListener.forDedicatedServer(),
				false,
				new NotificationManager());
		this.daemon = daemon;
		this.selection = selection;
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
				// Nothing is persisted: no playerdata, stats or advancements, dummies included
			}
		});
		Gizmos.withCollector(GizmoCollector.NOOP);
		this.loadLevel();

		// The world only lives in memory. The vanilla shutdown path resets this flag and
		// still tries to save, but IOWorkerMixin and SavedDataStorageMixin drop the writes
		for (ServerLevel level : this.getAllLevels()) {
			level.noSave = true;
		}

		Ward.LOGGER.info("Ward test server started");
		return true;
	}

	@Override
	public boolean saveAllChunks(boolean silent, boolean flush, boolean force) {
		// Nothing is persisted. This skips chunks, level.dat, scoreboard and
		// saved data, for autosaves and the shutdown save alike
		return true;
	}

	@Override
	protected void tickServer(BooleanSupplier haveTime) {
		super.tickServer(haveTime);

		if (!this.started) {
			try {
				startTests(this.overworld());
			} catch (Exception e) {
				this.daemon.reportFailure(e);
				this.halt(false);
			}

			return;
		}

		if (ReportManager.isRunComplete()) {
			this.stopwatch.stop();
			long elapsed = this.stopwatch.elapsed(TimeUnit.MILLISECONDS);

			Ward.LOGGER.info("Test run finished in {}", formatMillis(elapsed));
			ReportManager.runFinished(elapsed);

			GameTestTicker.SINGLETON.clear();
			this.halt(false);
		}
	}

	/**
	 * Runs the tests matching the selection pattern. The run only finishes once every test has
	 * reported a final result, so flaky reruns settle before the server halts.
	 */
	private void startTests(ServerLevel level) throws Exception {
		GameTestTicker.SINGLETON.clear();
		Collection<Holder.Reference<GameTestInstance>> tests = ResourceSelectorArgument
				.parse(new StringReader(this.selection), level.registryAccess().lookupOrThrow(Registries.TEST_INSTANCE))
				.stream()
				.filter(test -> !test.key().identifier().getNamespace().equals(Identifier.DEFAULT_NAMESPACE))
				.filter(test -> !test.value().manualOnly())
				.toList();

		if (tests.isEmpty()) {
			throw new Exception("No tests found matching selector: " + this.selection);
		}

		BlockPos startPos = pickStartPosition(level);
		level.setRespawnData(LevelData.RespawnData.of(level.dimension(), startPos, 0.0F, 0.0F));

		List<GameTestBatch> batches = GameTestBatchFactory.divideIntoBatches(tests, GameTestBatchFactory.DIRECT, this);
		GameTestRunner runner = GameTestRunner.Builder.fromBatches(batches, this)
				.newStructureSpawner(new StructureGridSpawner(dimension -> startPositionFor(dimension, startPos), STRUCTURE_GRID_SPACING, false))
				.build();

		runner.addListener(new BatchListener());
		ReportManager.runStarted(tests.size(), startPos);

		Ward.LOGGER.info("{} tests are now running at position {}!", tests.size(), startPos.toShortString());
		this.stopwatch.reset();
		this.stopwatch.start();
		runner.start();
		this.started = true;
	}

	@Override
	protected void waitUntilNextTick() {
		this.runAllTasks();
	}

	@Override
	protected void onServerExit() {
		super.onServerExit();
		WardRegistries.release();
		ChatRecorder.clear();
		this.daemon.serverExited();
	}

	@Override
	protected void onServerCrash(CrashReport report) {
		super.onServerCrash(report);
		// The daemon outlives this instance, so clients must hear about the crash
		this.daemon.reportFailure(report.getException());
	}

	private static List<String> selectPacks(PackRepository packs) {
		List<String> enabledPacks = new ArrayList<>(packs.getAvailableIds());
		enabledPacks.remove("vanilla");
		enabledPacks.addFirst("vanilla");
		return enabledPacks;
	}

	/**
	 * Picks a random position far from previous runs so structures never overlap.
	 */
	private static BlockPos pickStartPosition(ServerLevel level) {
		RandomSource random = level.getRandom();
		int x = random.nextIntBetweenInclusive(-TEST_POSITION_RANGE, TEST_POSITION_RANGE);
		int z = random.nextIntBetweenInclusive(-TEST_POSITION_RANGE, TEST_POSITION_RANGE);
		return new BlockPos(x, 0, z);
	}

	/**
	 * Anchors a dimension's test grid at the shared {@code x}/{@code z}, just above that
	 * dimension's floor. Dimensions are separate levels, so they cannot overlap.
	 */
	private BlockPos startPositionFor(ResourceKey<Level> dimension, BlockPos startPos) {
		ServerLevel level = this.getLevel(dimension);
		int y = level != null ? level.getMinY() + TEST_HEIGHT_ABOVE_FLOOR : startPos.getY();
		return new BlockPos(startPos.getX(), y, startPos.getZ());
	}

	private static String formatMillis(long milliseconds) {
		if (milliseconds < 1000) {
			return milliseconds + "ms";
		} else {
			return String.format("%.1fs", milliseconds / 1000.0);
		}
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
	public SystemReport fillServerSystemReport(final SystemReport systemReport) {
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
		// Fabric API injects this method into MinecraftServer and implements it at runtime,
		// but javac still demands an override. Data resources are never used on this server
		throw new UnsupportedOperationException("Data resources are unsupported on the ward server");
	}

	private static class BatchListener implements GameTestBatchListener {
		@Override
		public void testBatchStarting(GameTestBatch batch) {
			ReportManager.batchStarted(batch.index(), batch.environment().getRegisteredName(), batch.dimension().identifier().toString());
		}

		@Override
		public void testBatchFinished(GameTestBatch batch) {
			ReportManager.batchFinished(batch.index(), batch.environment().getRegisteredName(), batch.dimension().identifier().toString());
		}
	}
}
