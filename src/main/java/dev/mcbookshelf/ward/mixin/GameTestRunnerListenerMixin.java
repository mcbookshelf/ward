package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import it.unimi.dsi.fastutil.longs.LongSet;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.server.level.ServerLevel;

import dev.mcbookshelf.ward.ForceloadGuard;

/**
 * Keeps {@link ForceloadGuard} chunks out of the runner's cleanup, which otherwise clears every
 * forced chunk of the level. The target class is the runner's anonymous batch listener.
 */
@Mixin(targets = "net.minecraft.gametest.framework.GameTestRunner$1")
public class GameTestRunnerListenerMixin {
	@WrapOperation(method = {"testCompleted", "testFailed"}, at = @At(value = "INVOKE", target = "Lnet/minecraft/server/level/ServerLevel;getForceLoadedChunks()Lit/unimi/dsi/fastutil/longs/LongSet;"))
	private LongSet ward$excludeUserForceloads(ServerLevel level, Operation<LongSet> original) {
		return ForceloadGuard.exclude(level, original.call(level));
	}
}
