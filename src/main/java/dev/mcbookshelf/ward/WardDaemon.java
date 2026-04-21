package dev.mcbookshelf.ward;

import com.google.gson.*;
import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.*;
import io.netty.channel.group.ChannelGroup;
import io.netty.channel.group.DefaultChannelGroup;
import io.netty.channel.nio.NioIoHandler;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.LineBasedFrameDecoder;
import io.netty.handler.codec.string.StringDecoder;
import io.netty.handler.codec.string.StringEncoder;
import io.netty.util.concurrent.GlobalEventExecutor;
import org.jspecify.annotations.Nullable;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class WardDaemon {
    private static final Gson GSON = new Gson();

    private final WardServer server;
    private final Path portFile;
    private final ChannelGroup channels = new DefaultChannelGroup(GlobalEventExecutor.INSTANCE);

    private @Nullable EventLoopGroup bossGroup;
    private @Nullable EventLoopGroup workerGroup;
    private @Nullable Channel serverChannel;

    public WardDaemon(WardServer server, Path portFile) {
        this.server = server;
        this.portFile = portFile;
    }

    public void start() throws Exception {
        bossGroup = new MultiThreadIoEventLoopGroup(1, NioIoHandler.newFactory());
        workerGroup = new MultiThreadIoEventLoopGroup(0, NioIoHandler.newFactory());

        WardDaemon daemon = this;
        ServerBootstrap b = new ServerBootstrap()
            .group(bossGroup, workerGroup)
            .channel(NioServerSocketChannel.class)
            .childHandler(new ChannelInitializer<>() {
                @Override
                protected void initChannel(Channel ch) {
                    ch.pipeline()
                        .addLast(new LineBasedFrameDecoder(1 << 20))   // 1MB max line
                        .addLast(new StringDecoder(StandardCharsets.UTF_8))
                        .addLast(new StringEncoder(StandardCharsets.UTF_8))
                        .addLast(new WardRpcHandler(daemon));
                }
            });

        // Bind to port 0 to let OS choose available port
        serverChannel = b.bind("127.0.0.1", 0).sync().channel();

        // Write port to file for Python to discover
        int port = ((InetSocketAddress) serverChannel.localAddress()).getPort();
        Files.writeString(portFile, String.valueOf(port), StandardCharsets.UTF_8);
    }

    public void stop() throws Exception {
        if (serverChannel != null) serverChannel.close().sync();
        channels.close().sync();
        if (bossGroup != null) bossGroup.shutdownGracefully().sync();
        if (workerGroup != null) workerGroup.shutdownGracefully().sync();
        Files.deleteIfExists(portFile);
    }

    public void broadcast(String type, JsonObject data) {
        data.addProperty("type", type);
        channels.writeAndFlush(GSON.toJson(data) + "\n");
    }

    private final class WardRpcHandler extends SimpleChannelInboundHandler<String> {
        private WardDaemon daemon;

        public WardRpcHandler(WardDaemon daemon) {
            this.daemon = daemon;
            super();
        }

        @Override
        public void channelActive(ChannelHandlerContext ctx) {
            channels.add(ctx.channel());
        }

        @Override
        public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
            ctx.close();
        }

        @Override
        protected void channelRead0(ChannelHandlerContext ctx, String line) {
            JsonObject msg;
            try {
                msg = JsonParser.parseString(line).getAsJsonObject();
            } catch (Exception e) {
                return;
            }

            String type = msg.has("type") ? msg.get("type").getAsString() : null;
            int protocol = msg.has("protocol") ? msg.get("protocol").getAsInt() : 0;
            Channel ch = ctx.channel();

            // Validate protocol version
            if (protocol != 1) {
                sendError(ch, "protocol_mismatch", "Expected protocol 1, got " + protocol);
                return;
            }

            if (type == null) {
                sendError(ch, "invalid_request", "Missing 'type' field");
                return;
            }

            // Execute command on server thread
            server.execute(() -> {
                try {
                    switch (type) {
                        case "status" -> handleStatus(ch);
                        case "test" -> handleTest(ch, msg);
                        case "stop" -> handleStop(ch);
                        default -> sendError(ch, "unknown_command", "Unknown command: " + type);
                    }
                } catch (Exception e) {
                    sendError(ch, "server_error", e.getMessage());
                }
            });
        }

        private void sendError(Channel ch, String code, String message) {
            JsonObject error = new JsonObject();
            error.addProperty("type", "error");
            error.addProperty("code", code);
            error.addProperty("message", message);
            ch.writeAndFlush(GSON.toJson(error) + "\n");
        }

        private void handleStatus(Channel ch) {
            JsonObject response = new JsonObject();
            response.addProperty("type", "status_response");
            response.addProperty("ready", server.isPaused());
            ch.writeAndFlush(GSON.toJson(response) + "\n");
        }

        private void handleTest(Channel ch, JsonObject msg) throws Exception {
            String selector = msg.has("selector") ? msg.get("selector").getAsString() : "*:*";
            server.reloadAndRunTests(selector);
        }

        private void handleStop(Channel ch) {
            server.halt(false);
            new Thread(() -> {
                try {
                    Ward.LOGGER.info("Stopping daemon");
                    daemon.stop();
                    Ward.LOGGER.info("Daemon stopped successfully");

                    Thread serverThread = server.getRunningThread();
                    while (serverThread.isAlive() && server.isRunning()) Thread.sleep(100);

                    System.exit(0);
                } catch (Exception e) {
                    Ward.LOGGER.error("Error during shutdown", e);
                    System.exit(1);
                }
            }, "ward-shutdown").start();
        }
    }
}
