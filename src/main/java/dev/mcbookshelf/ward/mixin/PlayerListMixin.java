package dev.mcbookshelf.ward.mixin;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.function.Predicate;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import com.mojang.authlib.GameProfile;
import net.fabricmc.fabric.impl.networking.PacketListenerExtensions;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.network.Connection;
import net.minecraft.network.chat.ChatType;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.PlayerChatMessage;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.PlayerAdvancements;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import net.minecraft.server.players.PlayerList;
import net.minecraft.stats.ServerStatsCounter;
import net.minecraft.util.Util;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.storage.LevelResource;

import dev.mcbookshelf.ward.ChatRecorder;
import dev.mcbookshelf.ward.dummy.Dummy;
import dev.mcbookshelf.ward.dummy.FakeGamePacketListener;

/**
 * Dummies never touch the disk: their stats and advancements live here, in memory, and saves are skipped.
 */
@Mixin(PlayerList.class)
public abstract class PlayerListMixin {
	@Unique
	private static final LevelResource STATS_DIR = new LevelResource("ward/stats");

	@Unique
	private static final LevelResource ADVANCEMENTS_DIR = new LevelResource("ward/advancements");

	@Shadow
	@Final
	private MinecraftServer server;
	@Unique
	private final Map<UUID, ServerStatsCounter> ward$stats = new HashMap<>();
	@Unique
	private final Map<UUID, PlayerAdvancements> ward$advancements = new HashMap<>();

	@Inject(method = "save", at = @At(value = "HEAD"), cancellable = true)
	private void skipSave(ServerPlayer player, CallbackInfo ci) {
		if (player instanceof Dummy) {
			ci.cancel();
		}
	}

	@Inject(method = "broadcastSystemMessage(Lnet/minecraft/network/chat/Component;Ljava/util/function/Function;Z)V", at = @At("HEAD"))
	private void recordBroadcast(Component message, Function<ServerPlayer, Component> playerMessages, boolean overlay, CallbackInfo ci) {
		this.ward$recordServerCopy(message);
	}

	@Inject(method = "broadcastChatMessage(Lnet/minecraft/network/chat/PlayerChatMessage;Ljava/util/function/Predicate;Lnet/minecraft/server/level/ServerPlayer;Lnet/minecraft/network/chat/ChatType$Bound;)V", at = @At("HEAD"))
	private void recordChatBroadcast(
			PlayerChatMessage message,
			Predicate<ServerPlayer> isFiltered,
			ServerPlayer senderPlayer,
			ChatType.Bound chatType,
			CallbackInfo ci) {
		this.ward$recordServerCopy(message.decoratedContent());
	}

	/**
	 * Chat assertions see broadcasts even when no player is online to receive them.
	 */
	@Unique
	private void ward$recordServerCopy(Component message) {
		ChatRecorder.record(Util.NIL_UUID, message.getString());
	}

	@Inject(method = "remove", at = @At("RETURN"))
	private void removeDummyData(ServerPlayer player, CallbackInfo ci) {
		if (player instanceof Dummy) {
			this.ward$stats.remove(player.getUUID());
			this.ward$advancements.remove(player.getUUID());

			// Fabric untracks its per-player network addon from a global registry when the netty
			// channel goes inactive, which a fake connection never does: without this, every dummy
			// pins its whole server in the daemon until the JVM runs out of memory
			if (player.connection instanceof PacketListenerExtensions extensions) {
				extensions.getAddon().handleDisconnect();
			}
		}
	}

	@Inject(method = "getPlayerStats", at = @At("HEAD"), cancellable = true)
	private void getDummyStats(Player player, CallbackInfoReturnable<ServerStatsCounter> ci) {
		if (player instanceof Dummy) {
			ci.setReturnValue(this.ward$stats.computeIfAbsent(player.getUUID(), uuid -> new ServerStatsCounter(
					this.server,
					this.server.getWorldPath(STATS_DIR).resolve(uuid + ".json"))));
		}
	}

	@Inject(method = "getPlayerAdvancements", at = @At("HEAD"), cancellable = true)
	private void getDummyAdvancements(ServerPlayer player, CallbackInfoReturnable<PlayerAdvancements> ci) {
		if (player instanceof Dummy) {
			PlayerAdvancements result = this.ward$advancements.computeIfAbsent(player.getUUID(), uuid -> new PlayerAdvancements(
					this.server.getFixerUpper(),
					(PlayerList) (Object) this,
					this.server.getAdvancements(),
					this.server.getWorldPath(ADVANCEMENTS_DIR).resolve(uuid + ".json"),
					player));
			// Respawn creates a new Dummy instance, so rebind the reference
			result.setPlayer(player);
			ci.setReturnValue(result);
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
				? new FakeGamePacketListener(this.server, connection, dummy, cookie)
				: original.call(server, connection, player, cookie);
	}

	@WrapOperation(method = "respawn", at = @At(value = "NEW", target = "(Lnet/minecraft/server/MinecraftServer;Lnet/minecraft/server/level/ServerLevel;Lcom/mojang/authlib/GameProfile;Lnet/minecraft/server/level/ClientInformation;)Lnet/minecraft/server/level/ServerPlayer;"))
	private ServerPlayer replacePlayer(
			MinecraftServer server,
			ServerLevel level,
			GameProfile profile,
			ClientInformation cli,
			Operation<ServerPlayer> original,
			@Local(argsOnly = true) ServerPlayer player) {
		return player instanceof Dummy dummy
				? new Dummy(server, level, profile, cli, dummy.spawnPosition, dummy.spawnRotation)
				: original.call(server, level, profile, cli);
	}
}
