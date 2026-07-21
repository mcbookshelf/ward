package dev.mcbookshelf.ward.mixin;

import java.util.ArrayList;
import java.util.List;

import com.llamalad7.mixinextras.injector.ModifyReturnValue;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.commands.Commands;
import net.minecraft.core.Registry;
import net.minecraft.core.component.DataComponentInitializers;
import net.minecraft.server.ReloadableServerRegistries;
import net.minecraft.server.ReloadableServerResources;
import net.minecraft.server.packs.resources.PreparableReloadListener;
import net.minecraft.server.permissions.PermissionSet;
import net.minecraft.world.flag.FeatureFlagSet;

import dev.mcbookshelf.ward.TestLibrary;

/**
 * Adds {@link TestLibrary} to the /reload listeners.
 */
@Mixin(ReloadableServerResources.class)
public abstract class ReloadableServerResourcesMixin {
	@Shadow
	@Final
	private Commands commands;
	@Unique
	private TestLibrary testLibrary;

	@Inject(method = "<init>", at = @At("RETURN"))
	private void init(
			ReloadableServerRegistries.LoadResult loadingContext,
			FeatureFlagSet enabledFeatures,
			Commands.CommandSelection commandSelection,
			List<Registry.PendingTags<?>> postponedTags,
			PermissionSet functionCompilationPermissions,
			List<DataComponentInitializers.PendingComponents<?>> newComponents,
			CallbackInfo ci) {
		this.testLibrary = new TestLibrary(
				loadingContext.lookupWithUpdatedTags(),
				functionCompilationPermissions,
				this.commands.getDispatcher());
	}

	@ModifyReturnValue(method = "listeners", at = @At("RETURN"))
	private List<PreparableReloadListener> listeners(List<PreparableReloadListener> list) {
		List<PreparableReloadListener> result = new ArrayList<>(list);
		result.add(this.testLibrary);
		return result;
	}
}
