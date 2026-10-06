package dev.mcbookshelf.ward.mixin;

import java.util.function.Function;
import java.util.function.Predicate;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import com.mojang.authlib.GameProfile;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.network.Connection;
import net.minecraft.network.chat.ChatType;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.PlayerChatMessage;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import net.minecraft.server.players.NameAndId;
import net.minecraft.server.players.PlayerList;
import net.minecraft.server.players.UserNameToIdResolver;

import dev.mcbookshelf.ward.dummy.Dummy;
import dev.mcbookshelf.ward.dummy.FakeGamePacketListener;
import dev.mcbookshelf.ward.test.ChatRecorder;

@Mixin(PlayerList.class)
public abstract class PlayerListMixin {
	@Inject(method = "save", at = @At("HEAD"), cancellable = true)
	private void skipSave(ServerPlayer player, CallbackInfo info) {
		if (player instanceof Dummy) {
			info.cancel();
		}
	}

	@WrapMethod(method = "broadcastSystemMessage(Lnet/minecraft/network/chat/Component;Ljava/util/function/Function;Z)V")
	private void recordBroadcast(Component message, Function<ServerPlayer, Component> playerMessages, boolean overlay, Operation<Void> original) {
		ChatRecorder.broadcast(message.getString(), () -> original.call(message, playerMessages, overlay));
	}

	@WrapMethod(method = "broadcastChatMessage(Lnet/minecraft/network/chat/PlayerChatMessage;Ljava/util/function/Predicate;Lnet/minecraft/server/level/ServerPlayer;Lnet/minecraft/network/chat/ChatType$Bound;)V")
	private void recordChatBroadcast(
			PlayerChatMessage message,
			Predicate<ServerPlayer> isFiltered,
			ServerPlayer senderPlayer,
			ChatType.Bound chatType,
			Operation<Void> original) {
		ChatRecorder.broadcast(message.decoratedContent().getString(), () -> original.call(message, isFiltered, senderPlayer, chatType));
	}

	@WrapOperation(method = "placeNewPlayer", at = @At(value = "INVOKE", target = "Lnet/minecraft/server/players/UserNameToIdResolver;add(Lnet/minecraft/server/players/NameAndId;)V"))
	private void skipNameCache(
			UserNameToIdResolver cache,
			NameAndId profile,
			Operation<Void> original,
			@Local(argsOnly = true) ServerPlayer player) {
		if (!(player instanceof Dummy)) {
			original.call(cache, profile);
		}
	}

	@WrapOperation(method = "placeNewPlayer", at = @At(value = "NEW", target = "(Lnet/minecraft/server/MinecraftServer;Lnet/minecraft/network/Connection;Lnet/minecraft/server/level/ServerPlayer;Lnet/minecraft/server/network/CommonListenerCookie;)Lnet/minecraft/server/network/ServerGamePacketListenerImpl;"))
	private ServerGamePacketListenerImpl replacePacketListener(
			MinecraftServer server,
			Connection connection,
			ServerPlayer player,
			CommonListenerCookie cookie,
			Operation<ServerGamePacketListenerImpl> original) {
		return player instanceof Dummy dummy
				? new FakeGamePacketListener(server, connection, dummy, cookie)
				: original.call(server, connection, player, cookie);
	}

	@WrapOperation(method = "respawn", at = @At(value = "NEW", target = "(Lnet/minecraft/server/MinecraftServer;Lnet/minecraft/server/level/ServerLevel;Lcom/mojang/authlib/GameProfile;Lnet/minecraft/server/level/ClientInformation;)Lnet/minecraft/server/level/ServerPlayer;"))
	private ServerPlayer replacePlayer(
			MinecraftServer server,
			ServerLevel level,
			GameProfile profile,
			ClientInformation clientInformation,
			Operation<ServerPlayer> original,
			@Local(argsOnly = true) ServerPlayer player) {
		return player instanceof Dummy dummy
				? new Dummy(server, level, profile, clientInformation, dummy.spawnDimension, dummy.spawnPosition, dummy.spawnRotation)
				: original.call(server, level, profile, clientInformation);
	}
}
