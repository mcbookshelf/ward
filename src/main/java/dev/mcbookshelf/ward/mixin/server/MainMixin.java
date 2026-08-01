package dev.mcbookshelf.ward.mixin.server;

import com.llamalad7.mixinextras.injector.ModifyExpressionValue;
import com.llamalad7.mixinextras.sugar.Local;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.server.Main;
import net.minecraft.world.level.storage.LevelStorageSource;

import dev.mcbookshelf.ward.Ward;
import dev.mcbookshelf.ward.WardDaemon;

@Mixin(Main.class)
public class MainMixin {
	@ModifyExpressionValue(method = "main", at = @At(value = "INVOKE", target = "Lnet/minecraft/server/Eula;hasAgreedToEULA()Z"))
	private static boolean isEulaAgreedTo(boolean isEulaAgreedTo) {
		return Ward.ENABLED || isEulaAgreedTo;
	}

	/**
	 * Exit with a non-zero exit code when the server fails to start.
	 */
	@Inject(method = "main", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Lorg/slf4j/Marker;Ljava/lang/String;Ljava/lang/Throwable;)V", shift = At.Shift.AFTER))
	private static void exitOnError(CallbackInfo info) {
		if (Ward.ENABLED) {
			System.exit(-1);
		}
	}

	/**
	 * Export the command tree instead of starting the server.
	 */
	@Inject(method = "main", cancellable = true, at = @At(value = "INVOKE", target = "Lnet/minecraft/server/Eula;hasAgreedToEULA()Z"))
	private static void exportCommandTree(CallbackInfo info) {
		if (Ward.GENERATE_COMMANDS != null) {
			Ward.exportCommandTree();
			info.cancel();
		}
	}

	/**
	 * Start the test daemon instead of the normal dedicated server.
	 */
	@Inject(method = "main", cancellable = true, at = @At(value = "INVOKE_ASSIGN", target = "Lnet/minecraft/server/packs/repository/ServerPacksSource;createPackRepository(Lnet/minecraft/world/level/storage/LevelStorageSource$LevelStorageAccess;)Lnet/minecraft/server/packs/repository/PackRepository;"))
	private static void runWardDaemon(
			String[] args,
			CallbackInfo info,
			@Local LevelStorageSource source,
			@Local LevelStorageSource.LevelStorageAccess storage) {
		if (Ward.ENABLED) {
			WardDaemon.launch(source, storage);
			info.cancel();
		}
	}
}
