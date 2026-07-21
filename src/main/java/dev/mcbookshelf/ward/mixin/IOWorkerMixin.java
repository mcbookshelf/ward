package dev.mcbookshelf.ward.mixin;

import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.function.Supplier;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.StreamTagVisitor;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.storage.IOWorker;

import dev.mcbookshelf.ward.Ward;

/**
 * Cuts region storage (chunks, POI, entities) off from the disk in daemon mode, since worlds only
 * live in memory. Reads are skipped too because they would create empty region files (opened rw).
 */
@Mixin(IOWorker.class)
public class IOWorkerMixin {
	@Inject(
			method = "store(Lnet/minecraft/world/level/ChunkPos;Ljava/util/function/Supplier;)Ljava/util/concurrent/CompletableFuture;",
			at = @At("HEAD"),
			cancellable = true)
	private void skipStore(ChunkPos pos, Supplier<CompoundTag> supplier, CallbackInfoReturnable<CompletableFuture<Void>> cir) {
		if (Ward.ENABLED) {
			cir.setReturnValue(CompletableFuture.completedFuture(null));
		}
	}

	@Inject(method = "loadAsync", at = @At("HEAD"), cancellable = true)
	private void skipLoad(ChunkPos pos, CallbackInfoReturnable<CompletableFuture<Optional<CompoundTag>>> cir) {
		if (Ward.ENABLED) {
			cir.setReturnValue(CompletableFuture.completedFuture(Optional.empty()));
		}
	}

	@Inject(method = "scanChunk", at = @At("HEAD"), cancellable = true)
	private void skipScan(ChunkPos pos, StreamTagVisitor visitor, CallbackInfoReturnable<CompletableFuture<Void>> cir) {
		if (Ward.ENABLED) {
			cir.setReturnValue(CompletableFuture.completedFuture(null));
		}
	}
}
