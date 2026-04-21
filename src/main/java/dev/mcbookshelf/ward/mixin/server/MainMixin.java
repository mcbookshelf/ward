package dev.mcbookshelf.ward.mixin.server;

import com.llamalad7.mixinextras.injector.ModifyExpressionValue;
import com.llamalad7.mixinextras.sugar.Local;
import dev.mcbookshelf.ward.Ward;
import net.minecraft.server.Main;
import net.minecraft.server.packs.repository.PackRepository;
import net.minecraft.world.level.storage.LevelStorageSource;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

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
     * Start the test server instead of the normal dedicated server.
     */
    @Inject(method = "main", cancellable = true, at = @At(value = "INVOKE_ASSIGN", target = "Lnet/minecraft/server/packs/repository/ServerPacksSource;createPackRepository(Lnet/minecraft/world/level/storage/LevelStorageSource$LevelStorageAccess;)Lnet/minecraft/server/packs/repository/PackRepository;"))
    private static void runGameTestServer(
        String[] args,
        CallbackInfo info,
        @Local(name = "access") LevelStorageSource.LevelStorageAccess storage,
        @Local(name = "packRepository") PackRepository packRepository
    ) {
        if (Ward.ENABLED) {
            Ward.runWardServer(storage, packRepository);
            info.cancel();
        }
    }
}
