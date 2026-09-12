package dev.mcbookshelf.ward;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.brigadier.context.ContextChain;

import net.minecraft.commands.execution.UnboundEntryAction;
import net.minecraft.commands.execution.tasks.BuildContexts;
import net.minecraft.commands.functions.InstantiatedFunction;
import net.minecraft.resources.Identifier;

import dev.mcbookshelf.ward.accessor.CoverageLineHolder;

/**
 * Records which function commands run during a coverage-enabled run.
 * A command is reached when its entry starts executing and executed when it dispatches with at least one source left.
 */
public final class CoverageRecorder {
	private static volatile boolean enabled;
	private static final Map<Identifier, Counters> functions = new ConcurrentHashMap<>();
	private static final Map<Identifier, Identifier> macroAliases = new ConcurrentHashMap<>();
	private static final Map<InstantiatedFunction<?>, List<?>> instrumented =
			Collections.synchronizedMap(new IdentityHashMap<>());

	/**
	 * Where a compiled command records its execution, stamped on every stage of its chain.
	 */
	public record Line(int[] executed, int index) {}

	private record Counters(int[] reached, int[] executed) {}

	private CoverageRecorder() {
	}

	public static boolean isEnabled() {
		return enabled;
	}

	public static void enable() {
		enabled = true;
	}

	public static void disable() {
		enabled = false;
		functions.clear();
		macroAliases.clear();
		instrumented.clear();
		DataCoverage.clear();
	}

	public static void registerMacroAlias(Identifier instantiated, Identifier original) {
		macroAliases.put(instantiated, original);
	}

	@SuppressWarnings("unchecked")
	public static <T> List<UnboundEntryAction<T>> instrument(
			InstantiatedFunction<T> function,
			List<UnboundEntryAction<T>> entries) {
		return (List<UnboundEntryAction<T>>) instrumented
				.computeIfAbsent(function, key -> build(function.id(), entries));
	}

	public static void recordExecuted(ContextChain<?> chain) {
		Line line = ((CoverageLineHolder) (Object) chain).ward$coverageLine();

		if (line != null) {
			line.executed()[line.index()]++;
		}
	}

	/**
	 * Serializes the counts, clearing them for the next run.
	 */
	public static JsonObject drain() {
		JsonObject report = new JsonObject();
		JsonObject functionCounts = new JsonObject();

		for (Map.Entry<Identifier, Counters> entry : functions.entrySet()) {
			JsonObject function = new JsonObject();
			function.add("reached", toJsonArray(entry.getValue().reached()));
			function.add("executed", toJsonArray(entry.getValue().executed()));
			functionCounts.add(entry.getKey().toString(), function);
		}

		report.add("functions", functionCounts);
		report.add("conditions", DataCoverage.drainConditions());
		report.add("runs", DataCoverage.drainRuns());
		functions.clear();
		macroAliases.clear();
		instrumented.clear();
		return report;
	}

	private static <T> List<UnboundEntryAction<T>> build(Identifier id, List<UnboundEntryAction<T>> entries) {
		Identifier function = macroAliases.getOrDefault(id, id);
		Counters counters = functions.computeIfAbsent(function,
				key -> new Counters(new int[entries.size()], new int[entries.size()]));
		List<UnboundEntryAction<T>> wrapped = new ArrayList<>(entries.size());
		int[] reached = counters.reached();

		for (int i = 0; i < entries.size(); i++) {
			UnboundEntryAction<T> entry = entries.get(i);

			if (entry instanceof BuildContexts<?> contexts) {
				stamp(contexts.command, new Line(counters.executed(), i));
			}

			int index = i;
			wrapped.add((sender, context, frame) -> {
				reached[index]++;
				entry.execute(sender, context, frame);
			});
		}

		return wrapped;
	}

	/**
	 * Every stage gets the line, so continuations scheduled by custom modifiers (like {@code execute if function}) still attribute to it.
	 */
	private static void stamp(ContextChain<?> chain, Line line) {
		for (ContextChain<?> stage = chain; stage != null; stage = stage.nextStage()) {
			((CoverageLineHolder) (Object) stage).ward$coverageLine(line);

			if (stage.getStage() == ContextChain.Stage.EXECUTE) {
				return;
			}
		}
	}

	private static JsonArray toJsonArray(int[] counts) {
		JsonArray array = new JsonArray();

		for (int count : counts) {
			array.add(count);
		}

		return array;
	}
}
