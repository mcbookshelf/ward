package dev.mcbookshelf.ward.coverage;

import java.util.Set;

import com.mojang.serialization.MapCodec;

import net.minecraft.util.context.ContextKey;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.slot.SlotCollection;
import net.minecraft.world.item.slot.SlotSource;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.ValidationContext;
import net.minecraft.world.level.storage.loot.functions.LootItemFunction;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraft.world.level.storage.loot.providers.number.floats.ContextFloatProvider;
import net.minecraft.world.level.storage.loot.providers.number.ints.ContextIntProvider;

sealed interface Recording<T> {
	T inner();

	@SuppressWarnings("unchecked")
	static <V> V unwrap(V value) {
		return value instanceof Recording<?> recording ? (V) recording.inner() : value;
	}

	record Condition(LootItemCondition inner, int[] counts) implements LootItemCondition, Recording<LootItemCondition> {
		@Override
		public boolean test(LootContext context) {
			boolean result = this.inner.test(context);
			this.counts[result ? 0 : 1]++;
			return result;
		}

		@Override
		public MapCodec<? extends LootItemCondition> codec() {
			return this.inner.codec();
		}

		@Override
		public Set<ContextKey<?>> getReferencedContextParams() {
			return this.inner.getReferencedContextParams();
		}

		@Override
		public void validate(ValidationContext context) {
			this.inner.validate(context);
		}
	}

	record Function(LootItemFunction inner, int[] counts) implements LootItemFunction, Recording<LootItemFunction> {
		@Override
		public ItemStack apply(ItemStack stack, LootContext context) {
			NodeTable.hit(this.counts);
			return this.inner.apply(stack, context);
		}

		@Override
		public MapCodec<? extends LootItemFunction> codec() {
			return this.inner.codec();
		}

		@Override
		public Set<ContextKey<?>> getReferencedContextParams() {
			return this.inner.getReferencedContextParams();
		}

		@Override
		public void validate(ValidationContext context) {
			this.inner.validate(context);
		}
	}

	record FloatProvider(ContextFloatProvider inner, int[] counts) implements ContextFloatProvider, Recording<ContextFloatProvider> {
		@Override
		public float getFloatUnsafe(LootContext context) throws ArithmeticException {
			NodeTable.hit(this.counts);
			return this.inner.getFloatUnsafe(context);
		}

		@Override
		public MapCodec<? extends ContextFloatProvider> codec() {
			return this.inner.codec();
		}

		@Override
		public void validate(ValidationContext context) {
			this.inner.validate(context);
		}
	}

	record IntProvider(ContextIntProvider inner, int[] counts) implements ContextIntProvider, Recording<ContextIntProvider> {
		@Override
		public int getIntUnsafe(LootContext context) throws ArithmeticException {
			NodeTable.hit(this.counts);
			return this.inner.getIntUnsafe(context);
		}

		@Override
		public MapCodec<? extends ContextIntProvider> codec() {
			return this.inner.codec();
		}

		@Override
		public void validate(ValidationContext context) {
			this.inner.validate(context);
		}
	}

	record Slots(SlotSource inner, int[] counts) implements SlotSource, Recording<SlotSource> {
		@Override
		public SlotCollection provide(LootContext context) {
			NodeTable.hit(this.counts);
			return this.inner.provide(context);
		}

		@Override
		public MapCodec<? extends SlotSource> codec() {
			return this.inner.codec();
		}

		@Override
		public Set<ContextKey<?>> getReferencedContextParams() {
			return this.inner.getReferencedContextParams();
		}

		@Override
		public void validate(ValidationContext context) {
			this.inner.validate(context);
		}
	}
}
