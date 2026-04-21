package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import com.mojang.authlib.GameProfile;
import dev.mcbookshelf.ward.dummy.Dummy;
import dev.mcbookshelf.ward.dummy.FakeGamePacketListener;
import net.minecraft.network.Connection;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.PlayerAdvancements;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import net.minecraft.server.players.PlayerList;
import net.minecraft.stats.ServerStatsCounter;
import net.minecraft.world.level.storage.LevelResource;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Prevents dummy data pollution and provides isolated stats/advancements.
 * <p>
 * Dummies skip disk saves, use separate stats/advancements in ward/ subdirectory,
 * inject FakeGamePacketListener, and respawn as Dummy instances.
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

    @Inject(method = "getPlayerStats", at = @At("HEAD"), cancellable = true)
    private void getDummyStats(net.minecraft.world.entity.player.Player player, CallbackInfoReturnable<ServerStatsCounter> ci) {
        if (player instanceof Dummy) {
            ci.setReturnValue(this.ward$stats.computeIfAbsent(
                player.getUUID(), uuid -> new ServerStatsCounter(
                    this.server,
                    this.server.getWorldPath(STATS_DIR).resolve(uuid + ".json"))));
        }
    }

    @Inject(method = "getPlayerAdvancements", at = @At("HEAD"), cancellable = true)
    private void getDummyAdvancements(ServerPlayer player, CallbackInfoReturnable<PlayerAdvancements> ci) {
        if (player instanceof Dummy) {
            PlayerAdvancements result = this.ward$advancements.computeIfAbsent(
                player.getUUID(), uuid -> new PlayerAdvancements(
                    this.server.getFixerUpper(),
                    (PlayerList) (Object) this,
                    this.server.getAdvancements(),
                    this.server.getWorldPath(ADVANCEMENTS_DIR).resolve(uuid + ".json"),
                    player));
            // Update player reference because respawn creates new Dummy instance
            result.setPlayer(player);
            ci.setReturnValue(result);
        }
    }

    @Redirect(method = "placeNewPlayer", at = @At(value = "NEW", target = "(Lnet/minecraft/server/MinecraftServer;Lnet/minecraft/network/Connection;Lnet/minecraft/server/level/ServerPlayer;Lnet/minecraft/server/network/CommonListenerCookie;)Lnet/minecraft/server/network/ServerGamePacketListenerImpl;"))
    private ServerGamePacketListenerImpl replacePacketListener(MinecraftServer server, Connection connection, ServerPlayer player, CommonListenerCookie cookie) {
        return player instanceof Dummy dummy
            ? new FakeGamePacketListener(this.server, connection, dummy, cookie)
            : new ServerGamePacketListenerImpl(this.server, connection, player, cookie);
    }

    @WrapOperation(method = "respawn", at = @At(value = "NEW", target = "(Lnet/minecraft/server/MinecraftServer;Lnet/minecraft/server/level/ServerLevel;Lcom/mojang/authlib/GameProfile;Lnet/minecraft/server/level/ClientInformation;)Lnet/minecraft/server/level/ServerPlayer;"))
    private ServerPlayer replacePlayer(MinecraftServer server, ServerLevel level, GameProfile profile, ClientInformation cli, Operation<ServerPlayer> original, @Local(ordinal = 0, argsOnly = true) ServerPlayer player) {
        return player instanceof Dummy dummy ? new Dummy(
            server,
            level,
            profile,
            cli,
            dummy.ward$originalSpawnPosition,
            dummy.ward$originalSpawnRotation
        ) : original.call(server, level, profile, cli);
    }
}
