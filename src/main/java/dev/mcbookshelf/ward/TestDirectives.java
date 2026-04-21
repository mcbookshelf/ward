package dev.mcbookshelf.ward;

import com.mojang.brigadier.StringReader;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.minecraft.commands.arguments.coordinates.Coordinates;
import net.minecraft.commands.arguments.coordinates.Vec3Argument;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTestEnvironments;
import net.minecraft.gametest.framework.TestData;
import net.minecraft.gametest.framework.TestEnvironmentDefinition;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.block.Rotation;
import org.jspecify.annotations.Nullable;

import java.util.Optional;

/**
 * Parsed directives from a test file header.
 * <p>
 * TestDirectives are specified as comments in the format: # @directive value
 *
 * @param template    The structure template ID (default: minecraft:empty)
 * @param environment The test environment ID (default: minecraft:default)
 * @param timeout     Maximum ticks before timeout (default: 100)
 * @param optional    If true, failure doesn't fail the test run (default: false)
 * @param skyAccess   If true, test has sky access (default: false)
 * @param dummy       Position to spawn a dummy player, if specified
 */
public record TestDirectives(
    Identifier template,
    Identifier environment,
    int timeout,
    boolean optional,
    boolean skyAccess,
    Optional<Coordinates> dummy
) {

    public static final TestDirectives DEFAULTS = new TestDirectives(
        Identifier.withDefaultNamespace("empty"),
        GameTestEnvironments.DEFAULT_KEY.identifier(),
        100,
        false,
        false,
        Optional.empty()
    );

    public TestData<Holder<TestEnvironmentDefinition<?>>> createTestData(Registry<TestEnvironmentDefinition<?>> environments) {
        return new TestData<>(
            environments.getOrThrow(ResourceKey.create(Registries.TEST_ENVIRONMENT, this.environment)),
            this.template,
            this.timeout,
            0,
            !this.optional,
            Rotation.NONE,
            false,
            1,
            1,
            this.skyAccess,
            0
        );
    }

    /**
     * Builder for constructing TestDirectives.
     */
    public static class Builder {
        private Identifier template = DEFAULTS.template();
        private Identifier environment = DEFAULTS.environment();
        private int timeout = DEFAULTS.timeout();
        private boolean optional = DEFAULTS.optional();
        private boolean skyAccess = DEFAULTS.skyAccess();
        private @Nullable Coordinates dummy = null;

        public void add(String name, @Nullable String value) {
            switch (name.toLowerCase()) {
                case "optional" -> this.optional = value == null || Boolean.parseBoolean(value.trim());
                case "skyaccess" -> this.skyAccess = value == null || Boolean.parseBoolean(value.trim());
                case "timeout" -> {
                    if (value == null) throw new IllegalStateException("Missing value");
                    this.timeout = Integer.parseInt(value.trim());
                }
                case "template" -> {
                    if (value == null) throw new IllegalArgumentException("Missing value");
                    this.template = Identifier.parse(value.trim());
                }
                case "environment" -> {
                    if (value == null) throw new IllegalArgumentException("Missing value");
                    this.environment = Identifier.parse(value.trim());
                }
                case "dummy" -> {
                    try {
                        if (value == null) value = "~.5 ~ ~.5";
                        this.dummy = Vec3Argument.vec3().parse(new StringReader(value));
                    } catch (CommandSyntaxException e) {
                        throw new IllegalArgumentException(e.getMessage());
                    }
                }
                default -> throw new IllegalArgumentException("Unknown directive");
            }
        }

        public TestDirectives build() {
            return new TestDirectives(
                template,
                environment,
                timeout,
                optional,
                skyAccess,
                Optional.ofNullable(dummy)
            );
        }
    }
}
