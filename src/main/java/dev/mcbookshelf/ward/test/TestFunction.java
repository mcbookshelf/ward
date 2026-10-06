package dev.mcbookshelf.ward.test;

import java.util.ArrayList;
import java.util.List;
import java.util.ListIterator;
import java.util.function.Consumer;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.StringReader;
import com.mojang.brigadier.context.ContextChain;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.execution.tasks.BuildContexts;
import net.minecraft.commands.functions.CommandFunction;
import net.minecraft.gametest.framework.GameTestHelper;

public record TestFunction(List<Entry> commands, TestDirectives directives) implements Consumer<GameTestHelper> {
	public record Entry(String command, ContextChain<CommandSourceStack> chain, int line) {
	}

	@Override
	public void accept(GameTestHelper helper) {
		new TestExecutor(helper).run(this);
	}

	public static TestFunction fromLines(
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandSourceStack context,
			List<String> lines) {
		TestDirectives.Builder directives = new TestDirectives.Builder();
		List<Entry> commands = new ArrayList<>();
		ListIterator<String> remaining = lines.listIterator();

		while (remaining.hasNext()) {
			int line = remaining.nextIndex() + 1;
			String command = readCommand(remaining);

			if (command.isEmpty()) continue;
			CommandFunction.checkCommandLineLength(command);

			if (command.startsWith("#")) {
				if (commands.isEmpty()) parseDirective(command, line, directives);
				continue;
			}

			commands.add(new Entry(command, parseCommand(dispatcher, context, command, line), line));
		}

		return new TestFunction(commands, directives.build());
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

	@SuppressWarnings("unchecked")
	private static ContextChain<CommandSourceStack> parseCommand(
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandSourceStack context,
			String command,
			int line) {
		if (command.startsWith("/")) {
			throw new IllegalArgumentException("Unknown or invalid command '" + command + "' on line " + line + " (do not use a preceding forwards slash)");
		}

		if (command.startsWith("$")) {
			throw new IllegalArgumentException("Macro line on line " + line + ": tests take no macro arguments");
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
