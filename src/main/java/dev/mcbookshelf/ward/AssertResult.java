package dev.mcbookshelf.ward;

import java.util.function.Function;

import net.minecraft.network.chat.Component;

/**
 * Result of an assertion check. A {@code count > 0} means the condition is met.
 */
public record AssertResult(int count, boolean errored, Function<Boolean, Component> message) {
	public AssertResult(int count, Function<Boolean, Component> message) {
		this(count, false, message);
	}

	public static AssertResult of(int count, String type, Object... args) {
		return new AssertResult(count, negated -> Component.translatable(translationKey(type, negated), args));
	}

	public static AssertResult error(Component message) {
		return new AssertResult(0, true, _ -> message);
	}

	private static String translationKey(String type, boolean negated) {
		return "ward.assert." + (negated ? "not_" : "") + type;
	}
}
