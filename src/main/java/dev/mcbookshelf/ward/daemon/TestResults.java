package dev.mcbookshelf.ward.daemon;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTestBatch;
import net.minecraft.gametest.framework.GameTestException;
import net.minecraft.gametest.framework.GameTestInfo;
import net.minecraft.gametest.framework.TestReporter;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.test.TestException;

final class TestResults implements TestReporter {
	private int total;
	private int passed;
	private int failed;
	private int skipped;

	void started(int total, BlockPos origin) {
		this.total = total;

		JsonArray pos = new JsonArray();
		pos.add(origin.getX());
		pos.add(origin.getY());
		pos.add(origin.getZ());

		JsonObject data = new JsonObject();
		data.addProperty("total", total);
		data.add("pos", pos);
		Reporter.send("tests_started", data);
	}

	void batchStarted(GameTestBatch batch) {
		JsonObject data = describe(batch);
		data.addProperty("total", batch.gameTestInfos().size());
		Reporter.send("batch_started", data);
	}

	void batchFinished(GameTestBatch batch) {
		Reporter.send("batch_finished", describe(batch));
	}

	void finished(long elapsedMillis) {
		JsonObject data = new JsonObject();
		data.addProperty("total", this.total);
		data.addProperty("passed", this.passed);
		data.addProperty("failed", this.failed);
		data.addProperty("skipped", this.skipped);
		data.addProperty("elapsed", elapsedMillis);
		Reporter.send("tests_finished", data);
	}

	@Override
	public void onTestSuccess(GameTestInfo test) {
		this.passed++;
		Reporter.send("test_passed", describe(test));
	}

	@Override
	public void onTestFailed(GameTestInfo test) {
		if (test.isRequired()) {
			this.failed++;
		} else {
			this.skipped++;
		}

		JsonObject data = describe(test);
		data.addProperty("required", test.isRequired());
		describeFailure(test.getError(), data);
		Reporter.send("test_failed", data);
	}

	@Override
	public void finish() {
	}

	private static void describeFailure(GameTestException error, JsonObject data) {
		if (!(error instanceof TestException failure)) {
			data.addProperty("error", error == null ? "Unknown failure" : Messages.describe(error));
			return;
		}

		data.addProperty("error", failure.getRawMessage());
		data.addProperty("line", failure.getLine());
		data.addProperty("tick", failure.getTick());
	}

	private static JsonObject describe(GameTestInfo test) {
		JsonObject data = new JsonObject();
		data.addProperty("name", test.getTestHolder().key().identifier().toString());
		data.addProperty("time", test.getRunTime());
		return data;
	}

	private static JsonObject describe(GameTestBatch batch) {
		JsonObject data = new JsonObject();
		data.addProperty("batch", batch.index());
		data.addProperty("environment", batch.environment().getRegisteredName());
		data.addProperty("dimension", batch.dimension().identifier().toString());
		return data;
	}
}
