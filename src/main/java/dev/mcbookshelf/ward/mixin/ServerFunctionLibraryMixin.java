package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import dev.mcbookshelf.ward.report.ReportEntry;
import dev.mcbookshelf.ward.report.ReportManager;
import net.minecraft.server.ServerFunctionLibrary;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

@Mixin(ServerFunctionLibrary.class)
public class ServerFunctionLibraryMixin {

    @WrapOperation(method = "lambda$reload$7", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"))
    private static void catchFunctionError(Logger logger, String message, Object id, Object e, Operation<Void> original) {
        original.call(logger, message, id, e);
        String error = ((Exception) e).getMessage().replaceFirst("^[A-Za-z0-9.]+Exception: ", "");
        ReportManager.report(ReportEntry.error("minecraft:function", id.toString(), error));
    }
}
