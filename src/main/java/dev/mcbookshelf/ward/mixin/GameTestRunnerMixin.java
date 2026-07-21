package dev.mcbookshelf.ward.mixin;

import java.util.Objects;

import com.google.common.collect.ImmutableList;
import it.unimi.dsi.fastutil.longs.LongArraySet;
import it.unimi.dsi.fastutil.longs.LongSet;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.gametest.framework.GameTestBatch;
import net.minecraft.gametest.framework.GameTestBatchListener;
import net.minecraft.gametest.framework.GameTestInfo;
import net.minecraft.gametest.framework.GameTestRunner;
import net.minecraft.server.level.ServerLevel;

import dev.mcbookshelf.ward.ForceloadGuard;

/**
 * Snapshots user forceloads into {@link ForceloadGuard} when a run starts and after each batch.
 * {@code GameTestRunnerListenerMixin} then keeps those chunks out of the runner's cleanup.
 */
@Mixin(GameTestRunner.class)
public class GameTestRunnerMixin {
	@Shadow
	private ImmutableList<GameTestBatch> batches;

	@Inject(method = "start", at = @At("HEAD"))
	private void snapshotForcedChunks(CallbackInfo info) {
		ServerLevel level = this.ward$anyLevel();

		if (level == null) {
			return;
		}

		ForceloadGuard.reset(level.getServer());

		// Batch listeners run before the cleanup, so this is the last chance
		// to see which chunks stayed forced
		((GameTestRunner) (Object) this).addListener(new GameTestBatchListener() {
			@Override
			public void testBatchStarting(GameTestBatch batch) {
			}

			@Override
			public void testBatchFinished(GameTestBatch batch) {
				ServerLevel batchLevel = GameTestRunnerMixin.this.ward$levelOf(batch);

				if (batchLevel == null) {
					return;
				}

				LongSet forced = new LongArraySet(batchLevel.getForceLoadedChunks());
				batch.gameTestInfos().forEach(test -> test.getTestInstanceBlockEntity()
						.getStructureBoundingBox()
						.intersectingChunks()
						.forEach(pos -> forced.remove(pos.pack())));
				ForceloadGuard.update(batchLevel, forced);
			}
		});
	}

	@Unique
	private ServerLevel ward$anyLevel() {
		return this.batches.stream()
				.map(this::ward$levelOf)
				.filter(Objects::nonNull)
				.findFirst()
				.orElse(null);
	}

	@Unique
	private ServerLevel ward$levelOf(GameTestBatch batch) {
		return batch.gameTestInfos().stream()
				.findFirst()
				.map(GameTestInfo::getLevel)
				.orElse(null);
	}
}
