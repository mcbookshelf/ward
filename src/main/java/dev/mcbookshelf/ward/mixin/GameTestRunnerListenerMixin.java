package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import it.unimi.dsi.fastutil.longs.LongSet;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.gametest.framework.GameTestBatch;
import net.minecraft.gametest.framework.GameTestRunner;
import net.minecraft.server.level.ServerLevel;

import dev.mcbookshelf.ward.test.ForceloadGuard;

@Mixin(targets = "net.minecraft.gametest.framework.GameTestRunner$1")
public class GameTestRunnerListenerMixin {
	@Shadow
	@Final
	private GameTestBatch val$currentBatch;

	@Shadow
	@Final
	private GameTestRunner this$0;

	@WrapOperation(method = {"testCompleted", "testFailed"}, require = 2, allow = 2, at = @At(value = "INVOKE", target = "Lnet/minecraft/server/level/ServerLevel;getForceLoadedChunks()Lit/unimi/dsi/fastutil/longs/LongSet;"))
	private LongSet excludeGuardedChunks(ServerLevel level, Operation<LongSet> original) {
		LongSet forced = original.call(level);
		ForceloadGuard guard = ((ForceloadGuard.Holder) this.this$0).ward$forceloadGuard();
		return guard != null ? guard.exclude(level, this.val$currentBatch, forced) : forced;
	}
}
