package dev.mcbookshelf.ward.accessor;

import java.util.function.Predicate;

import net.minecraft.resources.ResourceKey;

/**
 * Duck interface implemented by {@code MappedRegistryMixin} to mutate frozen registries.
 */
public interface MappedRegistryAccessor<T> {
	void ward$unfreeze();

	void ward$clearByPredicate(Predicate<ResourceKey<T>> predicate);
}
