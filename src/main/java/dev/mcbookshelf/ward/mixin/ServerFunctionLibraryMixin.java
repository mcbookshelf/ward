package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.server.ServerFunctionLibrary;

import dev.mcbookshelf.ward.LoadDiagnostic;
import dev.mcbookshelf.ward.ReportManager;

@Mixin(ServerFunctionLibrary.class)
public class ServerFunctionLibraryMixin {
	/**
	 * Reports functions that fail to compile, from the "Failed to load function" handler lambda
	 * in {@code reload}.
	 */
	@WrapOperation(method = "lambda$reload$7", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"))
	private static void catchFunctionError(
			Logger logger,
			String message,
			Object id,
			Object e,
			Operation<Void> original) {
		original.call(logger, message, id, e);
		ReportManager.report(LoadDiagnostic.error("minecraft:function", id.toString(), LoadDiagnostic.describe((Throwable) e)));
	}
}
