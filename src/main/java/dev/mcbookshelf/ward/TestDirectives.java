package dev.mcbookshelf.ward;

import java.util.Locale;
import java.util.Objects;
import java.util.Optional;

import com.mojang.brigadier.StringReader;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import org.jspecify.annotations.Nullable;

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
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Rotation;

/**
 * Parsed {@code # @directive value} headers from a test file. The ids stay strings and are
 * resolved in {@link #createTestData} against the registries of the run that loaded the test.
 */
public record TestDirectives(
		String environment,
		String dimension,
		String structure,
		int maxTicks,
		int setupTicks,
		boolean required,
		boolean skyAccess,
		Rotation rotation,
		int maxAttempts,
		int requiredSuccesses,
		int padding,
		Optional<Coordinates> dummy) {
	public TestData<Holder<TestEnvironmentDefinition<?>>> createTestData(Registry<TestEnvironmentDefinition<?>> environments) {
		return new TestData<>(
				environments.getOrThrow(ResourceKey.create(Registries.TEST_ENVIRONMENT, Identifier.parse(this.environment))),
				ResourceKey.create(Registries.DIMENSION, Identifier.parse(this.dimension)),
				Identifier.parse(this.structure),
				this.maxTicks,
				this.setupTicks,
				this.required,
				this.rotation,
				false,
				this.maxAttempts,
				this.requiredSuccesses,
				this.skyAccess,
				this.padding);
	}

	public static class Builder {
		private String environment = GameTestEnvironments.DEFAULT_KEY.identifier().toString();
		private String dimension = Level.OVERWORLD.identifier().toString();
		private String structure = Identifier.withDefaultNamespace("empty").toString();
		private int maxTicks = 100;
		private int setupTicks = 0;
		private boolean required = true;
		private boolean skyAccess = false;
		private Rotation rotation = Rotation.NONE;
		private int maxAttempts = 1;
		private int requiredSuccesses = 1;
		private int padding = 0;
		private @Nullable Coordinates dummy = null;

		public void add(String name, @Nullable String value) {
			switch (name.toLowerCase(Locale.ROOT)) {
				case "environment" ->
						this.environment = identifier(value);
				case "dimension" ->
						this.dimension = identifier(value);
				case "template", "structure" ->
						this.structure = identifier(value);
				case "timeout", "max_ticks" ->
						this.maxTicks = positiveInt(value);
				case "setup_ticks" ->
						this.setupTicks = nonNegativeInt(value);
				case "optional" ->
						this.required = !(value == null || Boolean.parseBoolean(value.trim()));
				case "skyaccess", "sky_access" ->
						this.skyAccess = value == null || Boolean.parseBoolean(value.trim());
				case "rotation" ->
						this.rotation = rotation(value);
				case "max_attempts" ->
						this.maxAttempts = positiveInt(value);
				case "required_successes" ->
						this.requiredSuccesses = positiveInt(value);
				case "padding" -> {
					this.padding = nonNegativeInt(value);
					if (this.padding > 128) throw new IllegalArgumentException("Padding must be between 0 and 128");
				}
				case "dummy" -> {
					try {
						String pos = Objects.requireNonNullElse(value, "~ ~ ~");
						this.dummy = Vec3Argument.vec3().parse(new StringReader(pos));
					} catch (CommandSyntaxException e) {
						throw new IllegalArgumentException(e.getMessage());
					}
				}
				default -> throw new IllegalArgumentException("Unknown directive");
			}
		}

		public TestDirectives build() {
			return new TestDirectives(
					environment,
					dimension,
					structure,
					maxTicks,
					setupTicks,
					required,
					skyAccess,
					rotation,
					maxAttempts,
					requiredSuccesses,
					padding,
					Optional.ofNullable(dummy));
		}

		private static String identifier(@Nullable String value) {
			return Identifier.parse(require(value)).toString();
		}

		private static Rotation rotation(@Nullable String value) {
			int degrees = Integer.parseInt(require(value));

			return switch (Math.floorMod(degrees, 360)) {
				case 0 -> Rotation.NONE;
				case 90 -> Rotation.CLOCKWISE_90;
				case 180 -> Rotation.CLOCKWISE_180;
				case 270 -> Rotation.COUNTERCLOCKWISE_90;
				default -> throw new IllegalArgumentException("Rotation must be a multiple of 90 degrees");
			};
		}

		private static int positiveInt(@Nullable String value) {
			int parsed = Integer.parseInt(require(value));
			if (parsed <= 0) throw new IllegalArgumentException("Value must be positive");
			return parsed;
		}

		private static int nonNegativeInt(@Nullable String value) {
			int parsed = Integer.parseInt(require(value));
			if (parsed < 0) throw new IllegalArgumentException("Value must not be negative");
			return parsed;
		}

		private static String require(@Nullable String value) {
			if (value == null) throw new IllegalArgumentException("Missing value");
			return value.trim();
		}
	}
}
