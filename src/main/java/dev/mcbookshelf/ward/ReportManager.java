package dev.mcbookshelf.ward;

import java.util.Locale;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import org.jspecify.annotations.Nullable;

import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTestInfo;
import net.minecraft.gametest.framework.GlobalTestReporter;
import net.minecraft.gametest.framework.TestReporter;

/**
 * Broadcasts load diagnostics, test results and run lifecycle events over the bridge. Reports
 * come from the server thread as well as reload workers, so every dispatch is synchronized.
 */
public class ReportManager {
	private static @Nullable WardBridge bridge;

	private static int expectedTotal;
	private static int passedCount;
	private static int failedCount;
	private static int skippedCount;

	public static synchronized boolean isRunComplete() {
		return passedCount + failedCount + skippedCount >= expectedTotal;
	}

	public static synchronized void register(WardBridge wardBridge) {
		GlobalTestReporter.replaceWith(new TestReporterProxy());
		bridge = wardBridge;
	}

	public static synchronized void report(LoadDiagnostic diagnostic) {
		JsonObject data = new JsonObject();
		data.addProperty("severity", diagnostic.severity().name().toLowerCase(Locale.ROOT));
		data.addProperty("kind", diagnostic.type());
		data.addProperty("id", diagnostic.id());
		data.addProperty("message", diagnostic.message());
		broadcast("load_diagnostic", data);
	}

	public static synchronized void runStarted(int total, BlockPos startPos) {
		expectedTotal = total;
		passedCount = 0;
		failedCount = 0;
		skippedCount = 0;

		JsonObject data = new JsonObject();
		data.addProperty("total", total);

		JsonArray pos = new JsonArray();
		pos.add(startPos.getX());
		pos.add(startPos.getY());
		pos.add(startPos.getZ());
		data.add("pos", pos);

		broadcast("tests_started", data);
	}

	public static synchronized void batchStarted(int index, String environment, String dimension) {
		broadcast("batch_started", createBatchData(index, environment, dimension));
	}

	public static synchronized void batchFinished(int index, String environment, String dimension) {
		broadcast("batch_finished", createBatchData(index, environment, dimension));
	}

	public static synchronized void runFinished(long elapsedMs) {
		JsonObject data = new JsonObject();
		data.addProperty("total", expectedTotal);
		data.addProperty("passed", passedCount);
		data.addProperty("failed", failedCount);
		data.addProperty("skipped", skippedCount);
		data.addProperty("elapsed", elapsedMs);
		broadcast("tests_finished", data);
	}

	private static synchronized void reportTest(GameTestInfo info, boolean passed) {
		JsonObject data = new JsonObject();
		data.addProperty("name", info.getTestHolder().key().identifier().toString());
		// Durations cross the wire as milliseconds and consumers format them
		data.addProperty("time", info.getRunTime());

		if (passed) {
			passedCount++;
			broadcast("test_passed", data);
		} else if (info.getError() != null) {
			// Consumers treat failures of optional tests as skipped
			boolean required = info.isRequired();
			data.addProperty("required", required);

			if (info.getError() instanceof TestException error) {
				data.addProperty("error", error.getRawMessage());
				data.addProperty("line", error.getLine());
				data.addProperty("tick", error.getTick());
			} else {
				data.addProperty("error", info.getError().getMessage());
			}

			broadcast("test_failed", data);

			if (required) {
				failedCount++;
			} else {
				skippedCount++;
			}
		}
	}

	private static JsonObject createBatchData(int index, String environment, String dimension) {
		JsonObject data = new JsonObject();
		data.addProperty("batch", index);
		data.addProperty("environment", environment);
		data.addProperty("dimension", dimension);
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
		}
	}
}
