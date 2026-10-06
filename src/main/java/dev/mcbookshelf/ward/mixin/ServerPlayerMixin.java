package dev.mcbookshelf.ward.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.network.chat.ChatType;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.OutgoingChatMessage;
import net.minecraft.server.level.ServerPlayer;

import dev.mcbookshelf.ward.test.ChatRecorder;

@Mixin(ServerPlayer.class)
public class ServerPlayerMixin {
	@Inject(method = "sendSystemMessage(Lnet/minecraft/network/chat/Component;Z)V", at = @At("HEAD"))
	private void recordSystemMessage(Component message, boolean overlay, CallbackInfo info) {
		record(message);
	}

	@Inject(method = "sendChatMessage", at = @At(value = "INVOKE", target = "Lnet/minecraft/network/chat/OutgoingChatMessage;sendToPlayer(Lnet/minecraft/server/level/ServerPlayer;ZLnet/minecraft/network/chat/ChatType$Bound;)V"))
	private void recordChatMessage(OutgoingChatMessage message, boolean filtered, ChatType.Bound chatType, CallbackInfo info) {
		record(message.content());
	}

	@Unique
	private void record(Component message) {
		ServerPlayer player = (ServerPlayer) (Object) this;
		ChatRecorder.record(player.getUUID(), message.getString());
	}
}
