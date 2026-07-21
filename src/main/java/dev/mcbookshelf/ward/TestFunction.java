package dev.mcbookshelf.ward;

import java.util.ArrayList;
import java.util.List;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.ParseResults;
import com.mojang.brigadier.StringReader;
import com.mojang.brigadier.context.ContextChain;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.functions.CommandFunction;
import net.minecraft.gametest.framework.GameTestHelper;

/**
 * A test parsed from a function file, with its commands and directives.
 */
public record TestFunction(List<Entry> commands, TestDirectives directives) {
	public record Entry(String command, ContextChain<CommandSourceStack> chain, int line) {
	}

	public void run(GameTestHelper helper) {
		TestExecutor test = new TestExecutor(helper, this.directives().maxTicks());
		test.run(this);
	}

	public static TestFunction fromLines(
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandSourceStack context,
			List<String> lines) throws IllegalArgumentException {
		TestDirectives.Builder directives = new TestDirectives.Builder();
		List<Entry> commands = new ArrayList<>();

		int i = 0;

		while (i < lines.size()) {
			final int line = i + 1;
			StringBuilder builder = new StringBuilder(lines.get(i++).trim());

			while (!builder.isEmpty() && builder.charAt(builder.length() - 1) == '\\') {
				if (i >= lines.size()) {
					throw new IllegalArgumentException("Line continuation at end of file");
				}

				builder.deleteCharAt(builder.length() - 1);
				builder.append(lines.get(i++).trim());
				CommandFunction.checkCommandLineLength(builder);
			}

			String command = builder.toString();

			if (command.isEmpty()) continue;

			CommandFunction.checkCommandLineLength(command);
			StringReader reader = new StringReader(command);

			if (!reader.canRead()) continue;

			if (reader.peek() == '#') {
				parseDirective(reader, line, directives);
				continue;
			}

			try {
				commands.add(new Entry(command, parseCommand(dispatcher, context, command), line));
			} catch (CommandSyntaxException e) {
				throw new IllegalArgumentException("Whilst parsing command on line " + line + ": " + e.getMessage());
			}
		}

		return new TestFunction(commands, directives.build());
	}

	private static void parseDirective(
			StringReader reader,
			int line,
			TestDirectives.Builder directives) throws IllegalArgumentException {
		reader.skip();
		reader.skipWhitespace();

		if (reader.canRead() && reader.peek() == '@') {
			reader.skip();
			String name = reader.readUnquotedString();
			reader.skipWhitespace();
			String value = reader.canRead() ? reader.getRemaining() : null;

			try {
				directives.add(name, value);
			} catch (Exception e) {
				throw new IllegalArgumentException("Invalid directive @" + name + " on line " + line + ": " + e.getMessage());
			}
		}
	}

	private static ContextChain<CommandSourceStack> parseCommand(
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandSourceStack context,
			String command) throws CommandSyntaxException {
		ParseResults<CommandSourceStack> parseResults = dispatcher.parse(command, context);
		Commands.validateParseResults(parseResults);

		return ContextChain.tryFlatten(parseResults.getContext().build(command))
				.orElseThrow(() -> CommandSyntaxException.BUILT_IN_EXCEPTIONS
						.dispatcherUnknownCommand()
						.createWithContext(parseResults.getReader()));
	}
}
