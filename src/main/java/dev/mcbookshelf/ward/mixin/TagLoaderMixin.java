package dev.mcbookshelf.ward.mixin;

import java.util.List;
import java.util.Map;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.resources.Identifier;
import net.minecraft.tags.TagLoader;

import dev.mcbookshelf.ward.LoadDiagnostic;
import dev.mcbookshelf.ward.ReportManager;

@Mixin(TagLoader.class)
public class TagLoaderMixin {
	@Shadow
	@Final
	private String directory;

	@Unique
	private static final ThreadLocal<String> ward$currentDirectory = new ThreadLocal<>();

	@Inject(method = "build", at = @At("HEAD"))
	private void captureDirectory(
			Map<Identifier, List<TagLoader.EntryWithSource>> builders,
			CallbackInfoReturnable<Map<Identifier, List<?>>> cir) {
		ward$currentDirectory.set(this.directory);
	}

	@Inject(method = "build", at = @At("RETURN"))
	private void clearDirectory(
			Map<Identifier, List<TagLoader.EntryWithSource>> builders,
			CallbackInfoReturnable<Map<Identifier, List<?>>> cir) {
		ward$currentDirectory.remove();
	}

	/**
	 * Reports tag files that fail to read. The log args carry the id first and the exception last.
	 */
	@WrapOperation(method = "load", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;[Ljava/lang/Object;)V"))
	private void catchLoadError(
			Logger logger,
			String message,
			Object[] args,
			Operation<Void> original) {
		original.call(logger, message, args);

		if (args.length > 0 && args[args.length - 1] instanceof Throwable throwable) {
			String error = LoadDiagnostic.describe(throwable);
			ReportManager.report(LoadDiagnostic.error("minecraft:" + this.directory, args[0].toString(), error));
		}
	}

	/**
	 * Reports tags with missing references, from the static "Couldn't load tag" lambda in
	 * {@code build}. The lambda only captures the id, which is why {@link #directory} goes
	 * through a ThreadLocal.
	 */
	@WrapOperation(method = "lambda$build$2", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"))
	private static void catchBuildError(
			Logger logger,
			String message,
			Object id,
			Object references,
			Operation<Void> original) {
		original.call(logger, message, id, references);
		String error = String.format("Missing references: %s", references);
		ReportManager.report(LoadDiagnostic.error("minecraft:" + ward$currentDirectory.get(), id.toString(), error));
	}
}
