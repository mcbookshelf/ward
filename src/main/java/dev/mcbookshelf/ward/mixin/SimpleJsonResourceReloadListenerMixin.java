package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.mojang.serialization.DataResult;
import dev.mcbookshelf.ward.report.ReportEntry;
import dev.mcbookshelf.ward.report.ReportManager;
import net.minecraft.resources.Identifier;
import net.minecraft.server.packs.resources.SimpleJsonResourceReloadListener;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;

import java.util.List;

@Mixin(SimpleJsonResourceReloadListener.class)
public class SimpleJsonResourceReloadListenerMixin {

    @Unique
    private static final List<String> NESTED_REGISTRIES = List.of("worldgen");

    @WrapOperation(method = "lambda$scanDirectory$1", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;[Ljava/lang/Object;)V"))
    private static void catchParseError(Logger logger, String message, Object[] args, Operation<Void> original) {
        original.call(logger, message, args);
        String type = extractType(((Identifier) args[1]).toString());
        ReportManager.report(ReportEntry.error(type, (String) args[0], ((DataResult.Error<?>)args[2]).message()));
    }

    @WrapOperation(method = "scanDirectory(Lnet/minecraft/server/packs/resources/ResourceManager;Lnet/minecraft/resources/FileToIdConverter;Lcom/mojang/serialization/DynamicOps;Lcom/mojang/serialization/Codec;Ljava/util/Map;)V", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;[Ljava/lang/Object;)V"))
    private static void catchException(Logger logger, String message, Object[] args, Operation<Void> original) {
        original.call(logger, message, args);
        String type = extractType(((Identifier) args[1]).toString());
        ReportManager.report(ReportEntry.error(type, (String) args[0], (args[2]).toString()));
    }

    @Unique
    private static String extractType(String path) {
        for (String parent : NESTED_REGISTRIES) {
            if (path.startsWith(parent + "/")) {
                return path.substring(0, path.indexOf('/', parent.length() + 1));
            }
        }
        return path.substring(0, path.indexOf('/'));
    }
}
