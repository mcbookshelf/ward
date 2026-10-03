package dev.mcbookshelf.ward.commands.assertions;

import java.util.List;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;
import dev.mcbookshelf.ward.test.TestExecutor;

class ChatAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("chat")
				.then(Commands.argument("pattern", StringArgumentType.string())
						.executes(ctx -> mode.check(ctx, attempt -> check(attempt, false)))
						.then(Commands.argument("players", EntityArgument.players())
								.executes(ctx -> mode.check(ctx, attempt -> check(attempt, true))))));
	}

	private static AssertResult check(CommandContext<CommandSourceStack> context, boolean players) throws CommandSyntaxException {
		TestExecutor executor = TestExecutor.current();
		String pattern = StringArgumentType.getString(context, "pattern");
		Pattern compiled = compile(pattern);
		Stream<String> messages = players
				? EntityArgument.getPlayers(context, "players").stream().flatMap(p -> executor.chatMessages(p.getUUID()))
				: executor.chatMessages();
		List<String> received = messages.toList();
		int count = (int) received.stream().filter(msg -> compiled.matcher(msg).find()).count();

		return AssertResult.of(count, negated -> Messages.translatable(
				negated ? "ward.assert.not_chat" : "ward.assert.chat",
				pattern, count, describe(received)));
	}

	private static Pattern compile(String pattern) throws CommandSyntaxException {
		try {
			return Pattern.compile(pattern);
		} catch (PatternSyntaxException e) {
			throw Messages.error("ward.assert.invalid_pattern", pattern);
		}
	}

	private static String describe(List<String> received) {
		if (received.isEmpty()) return "nothing";

		String sample = received.stream()
				.limit(5)
				.map(msg -> '"' + (msg.length() > 80 ? msg.substring(0, 80) + "…" : msg) + '"')
				.collect(Collectors.joining(", "));

		return received.size() > 5 ? sample + " and " + (received.size() - 5) + " more" : sample;
	}
}
