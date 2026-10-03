package dev.mcbookshelf.ward.dummy;

import io.netty.channel.ChannelFutureListener;
import org.jspecify.annotations.Nullable;

import net.minecraft.network.Connection;
import net.minecraft.network.PacketListener;
import net.minecraft.network.ProtocolInfo;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.PacketFlow;

public class FakeConnection extends Connection {
	public FakeConnection(PacketFlow receiving) {
		super(receiving);
	}

	@Override
	public <T extends PacketListener> void setupInboundProtocol(ProtocolInfo<T> protocol, T packetListener) {
	}

	@Override
	public void send(Packet<?> packet, @Nullable ChannelFutureListener listener, boolean flush) {
	}

	@Override
	public void flushChannel() {
	}
}
