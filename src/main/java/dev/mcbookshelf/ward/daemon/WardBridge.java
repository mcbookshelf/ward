package dev.mcbookshelf.ward.daemon;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.Channel;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.MultiThreadIoEventLoopGroup;
import io.netty.channel.SimpleChannelInboundHandler;
import io.netty.channel.nio.NioIoHandler;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.LineBasedFrameDecoder;
import io.netty.handler.codec.string.StringDecoder;
import io.netty.handler.codec.string.StringEncoder;
import org.jspecify.annotations.Nullable;

import net.minecraft.SharedConstants;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.Ward;

public final class WardBridge {
	private static final int PROTOCOL = 1;

	private static final Gson GSON = new Gson();
	private static final int LAST_WRITE_TIMEOUT_SECONDS = 5;

	private final Path portFile;
	private final WardDaemon daemon;

	private volatile @Nullable Channel client;

	public WardBridge(WardDaemon daemon, Path portFile) {
		this.daemon = daemon;
		this.portFile = portFile;
	}

	public void start() throws Exception {
		EventLoopGroup group = new MultiThreadIoEventLoopGroup(1, NioIoHandler.newFactory());

		Channel serverChannel = new ServerBootstrap()
				.group(group)
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
				})
				.bind("127.0.0.1", 0)
				.sync()
				.channel();

		int port = ((InetSocketAddress) serverChannel.localAddress()).getPort();
		Files.writeString(portFile, String.valueOf(port), StandardCharsets.UTF_8);
		portFile.toFile().deleteOnExit();
	}

	public void send(String type, JsonObject data) {
		Channel ch = this.client;

		if (ch != null) {
			write(ch, type, data);
		}
	}

	public void sendError(String code, String message) {
		send("error", createError(code, message));
	}

	public void sendLastError(String code, String message) {
		Channel ch = this.client;

		if (ch != null) {
			write(ch, "error", createError(code, message)).awaitUninterruptibly(LAST_WRITE_TIMEOUT_SECONDS, TimeUnit.SECONDS);
		}
	}

	public boolean clientGone() {
		Channel ch = this.client;
		return ch != null && !ch.isActive();
	}

	public void release() {
		this.client = null;
	}

	private static JsonObject createError(String code, String message) {
		JsonObject error = new JsonObject();
		error.addProperty("code", code);
		error.addProperty("message", message);
		return error;
	}

	private static ChannelFuture write(Channel ch, String type, JsonObject data) {
		data.addProperty("type", type);
		return ch.writeAndFlush(GSON.toJson(data) + "\n");
	}

	private final class WardHandler extends SimpleChannelInboundHandler<String> {
		@Override
		public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
			if (cause instanceof IOException) {
				Ward.LOGGER.debug("Closing bridge connection: {}", cause.getMessage());
			} else {
				Ward.LOGGER.warn("Closing bridge connection", cause);
			}

			ctx.close();
		}

		@Override
		protected void channelRead0(ChannelHandlerContext ctx, String line) {
			Channel ch = ctx.channel();
			JsonObject msg;
			String type;
			int protocol;

			try {
				msg = JsonParser.parseString(line).getAsJsonObject();
				type = msg.has("type") ? msg.get("type").getAsString() : null;
				protocol = msg.has("protocol") ? msg.get("protocol").getAsInt() : 0;
			} catch (RuntimeException e) {
				replyError(ch, "invalid_request", "Malformed request: " + Messages.describe(e));
				return;
			}

			if (protocol != PROTOCOL) {
				replyError(ch, "protocol_mismatch", "Expected protocol " + PROTOCOL + ", got " + protocol);
				return;
			}

			if (type == null) {
				replyError(ch, "invalid_request", "Missing 'type' field");
				return;
			}

			try {
				switch (type) {
					case "status" -> handleStatus(ch);
					case "test" -> handleRun(ch, TestRunner.Options.parse(msg));
					case "bench" -> handleRun(ch, BenchRunner.Options.parse(msg));
					case "stop" -> daemon.shutdown();
					default -> replyError(ch, "unknown_command", "Unknown command: " + type);
				}
			} catch (RuntimeException e) {
				replyError(ch, "server_error", Messages.describe(e));
			}
		}

		private void replyError(Channel ch, String code, String message) {
			write(ch, "error", createError(code, message));
		}

		private void handleStatus(Channel ch) {
			JsonObject response = new JsonObject();
			response.addProperty("ready", daemon.isIdle());
			response.addProperty("protocol", PROTOCOL);
			response.addProperty("mod", Ward.version());
			response.addProperty("minecraft", SharedConstants.getCurrentVersion().name());
			write(ch, "status", response);
		}

		private void handleRun(Channel ch, Runner.Options options) {
			if (!daemon.isIdle()) {
				replyError(ch, "server_error", "Tests are already running");
				return;
			}

			client = ch;
			daemon.run(options);
		}
	}
}
