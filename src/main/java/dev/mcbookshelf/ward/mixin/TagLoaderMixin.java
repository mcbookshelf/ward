package dev.mcbookshelf.ward.mixin;

import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

import com.llamalad7.mixinextras.injector.ModifyReturnValue;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import com.mojang.datafixers.util.Either;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.core.Registry;
import net.minecraft.resources.Identifier;
import net.minecraft.tags.TagEntry;
import net.minecraft.tags.TagLoader;

import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.test.TestRegistries;

@Mixin(TagLoader.class)
public class TagLoaderMixin {
	@Shadow
	@Final
	private String directory;

	@WrapOperation(method = "load", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;error(Ljava/lang/String;[Ljava/lang/Object;)V"))
	private void catchLoadError(
			Logger logger,
			String message,
			Object[] args,
			Operation<Void> original) {
		original.call(logger, message, args);

		if (args.length > 0 && args[args.length - 1] instanceof Throwable throwable) {
			Reporter.loadError("minecraft:" + this.directory, args[0].toString(), throwable);
		}
	}

	/**
	 * The lambda of build that resolves each tag.
	 */
	@WrapOperation(method = "lambda$build$1", allow = 1, at = @At(value = "INVOKE", target = "Lnet/minecraft/tags/TagLoader;tryBuildTag(Lnet/minecraft/tags/TagEntry$Lookup;Ljava/util/List;)Lcom/mojang/datafixers/util/Either;"))
	private Either<List<TagLoader.EntryWithSource>, List<?>> reportMissingReferences(
			TagLoader<?> loader,
			TagEntry.Lookup<?> lookup,
			List<TagLoader.EntryWithSource> entries,
			Operation<Either<List<TagLoader.EntryWithSource>, List<?>>> original,
			@Local(argsOnly = true) Identifier id) {
		Either<List<TagLoader.EntryWithSource>, List<?>> result = original.call(loader, lookup, entries);
		result.ifLeft(missing -> Reporter.loadError(
				"minecraft:" + this.directory,
				id.toString(),
				"Missing references: " + missing.stream().map(Objects::toString).collect(Collectors.joining(", "))));
		return result;
	}

	/**
	 * Vanilla resolves these tags before the reload and applies them after it,
	 * which would bind them to holders TestRegistries has already replaced.
	 */
	@ModifyReturnValue(method = "loadTagsForExistingRegistries", at = @At("RETURN"))
	private static List<Registry.PendingTags<?>> dropReloadedRegistries(List<Registry.PendingTags<?>> tags) {
		return tags.stream().filter(pending -> !TestRegistries.owns(pending.key())).toList();
	}
}
