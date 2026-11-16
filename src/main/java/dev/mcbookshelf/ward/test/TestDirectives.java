package dev.mcbookshelf.ward.test;

import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

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
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import net.minecraft.nbt.TagParser;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Rotation;

public record TestDirectives(TestData<Identifier> data, @Nullable Coordinates dummy, List<CompoundTag> cases) {
	public TestData<Holder<TestEnvironmentDefinition<?>>> createTestData(Registry<TestEnvironmentDefinition<?>> environments) {
		return this.data.map(id -> environments.getOrThrow(ResourceKey.create(Registries.TEST_ENVIRONMENT, id)));
	}

	public static class Builder {
		private Identifier environment = GameTestEnvironments.DEFAULT_KEY.identifier();
		private Identifier dimension = Level.OVERWORLD.identifier();
		private Identifier structure = Identifier.withDefaultNamespace("empty");
		private int maxTicks = 100;
		private int setupTicks = 0;
		private boolean required = true;
		private boolean skyAccess = false;
		private Rotation rotation = Rotation.NONE;
		private int maxAttempts = 1;
		private int requiredSuccesses = 1;
		private int padding = 0;
		private @Nullable Coordinates dummy = null;
		private List<CompoundTag> cases = List.of();

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
						this.required = !bool(value);
				case "skyaccess", "sky_access" ->
						this.skyAccess = bool(value);
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
						StringReader reader = new StringReader(Objects.requireNonNullElse(value, "~ ~ ~").trim());
						this.dummy = Vec3Argument.vec3().parse(reader);
						if (reader.canRead()) throw new IllegalArgumentException("Unexpected trailing input '" + reader.getRemaining() + "'");
					} catch (CommandSyntaxException e) {
						throw new IllegalArgumentException(e.getMessage());
					}
				}
				case "cases" ->
						this.cases = cases(value);
				default -> throw new IllegalArgumentException("Unknown directive");
			}
		}

		public TestDirectives build() {
			if (this.requiredSuccesses > this.maxAttempts) {
				throw new IllegalArgumentException("@required_successes is above @max_attempts, so the test can never pass");
			}

			TestData<Identifier> data = new TestData<>(
					this.environment,
					ResourceKey.create(Registries.DIMENSION, this.dimension),
					this.structure,
					this.maxTicks,
					this.setupTicks,
					this.required,
					this.rotation,
					false,
					this.maxAttempts,
					this.requiredSuccesses,
					this.skyAccess,
					this.padding);
			return new TestDirectives(data, this.dummy, this.cases);
		}

		private static Identifier identifier(@Nullable String value) {
			return Identifier.parse(require(value));
		}

		private static List<CompoundTag> cases(@Nullable String value) {
			Tag parsed;

			try {
				parsed = TagParser.create(NbtOps.INSTANCE).parseFully(require(value));
			} catch (CommandSyntaxException e) {
				throw new IllegalArgumentException(e.getMessage());
			}

			if (!(parsed instanceof ListTag list) || list.isEmpty() || !list.stream().allMatch(CompoundTag.class::isInstance)) {
				throw new IllegalArgumentException("Value must be a list of compounds, like [{x:1},{x:2}]");
			}

			List<CompoundTag> cases = list.stream().map(CompoundTag.class::cast).toList();
			if (new HashSet<>(cases).size() < cases.size()) throw new IllegalArgumentException("Two cases have the same arguments");
			return cases;
		}

		private static boolean bool(@Nullable String value) {
			if (value == null) return true;

			return switch (value.trim().toLowerCase(Locale.ROOT)) {
				case "true" -> true;
				case "false" -> false;
				default -> throw new IllegalArgumentException("Value must be true or false");
			};
		}

		private static Rotation rotation(@Nullable String value) {
			int degrees = integer(value);

			return switch (Math.floorMod(degrees, 360)) {
				case 0 -> Rotation.NONE;
				case 90 -> Rotation.CLOCKWISE_90;
				case 180 -> Rotation.CLOCKWISE_180;
				case 270 -> Rotation.COUNTERCLOCKWISE_90;
				default -> throw new IllegalArgumentException("Rotation must be a multiple of 90 degrees");
			};
		}

		private static int integer(@Nullable String value) {
			try {
				return Integer.parseInt(require(value));
			} catch (NumberFormatException e) {
				throw new IllegalArgumentException("Value must be a whole number");
			}
		}

		private static int positiveInt(@Nullable String value) {
			int parsed = integer(value);
			if (parsed <= 0) throw new IllegalArgumentException("Value must be positive");
			return parsed;
		}

		private static int nonNegativeInt(@Nullable String value) {
			int parsed = integer(value);
			if (parsed < 0) throw new IllegalArgumentException("Value must not be negative");
			return parsed;
		}

		private static String require(@Nullable String value) {
			if (value == null) throw new IllegalArgumentException("Missing value");
			return value.trim();
		}
	}
}
