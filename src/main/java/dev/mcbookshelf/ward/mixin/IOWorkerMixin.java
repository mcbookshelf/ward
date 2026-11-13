package dev.mcbookshelf.ward.mixin;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.function.Supplier;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.StreamTagVisitor;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.storage.IOWorker;
import net.minecraft.world.level.chunk.storage.RegionStorageInfo;

import dev.mcbookshelf.ward.Ward;

/**
 * A daemon never writes its world. It reads the folders a saved world came with;
 * a flat world has none, so its chunks skip the IO thread.
 */
@Mixin(IOWorker.class)
public class IOWorkerMixin {
	@Unique
	private boolean empty;

	@Inject(method = "<init>", at = @At("TAIL"))
	private void findFolder(RegionStorageInfo info, Path dir, boolean sync, CallbackInfo callback) {
		this.empty = Ward.DAEMON && !Files.isDirectory(dir);
	}

	@Inject(method = "store(Lnet/minecraft/world/level/ChunkPos;Ljava/util/function/Supplier;)Ljava/util/concurrent/CompletableFuture;", at = @At("HEAD"), cancellable = true)
	private void skipStore(ChunkPos pos, Supplier<CompoundTag> supplier, CallbackInfoReturnable<CompletableFuture<Void>> info) {
		if (Ward.DAEMON) {
			info.setReturnValue(CompletableFuture.completedFuture(null));
		}
	}

	@Inject(method = "loadAsync", at = @At("HEAD"), cancellable = true)
	private void skipLoad(ChunkPos pos, CallbackInfoReturnable<CompletableFuture<Optional<CompoundTag>>> info) {
		if (this.empty) {
			info.setReturnValue(CompletableFuture.completedFuture(Optional.empty()));
		}
	}

	@Inject(method = "scanChunk", at = @At("HEAD"), cancellable = true)
	private void skipScan(ChunkPos pos, StreamTagVisitor visitor, CallbackInfoReturnable<CompletableFuture<Void>> info) {
		if (this.empty) {
			info.setReturnValue(CompletableFuture.completedFuture(null));
		}
	}
}
