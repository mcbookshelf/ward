package dev.mcbookshelf.ward.test;

import java.util.HashMap;
import java.util.Map;

import it.unimi.dsi.fastutil.longs.LongOpenHashSet;
import it.unimi.dsi.fastutil.longs.LongSet;
import org.jspecify.annotations.Nullable;

import net.minecraft.gametest.framework.GameTestBatch;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.Level;

public final class ForceloadGuard {
	private final Map<ResourceKey<Level>, LongSet> preRun = new HashMap<>();

	public interface Holder {
		@Nullable ForceloadGuard ward$forceloadGuard();
	}

	public ForceloadGuard(MinecraftServer server) {
		for (ServerLevel level : server.getAllLevels()) {
			this.preRun.put(level.dimension(), new LongOpenHashSet(level.getForceLoadedChunks()));
		}
	}

	public LongSet exclude(ServerLevel level, GameTestBatch batch, LongSet forced) {
		LongSet areas = new LongOpenHashSet();
		batch.gameTestInfos().forEach(test -> test.getTestInstanceBlockEntity()
				.getStructureBoundingBox()
				.intersectingChunks()
				.forEach(pos -> areas.add(pos.pack())));

		LongSet result = new LongOpenHashSet(forced);
		result.retainAll(areas);
		result.removeAll(this.preRun.getOrDefault(level.dimension(), LongSet.of()));
		return result;
	}
}
