package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.server.packs.PackLocationInfo;
import net.minecraft.server.packs.repository.Pack;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.Reporter;

@Mixin(Pack.class)
public class PackMixin {
	@WrapOperation(method = "readPackMetadata", allow = 1, at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;warn(Ljava/lang/String;Ljava/lang/Throwable;)V"))
	private static void catchPackParseError(
			Logger logger,
			String message,
			Throwable throwable,
			Operation<Void> original,
			@Local(argsOnly = true) PackLocationInfo location) {
		original.call(logger, message, throwable);
		Reporter.loadWarning("pack.mcmeta", location.id(), Messages.describe(throwable));
	}

	@WrapOperation(method = "readPackMetadata", allow = 1, at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;warn(Ljava/lang/String;Ljava/lang/Object;)V"))
	private static void catchMissingMetadata(Logger logger, String message, Object id, Operation<Void> original) {
		original.call(logger, message, id);
		Reporter.loadError("pack.mcmeta", id.toString(), "Missing pack section");
	}

	@WrapOperation(method = "readPackMetadata", allow = 1, at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;warn(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"))
	private static void catchPackValidationError(
			Logger logger,
			String message,
			Object location,
			Object throwable,
			Operation<Void> original) {
		original.call(logger, message, location, throwable);
		Reporter.loadError("pack.mcmeta", location.toString(), (Throwable) throwable);
	}
}
