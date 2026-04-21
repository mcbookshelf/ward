package dev.mcbookshelf.ward.mixin;

import dev.mcbookshelf.ward.ChatRecorder;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ServerPlayer.class)
public class ServerPlayerMixin {

    @Inject(method = "sendSystemMessage(Lnet/minecraft/network/chat/Component;Z)V", at = @At("HEAD"))
    private void sendSystemMessage(Component message, boolean overlay, CallbackInfo ci) {
        ChatRecorder.record(((ServerPlayer) (Object) this).getUUID(), message.getString());
    }
}
