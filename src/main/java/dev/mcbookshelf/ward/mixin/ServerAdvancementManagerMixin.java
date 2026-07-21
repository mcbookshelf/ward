package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.server.ServerAdvancementManager;

import dev.mcbookshelf.ward.LoadDiagnostic;
import dev.mcbookshelf.ward.ReportManager;

@Mixin(ServerAdvancementManager.class)
public class ServerAdvancementManagerMixin {
	@WrapOperation(method = "validate", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;warn(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"))
	private static void catchAdvancementValidationError(
			Logger logger,
			String message,
			Object id,
			Object report,
			Operation<Void> original) {
		original.call(logger, message, id, report);
		ReportManager.report(LoadDiagnostic.warn("minecraft:advancement", id.toString(), report.toString()));
	}
}
