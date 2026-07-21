package dev.mcbookshelf.ward;

import net.minecraft.gametest.framework.GameTestException;
import net.minecraft.network.chat.Component;

public class TestException extends GameTestException {
	private final Component message;
	private final int line;
	private final long tick;

	public TestException(final Component message, final int line, final long tick) {
		super(message.getString());
		this.message = message;
		this.line = line;
		this.tick = tick;
	}

	public int getLine() {
		return this.line;
	}

	public long getTick() {
		return this.tick;
	}

	public String getMessage() {
		return this.getDescription().getString();
	}

	public String getRawMessage() {
		return this.message.getString();
	}

	public Component getDescription() {
		return Component.translatable("ward.error", this.message, this.line, this.tick);
	}
}
