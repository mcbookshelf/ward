package dev.mcbookshelf.ward.coverage;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.brigadier.context.ContextChain;

import net.minecraft.commands.execution.UnboundEntryAction;
import net.minecraft.commands.execution.tasks.BuildContexts;
import net.minecraft.resources.Identifier;

public final class FunctionCoverage {
	private static final Map<Identifier, Counters> FUNCTIONS = new ConcurrentHashMap<>();

	public record Line(int[] reached, int[] executed, int index) {}
	private record Counters(int[] reached, int[] executed) {}

	private FunctionCoverage() {
	}

	public static void stamp(Identifier function, List<? extends UnboundEntryAction<?>> entries) {
		if (!Coverage.isEnabled()) {
			return;
		}

		Counters counters = FUNCTIONS.computeIfAbsent(function,
				_ -> new Counters(new int[entries.size()], new int[entries.size()]));

		for (int i = 0; i < entries.size(); i++) {
			if (entries.get(i) instanceof BuildContexts<?> contexts) {
				stamp(contexts.command, new Line(counters.reached(), counters.executed(), i));
			}
		}
	}

	private static void stamp(ContextChain<?> command, Line line) {
		for (ContextChain<?> stage = command; stage != null; stage = stage.nextStage()) {
			((CoverageLineHolder) (Object) stage).ward$coverageLine(line);
		}
	}

	public static void recordReached(ContextChain<?> chain) {
		Line line = ((CoverageLineHolder) (Object) chain).ward$coverageLine();

		if (line != null) {
			line.reached()[line.index()]++;
		}
	}

	public static void recordExecuted(ContextChain<?> chain) {
		Line line = ((CoverageLineHolder) (Object) chain).ward$coverageLine();

		if (line != null) {
			line.executed()[line.index()]++;
		}
	}

	static void clear() {
		FUNCTIONS.clear();
	}

	static JsonObject report() {
		JsonObject report = new JsonObject();

		FUNCTIONS.forEach((id, counters) -> {
			if (Arrays.stream(counters.reached()).anyMatch(count -> count > 0)) {
				JsonObject function = new JsonObject();
				function.add("reached", toJson(counters.reached()));
				function.add("executed", toJson(counters.executed()));
				report.add(id.toString(), function);
			}
		});

		return report;
	}

	private static JsonArray toJson(int[] counts) {
		JsonArray array = new JsonArray();
		Arrays.stream(counts).forEach(array::add);
		return array;
	}
}
