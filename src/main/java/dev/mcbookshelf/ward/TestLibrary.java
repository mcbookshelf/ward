package dev.mcbookshelf.ward;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;
import com.mojang.brigadier.CommandDispatcher;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.RegistryAccess;
import net.minecraft.resources.FileToIdConverter;
import net.minecraft.resources.Identifier;
import net.minecraft.server.packs.resources.PreparableReloadListener;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.server.permissions.PermissionSet;

/**
 * Discovers test .mcfunction files on every /reload, parses them into {@link TestFunction}s and
 * hands them to {@link WardRegistries} for registration.
 */
public class TestLibrary implements PreparableReloadListener {
	private static final FileToIdConverter TEST_FUNCTION_LISTER = new FileToIdConverter("test", ".mcfunction");

	private final WardRegistries registries;
	private final PermissionSet testCompilationPermissions;
	private final CommandDispatcher<CommandSourceStack> dispatcher;

	public TestLibrary(
			HolderLookup.Provider registries,
			PermissionSet testCompilationPermissions,
			CommandDispatcher<CommandSourceStack> dispatcher) {
		this.registries = new WardRegistries(registries);
		this.testCompilationPermissions = testCompilationPermissions;
		this.dispatcher = dispatcher;
	}

	@Override
	public CompletableFuture<Void> reload(
			SharedState currentReload,
			Executor taskExecutor,
			PreparationBarrier preparationBarrier,
			Executor reloadExecutor) {
		ResourceManager manager = currentReload.resourceManager();

		// Prepare phase: load the test registries and parse every test .mcfunction in parallel
		CompletableFuture<RegistryAccess.Frozen> registryLoad = this.registries.load(manager, taskExecutor);

		CompletableFuture<Map<Identifier, CompletableFuture<TestFunction>>> testFunctions = CompletableFuture.supplyAsync(() ->
				TEST_FUNCTION_LISTER.listMatchingResources(manager), taskExecutor)
				.thenCompose(resources -> prepareTestFunctions(resources, taskExecutor));

		// Apply phase: register the freshly parsed tests on the reload thread
		return CompletableFuture.allOf(registryLoad, testFunctions)
				.thenCompose(preparationBarrier::wait)
				.thenAcceptAsync((_) ->
						this.registries.register(registryLoad.join(), collectTestFunctions(testFunctions.join())),
						reloadExecutor);
	}

	/**
	 * Parses each test .mcfunction file into a {@link TestFunction} asynchronously.
	 */
	private CompletableFuture<Map<Identifier, CompletableFuture<TestFunction>>> prepareTestFunctions(
			Map<Identifier, Resource> resources,
			Executor taskExecutor) {
		Map<Identifier, CompletableFuture<TestFunction>> result = Maps.newHashMap();
		CommandSourceStack compilationContext = Commands.createCompilationContext(this.testCompilationPermissions);

		for (Map.Entry<Identifier, Resource> entry : resources.entrySet()) {
			Identifier id = TEST_FUNCTION_LISTER.fileToId(entry.getKey());
			result.put(id, CompletableFuture.supplyAsync(() -> {
				List<String> lines = readLines(entry.getValue());
				return TestFunction.fromLines(this.dispatcher, compilationContext, lines);
			}, taskExecutor));
		}

		return CompletableFuture.allOf(result.values().toArray(new CompletableFuture[0])).handle((_, _) -> result);
	}

	/**
	 * Collects the parsed tests, reporting the ones that failed to parse.
	 */
	private static Map<Identifier, TestFunction> collectTestFunctions(Map<Identifier, CompletableFuture<TestFunction>> futures) {
		ImmutableMap.Builder<Identifier, TestFunction> result = ImmutableMap.builder();
		futures.forEach((id, future) -> future.handle((test, e) -> {
			if (e == null) {
				result.put(id, test);
			} else {
				Ward.LOGGER.error("Failed to load test {}", id, e);
				ReportManager.report(LoadDiagnostic.error("ward:test", id.toString(), LoadDiagnostic.describe(e)));
			}

			return null;
		}).join());
		return result.build();
	}

	private static List<String> readLines(Resource resource) {
		try (BufferedReader reader = resource.openAsReader()) {
			return reader.lines().toList();
		} catch (IOException e) {
			throw new UncheckedIOException(e);
		}
	}
}
