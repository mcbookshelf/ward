package dev.mcbookshelf.ward;

import java.util.function.BiConsumer;

import com.google.gson.JsonObject;

public final class Reporter {
	private static volatile BiConsumer<String, JsonObject> sink = (_, _) -> { };

	private Reporter() {
	}

	public static void register(BiConsumer<String, JsonObject> events) {
		sink = events;
	}

	public static void send(String type, JsonObject data) {
		sink.accept(type, data);
	}

	public static void loadError(String kind, String id, String message) {
		loadDiagnostic("error", kind, id, message);
	}

	public static void loadError(String kind, String id, Throwable error) {
		loadDiagnostic("error", kind, id, Messages.describe(error));
	}

	public static void loadWarning(String kind, String id, String message) {
		loadDiagnostic("warn", kind, id, message);
	}

	private static void loadDiagnostic(String severity, String kind, String id, String message) {
		JsonObject data = new JsonObject();
		data.addProperty("severity", severity);
		data.addProperty("kind", kind);
		data.addProperty("id", id);
		data.addProperty("message", message);
		send("load_diagnostic", data);
	}
}
