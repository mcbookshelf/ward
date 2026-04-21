package dev.mcbookshelf.ward;

import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;
import com.mojang.brigadier.CommandDispatcher;

import dev.mcbookshelf.ward.accessor.MappedRegistryAccessor;
import dev.mcbookshelf.ward.report.ReportEntry;
import dev.mcbookshelf.ward.report.ReportManager;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.*;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.*;
import net.minecraft.resources.FileToIdConverter;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.packs.resources.PreparableReloadListener;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.server.permissions.PermissionSet;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;
import java.util.function.Consumer;

/**
 * Discovers and loads test files from data packs.
 */
public class TestLibrary implements PreparableReloadListener {

    private static final FileToIdConverter LISTER = new FileToIdConverter("test", ".mcfunction");

    private static final Set<ResourceKey<GameTestInstance>> registeredInstanceKeys = new HashSet<>();
    private static final Set<ResourceKey<Consumer<GameTestHelper>>> registeredFunctionKeys = new HashSet<>();

    private final HolderLookup.Provider registries;
    private final PermissionSet testCompilationPermissions;
    private final CommandDispatcher<CommandSourceStack> dispatcher;

    public TestLibrary(
        HolderLookup.Provider registries,
        PermissionSet testCompilationPermissions,
        CommandDispatcher<CommandSourceStack> dispatcher
    ) {
        this.registries = registries;
        this.testCompilationPermissions = testCompilationPermissions;
        this.dispatcher = dispatcher;
    }

    /**
     * Reload callback invoked when data packs are reloaded.
     * <p>
     * Discovers all matching test resources, parses them into
     * {@link TestFunction} instances, and update registries.
     */
    @Override
    public CompletableFuture<Void> reload(
        SharedState currentReload,
        Executor taskExecutor,
        PreparationBarrier preparationBarrier,
        Executor reloadExecutor
    ) {
        ResourceManager manager = currentReload.resourceManager();
        CompletableFuture<Map<Identifier, CompletableFuture<TestFunction>>> testsToReg = CompletableFuture
            .supplyAsync(() -> LISTER.listMatchingResources(manager), taskExecutor)
            .thenCompose((resources) -> {
                Map<Identifier, CompletableFuture<TestFunction>> result = Maps.newHashMap();
                CommandSourceStack compilationContext = Commands.createCompilationContext(this.testCompilationPermissions);

                for (Map.Entry<Identifier, Resource> entry : resources.entrySet()) {
                    Identifier id = LISTER.fileToId(entry.getKey());
                    result.put(id, CompletableFuture.supplyAsync(() -> {
                        List<String> lines = readLines(entry.getValue());
                        return TestFunction.fromLines(this.dispatcher, compilationContext, lines);
                    }, taskExecutor));
                }

                CompletableFuture<?>[] futuresToCollect = result.values().toArray(new CompletableFuture[0]);
                return CompletableFuture.allOf(futuresToCollect).handle((_, _) -> result);
            });

        return testsToReg.thenCompose(preparationBarrier::wait).thenAcceptAsync((futures) -> {
            var instReg = (MappedRegistry<GameTestInstance>) registries.lookupOrThrow(Registries.TEST_INSTANCE);
            var funcReg = (MappedRegistry<Consumer<GameTestHelper>>) registries.lookupOrThrow(Registries.TEST_FUNCTION);
            var envReg = (MappedRegistry<TestEnvironmentDefinition<?>>) registries.lookupOrThrow(Registries.TEST_ENVIRONMENT);

            ImmutableMap.Builder<Identifier, TestFunction> newTests = ImmutableMap.builder();
            futures.forEach((id, future) ->
                future.handle((test, e) -> {
                    if (e == null) {
                        newTests.put(id, test);
                    } else {
                        Ward.LOGGER.error("Failed to load test function {}", id, e);
                        String error = e.getMessage().replaceFirst("^[A-Za-z0-9.]+Exception: ", "");
                        ReportManager.report(ReportEntry.error("ward:test", id.toString(), error));
                    }
                    return null;
                }).join()
            );
            Map<Identifier, TestFunction> tests = newTests.build();

            @SuppressWarnings("unchecked")
            MappedRegistryAccessor<GameTestInstance> dynInstReg = (MappedRegistryAccessor<GameTestInstance>) instReg;
            dynInstReg.ward$unfreeze();
            if (!registeredInstanceKeys.isEmpty()) {
                dynInstReg.ward$clearByPredicate(registeredInstanceKeys::contains);
                registeredInstanceKeys.clear();
            }

            @SuppressWarnings("unchecked")
            MappedRegistryAccessor<Consumer<GameTestHelper>> dynFuncReg = (MappedRegistryAccessor<Consumer<GameTestHelper>>) funcReg;
            dynFuncReg.ward$unfreeze();
            if (!registeredFunctionKeys.isEmpty()) {
                dynFuncReg.ward$clearByPredicate(registeredFunctionKeys::contains);
                registeredFunctionKeys.clear();
            }

            tests.forEach((id, test) -> {
                ResourceKey<Consumer<GameTestHelper>> functionKey = ResourceKey.create(Registries.TEST_FUNCTION, id);
                ResourceKey<GameTestInstance> instanceKey = ResourceKey.create(Registries.TEST_INSTANCE, id);
                TestData<Holder<TestEnvironmentDefinition<?>>> testData = test.directives().createTestData(envReg);
                FunctionGameTestInstance instance = new FunctionGameTestInstance(functionKey, testData);
                funcReg.register(functionKey, test::run, RegistrationInfo.BUILT_IN);
                instReg.register(instanceKey, instance, RegistrationInfo.BUILT_IN);
                registeredFunctionKeys.add(functionKey);
                registeredInstanceKeys.add(instanceKey);
            });

            instReg.freeze();
            funcReg.freeze();

            Ward.LOGGER.info("Loaded {} tests", tests.size());
        }, reloadExecutor);
    }

    private static List<String> readLines(Resource resource) {
        try (BufferedReader reader = resource.openAsReader()) {
            return reader.lines().toList();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
