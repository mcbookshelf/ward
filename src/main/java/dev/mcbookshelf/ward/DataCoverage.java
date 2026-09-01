package dev.mcbookshelf.ward;

import java.util.IdentityHashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Stream;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.DynamicOps;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.MapLike;
import com.mojang.serialization.RecordBuilder;
import org.jspecify.annotations.Nullable;

import net.minecraft.resources.ResourceKey;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.util.context.ContextKey;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.slot.SlotCollection;
import net.minecraft.world.item.slot.SlotSource;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.ValidationContext;
import net.minecraft.world.level.storage.loot.entries.LootPoolEntryContainer;
import net.minecraft.world.level.storage.loot.functions.LootItemFunction;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraft.world.level.storage.loot.providers.number.floats.ContextFloatProvider;
import net.minecraft.world.level.storage.loot.providers.number.ints.ContextIntProvider;

import dev.mcbookshelf.ward.accessor.RunCounterHolder;

/**
 * Records how the packs JSON behaves during a coverage run.
 * Conditions count [true, false] outcomes.
 */
public final class DataCoverage {
	private static final ThreadLocal<Provenance> CURRENT = new ThreadLocal<>();

	// Deployed packs load from the world's datapack folder; vanilla, feature packs and mods are not under test
	private static final String DEPLOYED_PACK_PREFIX = "file/";
	private static final String ADVANCEMENT_REGISTRY = "minecraft:advancement";

	private static final NodeTable conditions = new NodeTable();
	private static final NodeTable runs = new NodeTable();

	private DataCoverage() {
	}

	public static MapCodec<? extends LootItemCondition> wrapCondition(MapCodec<? extends LootItemCondition> codec) {
		return new RecordingCodec<LootItemCondition>(codec, conditions, RecordingCondition::new);
	}

	/**
	 * Entries are stamped rather than delegated (see {@code LootPoolEntryContainerMixin}): their class hierarchy does not delegate well.
	 * Loot tables are never encoded at runtime, so the entry keeping its original codec is safe.
	 */
	public static MapCodec<? extends LootPoolEntryContainer> wrapEntry(MapCodec<? extends LootPoolEntryContainer> codec) {
		return new RecordingCodec<LootPoolEntryContainer>(codec, runs, (entry, wrapper, counts) -> {
			if (entry instanceof RunCounterHolder holder) {
				holder.ward$runCounters(counts);
			}

			return entry;
		});
	}

	public static MapCodec<? extends LootItemFunction> wrapFunction(MapCodec<? extends LootItemFunction> codec) {
		return new RecordingCodec<LootItemFunction>(codec, runs, RecordingFunction::new);
	}

	public static MapCodec<? extends ContextFloatProvider> wrapFloatProvider(MapCodec<? extends ContextFloatProvider> codec) {
		return new RecordingCodec<ContextFloatProvider>(codec, runs, RecordingFloatProvider::new);
	}

	public static MapCodec<? extends ContextIntProvider> wrapIntProvider(MapCodec<? extends ContextIntProvider> codec) {
		return new RecordingCodec<ContextIntProvider>(codec, runs, RecordingIntProvider::new);
	}

	public static MapCodec<? extends SlotSource> wrapSlotSource(MapCodec<? extends SlotSource> codec) {
		return new RecordingCodec<SlotSource>(codec, runs, RecordingSlotSource::new);
	}

	/**
	 * Marks the element being decoded on this thread, when it comes from a deployed pack (overrides of vanilla ids included).
	 */
	public static void beginElement(ResourceKey<?> key, Resource resource, Object json) {
		if (CoverageRecorder.isEnabled()
				&& resource.sourcePackId().startsWith(DEPLOYED_PACK_PREFIX)
				&& json instanceof JsonElement element) {
			CURRENT.set(new Provenance(key.registry().toString(), key.identifier().toString(), element));
		}
	}

	public static void endElement() {
		CURRENT.remove();
	}

	/**
	 * Registers what a decoded element can run on its own: a loot table's rolls, and an advancement's criteria.
	 * Criteria only record when they fire, so their universe is read from the file.
	 */
	public static void completeElement(Object value) {
		Provenance provenance = CURRENT.get();

		if (provenance == null) {
			return;
		}

		if (value instanceof RunCounterHolder holder) {
			holder.ward$runCounters(runs.node(provenance, ""));
		}

		if (ADVANCEMENT_REGISTRY.equals(provenance.registry)
				&& provenance.root instanceof JsonObject root
				&& root.get("criteria") instanceof JsonObject criteria) {
			for (String name : criteria.keySet()) {
				runs.node(provenance, "criteria." + name);
			}
		}
	}

	/**
	 * Fabric's loot API can rebuild loot tables after decode, so the registered instance needs its counters again.
	 * Counters are shared, so stamping twice is harmless.
	 */
	public static void stampRegistered(String registry, String element, Object value) {
		int[] counts = runs.get(registry, element, "");

		if (counts != null && value instanceof RunCounterHolder holder) {
			holder.ward$runCounters(counts);
		}
	}

	public static void recordCriterion(String advancement, String criterion) {
		int[] counts = runs.get(ADVANCEMENT_REGISTRY, advancement, "criteria." + criterion);

		if (counts != null) {
			counts[0]++;
			counts[1]++;
		}
	}

	public static JsonObject drainConditions() {
		return conditions.drain();
	}

	public static JsonObject drainRuns() {
		return runs.drain();
	}

	public static void clear() {
		conditions.clear();
		runs.clear();
	}

	/**
	 * The element being decoded, with its JSON tree indexed by identity on first use.
	 * The parser creates a distinct instance per position, so a member element pins the exact node holding it.
	 */
	private static final class Provenance {
		final String registry;
		final String element;
		final JsonElement root;
		private @Nullable Map<JsonElement, String> paths;

		Provenance(String registry, String element, JsonElement root) {
			this.registry = registry;
			this.element = element;
			this.root = root;
		}

		/**
		 * The path of the object holding {@code member}, in NBT path syntax: {@code .key} for members, {@code [i]} for indices.
		 */
		@Nullable String pathOf(JsonElement member) {
			if (this.paths == null) {
				this.paths = new IdentityHashMap<>();
				index(this.root, "");
			}

			return this.paths.get(member);
		}

		private void index(JsonElement element, String path) {
			if (element instanceof JsonObject object) {
				for (Map.Entry<String, JsonElement> entry : object.entrySet()) {
					this.paths.put(entry.getValue(), path);
					index(entry.getValue(), path.isEmpty() ? entry.getKey() : path + "." + entry.getKey());
				}
			} else if (element instanceof JsonArray array) {
				for (int i = 0; i < array.size(); i++) {
					index(array.get(i), path + "[" + i + "]");
				}
			}
		}
	}

	/**
	 * Counters per node: registry id, then element id, then path.
	 */
	private static final class NodeTable {
		private final Map<String, Map<String, Map<String, int[]>>> counts = new ConcurrentHashMap<>();

		int[] node(Provenance provenance, String path) {
			return this.counts
					.computeIfAbsent(provenance.registry, key -> new ConcurrentHashMap<>())
					.computeIfAbsent(provenance.element, key -> new ConcurrentHashMap<>())
					.computeIfAbsent(path, key -> new int[2]);
		}

		int @Nullable [] get(String registry, String element, String path) {
			return this.counts
					.getOrDefault(registry, Map.of())
					.getOrDefault(element, Map.of())
					.get(path);
		}

		/**
		 * Serializes the counts, clearing them for the next run.
		 */
		JsonObject drain() {
			JsonObject report = new JsonObject();

			for (Map.Entry<String, Map<String, Map<String, int[]>>> registry : this.counts.entrySet()) {
				JsonObject elements = new JsonObject();

				for (Map.Entry<String, Map<String, int[]>> element : registry.getValue().entrySet()) {
					JsonObject paths = new JsonObject();

					for (Map.Entry<String, int[]> node : element.getValue().entrySet()) {
						JsonArray pair = new JsonArray();
						pair.add(node.getValue()[0]);
						pair.add(node.getValue()[1]);
						paths.add(node.getKey(), pair);
					}

					elements.add(element.getKey(), paths);
				}

				report.add(registry.getKey(), elements);
			}

			this.counts.clear();
			return report;
		}

		void clear() {
			this.counts.clear();
		}
	}

	/**
	 * Wraps a registered type's codec.
	 * Decoding resolves the node through the {@code "type"} element and hands the value to {@code wrap}; encoding unwraps delegates back to the original.
	 */
	private static final class RecordingCodec<A> extends MapCodec<A> {
		interface Wrap<A> {
			A apply(A value, MapCodec<A> codec, int[] counts);
		}

		private final MapCodec<A> inner;
		private final NodeTable nodes;
		private final Wrap<A> wrap;

		@SuppressWarnings("unchecked")
		RecordingCodec(MapCodec<? extends A> inner, NodeTable nodes, Wrap<A> wrap) {
			this.inner = (MapCodec<A>) inner;
			this.nodes = nodes;
			this.wrap = wrap;
		}

		@Override
		public <T> Stream<T> keys(DynamicOps<T> ops) {
			return this.inner.keys(ops);
		}

		@Override
		public <T> DataResult<A> decode(DynamicOps<T> ops, MapLike<T> input) {
			return this.inner.decode(ops, input).map(value -> {
				int[] counts = counters(input.get("type"));
				return counts == null || value instanceof Recording
						? value
						: this.wrap.apply(value, this, counts);
			});
		}

		@Override
		@SuppressWarnings("unchecked")
		public <T> RecordBuilder<T> encode(A value, DynamicOps<T> ops, RecordBuilder<T> builder) {
			A unwrapped = value instanceof Recording<?> recording ? (A) recording.inner : value;
			return this.inner.encode(unwrapped, ops, builder);
		}

		@Override
		public String toString() {
			return this.inner.toString();
		}

		private int @Nullable [] counters(Object anchor) {
			Provenance provenance = CURRENT.get();

			if (provenance == null || !(anchor instanceof JsonElement element)) {
				return null;
			}

			String path = provenance.pathOf(element);
			return path == null ? null : this.nodes.node(provenance, path);
		}
	}

	private abstract static class Recording<A> {
		final A inner;
		final MapCodec<A> codec;
		final int[] counts;

		Recording(A inner, MapCodec<A> codec, int[] counts) {
			this.inner = inner;
			this.codec = codec;
			this.counts = counts;
		}

		/**
		 * The wrapper is what the registry holds, so encoding dispatches back through it.
		 */
		public MapCodec<A> codec() {
			return this.codec;
		}

		/**
		 * A block that runs always ran fully: reached and ran move together.
		 */
		void hit() {
			this.counts[0]++;
			this.counts[1]++;
		}
	}

	private static final class RecordingCondition extends Recording<LootItemCondition> implements LootItemCondition {
		RecordingCondition(LootItemCondition inner, MapCodec<LootItemCondition> codec, int[] counts) {
			super(inner, codec, counts);
		}

		@Override
		public boolean test(LootContext context) {
			boolean result = this.inner.test(context);
			this.counts[result ? 0 : 1]++;
			return result;
		}

		@Override
		public Set<ContextKey<?>> getReferencedContextParams() {
			return this.inner.getReferencedContextParams();
		}

		@Override
		public void validate(ValidationContext context) {
			this.inner.validate(context);
		}
	}

	private static final class RecordingFunction extends Recording<LootItemFunction> implements LootItemFunction {
		RecordingFunction(LootItemFunction inner, MapCodec<LootItemFunction> codec, int[] counts) {
			super(inner, codec, counts);
		}

		@Override
		public ItemStack apply(ItemStack stack, LootContext context) {
			hit();
			return this.inner.apply(stack, context);
		}

		@Override
		public Set<ContextKey<?>> getReferencedContextParams() {
			return this.inner.getReferencedContextParams();
		}

		@Override
		public void validate(ValidationContext context) {
			this.inner.validate(context);
		}
	}

	private static final class RecordingFloatProvider extends Recording<ContextFloatProvider> implements ContextFloatProvider {
		RecordingFloatProvider(ContextFloatProvider inner, MapCodec<ContextFloatProvider> codec, int[] counts) {
			super(inner, codec, counts);
		}

		/**
		 * The safe default method funnels through here, so both entry points are counted.
		 */
		@Override
		public float getFloatUnsafe(LootContext context) throws ArithmeticException {
			hit();
			return this.inner.getFloatUnsafe(context);
		}

		@Override
		public void validate(ValidationContext context) {
			this.inner.validate(context);
		}
	}

	private static final class RecordingIntProvider extends Recording<ContextIntProvider> implements ContextIntProvider {
		RecordingIntProvider(ContextIntProvider inner, MapCodec<ContextIntProvider> codec, int[] counts) {
			super(inner, codec, counts);
		}

		@Override
		public int getIntUnsafe(LootContext context) throws ArithmeticException {
			hit();
			return this.inner.getIntUnsafe(context);
		}

		@Override
		public void validate(ValidationContext context) {
			this.inner.validate(context);
		}
	}

	private static final class RecordingSlotSource extends Recording<SlotSource> implements SlotSource {
		RecordingSlotSource(SlotSource inner, MapCodec<SlotSource> codec, int[] counts) {
			super(inner, codec, counts);
		}

		@Override
		public SlotCollection provide(LootContext context) {
			hit();
			return this.inner.provide(context);
		}

		@Override
		public Set<ContextKey<?>> getReferencedContextParams() {
			return this.inner.getReferencedContextParams();
		}

		@Override
		public void validate(ValidationContext context) {
			this.inner.validate(context);
		}
	}
}
