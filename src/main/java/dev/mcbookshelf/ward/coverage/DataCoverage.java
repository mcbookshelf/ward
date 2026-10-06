package dev.mcbookshelf.ward.coverage;

import java.util.function.Supplier;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.serialization.DataResult;

import net.minecraft.advancements.Advancement;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.world.item.slot.SlotSource;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.functions.LootItemFunction;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraft.world.level.storage.loot.providers.number.floats.ContextFloatProvider;
import net.minecraft.world.level.storage.loot.providers.number.ints.ContextIntProvider;

public final class DataCoverage {
	private static final ThreadLocal<Provenance> DECODING = new ThreadLocal<>();
	private static final String DEPLOYED_PACK_PREFIX = "file/";

	private static final NodeTable CONDITIONS = new NodeTable();
	private static final NodeTable RUNS = new NodeTable();

	private DataCoverage() {
	}

	public static DataResult<?> track(ResourceKey<?> key, Resource resource, Object json, Supplier<DataResult<?>> decode) {
		if (!Coverage.isEnabled()
				|| !resource.sourcePackId().startsWith(DEPLOYED_PACK_PREFIX)
				|| !(json instanceof JsonElement root)) {
			return decode.get();
		}

		Provenance provenance = new Provenance(key, root);
		DECODING.set(provenance);

		try {
			DataResult<?> result = decode.get();
			result.result().ifPresent(value -> countRoot(provenance, value));
			return result;
		} finally {
			DECODING.remove();
		}
	}

	private static void countRoot(Provenance provenance, Object value) {
		if (value instanceof LootTable) {
			RUNS.node(provenance.registry, provenance.element, "");
		}

		if (value instanceof Advancement advancement) {
			advancement.criteria().keySet().forEach(name -> RUNS.node(provenance.registry, provenance.element, "criteria." + name));
		}
	}

	public static <V> DataResult<V> decoded(DataResult<V> result, JsonElement type) {
		Provenance provenance = DECODING.get();

		if (provenance == null) {
			return result;
		}

		String path = provenance.pathOf(type);
		return path == null ? result : result.map(value -> counted(value, provenance, path));
	}

	public static <V> V unwrap(V value) {
		return Recording.unwrap(value);
	}

	@SuppressWarnings("unchecked")
	private static <V> V counted(V value, Provenance provenance, String path) {
		return (V) switch (value) {
			case LootItemCondition condition -> new Recording.Condition(condition, CONDITIONS.node(provenance.registry, provenance.element, path));
			case LootItemFunction function -> new Recording.Function(function, RUNS.node(provenance.registry, provenance.element, path));
			case ContextFloatProvider provider -> new Recording.FloatProvider(provider, RUNS.node(provenance.registry, provenance.element, path));
			case ContextIntProvider provider -> new Recording.IntProvider(provider, RUNS.node(provenance.registry, provenance.element, path));
			case SlotSource source -> new Recording.Slots(source, RUNS.node(provenance.registry, provenance.element, path));
			case RunCounterHolder entry -> {
				entry.ward$runCounters(RUNS.node(provenance.registry, provenance.element, path));
				yield value;
			}
			default -> value;
		};
	}

	public static void stampRegistered(ResourceKey<LootTable> key, LootTable table) {
		int[] counts = RUNS.find(key.registry().toString(), key.identifier().toString(), "");

		if (counts != null) {
			((RunCounterHolder) (Object) table).ward$runCounters(counts);
		}
	}

	public static void recordCriterion(String advancement, String criterion) {
		int[] counts = RUNS.find(Registries.ADVANCEMENT.identifier().toString(), advancement, "criteria." + criterion);

		if (counts != null) {
			NodeTable.hit(counts);
		}
	}

	static void clear() {
		CONDITIONS.clear();
		RUNS.clear();
	}

	static JsonObject conditions() {
		return CONDITIONS.toJson();
	}

	static JsonObject runs() {
		return RUNS.toJson();
	}
}
