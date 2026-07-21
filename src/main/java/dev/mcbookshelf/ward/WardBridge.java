package dev.mcbookshelf.ward;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.MultiThreadIoEventLoopGroup;
import io.netty.channel.SimpleChannelInboundHandler;
import io.netty.channel.group.ChannelGroup;
import io.netty.channel.group.DefaultChannelGroup;
import io.netty.channel.nio.NioIoHandler;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.LineBasedFrameDecoder;
import io.netty.handler.codec.string.StringDecoder;
import io.netty.handler.codec.string.StringEncoder;
import io.netty.util.concurrent.GlobalEventExecutor;
import org.jspecify.annotations.Nullable;

public final class WardBridge {
	private static final Gson GSON = new Gson();

	private final Path portFile;
	private final WardDaemon daemon;
	private final ChannelGroup channels = new DefaultChannelGroup(GlobalEventExecutor.INSTANCE);

	private @Nullable EventLoopGroup bossGroup;
	private @Nullable EventLoopGroup workerGroup;
	private @Nullable Channel serverChannel;

	public WardBridge(WardDaemon daemon, Path portFile) {
		this.daemon = daemon;
		this.portFile = portFile;
	}

	public void start() throws Exception {
		bossGroup = new MultiThreadIoEventLoopGroup(1, NioIoHandler.newFactory());
		workerGroup = new MultiThreadIoEventLoopGroup(0, NioIoHandler.newFactory());

		ServerBootstrap b = new ServerBootstrap()
				.group(bossGroup, workerGroup)
				.channel(NioServerSocketChannel.class)
				.childHandler(new ChannelInitializer<>() {
					@Override
					protected void initChannel(Channel ch) {
						ch.pipeline()
								.addLast(new LineBasedFrameDecoder(1 << 20))
								.addLast(new StringDecoder(StandardCharsets.UTF_8))
								.addLast(new StringEncoder(StandardCharsets.UTF_8))
								.addLast(new WardHandler());
					}
				});

		serverChannel = b.bind("127.0.0.1", 0).sync().channel();

		// Write the port to a file so the Python client can find it. Also delete
		// the file if the JVM exits for any reason other than a normal stop
		int port = ((InetSocketAddress) serverChannel.localAddress()).getPort();
		Files.writeString(portFile, String.valueOf(port), StandardCharsets.UTF_8);
		portFile.toFile().deleteOnExit();
	}

	public void stop() throws Exception {
		if (serverChannel != null) {
			serverChannel.close().sync();
		}

		channels.close().sync();

		if (bossGroup != null) {
			bossGroup.shutdownGracefully().sync();
		}

		if (workerGroup != null) {
			workerGroup.shutdownGracefully().sync();
		}

		Files.deleteIfExists(portFile);
	}

	/**
	 * Broadcasts an event to all connected clients. Note that {@code data} is modified to carry
	 * the event type.
	 */
	public void broadcast(String type, JsonObject data) {
		data.addProperty("type", type);
		channels.writeAndFlush(encode(data));
	}

	public void broadcastError(String code, String message) {
		broadcast("error", createError(code, message));
	}

	private static JsonObject createError(String code, String message) {
		JsonObject error = new JsonObject();
		error.addProperty("code", code);
		error.addProperty("message", message);
		return error;
	}

	private static String encode(JsonObject data) {
		return GSON.toJson(data) + "\n";
	}

	private final class WardHandler extends SimpleChannelInboundHandler<String> {
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

			if (protocol != 1) {
				sendError(ch, "protocol_mismatch", "Expected protocol 1, got " + protocol);
				return;
			}

			if (type == null) {
				sendError(ch, "invalid_request", "Missing 'type' field");
				return;
			}

			try {
				switch (type) {
					case "status" -> handleStatus(ch);
					case "test" -> handleTest(ch, msg);
					case "stop" -> daemon.shutdown();
					default -> sendError(ch, "unknown_command", "Unknown command: " + type);
				}
			} catch (Exception e) {
				sendError(ch, "server_error", e.getMessage());
			}
		}

		private void sendError(Channel ch, String code, String message) {
			JsonObject error = createError(code, message);
			error.addProperty("type", "error");
			ch.writeAndFlush(encode(error));
		}

		private void handleStatus(Channel ch) {
			JsonObject response = new JsonObject();
			response.addProperty("type", "status");
			response.addProperty("ready", daemon.isIdle());
			ch.writeAndFlush(encode(response));
		}

		private void handleTest(Channel ch, JsonObject msg) throws Exception {
			String selector = msg.has("selector") ? msg.get("selector").getAsString() : "*:*";
			daemon.runTests(selector);
		}
	}
}
