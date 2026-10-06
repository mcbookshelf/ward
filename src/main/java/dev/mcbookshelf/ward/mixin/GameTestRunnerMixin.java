package dev.mcbookshelf.ward.mixin;

import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.gametest.framework.GameTestRunner;
import net.minecraft.server.MinecraftServer;

import dev.mcbookshelf.ward.test.ForceloadGuard;

@Mixin(GameTestRunner.class)
public class GameTestRunnerMixin implements ForceloadGuard.Holder {
	@Shadow
	@Final
	private MinecraftServer server;

	@Unique
	private @Nullable ForceloadGuard ward$forceloadGuard;

	/**
	 * What is forced before the run is not the runner's to release.
	 */
	@Inject(method = "start", at = @At("HEAD"))
	private void snapshotForcedChunks(CallbackInfo info) {
		this.ward$forceloadGuard = new ForceloadGuard(this.server);
	}

	@Override
	public @Nullable ForceloadGuard ward$forceloadGuard() {
		return this.ward$forceloadGuard;
	}
}
