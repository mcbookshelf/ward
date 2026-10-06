package dev.mcbookshelf.ward.coverage;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import org.jspecify.annotations.Nullable;

final class NodeTable {
	private final Map<String, Map<String, Map<String, int[]>>> counts = new ConcurrentHashMap<>();

	int[] node(String registry, String element, String path) {
		return this.counts
				.computeIfAbsent(registry, _ -> new ConcurrentHashMap<>())
				.computeIfAbsent(element, _ -> new ConcurrentHashMap<>())
				.computeIfAbsent(path, _ -> new int[2]);
	}

	int @Nullable [] find(String registry, String element, String path) {
		return this.counts
				.getOrDefault(registry, Map.of())
				.getOrDefault(element, Map.of())
				.get(path);
	}

	void clear() {
		this.counts.clear();
	}

	static void hit(int[] counts) {
		counts[0]++;
		counts[1]++;
	}

	JsonObject toJson() {
		JsonObject report = new JsonObject();

		this.counts.forEach((registry, elements) -> {
			JsonObject byElement = new JsonObject();
			elements.forEach((element, paths) -> byElement.add(element, toJson(paths)));
			report.add(registry, byElement);
		});

		return report;
	}

	private static JsonObject toJson(Map<String, int[]> paths) {
		JsonObject byPath = new JsonObject();

		paths.forEach((path, counts) -> {
			JsonArray pair = new JsonArray();
			pair.add(counts[0]);
			pair.add(counts[1]);
			byPath.add(path, pair);
		});

		return byPath;
	}
}
