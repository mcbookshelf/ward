package dev.mcbookshelf.ward.dummy;

import io.netty.channel.ChannelFutureListener;
import net.minecraft.network.Connection;
import net.minecraft.network.PacketListener;
import net.minecraft.network.ProtocolInfo;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.PacketFlow;
import org.jspecify.annotations.Nullable;

public class FakeConnection extends Connection {

    public FakeConnection(PacketFlow receiving) {
        super(receiving);
    }

    @Override
    public void handleDisconnection() {}

    @Override
    public void setReadOnly() {}

    @Override
    public void setListenerForServerboundHandshake(PacketListener packetListener) {}

    @Override
    public <T extends PacketListener> void setupInboundProtocol(ProtocolInfo<T> protocol, T packetListener) {}

    @Override
    public void send(Packet<?> packet, @Nullable ChannelFutureListener listener, boolean flush) {}
}
