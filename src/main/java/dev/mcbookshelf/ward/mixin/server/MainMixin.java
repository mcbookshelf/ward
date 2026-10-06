package dev.mcbookshelf.ward.mixin.server;

import java.nio.file.Path;

import com.llamalad7.mixinextras.sugar.Local;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.server.Main;
import net.minecraft.server.dedicated.DedicatedServerSettings;

import dev.mcbookshelf.ward.Ward;
import dev.mcbookshelf.ward.daemon.WardDaemon;

@Mixin(Main.class)
public class MainMixin {
	/**
	 * The EULA check is the last step before vanilla creates what only a dedicated server needs.
	 */
	@Inject(method = "main", cancellable = true, allow = 1, at = @At(value = "INVOKE", target = "Lnet/minecraft/server/Eula;hasAgreedToEULA()Z"))
	private static void runWard(String[] args, CallbackInfo info, @Local DedicatedServerSettings settings) {
		if (Ward.GENERATE_COMMANDS != null) {
			Ward.exportCommandTree(Path.of(Ward.GENERATE_COMMANDS));
			info.cancel();
		} else if (Ward.DAEMON) {
			WardDaemon.launch(settings.getProperties().levelName);
			info.cancel();
		}
	}
}
