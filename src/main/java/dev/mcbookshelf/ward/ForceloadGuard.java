package dev.mcbookshelf.ward;

import java.util.HashMap;
import java.util.Map;

import it.unimi.dsi.fastutil.longs.LongOpenHashSet;
import it.unimi.dsi.fastutil.longs.LongSet;

import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.Level;

/**
 * Tracks the chunks that were force-loaded by data packs rather than by the test runner, so the runner's cleanup can leave them alone.
 */
public final class ForceloadGuard {
	// Chunks forced before the run, spared even when inside test areas
	private static final Map<ResourceKey<Level>, LongSet> preRun = new HashMap<>();
	// Everything still forced at batch end, minus that batch's test areas
	private static final Map<ResourceKey<Level>, LongSet> kept = new HashMap<>();

	private ForceloadGuard() {
	}

	/**
	 * Starts guarding the chunks currently forced in every dimension.
	 */
	public static void reset(MinecraftServer server) {
		preRun.clear();
		kept.clear();

		for (ServerLevel level : server.getAllLevels()) {
			preRun.put(level.dimension(), new LongOpenHashSet(level.getForceLoadedChunks()));
		}
	}

	/**
	 * Replaces the guarded set of the level's dimension.
	 */
	public static void update(ServerLevel level, LongSet chunks) {
		kept.put(level.dimension(), chunks);
	}

	/**
	 * Removes the guarded chunks from the given set.
	 */
	public static LongSet exclude(ServerLevel level, LongSet chunks) {
		LongSet result = new LongOpenHashSet(chunks);
		LongSet keptChunks = kept.get(level.dimension());
		LongSet preRunChunks = preRun.get(level.dimension());

		if (keptChunks != null) {
			result.removeAll(keptChunks);
		}

		if (preRunChunks != null) {
			result.removeAll(preRunChunks);
		}

		return result;
	}
}
