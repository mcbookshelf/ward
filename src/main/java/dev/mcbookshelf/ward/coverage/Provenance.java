package dev.mcbookshelf.ward.coverage;

import java.util.IdentityHashMap;
import java.util.Map;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import org.jspecify.annotations.Nullable;

import net.minecraft.resources.ResourceKey;

final class Provenance {
	final String registry;
	final String element;
	private final JsonElement root;
	private @Nullable Map<JsonElement, String> paths;

	Provenance(ResourceKey<?> key, JsonElement root) {
		this.registry = key.registry().toString();
		this.element = key.identifier().toString();
		this.root = root;
	}

	@Nullable String pathOf(JsonElement member) {
		if (this.paths == null) {
			this.paths = new IdentityHashMap<>();
			index(this.root, "", this.paths);
		}

		return this.paths.get(member);
	}

	private static void index(JsonElement element, String path, Map<JsonElement, String> paths) {
		if (element instanceof JsonObject object) {
			object.entrySet().forEach(member -> {
				paths.put(member.getValue(), path);
				index(member.getValue(), path.isEmpty() ? member.getKey() : path + "." + member.getKey(), paths);
			});
		}

		if (element instanceof JsonArray array) {
			for (int i = 0; i < array.size(); i++) {
				index(array.get(i), path + "[" + i + "]", paths);
			}
		}
	}
}
