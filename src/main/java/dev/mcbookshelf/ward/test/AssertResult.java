package dev.mcbookshelf.ward.test;

import java.util.function.Function;

import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentUtils;

public record AssertResult(int count, boolean errored, Function<Boolean, Component> message) {
	public static AssertResult of(boolean success, Function<Boolean, Component> message) {
		return of(success ? 1 : 0, message);
	}

	public static AssertResult of(int count, Function<Boolean, Component> message) {
		return new AssertResult(count, false, message);
	}

	public static AssertResult error(CommandSyntaxException e) {
		Component message = ComponentUtils.fromMessage(e.getRawMessage());
		return new AssertResult(0, true, _ -> message);
	}
}
