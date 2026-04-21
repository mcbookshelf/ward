package dev.mcbookshelf.ward.accessor;

import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import dev.mcbookshelf.ward.TestContext;
import net.minecraft.commands.CommandSourceStack;

/**
 * Duck interface for accessing TestContext from CommandSourceStack via mixin.
 * <p>
 * This interface is implemented by CommandSourceStackMixin to store and retrieve
 * the current test context for Ward commands.
 */
public interface TestContextAccessor {
    /**
     * Injects the current test context into this CommandSourceStack.
     */
    void ward$setContext(TestContext context);

    /**
     * Retrieves the current test context from this CommandSourceStack.
     */
    TestContext ward$getContext() throws CommandSyntaxException;

    /**
     * Retrieves the current test context from a CommandContext.
     */
    static TestContext getContext(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
        return getContext(context.getSource());
    }

    /**
     * Retrieves the current test context from a CommandSourceStack.
     */
    static TestContext getContext(CommandSourceStack source) throws CommandSyntaxException {
        return ((TestContextAccessor) source).ward$getContext();
    }
}
