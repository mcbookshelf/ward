package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.server.ServerFunctionLibrary;

import dev.mcbookshelf.ward.Reporter;

@Mixin(ServerFunctionLibrary.class)
public class ServerFunctionLibraryMixin {
	/**
	 * The lambda of reload that logs "Failed to load function".
	 */
	@WrapOperation(method = "lambda$reload$7", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"))
	private static void catchFunctionError(
			Logger logger,
			String message,
			Object id,
			Object e,
			Operation<Void> original) {
		original.call(logger, message, id, e);
		Reporter.loadError("minecraft:function", id.toString(), (Throwable) e);
	}
}
