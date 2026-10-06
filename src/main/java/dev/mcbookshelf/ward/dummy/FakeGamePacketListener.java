package dev.mcbookshelf.ward.dummy;

import java.util.Set;

import net.fabricmc.fabric.impl.networking.UntrackedPacketListener;

import net.minecraft.network.Connection;
import net.minecraft.network.DisconnectionDetails;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import net.minecraft.world.entity.PositionMoveRotation;
import net.minecraft.world.entity.Relative;

/**
 * Untracked: Fabric only releases the network addon of a tracked listener when its channel closes.
 * A dummy has no channel, so it would pin its whole server for the life of the JVM.
 */
public class FakeGamePacketListener extends ServerGamePacketListenerImpl implements UntrackedPacketListener {
	public FakeGamePacketListener(
			MinecraftServer server,
			Connection connection,
			ServerPlayer player,
			CommonListenerCookie cookie) {
		super(server, connection, player, cookie);
	}

	@Override
	public void disconnect(DisconnectionDetails details) {
		this.onDisconnect(details);
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
