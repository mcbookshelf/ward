package dev.mcbookshelf.ward.accessor;

import java.util.function.Predicate;

import net.minecraft.core.HolderOwner;
import net.minecraft.resources.ResourceKey;

/**
 * Implemented by {@code MappedRegistryMixin}.
 */
public interface MappedRegistryAccessor<T> {
	void ward$unfreeze();

	void ward$adopt(HolderOwner<T> owner);

	void ward$clearByPredicate(Predicate<ResourceKey<T>> predicate);
}
