package dev.mcbookshelf.ward.commands.assertions;

import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;
import java.util.stream.Stream;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.exceptions.DynamicCommandExceptionType;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.network.chat.Component;

import dev.mcbookshelf.ward.AssertResult;
import dev.mcbookshelf.ward.TestExecutor;

class ChatAssertion implements Assertion {
	private static final DynamicCommandExceptionType ERROR_INVALID_PATTERN = new DynamicCommandExceptionType(
			pattern -> Component.translatableEscape("ward.assert.invalid_pattern", pattern));

	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context context) {
		root.then(Commands.literal("chat")
				.then(Commands.argument("pattern", StringArgumentType.string())
						.executes(ctx -> run(ctx, context, false))
						.then(Commands.argument("players", EntityArgument.players())
								.executes(ctx -> run(ctx, context, true)))));
	}

	private static int run(CommandContext<CommandSourceStack> context, Context assertion, boolean players) throws CommandSyntaxException {
		TestExecutor executor = TestExecutor.current();
		String patternString = StringArgumentType.getString(context, "pattern");
		Pattern pattern = compilePattern(patternString);

		return assertion.apply(() -> {
			Stream<String> messages = players
					? EntityArgument.getPlayers(context, "players").stream().flatMap(player -> executor.chatMessages(player.getUUID()))
					: executor.chatMessages();
			int count = (int) messages.filter(msg -> pattern.matcher(msg).find()).count();

			return AssertResult.of(count, "chat", patternString, count);
		});
	}

	private static Pattern compilePattern(String pattern) throws CommandSyntaxException {
		try {
			return Pattern.compile(pattern);
		} catch (PatternSyntaxException e) {
			throw ERROR_INVALID_PATTERN.create(pattern);
		}
	}
}
