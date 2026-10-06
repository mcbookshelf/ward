package dev.mcbookshelf.ward;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.exceptions.SimpleCommandExceptionType;

import net.minecraft.locale.Language;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;

public final class Messages {
	private Messages() {
	}

	public static CommandSyntaxException error(String key, Object... args) {
		return new SimpleCommandExceptionType(translatable(key, args)).create();
	}

	public static MutableComponent translatable(String key, Object... args) {
		return Component.translatableWithFallback(key, Language.getInstance().getOrDefault(key), args);
	}

	public static String describe(Throwable error) {
		String message = error.getMessage();
		return message == null
				? error.getClass().getSimpleName()
				: message.replaceFirst("^[A-Za-z0-9.$]+(Exception|Error): ", "");
	}
}
