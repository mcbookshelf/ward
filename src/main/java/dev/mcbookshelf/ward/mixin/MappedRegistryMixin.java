package dev.mcbookshelf.ward.mixin;

import it.unimi.dsi.fastutil.objects.ObjectList;
import it.unimi.dsi.fastutil.objects.Reference2IntMap;
import net.minecraft.core.Holder;
import net.minecraft.core.MappedRegistry;
import net.minecraft.core.RegistrationInfo;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;

import dev.mcbookshelf.ward.accessor.MappedRegistryAccessor;

import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/**
 * Mixin to allow unfreezing and modifying MappedRegistry.
 * <p>
 * This enables dynamic reloading of TEST_INSTANCE and TEST_FUNCTION
 * when data packs are reloaded, without requiring a server restart.
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

    @Override
    @Unique
    public void ward$unfreeze() {
        this.frozen = false;
        this.allTags = MappedRegistry.TagSet.unbound();
    }

    @Override
    @Unique
    public void ward$clearByPredicate(Predicate<ResourceKey<T>> predicate) {
        List<ResourceKey<T>> keysToRemove = byKey.keySet().stream()
            .filter(predicate)
            .toList();
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
