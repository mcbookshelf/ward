package dev.mcbookshelf.ward.test;

import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.network.chat.Component;

import dev.mcbookshelf.ward.Messages;

public class TestException extends GameTestAssertException {
	private final int line;

	public TestException(Component message, int line, long tick) {
		super(message, (int) tick);
		this.line = line;
	}

	public int getLine() {
		return this.line;
	}

	public long getTick() {
		return this.tick;
	}

	public String getRawMessage() {
		return this.message.getString();
	}

	@Override
	public Component getDescription() {
		return Messages.translatable("ward.error", this.message, this.line, this.tick);
	}
}
