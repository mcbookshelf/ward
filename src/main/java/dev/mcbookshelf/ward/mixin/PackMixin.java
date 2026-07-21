package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.server.packs.PackLocationInfo;
import net.minecraft.server.packs.repository.Pack;

import dev.mcbookshelf.ward.LoadDiagnostic;
import dev.mcbookshelf.ward.ReportManager;

@Mixin(Pack.class)
public class PackMixin {
	@WrapOperation(method = "readPackMetadata", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;warn(Ljava/lang/String;Ljava/lang/Throwable;)V"))
	private static void catchPackParseError(
			Logger logger,
			String message,
			Throwable throwable,
			Operation<Void> original,
			@Local(argsOnly = true) PackLocationInfo location) {
		original.call(logger, message, throwable);
		ReportManager.report(LoadDiagnostic.error("pack.mcmeta", location.id(), LoadDiagnostic.describe(throwable)));
	}

	/**
	 * Reports pack.mcmeta validation errors. The {@code Object} params match the wrapped log
	 * call: pack location, then the exception.
	 */
	@WrapOperation(method = "readPackMetadata", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;warn(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"))
	private static void catchPackValidationError(
			Logger logger,
			String message,
			Object location,
			Object throwable,
			Operation<Void> original) {
		original.call(logger, message, location, throwable);
		ReportManager.report(LoadDiagnostic.error("pack.mcmeta", location.toString(), LoadDiagnostic.describe((Throwable) throwable)));
	}
}
