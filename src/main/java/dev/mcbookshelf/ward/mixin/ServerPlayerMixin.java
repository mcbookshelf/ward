package dev.mcbookshelf.ward.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;

import dev.mcbookshelf.ward.ChatRecorder;

@Mixin(ServerPlayer.class)
public class ServerPlayerMixin {
	@Inject(method = "sendSystemMessage(Lnet/minecraft/network/chat/Component;Z)V", at = @At("HEAD"))
	private void sendSystemMessage(Component message, boolean overlay, CallbackInfo ci) {
		ServerPlayer player = (ServerPlayer) (Object) this;
		ChatRecorder.record(player.getUUID(), message.getString());
	}
}
