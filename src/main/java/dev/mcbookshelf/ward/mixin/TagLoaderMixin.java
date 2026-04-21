package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import dev.mcbookshelf.ward.report.ReportEntry;
import dev.mcbookshelf.ward.report.ReportManager;
import net.minecraft.resources.Identifier;
import net.minecraft.tags.TagLoader;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.util.List;
import java.util.Map;

@Mixin(TagLoader.class)
public class TagLoaderMixin {

    @Shadow
    @Final
    private String directory;

    @Unique
    private static final ThreadLocal<String> ward$currentDirectory = new ThreadLocal<>();

    /**
     * Capture the directory at the start of build() so the lambda can access it
     */
    @Inject(method = "build", at = @At("HEAD"))
    private void captureDirectory(Map<Identifier, List<TagLoader.EntryWithSource>> builders, CallbackInfoReturnable<Map<Identifier, List<?>>> cir) {
        ward$currentDirectory.set(this.directory);
    }

    /**
     * Clear the ThreadLocal after build() completes
     */
    @Inject(method = "build", at = @At("RETURN"))
    private void clearDirectory(Map<Identifier, List<TagLoader.EntryWithSource>> builders, CallbackInfoReturnable<Map<Identifier, List<?>>> cir) {
        ward$currentDirectory.remove();
    }

    /**
     * Intercept error logging in load() method when reading tag files fails.
     */
    @WrapOperation(method = "load", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;[Ljava/lang/Object;)V"))
    private void catchLoadError(Logger logger, String message, Object[] args, Operation<Void> original) {
        original.call(logger, message, args);
        String error = ((Exception) args[3]).getMessage().replaceFirst("^[A-Za-z0-9.]+Exception: ", "");
        ReportManager.report(ReportEntry.error("minecraft:" + this.directory, args[0].toString(), error));
    }

    /**
     * Intercept error logging in build() method when tags have missing references.
     */
    @WrapOperation(method = "lambda$build$2", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"))
    private static void catchBuildError(Logger logger, String message, Object id, Object references, Operation<Void> original) {
        original.call(logger, message, id, references);
        String error = String.format("Missing references: %s", references);
        ReportManager.report(ReportEntry.error("minecraft:" + ward$currentDirectory.get(), id.toString(), error));
    }
}
