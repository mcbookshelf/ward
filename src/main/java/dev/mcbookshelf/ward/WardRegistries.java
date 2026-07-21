package dev.mcbookshelf.ward;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;
import java.util.function.Consumer;

import net.minecraft.core.Holder;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.MappedRegistry;
import net.minecraft.core.RegistrationInfo;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.FunctionGameTestInstance;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestInstance;
import net.minecraft.gametest.framework.TestData;
import net.minecraft.gametest.framework.TestEnvironmentDefinition;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.RegistryDataLoader;
import net.minecraft.resources.RegistryValidator;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.packs.resources.ResourceManager;

import dev.mcbookshelf.ward.accessor.MappedRegistryAccessor;

/**
 * Owns the contents of the {@code test_*} registries across reloads. Vanilla loads them once at
 * world load and keeps frozen references everywhere, so a reload has to refresh them in place.
 * All the unfreeze/clear/freeze mutation lives here.
 */
public class WardRegistries {
	private static final List<RegistryDataLoader.RegistryData<?>> TEST_REGISTRIES = List.of(
			new RegistryDataLoader.RegistryData<>(Registries.TEST_ENVIRONMENT, TestEnvironmentDefinition.DIRECT_CODEC, RegistryValidator.none()),
			new RegistryDataLoader.RegistryData<>(Registries.TEST_INSTANCE, GameTestInstance.DIRECT_CODEC, RegistryValidator.none()));

	private static final Set<ResourceKey<Consumer<GameTestHelper>>> registeredFunctionKeys = new HashSet<>();

	private final HolderLookup.Provider registries;

	public WardRegistries(HolderLookup.Provider registries) {
		this.registries = registries;
	}

	/**
	 * Releases the last run's test functions from the global TEST_FUNCTION registry.
	 */
	public static void release() {
		if (registeredFunctionKeys.isEmpty()) return;
		MappedRegistry<Consumer<GameTestHelper>> functions = (MappedRegistry<Consumer<GameTestHelper>>) BuiltInRegistries.TEST_FUNCTION;
		clearRegistered(functions);
		functions.freeze();
	}

	/**
	 * Loads TEST_ENVIRONMENT and TEST_INSTANCE into a throwaway access via vanilla's own
	 * {@link RegistryDataLoader}, so parsing and error reporting match a normal datapack load.
	 */
	public CompletableFuture<RegistryAccess.Frozen> load(ResourceManager manager, Executor executor) {
		return RegistryDataLoader.load(manager, this.registries.listRegistries().toList(), TEST_REGISTRIES, executor);
	}

	/**
	 * Copies the loaded environments and instances into the live registries, registers a
	 * TEST_FUNCTION per test (plus a TEST_INSTANCE for tests without JSON), and freezes all three.
	 */
	public void register(RegistryAccess.Frozen loaded, Map<Identifier, TestFunction> tests) {
		MappedRegistry<TestEnvironmentDefinition<?>> environments = replace(Registries.TEST_ENVIRONMENT, loaded);
		environments.freeze();

		// Left unfrozen until the loop below adds an instance per .mcfunction test
		MappedRegistry<GameTestInstance> instances = replace(Registries.TEST_INSTANCE, loaded);
		MappedRegistry<Consumer<GameTestHelper>> functions = (MappedRegistry<Consumer<GameTestHelper>>) registries.lookupOrThrow(Registries.TEST_FUNCTION);
		clearRegistered(functions);

		for (Map.Entry<Identifier, TestFunction> entry : tests.entrySet()) {
			Identifier id = entry.getKey();
			TestFunction test = entry.getValue();

			ResourceKey<Consumer<GameTestHelper>> functionKey = ResourceKey.create(Registries.TEST_FUNCTION, id);
			ResourceKey<GameTestInstance> instanceKey = ResourceKey.create(Registries.TEST_INSTANCE, id);

			try {
				if (!instances.containsKey(instanceKey)) {
					TestData<Holder<TestEnvironmentDefinition<?>>> testData = test.directives().createTestData(environments);
					instances.register(instanceKey, new FunctionGameTestInstance(functionKey, testData), RegistrationInfo.BUILT_IN);
				}

				functions.register(functionKey, test::run, RegistrationInfo.BUILT_IN);
				registeredFunctionKeys.add(functionKey);
			} catch (Exception e) {
				Ward.LOGGER.error("Failed to load test {}", id, e);
				ReportManager.report(LoadDiagnostic.error("ward:test", id.toString(), LoadDiagnostic.describe(e)));
			}
		}

		instances.freeze();
		functions.freeze();

		Ward.LOGGER.info("Loaded {} test functions", tests.size());
	}

	/**
	 * Drops the previous run's registrations. The registry is left unfrozen for the caller.
	 */
	private static void clearRegistered(MappedRegistry<Consumer<GameTestHelper>> functions) {
		MappedRegistryAccessor<Consumer<GameTestHelper>> accessor = unfrozen(functions);

		if (!registeredFunctionKeys.isEmpty()) {
			accessor.ward$clearByPredicate(registeredFunctionKeys::contains);
			registeredFunctionKeys.clear();
		}
	}

	/**
	 * Unfreezes a live registry, clears it, and copies in every element freshly loaded into
	 * {@code source}. The registry is returned still unfrozen and the caller decides when to
	 * freeze it.
	 */
	private <T> MappedRegistry<T> replace(ResourceKey<Registry<T>> registryKey, RegistryAccess.Frozen source) {
		MappedRegistry<T> registry = (MappedRegistry<T>) registries.lookupOrThrow(registryKey);
		unfrozen(registry).ward$clearByPredicate(_ -> true);

		for (Holder.Reference<T> holder : source.lookupOrThrow(registryKey).listElements().toList()) {
			registry.register(holder.key(), holder.value(), RegistrationInfo.BUILT_IN);
		}

		return registry;
	}

	/**
	 * Unfreezes a registry and returns it as its mutation accessor.
	 */
	@SuppressWarnings("unchecked")
	private static <T> MappedRegistryAccessor<T> unfrozen(MappedRegistry<T> registry) {
		MappedRegistryAccessor<T> accessor = (MappedRegistryAccessor<T>) registry;
		accessor.ward$unfreeze();
		return accessor;
	}
}
