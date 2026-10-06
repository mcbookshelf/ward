package dev.mcbookshelf.ward.test;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;
import java.util.function.Consumer;
import java.util.stream.Collectors;

import net.minecraft.core.Holder;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.HolderSet;
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
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.tags.TagKey;

import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.Ward;

public class TestRegistries {
	private static final Set<ResourceKey<? extends Registry<?>>> TEST_REGISTRY_KEYS =
			Set.of(Registries.TEST_ENVIRONMENT, Registries.TEST_INSTANCE);

	private static final List<RegistryDataLoader.RegistryData<?>> TEST_REGISTRIES =
			RegistryDataLoader.WORLD_REGISTRIES.stream()
			.filter(data -> TEST_REGISTRY_KEYS.contains(data.key()))
			.toList();

	private final HolderLookup.Provider registries;

	public TestRegistries(HolderLookup.Provider registries) {
		this.registries = registries;
	}

	public static boolean owns(ResourceKey<? extends Registry<?>> registryKey) {
		return TEST_REGISTRY_KEYS.contains(registryKey);
	}

	public CompletableFuture<RegistryAccess.Frozen> load(ResourceManager manager, Executor executor) {
		return RegistryDataLoader.load(manager, this.registries.listRegistries().toList(), TEST_REGISTRIES, executor);
	}

	public void register(RegistryAccess.Frozen loaded, Map<Identifier, TestFunction> tests) {
		replace(Registries.TEST_ENVIRONMENT, loaded).freeze();
		Registry<TestEnvironmentDefinition<?>> environments = loaded.lookupOrThrow(Registries.TEST_ENVIRONMENT);

		MappedRegistry<GameTestInstance> instances = replace(Registries.TEST_INSTANCE, loaded);
		MappedRegistry<Consumer<GameTestHelper>> functions = (MappedRegistry<Consumer<GameTestHelper>>) BuiltInRegistries.TEST_FUNCTION;
		unfrozen(functions).ward$clearByPredicate(key -> functions.getValue(key) instanceof TestFunction);

		int registered = 0;

		for (Map.Entry<Identifier, TestFunction> entry : tests.entrySet()) {
			Identifier id = entry.getKey();

			try {
				register(id, entry.getValue(), instances, functions, environments);
				registered++;
			} catch (RuntimeException e) {
				Ward.LOGGER.error("Failed to load test {}", id, e);
				Reporter.loadError("ward:test", id.toString(), e);
			}
		}

		instances.freeze();
		functions.freeze();
		Ward.LOGGER.info("Loaded {} test functions", registered);
	}

	private static void register(
			Identifier id,
			TestFunction test,
			MappedRegistry<GameTestInstance> instances,
			MappedRegistry<Consumer<GameTestHelper>> functions,
			Registry<TestEnvironmentDefinition<?>> environments) {
		ResourceKey<Consumer<GameTestHelper>> functionKey = ResourceKey.create(Registries.TEST_FUNCTION, id);
		ResourceKey<GameTestInstance> instanceKey = ResourceKey.create(Registries.TEST_INSTANCE, id);

		if (!instances.containsKey(instanceKey)) {
			TestData<Holder<TestEnvironmentDefinition<?>>> data = test.directives().createTestData(environments);
			instances.register(instanceKey, new FunctionGameTestInstance(functionKey, data), RegistrationInfo.BUILT_IN);
		}

		functions.register(functionKey, test, RegistrationInfo.BUILT_IN);
	}

	private <T> MappedRegistry<T> replace(ResourceKey<Registry<T>> registryKey, RegistryAccess.Frozen source) {
		MappedRegistry<T> registry = (MappedRegistry<T>) registries.lookupOrThrow(registryKey);
		MappedRegistryAccessor<T> accessor = unfrozen(registry);
		accessor.ward$clearByPredicate(_ -> true);

		Registry<T> loaded = source.lookupOrThrow(registryKey);

		for (Holder.Reference<T> holder : loaded.listElements().toList()) {
			registry.register(holder.key(), holder.value(), RegistrationInfo.BUILT_IN);
		}

		registry.bindAllTagsToEmpty();
		registry.bindTags(rebind(loaded, registry));

		accessor.ward$adopt(loaded);
		return registry;
	}

	private static <T> Map<TagKey<T>, List<Holder<T>>> rebind(Registry<T> loaded, Registry<T> registry) {
		return loaded.getTags().collect(Collectors.toMap(
				HolderSet.Named::key,
				tag -> tag.stream().<Holder<T>>flatMap(holder -> holder.unwrapKey().flatMap(registry::get).stream()).toList()));
	}

	@SuppressWarnings("unchecked")
	private static <T> MappedRegistryAccessor<T> unfrozen(MappedRegistry<T> registry) {
		MappedRegistryAccessor<T> accessor = (MappedRegistryAccessor<T>) registry;
		accessor.ward$unfreeze();
		return accessor;
	}
}
