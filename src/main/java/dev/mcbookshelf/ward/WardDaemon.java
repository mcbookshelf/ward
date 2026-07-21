package dev.mcbookshelf.ward;

import java.nio.file.Path;
import java.util.Objects;

import org.jspecify.annotations.Nullable;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.packs.repository.PackRepository;
import net.minecraft.server.packs.repository.ServerPacksSource;
import net.minecraft.world.level.storage.LevelStorageSource;

/**
 * The long-lived test daemon. It keeps the JVM warm and serves test runs over the TCP bridge.
 * Each run boots a fresh {@link WardServer}, because dynamic registries are only read during
 * world load and cannot be reloaded on a live server.
 */
public final class WardDaemon {
	private final WardBridge bridge;
	private final LevelStorageSource source;
	private final String levelId;

	private @Nullable WardServer server;
	private volatile boolean busy;

	private WardDaemon(LevelStorageSource source, String levelId) {
		this.source = source;
		this.levelId = levelId;
		this.bridge = new WardBridge(this, Path.of(Objects.requireNonNull(Ward.DAEMON)).toAbsolutePath());
	}

	/**
	 * Creates and starts the daemon in place of the vanilla dedicated server.
	 */
	public static void launch(LevelStorageSource source, LevelStorageSource.LevelStorageAccess storage) {
		try {
			String levelId = storage.getLevelId();
			storage.close();

			WardDaemon daemon = new WardDaemon(source, levelId);
			daemon.bridge.start();
			ReportManager.register(daemon.bridge);
			Ward.LOGGER.info("Ward daemon started");
		} catch (Exception e) {
			// Propagates to Main.main, whose error handling exits with a non-zero code
			throw new RuntimeException("Failed to start Ward daemon", e);
		}
	}

	/**
	 * Returns true when no test run is active.
	 */
	public boolean isIdle() {
		return !this.busy;
	}

	/**
	 * Boots a fresh server and runs tests matching the given selection.
	 */
	public synchronized void runTests(String selection) throws Exception {
		if (this.busy) throw new Exception("Tests are already running");
		this.busy = true;
		new Thread(() -> boot(selection), "Ward bootstrap").start();
	}

	/**
	 * Broadcasts an asynchronous failure to connected clients.
	 */
	public void reportFailure(Throwable failure) {
		Ward.LOGGER.error("Failed to run tests", failure);
		bridge.broadcastError("server_error", LoadDiagnostic.describe(failure));
	}

	/**
	 * Stops the daemon: closes the bridge, halts any active server and exits the process.
	 */
	public void shutdown() {
		new Thread(() -> {
			try {
				bridge.stop();
				WardServer current;

				synchronized (this) {
					current = this.server;
				}

				if (current != null) {
					current.halt(true);
				}

				System.exit(0);
			} catch (Exception e) {
				Ward.LOGGER.error("Error during shutdown", e);
				System.exit(1);
			}
		}, "Ward shutdown").start();
	}

	/**
	 * Called from the server thread once a server instance has fully stopped.
	 */
	synchronized void serverExited() {
		this.server = null;
		this.busy = false;
	}

	/**
	 * Loads the world and spins up a server for this run. The server starts the tests itself and
	 * halts once they complete.
	 */
	private void boot(String selection) {
		try {
			LevelStorageSource.LevelStorageAccess storage = this.source.validateAndCreateAccess(this.levelId);

			try {
				PackRepository packs = ServerPacksSource.createPackRepository(storage);
				WardServer started = MinecraftServer.spin(thread -> WardServer.create(this, thread, storage, packs, selection));

				synchronized (this) {
					this.server = started;
				}
			} catch (Exception e) {
				// The server takes over the storage lock once it starts, until then we hold it
				storage.close();
				throw e;
			}
		} catch (Exception e) {
			reportFailure(e);
			serverExited();
		}
	}
}
