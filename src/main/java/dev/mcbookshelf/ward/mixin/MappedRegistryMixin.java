package dev.mcbookshelf.ward.mixin;

import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import it.unimi.dsi.fastutil.objects.ObjectList;
import it.unimi.dsi.fastutil.objects.Reference2IntMap;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.core.Holder;
import net.minecraft.core.MappedRegistry;
import net.minecraft.core.RegistrationInfo;
import net.minecraft.core.Registry;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;

import dev.mcbookshelf.ward.LoadDiagnostic;
import dev.mcbookshelf.ward.ReportManager;
import dev.mcbookshelf.ward.Ward;
import dev.mcbookshelf.ward.accessor.MappedRegistryAccessor;

/**
 * Allows unfreezing and clearing registries, so TEST_INSTANCE and TEST_FUNCTION can be reloaded
 * without a server restart.
 */
@Mixin(MappedRegistry.class)
public abstract class MappedRegistryMixin<T> implements MappedRegistryAccessor<T> {
	@Shadow
	@Final
	private ObjectList<Holder.Reference<T>> byId;
	@Shadow
	@Final
	private Reference2IntMap<T> toId;
	@Shadow
	@Final
	private Map<Identifier, Holder.Reference<T>> byLocation;
	@Shadow
	@Final
	private Map<ResourceKey<T>, Holder.Reference<T>> byKey;
	@Shadow
	@Final
	private Map<T, Holder.Reference<T>> byValue;
	@Shadow
	@Final
	private Map<ResourceKey<T>, RegistrationInfo> registrationInfos;
	@Shadow
	private boolean frozen;

	@Shadow
	MappedRegistry.TagSet<T> allTags;

	@Shadow
	public abstract ResourceKey<? extends Registry<T>> key();

	/**
	 * Reports references to missing elements and lets the registry freeze anyway. Vanilla would
	 * throw instead, dropping the whole registry and crashing later lookups.
	 */
	@WrapOperation(method = "freeze", at = @At(value = "INVOKE", target = "Ljava/util/List;isEmpty()Z", ordinal = 0))
	private boolean ward$reportUnboundValues(List<Identifier> unboundEntries, Operation<Boolean> original) {
		if (!original.call(unboundEntries)) {
			String registry = this.key().identifier().toString();
			unboundEntries.forEach(id -> {
				// Skipping the vanilla throw also skips its message, so log the entries too
				Ward.LOGGER.error("Unbound value in registry {}: {} is referenced but never defined", registry, id);
				ReportManager.report(LoadDiagnostic.error(
						registry, id.toString(), "Referenced but not defined in any loaded data pack"));
			});
		}

		return true;
	}

	@Override
	@Unique
	public void ward$unfreeze() {
		this.frozen = false;
		this.allTags = MappedRegistry.TagSet.unbound();
	}

	@Override
	@Unique
	public void ward$clearByPredicate(Predicate<ResourceKey<T>> predicate) {
		List<ResourceKey<T>> keysToRemove = byKey.keySet().stream().filter(predicate).toList();
		keysToRemove.forEach(this::removeEntry);
		rebuildIdMappings();
	}

	@Unique
	private void removeEntry(ResourceKey<T> key) {
		Holder.Reference<T> holder = byKey.remove(key);

		if (holder != null && holder.isBound()) {
			T value = holder.value();
			byLocation.remove(key.identifier());
			byValue.remove(value);
			toId.removeInt(value);
			registrationInfos.remove(key);
		}
	}

	@Unique
	private void rebuildIdMappings() {
		byId.clear();
		toId.clear();

		for (Holder.Reference<T> holder : byKey.values()) {
			if (holder.isBound()) {
				int newId = byId.size();
				byId.add(holder);
				toId.put(holder.value(), newId);
			}
		}
	}
}
