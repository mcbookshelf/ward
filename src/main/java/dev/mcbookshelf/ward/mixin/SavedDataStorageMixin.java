package dev.mcbookshelf.ward.mixin;

import java.util.concurrent.CompletableFuture;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.world.level.storage.SavedDataStorage;

import dev.mcbookshelf.ward.Ward;

@Mixin(SavedDataStorage.class)
public class SavedDataStorageMixin {
	@Inject(method = "scheduleSave", at = @At("HEAD"), cancellable = true)
	private void skipSave(CallbackInfoReturnable<CompletableFuture<?>> info) {
		if (Ward.DAEMON) {
			info.setReturnValue(CompletableFuture.completedFuture(null));
		}
	}
}
