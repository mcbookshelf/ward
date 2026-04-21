package dev.mcbookshelf.ward.dummy;

import net.minecraft.network.Connection;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import net.minecraft.world.entity.PositionMoveRotation;
import net.minecraft.world.entity.Relative;

import java.util.Set;

public class FakeGamePacketListener extends ServerGamePacketListenerImpl {

    public FakeGamePacketListener(
        final MinecraftServer server,
        final Connection connection,
        final ServerPlayer player,
        final CommonListenerCookie cookie
    ) {
        super(server, connection, player, cookie);
    }

    @Override
    public void teleport(PositionMoveRotation positionMoveRotation, Set<Relative> set) {
        super.teleport(positionMoveRotation, set);
        if (player.level().getPlayerByUUID(player.getUUID()) != null) {
            resetPosition();
            player.level().getChunkSource().move(player);
        }
    }
}
