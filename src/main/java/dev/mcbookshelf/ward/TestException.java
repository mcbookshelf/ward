package dev.mcbookshelf.ward;

import net.minecraft.gametest.framework.GameTestException;
import net.minecraft.network.chat.Component;

public class TestException extends GameTestException {
    protected final Component message;
    protected final int line;
    protected final long tick;

    public TestException(final Component message, final int line, final long tick) {
        super(message.getString());
        this.message = message;
        this.line = line;
        this.tick = tick;
    }

    public Component getDescription() {
        return Component.translatable("ward.error", this.message, this.line, this.tick);
    }

    public String getMessage() {
        return this.getDescription().getString();
    }
}
