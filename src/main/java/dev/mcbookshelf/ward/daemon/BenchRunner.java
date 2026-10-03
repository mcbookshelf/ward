package dev.mcbookshelf.ward.daemon;

import java.lang.management.ManagementFactory;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

import com.google.common.base.Stopwatch;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import org.jspecify.annotations.Nullable;

import net.minecraft.commands.CommandResultCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.execution.ExecutionContext;
import net.minecraft.commands.execution.TraceCallbacks;
import net.minecraft.commands.functions.CommandFunction;
import net.minecraft.commands.functions.InstantiatedFunction;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.Vec3;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.Ward;

final class BenchRunner implements Runner {
	private static final int MAX_SAMPLES = 100;
	private static final int MIN_SAMPLES = 10;
	private static final long WARMUP_BATCH_NANOS = 10_000_000;
	private static final int MAX_BATCH = 1 << 24;

	private enum Phase { LOAD, START, WARMUP, MEASURE }

	private final MinecraftServer server;
	private final Options options;
	private final ServerLevel level;
	private CommandSourceStack source;
	private Phase phase = Phase.LOAD;
	private int index;

	private @Nullable InstantiatedFunction<CommandSourceStack> body;
	private @Nullable InstantiatedFunction<CommandSourceStack> prepare;
	private final Probe probe = new Probe();
	private int batch;
	private long spent;
	private long allocated;
	private long runs;
	private JsonArray samples = new JsonArray();
	private @Nullable ExecutionContext<CommandSourceStack> context;
	private final Stopwatch stopwatch = Stopwatch.createStarted();

	record Options(List<String> commands, List<String> setup, List<String> prepare, int warmup, int time, int batch) implements Runner.Options {
		static Options parse(JsonObject request) {
			return new Options(
					strings(request, "commands"),
					strings(request, "setup"),
					strings(request, "prepare"),
					request.has("warmup") ? request.get("warmup").getAsInt() : 1000,
					request.has("time") ? request.get("time").getAsInt() : 3000,
					request.has("batch") ? request.get("batch").getAsInt() : 0);
		}

		private static List<String> strings(JsonObject request, String name) {
			return request.has(name)
					? request.getAsJsonArray(name).asList().stream().map(JsonElement::getAsString).toList()
					: List.of();
		}
	}

	BenchRunner(MinecraftServer server, Options options) {
		this.server = server;
		this.options = options;
		this.level = server.overworld();
		this.source = server.getFunctions().getGameLoopSender();
	}

	@Override
	public boolean tick() {
		if (this.index >= this.options.commands().size()) {
			JsonObject data = new JsonObject();
			data.addProperty("elapsed", this.stopwatch.elapsed(TimeUnit.MILLISECONDS));
			Reporter.send("bench_finished", data);
			return true;
		}

		switch (this.phase) {
			case LOAD -> load();
			case START -> start();
			case WARMUP -> warmup();
			case MEASURE -> measure();
		}

		return false;
	}

	private void load() {
		BlockPos origin = BlockPos.ZERO;
		this.level.setChunkForced(0, 0, true);

		if (this.level.isPositionEntityTicking(origin)) {
			int floor = this.level.getHeight(Heightmap.Types.WORLD_SURFACE, origin.getX(), origin.getZ());
			this.source = this.source.withLevel(this.level).withPosition(Vec3.atBottomCenterOf(origin.atY(floor)));
			this.phase = Phase.START;
		}
	}

	private void start() {
		String command = this.options.commands().get(this.index);

		try {
			this.body = compile("body", List.of(command));
			this.prepare = this.options.prepare().isEmpty() ? null : compile("prepare", this.options.prepare());

			if (!this.options.setup().isEmpty()) {
				run(compile("setup", this.options.setup()));
			}
		} catch (IllegalArgumentException e) {
			finish(Messages.describe(e));
			return;
		}

		prepare();
		this.probe.reset();
		run(this.body, this.probe);
		ExecutionContext<CommandSourceStack> used = Objects.requireNonNull(this.context);

		if (used.queueOverflow || used.commandQuota <= 0 && !used.commandQueue.isEmpty()) {
			finish("One run goes over the command chain limit (game rule max_command_sequence_length)");
			return;
		}

		this.batch = Math.max(this.options.batch(), 1);
		this.spent = 0;
		this.phase = Phase.WARMUP;
	}

	private void warmup() {
		long elapsed = timeBatch();
		this.spent += elapsed;

		if (this.spent < this.options.warmup() * 1_000_000L) {
			if (this.options.batch() <= 0 && elapsed < WARMUP_BATCH_NANOS && this.batch < MAX_BATCH) {
				this.batch *= 2;
			}

			return;
		}

		if (this.options.batch() <= 0) {
			double perRun = Math.max((double) elapsed / this.batch, 1);
			long perSample = this.options.time() * 1_000_000L / MAX_SAMPLES;
			this.batch = Math.clamp(Math.round(perSample / perRun), 1, MAX_BATCH);
		}

		this.spent = 0;
		this.allocated = 0;
		this.runs = 0;
		this.phase = Phase.MEASURE;
	}

	private void measure() {
		long before = allocatedBytes();
		long elapsed = timeBatch();
		long after = allocatedBytes();

		this.samples.add(elapsed);
		this.spent += elapsed;
		this.runs += this.batch;
		this.allocated += after - before;

		boolean enough = this.samples.size() >= MIN_SAMPLES && this.spent >= this.options.time() * 1_000_000L;

		if (enough || this.samples.size() >= MAX_SAMPLES) {
			finish(null);
		}
	}

	private long timeBatch() {
		prepare();
		InstantiatedFunction<CommandSourceStack> function = this.body;
		int count = this.batch;
		long start = System.nanoTime();

		for (int i = 0; i < count; i++) {
			run(function);
		}

		return System.nanoTime() - start;
	}

	private void prepare() {
		if (this.prepare != null) {
			run(this.prepare);
		}
	}

	private void finish(@Nullable String failure) {
		JsonObject result = new JsonObject();
		result.addProperty("index", this.index);
		result.addProperty("name", this.options.commands().get(this.index));

		if (failure != null) {
			result.addProperty("failed", failure);
		} else {
			result.addProperty("batch", this.batch);
			result.add("samples", this.samples);
			result.addProperty("commands", this.probe.commands);

			if (this.allocated >= 0 && this.runs > 0) {
				result.addProperty("allocated", this.allocated / this.runs);
			}

			if (this.probe.error != null) {
				result.addProperty("error", this.probe.error);
			}
		}

		Reporter.send("bench_result", result);
		this.samples = new JsonArray();
		this.index++;
		this.phase = Phase.START;
	}

	private InstantiatedFunction<CommandSourceStack> compile(String name, List<String> lines) {
		Identifier id = Identifier.fromNamespaceAndPath(Ward.MOD_ID, "bench/" + this.index + "/" + name);
		CommandFunction<CommandSourceStack> function = CommandFunction.fromLines(id, this.server.getFunctions().getDispatcher(), this.source, lines);

		try {
			return function.instantiate(null, this.server.getFunctions().getDispatcher());
		} catch (Exception e) {
			throw new IllegalArgumentException(Messages.describe(e));
		}
	}

	private void run(InstantiatedFunction<CommandSourceStack> function) {
		run(function, null);
	}

	private void run(InstantiatedFunction<CommandSourceStack> function, @Nullable TraceCallbacks tracer) {
		Commands.executeCommandInContext(this.source, used -> {
			this.context = used;
			used.tracer(tracer);
			ExecutionContext.queueInitialFunctionCall(used, function, this.source, CommandResultCallback.EMPTY);
		});
	}

	private static long allocatedBytes() {
		return ManagementFactory.getThreadMXBean() instanceof com.sun.management.ThreadMXBean threads
				? threads.getCurrentThreadAllocatedBytes()
				: -1;
	}

	private static final class Probe implements TraceCallbacks {
		private int commands;
		private @Nullable String error;

		void reset() {
			this.commands = 0;
			this.error = null;
		}

		@Override
		public void onCommand(int depth, String command) {
			this.commands++;
		}

		@Override
		public void onReturn(int depth, String command, int result) {
		}

		@Override
		public void onError(String message) {
			if (this.error == null) {
				this.error = message;
			}
		}

		@Override
		public void onCall(int depth, Identifier function, int size) {
		}

		@Override
		public void close() {
		}
	}
}
