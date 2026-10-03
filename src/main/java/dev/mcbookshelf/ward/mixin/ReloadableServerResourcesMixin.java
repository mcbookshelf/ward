package dev.mcbookshelf.ward.mixin;

import java.util.ArrayList;
import java.util.List;

import com.llamalad7.mixinextras.injector.ModifyReturnValue;
import com.llamalad7.mixinextras.sugar.Local;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.commands.Commands;
import net.minecraft.server.ReloadableServerRegistries;
import net.minecraft.server.ReloadableServerResources;
import net.minecraft.server.packs.resources.PreparableReloadListener;
import net.minecraft.server.permissions.PermissionSet;

import dev.mcbookshelf.ward.test.TestLibrary;

@Mixin(ReloadableServerResources.class)
public abstract class ReloadableServerResourcesMixin {
	@Shadow
	@Final
	private Commands commands;
	@Unique
	private TestLibrary ward$testLibrary;

	@Inject(method = "<init>", at = @At("RETURN"))
	private void createTestLibrary(
			CallbackInfo info,
			@Local(argsOnly = true) ReloadableServerRegistries.LoadResult loadingContext,
			@Local(argsOnly = true) PermissionSet functionCompilationPermissions) {
		this.ward$testLibrary = new TestLibrary(
				loadingContext.lookupWithUpdatedTags(),
				functionCompilationPermissions,
				this.commands.getDispatcher());
	}

	@ModifyReturnValue(method = "listeners", at = @At("RETURN"))
	private List<PreparableReloadListener> addTestLibrary(List<PreparableReloadListener> list) {
		List<PreparableReloadListener> result = new ArrayList<>(list);
		result.add(this.ward$testLibrary);
		return result;
	}
}
