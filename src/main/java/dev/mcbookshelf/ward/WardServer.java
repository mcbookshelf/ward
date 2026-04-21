package dev.mcbookshelf.ward;

import com.google.common.base.Stopwatch;
import com.google.common.collect.Lists;
import com.google.gson.JsonObject;
import com.mojang.authlib.GameProfile;
import com.mojang.authlib.GameProfileRepository;
import com.mojang.authlib.minecraft.MinecraftSessionService;
import com.mojang.authlib.yggdrasil.ServicesKeySet;
import com.mojang.brigadier.StringReader;
import com.mojang.serialization.Lifecycle;
import net.minecraft.SystemReport;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.ResourceSelectorArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.MappedRegistry;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.*;
import net.minecraft.gizmos.GizmoCollector;
import net.minecraft.gizmos.Gizmos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.Services;
import net.minecraft.server.WorldLoader;
import net.minecraft.server.WorldStem;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.progress.LoggingLevelLoadListener;
import net.minecraft.server.notifications.EmptyNotificationService;
import net.minecraft.server.packs.repository.PackRepository;
import net.minecraft.server.permissions.LevelBasedPermissionSet;
import net.minecraft.server.permissions.PermissionSet;
import net.minecraft.server.players.NameAndId;
import net.minecraft.server.players.PlayerList;
import net.minecraft.server.players.ProfileResolver;
import net.minecraft.server.players.UserNameToIdResolver;
import net.minecraft.util.RandomSource;
import net.minecraft.util.Util;
import net.minecraft.util.datafix.DataFixers;
import net.minecraft.util.debugchart.LocalSampleLogger;
import net.minecraft.util.debugchart.SampleLogger;
import net.minecraft.world.flag.FeatureFlag;
import net.minecraft.world.flag.FeatureFlagSet;
import net.minecraft.world.flag.FeatureFlags;
import net.minecraft.world.level.DataPackConfig;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.LevelSettings;
import net.minecraft.world.level.WorldDataConfiguration;
import net.minecraft.world.level.dimension.LevelStem;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.level.levelgen.WorldDimensions;
import net.minecraft.world.level.levelgen.WorldGenSettings;
import net.minecraft.world.level.levelgen.WorldOptions;
import net.minecraft.world.level.levelgen.presets.WorldPresets;
import net.minecraft.world.level.storage.*;
import org.jspecify.annotations.Nullable;

import java.net.Proxy;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;

/**
 * Game test server that supports two operational modes:
 * <ul>
 *   <li><b>Daemon mode</b>: Persistent server that runs tests on demand via TCP bridge</li>
 *   <li><b>Report mode</b>: One-shot test execution with optional report generation</li>
 * </ul>
 */
public class WardServer extends MinecraftServer {

    private static final Services NO_SERVICES;
    private static final FeatureFlagSet ENABLED_FEATURES;
    private static final WorldOptions WORLD_OPTIONS;
    private static final int TEST_POSITION_RANGE = 14999992;
    private static final int TEST_Y_LEVEL = -59;
    private static final int STRUCTURE_GRID_SPACING = 8;

    private final LocalSampleLogger sampleLogger = new LocalSampleLogger(4);
    private final @Nullable WardDaemon daemon;

    private final Stopwatch stopwatch = Stopwatch.createUnstarted();
    private @Nullable MultipleTestTracker testTracker;

    public static WardServer create(
        Thread thread,
        LevelStorageSource.LevelStorageAccess storage,
        PackRepository packs
    ) {
        packs.reload();
        List<String> enabledPacks = new ArrayList<>(packs.getAvailableIds());
        enabledPacks.remove("vanilla");
        enabledPacks.addFirst("vanilla");

        WorldDataConfiguration config = new WorldDataConfiguration(new DataPackConfig(enabledPacks, List.of()), ENABLED_FEATURES);

        LevelSettings settings = new LevelSettings(
            "Ward Test Level",
            GameType.CREATIVE,
            LevelSettings.DifficultySettings.DEFAULT,
            true,
            config
        );

        WorldLoader.PackConfig packConfig = new WorldLoader.PackConfig(packs, config, false, true);
        WorldLoader.InitConfig initConfig = new WorldLoader.InitConfig(packConfig, Commands.CommandSelection.DEDICATED, LevelBasedPermissionSet.OWNER);

        try {
            WorldStem worldStem = Util.blockUntilDone(executor -> WorldLoader.load(initConfig, context -> {
                Registry<LevelStem> noDatapack = new MappedRegistry<>(Registries.LEVEL_STEM, Lifecycle.stable()).freeze();

                WorldDimensions dimensions = context.datapackWorldgen()
                    .lookupOrThrow(Registries.WORLD_PRESET)
                    .getOrThrow(WorldPresets.FLAT)
                    .value()
                    .createWorldDimensions();

                WorldDimensions.Complete complete = dimensions.bake(noDatapack);
                PrimaryLevelData levelData = new PrimaryLevelData(settings, complete.specialWorldProperty(), complete.lifecycle());

                return new WorldLoader.DataLoadOutput<>(
                    new LevelDataAndDimensions.WorldDataAndGenSettings(levelData, new WorldGenSettings(WORLD_OPTIONS, dimensions)),
                    complete.dimensionsRegistryAccess()
                );
            }, WorldStem::new, Util.backgroundExecutor(), executor)).get();

            return new WardServer(thread, storage, packs, worldStem);

        } catch (Exception e) {
            Ward.LOGGER.error("Failed to load datapack", e);
            System.exit(-1);
            throw new IllegalStateException();
        }
    }

    public WardServer(
        Thread serverThread,
        LevelStorageSource.LevelStorageAccess storageSource,
        PackRepository packs,
        WorldStem worldStem
    ) {
        super(
            serverThread,
            storageSource,
            packs,
            worldStem,
            Optional.of(new GameRules(ENABLED_FEATURES)),
            Proxy.NO_PROXY,
            DataFixers.getDataFixer(),
            NO_SERVICES,
            LoggingLevelLoadListener.forDedicatedServer(),
            false
        );

        // Initialize bridge only in daemon mode (Ward.DAEMON contains port file path)
        this.daemon = Ward.DAEMON != null ? new WardDaemon(this, Path.of(Ward.DAEMON).toAbsolutePath()) : null;
    }

    /**
     * Runs tests with the given selection pattern. Assumes datapacks are already loaded.
     */
    private void runTests(String selection) throws Exception {
        if (!isPaused()) throw new Exception("Tests are already running");

        ServerLevel level = this.overworld();
        Collection<Holder.Reference<GameTestInstance>> tests = ResourceSelectorArgument
            .parse(new StringReader(selection), level.registryAccess().lookupOrThrow(Registries.TEST_INSTANCE)).stream()
            .filter(test -> !test.value().manualOnly())
            .toList();

        if (tests.isEmpty()) throw new Exception("No tests found matching selector: " + selection);

        RandomSource random = level.getRandom();
        int startX = random.nextIntBetweenInclusive(-TEST_POSITION_RANGE, TEST_POSITION_RANGE);
        int startZ = random.nextIntBetweenInclusive(-TEST_POSITION_RANGE, TEST_POSITION_RANGE);
        BlockPos startPos = new BlockPos(startX, TEST_Y_LEVEL, startZ);
        level.setRespawnData(LevelData.RespawnData.of(level.dimension(), startPos, 0.0F, 0.0F));

        List<GameTestBatch> batches = GameTestBatchFactory.divideIntoBatches(tests, GameTestBatchFactory.DIRECT, level);
        GameTestRunner testRunner = GameTestRunner.Builder.fromBatches(batches, level)
            .newStructureSpawner(new StructureGridSpawner(startPos, STRUCTURE_GRID_SPACING, false))
            .build();

        testTracker = new MultipleTestTracker(testRunner.getTestInfos());
        testTracker.addListener(new WardTestListener());
        testRunner.addListener(new WardBatchListener());

        if (daemon != null) {
            JsonObject params = new JsonObject();
            params.addProperty("total", testTracker.getTotalCount());
            daemon.broadcast("tests_started", params);
        }

        stopwatch.reset();
        stopwatch.start();
        testRunner.start();
    }

    /**
     * Reloads datapacks and then runs tests. Used in daemon mode to pick up datapack changes.
     */
    public void reloadAndRunTests(String selection) throws Exception {
        if (!isPaused()) throw new Exception("Tests are already running");

        PackRepository packRepository = this.getPackRepository();
        WorldData worldData = this.getWorldData();
        packRepository.reload();
        Collection<String> currentPacks = packRepository.getSelectedIds();
        Collection<String> disabled = worldData.getDataConfiguration().dataPacks().getDisabled();

        Collection<String> packsToLoad = Lists.newArrayList(currentPacks);
        for (String pack : packRepository.getAvailableIds()) {
            if (!disabled.contains(pack) && !packsToLoad.contains(pack)) {
                packsToLoad.add(pack);
            }
        }

        try {
            this.reloadResources(packsToLoad).get();
        } catch (Exception e) {
            throw new Exception("Failed to reload datapacks: " + e.getMessage());
        }

        runTests(selection);
    }

    @Override
    protected boolean initServer() {
        this.setPlayerList(new PlayerList(this, this.registries(), this.playerDataStorage, new EmptyNotificationService()) {});
        Gizmos.withCollector(GizmoCollector.NOOP);
        this.loadLevel();

        if (daemon != null) {
            Ward.LOGGER.info("Ward server started in daemon mode");
            try {
                daemon.start();
                daemon.broadcast("ready", new JsonObject());
            } catch (Exception e) {
                Ward.LOGGER.error("Failed to start bridge", e);
                return false;
            }
        } else {
            Ward.LOGGER.info("Ward server started in report mode");
            try {
                runTests("*:*");
            } catch (Exception e) {
                Ward.LOGGER.error("Failed to start tests in report mode", e);
                return false;
            }
        }

        return true;
    }

    @Override
    protected void tickServer(BooleanSupplier haveTime) {
        super.tickServer(haveTime);
        if (testTracker != null && testTracker.isDone()) {
            stopwatch.stop();
            if (daemon != null) {
                JsonObject params = new JsonObject();
                params.addProperty("total", testTracker.getTotalCount());
                params.addProperty("passed", testTracker.getTotalCount() - testTracker.getFailedRequiredCount() - testTracker.getFailedOptionalCount());
                params.addProperty("failed", testTracker.getFailedRequiredCount() + testTracker.getFailedOptionalCount());
                params.addProperty("elapsed", formatElapsedTime(stopwatch.elapsed(TimeUnit.MILLISECONDS)));
                daemon.broadcast("tests_finished", params);
            } else {
                halt(false);
            }
        }
    }

    @Override
    protected void waitUntilNextTick() {
        this.runAllTasks();
        if (isPaused()) {
            try {
                Thread.sleep(50);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
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
    public boolean isPaused() {
        return this.testTracker == null || this.testTracker.isDone();
    }

    @Override
    public int getRateLimitPacketsPerSecond() {
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
        throw new UnsupportedOperationException("getOrThrow should be provided by mixin");
    }

    private class WardBatchListener implements GameTestBatchListener {
        @Override
        public void testBatchStarting(GameTestBatch batch) {
            if (daemon != null) {
                daemon.broadcast("batch_started", createBatchParams(batch));
            }
        }

        @Override
        public void testBatchFinished(GameTestBatch batch) {
            if (daemon != null) {
                daemon.broadcast("batch_finished", createBatchParams(batch));
            }
        }

        private JsonObject createBatchParams(GameTestBatch batch) {
            JsonObject params = new JsonObject();
            params.addProperty("batch", batch.index());
            params.addProperty("environment", batch.environment().getRegisteredName());
            return params;
        }
    }

    private class WardTestListener implements GameTestListener {
        @Override
        public void testStructureLoaded(GameTestInfo testInfo) {
            // Not needed for event broadcasting
        }

        @Override
        public void testAddedForRerun(GameTestInfo original, GameTestInfo copy, GameTestRunner runner) {
            // Not needed for event broadcasting
        }

        @Override
        public void testPassed(GameTestInfo testInfo, GameTestRunner runner) {
            if (daemon != null) {
                daemon.broadcast("test_passed", createTestParams(testInfo));
            }
        }

        @Override
        public void testFailed(GameTestInfo testInfo, GameTestRunner runner) {
            if (daemon != null) {
                daemon.broadcast("test_failed", createTestParams(testInfo));
            }
        }

        private JsonObject createTestParams(GameTestInfo testInfo) {
            JsonObject params = new JsonObject();
            params.addProperty("name", testInfo.getTestHolder().key().identifier().toString());
            params.addProperty("time", formatElapsedTime(testInfo.getRunTime()));
            if (testInfo.hasFailed() && testInfo.getError() != null) {
                params.addProperty("error", testInfo.getError().getMessage());
            }
            return params;
        }
    }

    static {
        NO_SERVICES = new Services((MinecraftSessionService) null, ServicesKeySet.EMPTY, (GameProfileRepository) null, new MockUserNameToIdResolver(), new MockProfileResolver());
        ENABLED_FEATURES = FeatureFlags.REGISTRY.allFlags().subtract(FeatureFlagSet.of(FeatureFlags.REDSTONE_EXPERIMENTS, new FeatureFlag[]{FeatureFlags.MINECART_IMPROVEMENTS}));
        WORLD_OPTIONS = new WorldOptions(0L, false, false);
    }

    private static class MockUserNameToIdResolver implements UserNameToIdResolver {
        private final Set<NameAndId> savedIds = new HashSet<>();

        private MockUserNameToIdResolver() {}

        public void add(final NameAndId nameAndId) {
            this.savedIds.add(nameAndId);
        }

        public Optional<NameAndId> get(final String name) {
            return this.savedIds.stream().filter((e) -> e.name().equals(name)).findFirst().or(() -> Optional.of(NameAndId.createOffline(name)));
        }

        public Optional<NameAndId> get(final UUID id) {
            return this.savedIds.stream().filter((e) -> e.id().equals(id)).findFirst();
        }

        public void resolveOfflineUsers(final boolean value) {}

        public void save() {}
    }

    private static class MockProfileResolver implements ProfileResolver {
        private MockProfileResolver() {}

        public Optional<GameProfile> fetchByName(final String name) {
            return Optional.empty();
        }

        public Optional<GameProfile> fetchById(final UUID id) {
            return Optional.empty();
        }
    }

    private static String formatElapsedTime(long milliseconds) {
        if (milliseconds < 1000) {
            return milliseconds + "ms";
        } else {
            return String.format("%.1fs", milliseconds / 1000.0);
        }
    }
}
