package dev.mcbookshelf.ward.report;

import java.util.Locale;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import org.jspecify.annotations.Nullable;

import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTestInfo;
import net.minecraft.gametest.framework.GlobalTestReporter;
import net.minecraft.gametest.framework.TestReporter;

import dev.mcbookshelf.ward.TestException;
import dev.mcbookshelf.ward.WardBridge;

/**
 * Broadcasts load diagnostics, test results and run lifecycle events over the bridge, as JSON
 * messages to all connected clients.
 *
 * <p>Entries can be reported from the server thread as well as datapack reload worker threads, so
 * every dispatch is synchronized. The bridge is registered once at daemon startup, before any
 * world load, so the boot-time diagnostics of each run reach the clients that requested it.
 */
public class ReportManager {
	private static @Nullable WardBridge bridge;

	public static synchronized void register(WardBridge wardBridge) {
		GlobalTestReporter.replaceWith(new TestReporterProxy());
		bridge = wardBridge;
	}

	public static synchronized void report(Diagnostic diagnostic) {
		JsonObject data = new JsonObject();
		data.addProperty("severity", diagnostic.severity().name().toLowerCase(Locale.ROOT));
		data.addProperty("kind", diagnostic.type());
		data.addProperty("id", diagnostic.id());
		data.addProperty("message", diagnostic.message());
		broadcast("load_diagnostic", data);
	}

	public static synchronized void runStarted(int total, BlockPos startPos) {
		JsonObject data = new JsonObject();
		data.addProperty("total", total);

		JsonArray pos = new JsonArray();
		pos.add(startPos.getX());
		pos.add(startPos.getY());
		pos.add(startPos.getZ());
		data.add("pos", pos);

		broadcast("tests_started", data);
	}

	public static synchronized void batchStarted(int index, String environment) {
		broadcast("batch_started", createBatchData(index, environment));
	}

	public static synchronized void batchFinished(int index, String environment) {
		broadcast("batch_finished", createBatchData(index, environment));
	}

	public static synchronized void reportCoverage(JsonObject report) {
		broadcast("coverage", report);
	}

	public static synchronized void runFinished(int total, int passed, int failed, int skipped, long elapsedMs) {
		JsonObject data = new JsonObject();
		data.addProperty("total", total);
		data.addProperty("passed", passed);
		data.addProperty("failed", failed);
		data.addProperty("skipped", skipped);
		data.addProperty("elapsed", elapsedMs);
		broadcast("tests_finished", data);
	}

	private static synchronized void reportTest(GameTestInfo info, boolean passed) {
		JsonObject data = new JsonObject();
		data.addProperty("name", info.getTestHolder().key().identifier().toString());
		// Durations cross the wire as milliseconds; consumers format them
		data.addProperty("time", info.getRunTime());

		if (passed) {
			broadcast("test_passed", data);
		} else if (info.getError() != null) {
			// Consumers treat failures of optional tests as skipped
			data.addProperty("required", info.isRequired());

			if (info.getError() instanceof TestException error) {
				data.addProperty("error", error.getRawMessage());
				data.addProperty("line", error.getLine());
				data.addProperty("tick", error.getTick());
			} else {
				data.addProperty("error", info.getError().getMessage());
			}

			broadcast("test_failed", data);
		}
	}

	private static JsonObject createBatchData(int index, String environment) {
		JsonObject data = new JsonObject();
		data.addProperty("batch", index);
		data.addProperty("environment", environment);
		return data;
	}

	private static void broadcast(String type, JsonObject data) {
		if (bridge != null) {
			bridge.broadcast(type, data);
		}
	}

	private static class TestReporterProxy implements TestReporter {
		@Override
		public void onTestFailed(GameTestInfo testInfo) {
			reportTest(testInfo, false);
		}

		@Override
		public void onTestSuccess(GameTestInfo testInfo) {
			reportTest(testInfo, true);
		}

		@Override
		public void finish() {
			// Run completion is driven by WardServer through runFinished; vanilla
			// only invokes this from its own GameTestServer, never for Ward.
		}
	}
}
