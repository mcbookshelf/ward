package dev.mcbookshelf.ward.test;

import java.util.ArrayList;
import java.util.List;
import java.util.ListIterator;
import java.util.function.Consumer;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.StringReader;
import com.mojang.brigadier.context.ContextChain;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import org.jspecify.annotations.Nullable;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.execution.tasks.BuildContexts;
import net.minecraft.commands.functions.CommandFunction;
import net.minecraft.commands.functions.MacroFunction;
import net.minecraft.commands.functions.StringTemplate;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.Identifier;

/**
 * A compiled test file, or one case of it when the file has cases: arguments is then set.
 */
public record TestFunction(Identifier id, @Nullable CompoundTag arguments, List<Entry> commands, TestDirectives directives)
		implements Consumer<GameTestHelper> {
	public record Entry(String command, ContextChain<CommandSourceStack> chain, int line) {
	}

	private record Line(String text, int number) {
	}

	@Override
	public void accept(GameTestHelper helper) {
		new TestExecutor(helper).run(this);
	}

	/**
	 * A case reports under the id of its file and its arguments.
	 */
	public String name(Identifier instance) {
		return this.arguments == null ? instance.toString() : this.id + " " + this.arguments;
	}

	public static @Nullable TestFunction caseOf(Identifier instance) {
		return BuiltInRegistries.TEST_FUNCTION.getValue(instance) instanceof TestFunction test && test.arguments != null ? test : null;
	}

	/**
	 * One test for a plain file, or one for each of its cases.
	 */
	public static List<TestFunction> fromLines(
			Identifier id,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandSourceStack context,
			List<String> lines) {
		TestDirectives.Builder builder = new TestDirectives.Builder();
		List<Line> commands = new ArrayList<>();
		ListIterator<String> remaining = lines.listIterator();

		while (remaining.hasNext()) {
			int line = remaining.nextIndex() + 1;
			String command = readCommand(remaining);

			if (command.isEmpty()) continue;
			CommandFunction.checkCommandLineLength(command);

			if (command.startsWith("#")) {
				// A directive only counts in the header, before the first command
				if (commands.isEmpty()) parseDirective(command, line, builder);
				continue;
			}

			commands.add(new Line(command, line));
		}

		TestDirectives directives = builder.build();

		if (directives.cases().isEmpty()) {
			return List.of(new TestFunction(id, null, compile(dispatcher, context, commands, null), directives));
		}

		List<TestFunction> cases = new ArrayList<>();

		for (CompoundTag arguments : directives.cases()) {
			try {
				cases.add(new TestFunction(id, arguments, compile(dispatcher, context, commands, arguments), directives));
			} catch (IllegalArgumentException e) {
				throw new IllegalArgumentException("Case " + arguments + ": " + e.getMessage());
			}
		}

		return cases;
	}

	private static String readCommand(ListIterator<String> lines) {
		StringBuilder command = new StringBuilder(lines.next().trim());

		while (!command.isEmpty() && command.charAt(command.length() - 1) == '\\') {
			if (!lines.hasNext()) throw new IllegalArgumentException("Line continuation at end of file");
			command.deleteCharAt(command.length() - 1);
			command.append(lines.next().trim());
			CommandFunction.checkCommandLineLength(command);
		}

		return command.toString();
	}

	private static List<Entry> compile(
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandSourceStack context,
			List<Line> lines,
			@Nullable CompoundTag arguments) {
		List<Entry> commands = new ArrayList<>();

		for (Line line : lines) {
			String command = line.text().startsWith("$") ? substitute(line, arguments) : line.text();
			commands.add(new Entry(command, parseCommand(dispatcher, context, command, line.number()), line.number()));
		}

		return commands;
	}

	private static String substitute(Line line, @Nullable CompoundTag arguments) {
		if (arguments == null) {
			throw new IllegalArgumentException("Macro line on line " + line.number() + ": the test has no @cases");
		}

		try {
			StringTemplate template = StringTemplate.fromString(line.text().substring(1));
			return template.substitute(template.variables().stream().map(variable -> value(arguments, variable)).toList());
		} catch (IllegalArgumentException e) {
			throw new IllegalArgumentException("Macro line on line " + line.number() + ": " + e.getMessage());
		}
	}

	private static String value(CompoundTag arguments, String variable) {
		Tag value = arguments.get(variable);
		if (value == null) throw new IllegalArgumentException("No value for '" + variable + "'");
		return MacroFunction.stringify(value);
	}

	@SuppressWarnings("unchecked")
	private static ContextChain<CommandSourceStack> parseCommand(
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandSourceStack context,
			String command,
			int line) {
		if (command.startsWith("/")) {
			throw new IllegalArgumentException("Unknown or invalid command '" + command + "' on line " + line + " (do not use a preceding forwards slash)");
		}

		try {
			return ((BuildContexts<CommandSourceStack>) CommandFunction.parseCommand(dispatcher, context, new StringReader(command))).command;
		} catch (CommandSyntaxException e) {
			throw new IllegalArgumentException("Whilst parsing command on line " + line + ": " + e.getMessage());
		}
	}

	private static void parseDirective(String comment, int line, TestDirectives.Builder directives) {
		StringReader reader = new StringReader(comment);
		reader.skip();
		reader.skipWhitespace();

		if (!reader.canRead() || reader.peek() != '@') {
			return;
		}

		reader.skip();
		String name = reader.readUnquotedString();
		reader.skipWhitespace();
		String value = reader.canRead() ? reader.getRemaining() : null;

		try {
			directives.add(name, value);
		} catch (RuntimeException e) {
			throw new IllegalArgumentException("Invalid directive @" + name + " on line " + line + ": " + e.getMessage());
		}
	}
}
