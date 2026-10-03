package dev.mcbookshelf.ward.test;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;

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

import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.Ward;

public class TestLibrary implements PreparableReloadListener {
	private static final FileToIdConverter TEST_FUNCTION_LISTER = new FileToIdConverter("test", ".mcfunction");

	private final TestRegistries registries;
	private final PermissionSet testCompilationPermissions;
	private final CommandDispatcher<CommandSourceStack> dispatcher;

	public TestLibrary(
			HolderLookup.Provider registries,
			PermissionSet testCompilationPermissions,
			CommandDispatcher<CommandSourceStack> dispatcher) {
		this.registries = new TestRegistries(registries);
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
		CompletableFuture<RegistryAccess.Frozen> registryLoad = this.registries.load(manager, taskExecutor);
		CompletableFuture<Map<Identifier, TestFunction>> tests = CompletableFuture.supplyAsync(() -> parse(manager), taskExecutor);

		return CompletableFuture.allOf(registryLoad, tests)
				.thenCompose(preparationBarrier::wait)
				.thenAcceptAsync((_) -> this.registries.register(registryLoad.join(), tests.join()), reloadExecutor);
	}

	private Map<Identifier, TestFunction> parse(ResourceManager manager) {
		CommandSourceStack compilationContext = Commands.createCompilationContext(this.testCompilationPermissions);
		Map<Identifier, TestFunction> tests = new ConcurrentHashMap<>();

		TEST_FUNCTION_LISTER.listMatchingResources(manager).entrySet().parallelStream().forEach(entry -> {
			Identifier id = TEST_FUNCTION_LISTER.fileToId(entry.getKey());

			try {
				tests.put(id, TestFunction.fromLines(this.dispatcher, compilationContext, readLines(entry.getValue())));
			} catch (RuntimeException e) {
				Ward.LOGGER.error("Failed to load test {}", id, e);
				Reporter.loadError("ward:test", id.toString(), e);
			}
		});

		return tests;
	}

	private static List<String> readLines(Resource resource) {
		try (BufferedReader reader = resource.openAsReader()) {
			return reader.lines().toList();
		} catch (IOException e) {
			throw new UncheckedIOException(e);
		}
	}
}
