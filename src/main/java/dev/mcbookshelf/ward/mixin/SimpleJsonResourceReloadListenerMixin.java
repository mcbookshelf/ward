package dev.mcbookshelf.ward.mixin;

import java.util.List;
import java.util.Map;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.DynamicOps;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.resources.FileToIdConverter;
import net.minecraft.resources.Identifier;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.SimpleJsonResourceReloadListener;

import dev.mcbookshelf.ward.DataCoverage;
import dev.mcbookshelf.ward.report.Diagnostic;
import dev.mcbookshelf.ward.report.ReportManager;

/**
 * Reports data files that fail to load as diagnostics.
 *
 * <p>Both intercepted log calls receive {@code (id, location, error)} where id and location are
 * Identifiers ("Couldn't parse data file '{}' from '{}'").
 */
@Mixin(SimpleJsonResourceReloadListener.class)
public class SimpleJsonResourceReloadListenerMixin {
	@Unique
	private static final List<String> NESTED_REGISTRIES = List.of("worldgen");

	@WrapOperation(method = "lambda$scanDirectory$1", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;[Ljava/lang/Object;)V"))
	private static void catchParseError(
			Logger logger,
			String message,
			Object[] args,
			Operation<Void> original) {
		original.call(logger, message, args);
		String type = "minecraft:" + extractType(((Identifier) args[1]).getPath());
		ReportManager.report(Diagnostic.error(type, args[0].toString(), ((DataResult.Error<?>) args[2]).message()));
	}

	@WrapOperation(method = "scanDirectory(Lnet/minecraft/server/packs/resources/ResourceManager;Lnet/minecraft/resources/FileToIdConverter;Lcom/mojang/serialization/DynamicOps;Lcom/mojang/serialization/Codec;Ljava/util/Map;)V", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;[Ljava/lang/Object;)V"))
	private static void catchException(
			Logger logger,
			String message,
			Object[] args,
			Operation<Void> original) {
		original.call(logger, message, args);
		String type = "minecraft:" + extractType(((Identifier) args[1]).getPath());
		ReportManager.report(Diagnostic.error(type, args[0].toString(), Diagnostic.describe((Throwable) args[2])));
	}

	/**
	 * Tags the element decode with its file, so nodes decoded from its JSON attribute their coverage to it.
	 * Loot data and advancements load through here rather than the registry loader.
	 */
	@WrapOperation(method = "scanDirectory(Lnet/minecraft/server/packs/resources/ResourceManager;Lnet/minecraft/resources/FileToIdConverter;Lcom/mojang/serialization/DynamicOps;Lcom/mojang/serialization/Codec;Ljava/util/Map;)V", at = @At(value = "INVOKE", target = "Lcom/mojang/serialization/Codec;parse(Lcom/mojang/serialization/DynamicOps;Ljava/lang/Object;)Lcom/mojang/serialization/DataResult;"))
	private static DataResult<?> tagElementDecode(
			Codec<?> codec,
			DynamicOps<?> ops,
			Object json,
			Operation<DataResult<?>> original,
			@Local(argsOnly = true) FileToIdConverter lister,
			@Local Map.Entry<Identifier, Resource> entry) {
		String id = lister.fileToId(entry.getKey()).toString();
		DataCoverage.beginElement("minecraft:" + lister.prefix(), id, entry.getValue(), json);

		try {
			DataResult<?> result = original.call(codec, ops, json);
			result.result().ifPresent(DataCoverage::completeElement);
			return result;
		} finally {
			DataCoverage.endElement();
		}
	}

	/**
	 * Extracts the registry directory from a resource file path (e.g. "loot_table/broken.json" gives
	 * "loot_table").
	 */
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
