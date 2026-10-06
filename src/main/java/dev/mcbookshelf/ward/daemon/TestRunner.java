package dev.mcbookshelf.ward.daemon;

import java.util.Collection;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.stream.Stream;

import com.google.common.base.Stopwatch;
import com.google.gson.JsonObject;
import com.mojang.brigadier.StringReader;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.serialization.DynamicOps;
import org.jspecify.annotations.Nullable;

import net.minecraft.commands.arguments.ResourceSelectorArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.RegistrySynchronization;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTestBatch;
import net.minecraft.gametest.framework.GameTestBatchFactory;
import net.minecraft.gametest.framework.GameTestBatchListener;
import net.minecraft.gametest.framework.GameTestInstance;
import net.minecraft.gametest.framework.GameTestRunner;
import net.minecraft.gametest.framework.GlobalTestReporter;
import net.minecraft.gametest.framework.StructureGridSpawner;
import net.minecraft.gametest.framework.TestEnvironmentDefinition;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.RegistryLayer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.TagNetworkSerialization;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.storage.LevelData;

import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.Ward;
import dev.mcbookshelf.ward.coverage.Coverage;

final class TestRunner implements Runner {
	private static final int TEST_POSITION_RANGE = 14999992;
	private static final int TEST_HEIGHT_ABOVE_FLOOR = 5;

	private final MinecraftServer server;
	private final Options options;
	private final TestResults results = new TestResults();
	private final Stopwatch stopwatch = Stopwatch.createUnstarted();
	private @Nullable GameTestRunner runner;

	record Options(String selector, boolean coverage) implements Runner.Options {
		static Options parse(JsonObject request) {
			return new Options(
					request.has("selector") ? request.get("selector").getAsString() : "*:*",
					request.has("coverage") && request.get("coverage").getAsBoolean());
		}
	}

	TestRunner(MinecraftServer server, Options options) {
		this.server = server;
		this.options = options;
	}

	@Override
	public boolean tick() throws CommandSyntaxException {
		if (this.runner == null) {
			this.runner = start(this.server.overworld());
			return false;
		}

		if (!this.runner.stopped) {
			return false;
		}

		long elapsed = this.stopwatch.stop().elapsed(TimeUnit.MILLISECONDS);
		Ward.LOGGER.info("Test run finished in {} ms", elapsed);

		if (Coverage.isEnabled()) {
			Reporter.send("coverage", Coverage.report());
		}

		this.results.finished(elapsed);
		return true;
	}

	private GameTestRunner start(ServerLevel overworld) throws CommandSyntaxException {
		if (Ward.AUDIT) {
			auditClientSync();
		}

		Collection<Holder.Reference<GameTestInstance>> tests = selectTests(overworld);
		reportMissingFunctions(tests);

		BlockPos startPos = pickStartPosition(overworld);
		overworld.setRespawnData(LevelData.RespawnData.of(overworld.dimension(), startPos, 0.0F, 0.0F));

		GameTestRunner runner = GameTestRunner.Builder.fromBatches(orderedBatches(tests), this.server)
				.newStructureSpawner(new StructureGridSpawner(dimension -> startPositionFor(dimension, startPos), GameTestRunner.DEFAULT_TESTS_PER_ROW, false))
				.build();
		runner.addListener(new BatchListener());

		GlobalTestReporter.replaceWith(this.results);
		this.results.started(tests.size(), startPos);
		Ward.LOGGER.info("{} tests are now running at position {}!", tests.size(), startPos.toShortString());
		this.stopwatch.start();
		runner.start();
		return runner;
	}

	private Collection<Holder.Reference<GameTestInstance>> selectTests(ServerLevel level) throws CommandSyntaxException {
		String selector = this.options.selector();
		String pattern = selector.contains(":") || selector.startsWith("#") ? selector : "*:" + selector;
		List<Holder.Reference<GameTestInstance>> tests = ResourceSelectorArgument
				.parse(new StringReader(pattern), level.registryAccess().lookupOrThrow(Registries.TEST_INSTANCE))
				.stream()
				.filter(test -> !test.key().identifier().getNamespace().equals(Identifier.DEFAULT_NAMESPACE))
				.filter(test -> !test.value().manualOnly())
				.filter(this::hasLevel)
				.toList();

		if (tests.isEmpty()) {
			throw new IllegalArgumentException("No tests found matching selector: " + selector);
		}

		return tests;
	}

	private List<GameTestBatch> orderedBatches(Collection<Holder.Reference<GameTestInstance>> tests) {
		return GameTestBatchFactory.divideIntoBatches(tests, GameTestBatchFactory.DIRECT, this.server).stream()
				.sorted(Comparator.comparing((GameTestBatch batch) -> batch.environment().getRegisteredName())
						.thenComparing(batch -> batch.dimension().identifier())
						.thenComparingInt(GameTestBatch::index))
				.toList();
	}

	private void auditClientSync() {
		DynamicOps<Tag> ops = this.server.registries().compositeAccess().createSerializationContext(NbtOps.INSTANCE);
		RegistrySynchronization.packRegistries(ops, this.server.registries().getAccessFrom(RegistryLayer.WORLD), Set.of(), (_, _) -> { });
		TagNetworkSerialization.serializeTagsToNetwork(this.server.registries());
	}

	private void reportMissingFunctions(Collection<Holder.Reference<GameTestInstance>> tests) {
		tests.stream().map(test -> test.value().batch()).distinct()
				.forEach(environment -> reportMissingFunctions(environment.getRegisteredName(), environment.value()));
	}

	private void reportMissingFunctions(String environment, TestEnvironmentDefinition<?> definition) {
		if (definition instanceof TestEnvironmentDefinition.AllOf all) {
			all.definitions().forEach(child -> reportMissingFunctions(environment, child.value()));
			return;
		}

		if (!(definition instanceof TestEnvironmentDefinition.Functions functions)) {
			return;
		}

		Stream.of(functions.setupFunction(), functions.teardownFunction())
				.flatMap(Optional::stream)
				.filter(function -> this.server.getFunctions().get(function).isEmpty())
				.forEach(function -> Reporter.loadError("minecraft:test_environment", environment, "Unknown function '" + function + "'"));
	}

	private boolean hasLevel(Holder.Reference<GameTestInstance> test) {
		ResourceKey<Level> dimension = test.value().dimension();

		if (this.server.getLevel(dimension) != null) {
			return true;
		}

		String id = test.key().identifier().toString();
		Ward.LOGGER.error("Test {} targets the unknown dimension {}", id, dimension.identifier());
		Reporter.loadError("ward:test", id, "Unknown dimension '" + dimension.identifier() + "'");
		return false;
	}

	private static BlockPos pickStartPosition(ServerLevel level) {
		RandomSource random = level.getRandom();
		int x = random.nextIntBetweenInclusive(-TEST_POSITION_RANGE, TEST_POSITION_RANGE);
		int z = random.nextIntBetweenInclusive(-TEST_POSITION_RANGE, TEST_POSITION_RANGE);
		return new BlockPos(x, 0, z);
	}

	private BlockPos startPositionFor(ResourceKey<Level> dimension, BlockPos startPos) {
		ServerLevel level = Objects.requireNonNull(this.server.getLevel(dimension));
		return new BlockPos(startPos.getX(), level.getMinY() + TEST_HEIGHT_ABOVE_FLOOR, startPos.getZ());
	}

	private final class BatchListener implements GameTestBatchListener {
		@Override
		public void testBatchStarting(GameTestBatch batch) {
			TestRunner.this.results.batchStarted(batch);
		}

		@Override
		public void testBatchFinished(GameTestBatch batch) {
			TestRunner.this.server.tickRateManager().setFrozen(false);
			TestRunner.this.results.batchFinished(batch);
		}
	}
}
