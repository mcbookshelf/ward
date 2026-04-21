package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.ModifyReturnValue;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.exceptions.SimpleCommandExceptionType;
import dev.mcbookshelf.ward.TestContext;
import dev.mcbookshelf.ward.accessor.TestContextAccessor;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;

/**
 * Stores test context in CommandSourceStack for Ward commands.
 * <p>
 * Allows /fail, /assert, /await to access the TestContext. The context is set
 * before each command execution and propagated through with*() methods
 * to maintain context across /execute modifiers and function calls.
 */
@Mixin(CommandSourceStack.class)
public abstract class CommandSourceStackMixin implements TestContextAccessor {

    @Unique
    private TestContext ward$context;

    public void ward$setContext(TestContext context) {
        this.ward$context = context;
    }

    public TestContext ward$getContext() throws CommandSyntaxException {
        if (this.ward$context != null) return this.ward$context;
        throw new SimpleCommandExceptionType(Component.translatable("ward.not_in_test")).create();
    }

    @ModifyReturnValue(method = {
        "withSource",
        "withEntity",
        "withPosition",
        "withRotation",
        "withSuppressedOutput",
        "withPermission",
        "withMaximumPermission",
        "withAnchor",
        "withLevel"
    }, at = @At("RETURN"))
    private CommandSourceStack with(CommandSourceStack original) {
        ((CommandSourceStackMixin) (Object) original).ward$context = this.ward$context;
        return original;
    }

    @ModifyReturnValue(method = "withCallback(Lnet/minecraft/commands/CommandResultCallback;)Lnet/minecraft/commands/CommandSourceStack;", at = @At("RETURN"))
    private CommandSourceStack withCallback(CommandSourceStack original) {
        ((CommandSourceStackMixin) (Object) original).ward$context = this.ward$context;
        return original;
    }
}
