package dev.mcbookshelf.ward.mixin;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Predicate;
import java.util.stream.Collectors;

import it.unimi.dsi.fastutil.objects.ObjectList;
import it.unimi.dsi.fastutil.objects.Reference2IntMap;
import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.core.Holder;
import net.minecraft.core.HolderOwner;
import net.minecraft.core.HolderSet;
import net.minecraft.core.MappedRegistry;
import net.minecraft.core.RegistrationInfo;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.tags.TagKey;

import dev.mcbookshelf.ward.Reporter;
import dev.mcbookshelf.ward.Ward;
import dev.mcbookshelf.ward.test.MappedRegistryAccessor;

@Mixin(MappedRegistry.class)
public abstract class MappedRegistryMixin<T> implements MappedRegistryAccessor<T>, HolderOwner<T> {
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
	@Final
	private Map<TagKey<T>, HolderSet.Named<T>> frozenTags;
	@Shadow
	private boolean frozen;

	@Shadow
	private MappedRegistry.TagSet<T> allTags;

	@Shadow
	public abstract ResourceKey<? extends Registry<T>> key();

	@Unique
	private @Nullable HolderOwner<T> ward$adopted;

	@Override
	public boolean canSerialize(HolderOwner<T> owner) {
		return owner == this || owner == this.ward$adopted;
	}

	@Override
	@Unique
	public void ward$unfreeze() {
		this.frozen = false;
		this.allTags = MappedRegistry.TagSet.unbound();
	}

	@Override
	@Unique
	public void ward$adopt(HolderOwner<T> owner) {
		this.ward$adopted = owner;
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

	@Inject(method = "freeze", at = @At("HEAD"))
	private void dropDanglingReferences(CallbackInfoReturnable<Registry<T>> info) {
		if (this.frozen) {
			return;
		}

		String registry = this.key().identifier().toString();
		Set<Holder.Reference<T>> dangling = this.byKey.values().stream()
				.filter(holder -> !this.byLocation.containsKey(holder.key().identifier()))
				.collect(Collectors.toSet());

		for (Holder.Reference<T> holder : dangling) {
			Identifier id = holder.key().identifier();
			Ward.LOGGER.error("Unbound value in registry {}: {} is referenced but never defined", registry, id);
			Reporter.loadError(registry, id.toString(), "Referenced but not defined in any loaded data pack");
			this.byKey.remove(holder.key());
		}

		String kind = "minecraft:" + Registries.tagsDirPath(this.key());

		for (HolderSet.Named<T> tag : this.frozenTags.values()) {
			if (!tag.isBound()) {
				Ward.LOGGER.error("Unbound tag in registry {}: #{} is referenced but never defined", registry, tag.key().location());
				Reporter.loadError(kind, tag.key().location().toString(), "Referenced but not defined in any loaded data pack");
				tag.bind(List.of());
			} else if (!dangling.isEmpty() && tag.stream().anyMatch(dangling::contains)) {
				tag.bind(tag.stream().filter(holder -> !dangling.contains(holder)).toList());
			}
		}
	}
}
