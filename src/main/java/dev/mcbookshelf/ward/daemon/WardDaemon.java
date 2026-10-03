package dev.mcbookshelf.ward.daemon;

import java.nio.file.Path;
import java.util.Objects;

import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.MixinEnvironment;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.packs.repository.PackRepository;
import net.minecraft.server.packs.repository.ServerPacksSource;
import net.minecraft.world.level.storage.LevelStorageSource;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.Ward;
import dev.mcbookshelf.ward.coverage.Coverage;
import dev.mcbookshelf.ward.test.ChatRecorder;

public final class WardDaemon {
	private final WardBridge bridge;
	private final LevelStorageSource source;
	private final String levelId;
	private volatile boolean busy;

	private WardDaemon(LevelStorageSource source, String levelId) {
		this.source = source;
		this.levelId = levelId;
		this.bridge = new WardBridge(this, Path.of(Objects.requireNonNull(Ward.PORT_FILE)).toAbsolutePath());
	}

	public static void launch(String levelId) {
		try {
			if (Ward.AUDIT) MixinEnvironment.getCurrentEnvironment().audit();
			WardDaemon daemon = new WardDaemon(LevelStorageSource.createDefault(Path.of(".")), levelId);
			Reporter.register(daemon.bridge::send);
			daemon.bridge.start();
			Ward.LOGGER.info("Ward daemon started");
		} catch (Exception e) {
			Ward.LOGGER.error("Failed to start Ward daemon", e);
			System.exit(1);
		}
	}

	boolean isIdle() {
		return !this.busy;
	}

	void run(Runner.Options options) {
		this.busy = true;
		new Thread(() -> boot(options), "Ward bootstrap").start();
	}

	void shutdown() {
		System.exit(0);
	}

	boolean clientGone() {
		return this.bridge.clientGone();
	}

	void runEnded(@Nullable Throwable failure) {
		ChatRecorder.clear();
		Coverage.reset(false);

		if (failure != null) {
			Ward.LOGGER.error("Failed to run tests", failure);
			this.bridge.sendError("server_error", Messages.describe(failure));
		}

		this.bridge.release();
		this.busy = false;
	}

	void crashed(Throwable failure) {
		Ward.LOGGER.error("Test server crashed, stopping the daemon", failure);
		this.bridge.sendLastError("server_error", Messages.describe(failure));
		System.exit(1);
	}

	private void boot(Runner.Options options) {
		try {
			Coverage.reset(options instanceof TestRunner.Options tests && tests.coverage());
			LevelStorageSource.LevelStorageAccess storage = this.source.validateAndCreateAccess(this.levelId);

			try {
				PackRepository packs = ServerPacksSource.createPackRepository(storage);
				MinecraftServer.spin(thread -> WardServer.create(this, thread, storage, packs, options));
			} catch (Throwable e) {
				storage.close();
				throw e;
			}
		} catch (Throwable e) {
			runEnded(e);
		}
	}
}
