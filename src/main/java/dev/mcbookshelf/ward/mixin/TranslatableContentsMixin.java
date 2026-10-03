package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;

import net.minecraft.locale.Language;
import net.minecraft.network.chat.contents.TranslatableContents;

@Mixin(TranslatableContents.class)
public class TranslatableContentsMixin {
	@Unique
	private volatile @Nullable Language ward$decomposed;

	/**
	 * Vanilla marks the text of a message as built before it is, so a second thread reading it then gets an empty text.
	 */
	@WrapMethod(method = "decompose")
	private void decomposeOnce(Operation<Void> original) {
		Language current = Language.getInstance();

		if (this.ward$decomposed != current) {
			synchronized (this) {
				original.call();
				this.ward$decomposed = current;
			}
		}
	}
}
